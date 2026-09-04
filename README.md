# GoldPro V2.1 Trend Fix

Same GoldPro V2 Strong Signal strategy, with only the trend-detection/startup flow corrected.

Changes:
- 5M trend is calculated before the first 1M entry check.
- Trend no longer requires all EMA slope/price/DI conditions simultaneously.
- With ADX >= 25, a 3-of-5 directional vote can produce UP/DOWN; ties remain NEUTRAL.
- Added detailed TREND DEBUG logs showing price, EMA20/EMA50, ADX, +DI/-DI, votes and final trend.
- Entry filters, Score=80, RR, SL/TP and cooldown are otherwise unchanged.
