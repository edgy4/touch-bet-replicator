# Touch Bet Strategy (Replication)

## Concept (from Dimitris Andreou)
A "Touch" bet can be replicated using a **Vertical Spread** on Deribit.
- **Instrument:** Vertical Debit Spread (Buy Strike A / Sell Strike B).
- **Exit Strategy:** Close the position when Spot Price touches Strike B (or the midpoint).
- **Assumed Value at Touch:** $\approx 50\%$ of the Spread Width (Max Payout).
    - Why? At-The-Money options have $\Delta \approx 0.5$. So a spread centered on Spot is worth half its max value.

## "No Touch" Strategy (Inverse)
We want to bet **"No Touch $X$"**.
- **Polymarket:** Buy "No" shares. Payout = $1 if Spot never touches $X$.
- **Deribit Equivalent:** Sell the Debit Spread (Enter a **Credit Spread**).
    - Sell Call ($X$) / Buy Call ($X+\epsilon$).
    - Receive Premium $P$.
    - **Stop Loss:** If Spot hits $X$, the spread value rises to $\approx Width/2$. **CLOSE IMMEDIATELY.**
    - **Loss on Touch:** $L = (Width/2) - P$.
    - **Profit on No Touch:** $P$ (Expires worthless).

## The Edge Calculation
We compare the **Implied Probability of Touch** ($P_{touch}$) on both platforms.

### Polymarket
- Market: "Will BTC hit $X$?"
- Price of "Yes" ($Cost_{poly}$) represents the market's implied probability of touching.
- $P_{touch, poly} = Cost_{poly}$.

### Deribit Synthetic
- Credit Spread Width: $W$.
- Premium Received: $P$.
- Stop Loss Value: $S = W/2$.
- Risk (Loss on Touch): $R = S - P$.
- Reward (Profit on No Touch): $P$.
- **Implied Probability of Touch ($P_{touch, deribit}$):**
  $$ P_{touch, deribit} = \frac{Reward}{Reward + Risk} = \frac{P}{P + (S - P)} = \frac{P}{S} = \frac{P}{W/2} = \frac{2P}{W} $$
  
  Wait. This logic assumes fair odds.
  Let's re-derive:
  Expected Value = $P(Touch) \times (-R) + (1 - P(Touch)) \times P = 0$
  $P(Touch) \times R = P - P(Touch) \times P$
  $P(Touch) \times (R + P) = P$
  $P(Touch) = P / (R + P) = P / S = P / (W/2) = \frac{2P}{W}$.
  
  **Correction:**
  If we receive premium $P$ for a width $W$, and stop out at $W/2$:
  - If $P > W/2$, we make guaranteed profit even if stopped out! (Arbitrage).
  - If $P < W/2$, we risk losing $(W/2) - P$.
  
  **Arbitrage Condition:**
  If $P_{touch, poly} > P_{touch, deribit}$, then Polymarket thinks touch is MORE likely than Deribit implies.
  - **Strategy:** Sell Polymarket "Yes" (Bet No) / Buy Deribit Hedge?
  - No. If Poly implies high touch prob, "Yes" is expensive. "No" is cheap.
  - We want to take the side that pays better.
  - If Poly pays 30c for "No" (70% touch prob), but Deribit implies 40% touch prob:
    - Poly thinks touch is 70%. Deribit thinks 40%.
    - **Bet No on Polymarket?** No, if touch is less likely (40%), "No" should be expensive (60c). If it's cheap (30c), it's a steal!
    - **Wait.** If Poly "Yes" is 70c (Touch Prob 70%). "No" is 30c.
    - If Deribit Touch Prob is 40%.
    - "No" fair value is 60c.
    - Poly "No" is 30c. **BUY POLY NO.**
  
  **Comparison Formula:**
  - $Prob_{poly} = \text{Price of Yes}$.
  - $Prob_{deribit} = \frac{2 \times \text{Credit Received}}{\text{Width}}$.
  - If $Prob_{poly} > Prob_{deribit} + \text{Edge}$, **BUY POLY NO**.
  - (Because market overestimates touch risk).

## Implementation
1.  Fetch Poly "Yes" Price.
2.  Fetch Deribit Credit Spread ($X, X+\epsilon$) Premium.
3.  Calculate Deribit Touch Prob.
4.  Compare.

