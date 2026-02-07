# Correlation Arbitrage: The Next Frontier

## Concept
Instead of trading the same asset (BTC vs BTC), we trade **correlated assets**.

**Example:**
- **Market A:** "Will Trump win Pennsylvania?" ($P_A$)
- **Market B:** "Will Trump win the US Election?" ($P_B$)
- **Logic:** $P_B \approx P_A + \epsilon$ (PA is a swing state).
- **Arbitrage:** If $P_A > P_B$, it implies Trump wins PA but loses the election (unlikely).
- **Strategy:** Short $P_A$ / Long $P_B$.

## Application to Crypto
- **Market A:** "Will ETH hit $4k in Feb?"
- **Market B:** "Will BTC hit $100k in Feb?"
- **Logic:** ETH is highly correlated to BTC. If BTC rips, ETH likely rips.
- **Arbitrage:** If $P(\text{ETH Hit}) \ll P(\text{BTC Hit}) \times \rho$ (Correlation), Buy ETH / Short BTC (Hedge).
- **Problem:** Correlation varies. Not risk-free.

## Better Application: Nested Events
- **Market A:** "Will BTC be > $100k on Feb 28?" (European)
- **Market B:** "Will BTC hit $100k in Feb?" (Touch)
- **Logic:** Touch MUST be $\ge$ European.
- **Arbitrage:** If $P(\text{Touch}) < P(\text{European})$, Buy Touch / Short European.
- **Status:** Scanner checks this (`diff > 0.05`). Found 0.
- **Wait:** We can check **Cross-Platform**.
    - Poly Touch ($P_T$) vs Deribit European ($P_E$).
    - If $P_T < P_E$, Buy Poly / Short Deribit (Call Spread).
    - **Result:** 0 found.

## Conclusion
The market is efficient on the **Touch >= European** constraint.
The alpha is likely in **complex conditional probabilities** or **event correlations**.
