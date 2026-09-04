goldpro-signal-bot 


## Debug Mode
This version keeps the V2 strategy unchanged and adds detailed Railway logs.
Set `GOLDPRO_DEBUG=1` to see why an entry is rejected:
- ATR / ADX / EMA distance blockers
- BUY/SELL score out of 100
- missing confirmations (Momentum, Pullback, Candle, RSI zone, etc.)
- R/R rejection
- cooldown rejection

No Telegram debug messages are sent; diagnostics are written to the Railway deployment log.
