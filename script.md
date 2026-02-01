We beat the greyhound racing market using only high-school maths.

Well… kind of. Let us explain.

Some betting exchanges let you bet on just two dogs racing head-to-head.
So we built a Python algorithm that pulls all their past races, filters for the same distance, and calculates their average times and standard deviations.

From that, we model each dog with a normal distribution and run 100,000 simulations to estimate their true win probabilities.

For example: Billy wins about 66.7% of the time → fair odds of 1.5.

But the market was offering 2.0.

That means for every $1 we bet, the expected return was $1.33 — a 33% edge.

So… does it actually work?

In live tests across 45 races with EV > 10%, we averaged 25% profit.
Backtesting 400+ races gave weaker results — likely due to the huge variance in this kind of strategy.

Bottom line?
Despite the noise, the evidence suggests one thing:

We beat the greyhound racing market using only high-school maths.