"""
hypothesistesting.py

Hypothesis test for "no predictive power" using known per-bet win probabilities
(from offered odds) to compute the null mean and variance exactly (Bernoulli mix),
then a CLT Z-test on total P/L.

Under H0 (efficient odds), win probability p_i = 1 / offered_odds_i, and we expect
to lose due to comission over the long run.
"""

import math
from typing import List, Optional, Tuple

# =========================
# INPUTS
# =========================

# Offered odds for each bet (decimal odds)
offered_odds: List[float] = [
    2.00, 2.30, 2.20, 2.76, 2.34, 1.88, 1.98, 2.34, 
    2.36, 1.87, 2.84, 1.70, 2.28, 2.30, 1.99, 1.89, 
    2.34, 2.42, 2.20, 2.04, 2.00, 2.24, 1.77
]

# Observed outcomes: 'W' for win, 'L' for loss
# Must be same length as offered_odds
results: List[str] = [
    "L", "W", "W", "L", "W", "W", "W", "W", 
    "W", "W", "L", "W", "W", "L", "W", "W", 
    "W", "L", "L", "W", "W", "W", "W"
]

def betting_p_value(
    offered_odds: List[float],
    results: List[str],
    commission: float = 0.08
) -> float:
    """
    Returns one-sided p-value for positive edge using known p_i = 1 / odds.

    :param list offered_odds: the given odds that you backed at
    :param list results: the outcomes for the bets
    :param float commission: the relevant commission on betfair (default = 0.08)
    """

    if len(offered_odds) != len(results):
        raise ValueError("Lists must have the same length")

    S_obs = 0.0
    S_mu = 0.0
    S_var = 0.0

    for odds, res in zip(offered_odds, results):
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

if __name__ == "__main__":
    p_value = betting_p_value(offered_odds, results, 0.08)
    print(f"{p_value:.4f}")