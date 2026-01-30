"""
hypothesistesting.py

Hypothesis test for "no predictive power" using known per-bet win probabilities
(from offered odds) to compute the null mean and variance exactly (Bernoulli mix),
then a CLT Z-test on total P/L.

Under H0 (efficient odds), win probability p_i = 1 / offered_odds_i, and we expect
to lose due to comission over the long run.
"""

import csv
import math
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt


fair_odds: List[float] = []
offered_odds: List[float] = []
results: List[str] = []
overrounds: List[float] = []
commissions: List[float] = []

BACKTEST_RESULTS_PATH = Path("backtestresult.csv")
if BACKTEST_RESULTS_PATH.exists():
    with BACKTEST_RESULTS_PATH.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            # Skip header if present
            if row[0].strip().lower() == "fair_odds":
                continue
            fair_odds.append(float(row[0]))
            offered_odds.append(float(row[1]))
            commissions.append(float(row[2]))
            results.append(row[3].strip())
            overrounds.append(float(row[4]))

# boost odds to account for overround
for i, odds in enumerate(offered_odds):
    offered_odds[i] = overrounds[i] / (1 / odds)
    
def betting_p_value(
    offered_odds: List[float],
    results: List[str],
    commissions: List[float]
) -> float:
    """
    Returns one-sided p-value for positive edge using known p_i = 1 / odds.

    :param list offered_odds: the given odds that you backed at
    :param list results: the outcomes for the bets
    :param list commissions: per-bet commission values
    """

    if len(offered_odds) != len(results) or len(offered_odds) != len(commissions):
        raise ValueError("Lists must have the same length")

    S_obs = 0.0
    S_mu = 0.0
    S_var = 0.0

    for odds, res, commission in zip(offered_odds, results, commissions):
        if odds <= 1.0:
            raise ValueError("Odds must be > 1")

        # Null win probability
        p = 1.0 / odds

        # Payoffs
        win_profit = (odds - 1.0) * (1.0 - commission)
        lose_profit = -1.0

        # Observed P/L
        x = win_profit if res.upper() == "W" else lose_profit
        S_obs += x

        # Null mean
        mu = p * win_profit + (1.0 - p) * lose_profit
        S_mu += mu

        # Null variance
        ex2 = p * win_profit**2 + (1.0 - p) * lose_profit**2
        var = ex2 - mu**2
        S_var += var

    if S_var <= 0:
        raise RuntimeError("Zero variance encountered")

    Z = (S_obs - S_mu) / math.sqrt(S_var)

    # Standard normal CDF
    Phi = 0.5 * (1.0 + math.erf(Z / math.sqrt(2.0)))

    # One-sided p-value
    p_value = 1.0 - Phi
    return p_value


def betting_p_values_over_time(
    offered_odds: List[float],
    results: List[str],
    commissions: List[float]
) -> List[float]:
    """
    Returns cumulative one-sided p-values after each row.
    """
    if len(offered_odds) != len(results) or len(offered_odds) != len(commissions):
        raise ValueError("Lists must have the same length")

    p_values: List[float] = []
    S_obs = 0.0
    S_mu = 0.0
    S_var = 0.0

    for odds, res, commission in zip(offered_odds, results, commissions):
        if odds <= 1.0:
            raise ValueError("Odds must be > 1")

        p = 1.0 / odds
        win_profit = (odds - 1.0) * (1.0 - commission)
        lose_profit = -1.0

        x = win_profit if res.upper() == "W" else lose_profit
        S_obs += x

        mu = p * win_profit + (1.0 - p) * lose_profit
        S_mu += mu

        ex2 = p * win_profit**2 + (1.0 - p) * lose_profit**2
        var = ex2 - mu**2
        S_var += var

        if S_var <= 0:
            raise RuntimeError("Zero variance encountered")

        Z = (S_obs - S_mu) / math.sqrt(S_var)
        Phi = 0.5 * (1.0 + math.erf(Z / math.sqrt(2.0)))
        p_values.append(1.0 - Phi)

    return p_values

if __name__ == "__main__":
    p_value = betting_p_value(offered_odds, results, commissions)
    print(f"{p_value:.4f}")

    if (
        len(fair_odds) != len(offered_odds)
        or len(fair_odds) != len(results)
        or len(fair_odds) != len(commissions)
    ):
        raise ValueError("Lists must have the same length")

    predicted_return = 0.0
    actual_return = 0.0
    h0_return = 0.0
    cumulative_pl: List[float] = []

    for fair, odds, res, commission in zip(fair_odds, offered_odds, results, commissions):
        if odds <= 1.0 or fair <= 1.0:
            raise ValueError("Odds must be > 1")

        win_profit = (odds - 1.0) * (1.0 - commission)
        lose_profit = -1.0

        x = win_profit if res.upper() == "W" else lose_profit
        actual_return += x
        cumulative_pl.append(actual_return)

        p_pred = 1.0 / fair
        predicted_return += p_pred * win_profit + (1.0 - p_pred) * lose_profit

        p_null = 1.0 / odds
        h0_return += p_null * win_profit + (1.0 - p_null) * lose_profit

    print(f"Predicted returns (after commission): {predicted_return:.4f}")
    print(f"Actual returns: {actual_return:.4f}")
    print(f"Returns under H0 (after commission): {h0_return:.4f}")

    p_values = betting_p_values_over_time(offered_odds, results, commissions)
    fig, axes = plt.subplots(2, 1, figsize=(10, 9), sharex=True)

    axes[0].plot(range(1, len(p_values) + 1), p_values, label="Cumulative p-value")
    axes[0].axhline(0.05, color="red", linestyle="--", linewidth=1, label="0.05")
    axes[0].set_ylabel("P-value")
    axes[0].set_title("P-value (cumulative) after each bet")
    axes[0].set_ylim(bottom=0)
    axes[0].legend()

    axes[1].plot(range(1, len(cumulative_pl) + 1), cumulative_pl, label="Cumulative P/L")
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1].set_xlabel("Row")
    axes[1].set_ylabel("P/L")
    axes[1].set_title("Actual P/L (cumulative) after each bet")
    axes[1].legend()

    plt.tight_layout()
    plt.show()