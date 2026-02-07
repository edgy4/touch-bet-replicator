# Touch Bet Strategy Guide

## How to Trade "No Touch"

When the scanner signals **[BUY NO (Overpriced)]**, it means the market (Polymarket) thinks a touch event is **more likely** than the options market (Deribit) implies.

**Example Signal:**
```
Market: Will Bitcoin be above $70,000 on February 8?
Polymarket: 42.4%
Deribit Spread: 23.6%
Edge: 18.8%
>>> SIGNAL: BUY NO (Overpriced)
```

**Part 1: Execute the Polymarket Side (The Alpha)**

1.  **Interpret the Signal:**
    *   The scanner indicates that Polymarket believes there's a 42.4% chance Bitcoin will be above $70,000 on Feb 8.
    *   The Deribit options market (via spread replication) suggests the fair value probability is only 23.6%.
    *   Polymarket's "Yes" contract is overpriced according to the options market.
    *   Therefore, the strategy is to **Buy "NO"** on Polymarket.

2.  **Navigate to the Market:**
    *   Click the market link provided in the scanner output (e.g., `https://polymarket.com/event/[event-id]`).
    *   Ensure you are on the correct market matching the description and expiry date.

3.  **Prepare Your Wallet:**
    *   Connect your Ethereum-compatible wallet (e.g., MetaMask) to Polymarket.
    *   Ensure you have sufficient USDC (or the required stablecoin) in your wallet.

4.  **Place the Order:**
    *   Find the "NO" outcome for the specified event.
    *   Enter the amount of "NO" shares you wish to buy. The price will be determined by the current market odds (e.g., if the market says 42.4%, you might pay around $0.424 per share).
    *   Review the transaction details carefully (amount, price, total cost).
    *   Confirm the transaction in your wallet.

**Part 2: Hedge on Deribit (Risk Management)**

1.  **Understand the Hedge Purpose:**
    *   The Polymarket "NO" position loses money if Bitcoin *does* touch $70,000.
    *   The Deribit hedge aims to profit if Bitcoin touches, offsetting the Polymarket loss.
    *   Note: The hedge is imperfect and intended for risk mitigation, not perfect profit locking.

2.  **Determine the Hedge Instrument:**
    *   The scanner output shows the relevant Deribit spread: `Spread: 70000.0-71000.0`.
    *   This means the implied fair-value spread is between the $70,000 and $71,000 strikes.
    *   To hedge the "NO" bet on the $70,000 level, you would typically use a **Bear Call Spread**.
    *   **Bear Call Spread Mechanics:**
        *   **Sell** a Call Option at the Lower Strike (e.g., $70,000).
        *   **Buy** a Call Option at the Higher Strike (e.g., $71,000).
        *   This generates a credit (premium received) if the price stays below $70,000.
        *   If the price touches $70,000, the sold call increases in value, creating a loss, but the purchased call provides protection against unlimited losses.

3.  **Navigate Deribit:**
    *   Log in to your Deribit account.
    *   Go to the Options tab for BTC.

4.  **Place the Bear Call Spread Order:**
    *   Find the options expiring on or before the Polymarket expiry (Feb 8, 2026).
    *   Locate the $70,000 Call option and the $71,000 Call option.
    *   **Sell the $70,000 Call:** Place a "Sell" order for the desired number of contracts.
    *   **Buy the $71,000 Call:** Place a "Buy" order for the *same* number of contracts.
    *   **(Preferred Method):** Many platforms allow you to place a "Vertical Spread" order directly. Select the $70,000 (short) and $71,000 (long) legs as a single spread order. This ensures both legs are filled simultaneously and reduces execution risk.
    *   Specify the order type (e.g., Limit Order) and desired price/rate if placing manually.
    *   Double-check the strikes, expiry, and number of contracts.
    *   Submit the order.

**Important Considerations:**

*   **Account Funding:** Ensure both Polymarket (USDC) and Deribit (BTC for collateral) accounts are adequately funded.
*   **Order Sizing:** Start with small sizes to understand the mechanics and risks.
*   **Execution Speed:** The arbitrage opportunity might close quickly. Having pre-configured orders or fast execution methods can be crucial.
*   **Slippage:** Large orders may face slippage, especially on less liquid Deribit strikes.
*   **Monitoring:** Actively monitor both positions until expiration or until the arb opportunity closes.
*   **Risk:** Understand the risks of options trading. The hedge is not perfect. Losses are possible on both sides if the market moves unexpectedly.

## Website Automation
This repository includes a GitHub Actions workflow that runs the scanner every hour and updates a static website.

**To Enable:**
1.  Go to Repo Settings > Pages.
2.  Select Source: `gh-pages` branch (created automatically after first run).
3.  Your scanner will be live at `https://yourusername.github.io/touch-bet-replicator`.
