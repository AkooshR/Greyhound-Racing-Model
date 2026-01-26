# Written by ChatGPT
"""
bet_model_pvalue.py

Hypothesis test for "no predictive power" using known per-bet win probabilities
(from offered odds) to compute the null mean and variance exactly (Bernoulli mix),
then a CLT Z-test on total P/L.

Assumptions:
- Each bet i is $1 stake (or you provide stakes array).
- Under H0 (efficient odds), win probability p_i = 1 / offered_odds_i.
- Commission c is applied to net winnings only (common for exchanges):
    win profit = (offered_odds_i - 1) * stake_i * (1 - c)
    loss profit = - stake_i
- Bets are treated as independent for the CLT variance sum.

Outputs:
- Z statistic and one-sided p-value for positive edge
- Two-sided p-value
- Observed vs expected total P/L and per-bet averages
"""

import math
from typing import List, Optional, Tuple

# =========================
# INPUTS (EDIT THESE)
# =========================

# Offered odds for each bet (decimal odds)
offered_odds: List[float] = [
    2, 2.3, 2.2, 2.76, 2.34, 1.88, 1.98, 2.34, 2.36, 1.87, 2.84, 1.7, 2.28, 2.3, 1.99, 1.89, 2.34, 2.42, 2.2, 2.04, 
]

# Observed outcomes: 'W' for win, 'L' for loss
# Must be same length as offered_odds
results: List[str] = [
    "L", "W", "W", "L", "W", "W", "W", "W", "W", "W", "L", "W", "W", "L", "W", "W", "W", "L", "L", "W",

]

# OPTIONAL: stakes per bet. If None, stake = 1 for all bets.
stakes: Optional[List[float]] = None

# Exchange commission rate (e.g., Betfair 8% => 0.08)
commission: float = 0.08

# If you want to use "effective odds" instead of offered odds, put them here
# and set use_effective_odds = True. If left None, offered_odds is used.
effective_odds: Optional[List[float]] = None
use_effective_odds: bool = False


# =========================
# MATH HELPERS
# =========================

def norm_cdf(z: float) -> float:
    """Standard normal CDF using erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def per_bet_null_moments(odds: float, stake: float, c: float) -> Tuple[float, float]:
    """
    Under H0 with p = 1/odds, compute per-bet mean and variance of P/L.

    X = { win_profit with prob p, -stake with prob (1-p) }
    win_profit = (odds - 1)*stake*(1 - c)
    """
    if odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1. Got {odds}")

    p = 1.0 / odds
    win_profit = (odds - 1.0) * stake * (1.0 - c)
    lose_profit = -stake

    mu = p * win_profit + (1.0 - p) * lose_profit
    ex2 = p * (win_profit ** 2) + (1.0 - p) * (lose_profit ** 2)
    var = ex2 - mu ** 2
    return mu, var


def observed_pl(odds: float, stake: float, c: float, result: str) -> float:
    """Compute observed P/L for one bet given result."""
    r = result.strip().upper()
    if r not in ("W", "L"):
        raise ValueError(f"Result must be 'W' or 'L'. Got {result}")
    if r == "W":
        return (odds - 1.0) * stake * (1.0 - c)
    return -stake


# =========================
# MAIN
# =========================

def main() -> None:
    odds_list = effective_odds if (use_effective_odds and effective_odds is not None) else offered_odds

    n = len(odds_list)
    if len(results) != n:
        raise ValueError("results must have the same length as odds list.")
    if stakes is None:
        stake_list = [1.0] * n
    else:
        if len(stakes) != n:
            raise ValueError("stakes must have the same length as odds list.")
        stake_list = list(map(float, stakes))

    # Observed total P/L
    x = [observed_pl(odds_list[i], stake_list[i], commission, results[i]) for i in range(n)]
    S_obs = sum(x)

    # Null mean and variance for total P/L
    mus = []
    vars_ = []
    for i in range(n):
        mu_i, var_i = per_bet_null_moments(odds_list[i], stake_list[i], commission)
        mus.append(mu_i)
        vars_.append(var_i)

    S_mu = sum(mus)
    S_var = sum(vars_)
    S_sd = math.sqrt(S_var)

    if S_sd == 0:
        raise RuntimeError("Total null standard deviation is 0 (unexpected). Check inputs.")

    # CLT Z statistic
    Z = (S_obs - S_mu) / S_sd

    # One-sided p-value for positive edge: P(Z_null >= Z_obs)
    p_one_sided = 1.0 - norm_cdf(Z)

    # Two-sided p-value
    p_two_sided = 2.0 * min(norm_cdf(Z), 1.0 - norm_cdf(Z))

    # Print summary
    print("=== Betting Model Significance Test (Known p_i = 1/odds under H0) ===")
    print(f"Number of bets (n):           {n}")
    print(f"Commission (c):              {commission:.4f}")
    print(f"Using odds:                  {'effective_odds' if (use_effective_odds and effective_odds is not None) else 'offered_odds'}")
    print()
    print("--- Observed ---")
    print(f"Observed total P/L (S):      {S_obs:.6f}")
    print(f"Observed mean P/L per bet:   {S_obs / n:.6f}")
    print()
    print("--- Null (H0) ---")
    print(f"Null expected total P/L:     {S_mu:.6f}")
    print(f"Null expected per-bet P/L:   {S_mu / n:.6f}")
    print(f"Null SD of total P/L:        {S_sd:.6f}")
    print()
    print("--- Test ---")
    print(f"Z statistic:                 {Z:.6f}")
    print(f"One-sided p-value (H1: edge>0): {p_one_sided:.6g}")
    print(f"Two-sided p-value:           {p_two_sided:.6g}")
    print()
    if p_one_sided < 0.05:
        print("RESULT (5%): Reject H0 in favor of positive edge.")
    else:
        print("RESULT (5%): Cannot reject H0 (insufficient evidence of positive edge).")

    # Optional: show first few per-bet null means/vars (useful debugging)
    print("\n--- First 10 per-bet null moments (mu_i, sd_i) ---")
    for i in range(min(10, n)):
        print(f"Bet {i+1:>2}: odds={odds_list[i]:.4f}, stake={stake_list[i]:.4f}, "
              f"mu_i={mus[i]:+.6f}, sd_i={math.sqrt(vars_[i]):.6f}, result={results[i].upper()}, x_i={x[i]:+.6f}")


if __name__ == "__main__":
    main()
