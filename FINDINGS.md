# Deribit vs Polymarket Arbitrage (Touch Bets)

## Findings (2026-02-07)

We scanned 2000 markets on Polymarket and compared them to Deribit Option Chains.

### The Setup
- **Polymarket:** "Will BTC hit X?" (Touch Option) or "Will BTC be above X on Date?" (European).
- **Deribit:** Vertical Call Spread ($K-\epsilon, K+\epsilon$) approximating a European Binary Option.

### Results
- **General Trend:** Polymarket (Touch) trades at a **1.2x - 1.5x Premium** over Deribit (European).
  - This aligns with theory: $P(\text{Touch } K) \ge P(S_T \ge K)$.
  - The "Touch Premium" reflects the probability of hitting the strike but falling back before expiry.

### Anomalies
- **"Will the price of Bitcoin be above $70,000 on February 8?"**
  - **Poly Price:** $0.367 (36.7%)
  - **Deribit European:** $0.148 (14.8%)
  - **Ratio:** 2.48x
  - **Potential Alpha:** Sell Poly / Buy Deribit Spread.
  - **Risk:** If BTC hits 70k and stays above, both pay out (loss of premium). If BTC hits 70k and drops, Poly pays (loss on short), Deribit expires worthless (loss on long). WAIT.
  - **Correction:** If we SHORT Poly (Bet No), we win if it *doesn't* hit (or doesn't stay above).
  - If we Buy Deribit Call Spread, we win if it *does* stay above.
  - **Hedge:**
    - Scenario 1: BTC < 70k. Poly No wins (+$0.63). Deribit loses (-$0.15). Net: +$0.48.
    - Scenario 2: BTC > 70k. Poly No loses (-$0.37). Deribit wins (+$0.85). Net: +$0.48.
    - **Arbitrage Profit:** $0.48 risk-free?
    - **Caveat:** Slippage, Fees, and Capital Efficiency. And "Touch" definition. If Poly is Touch and hits 70k then drops, Poly Yes pays (Short loses). Deribit expires worthless (Long loses). **Double Loss.**
    - **CRITICAL:** You cannot arb Touch vs European by Shorting Touch. You must **Long Touch** vs Short European? No, that's negative carry.
    - **Conclusion:** You can only arb if Poly (Touch) is **CHEAPER** than European. (Buy Poly, Sell Deribit).
    - **Current State:** Poly is EXPENSIVE. No risk-free arb. Only directional bet that "Volatility is Overpriced".

## Next Steps
- Monitor for **Undervalued Touch** (Poly < European).
- This is rare but mathematically impossible (free money).
- Current scanner looks for `diff > 0.05` (Poly cheaper). found 0.
