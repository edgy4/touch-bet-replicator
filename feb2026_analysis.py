import pandas as pd
from deribit_connector import DeribitConnector

class Feb2026TouchAnalyzer:
    def __init__(self):
        self.deribit = DeribitConnector("BTC")
        self.option_chain = pd.DataFrame()

    def analyze(self):
        print("Fetching Deribit Option Chain...")
        self.option_chain = self.deribit.get_option_chain_summary()
        
        if self.option_chain.empty:
            print("Failed to fetch Deribit data.")
            return

        # Filter for 2026 expiries
        # Look for "FEB26", "MAR26", "JUN26"
        chain_2026 = self.option_chain[self.option_chain["expiry"].str.contains("2026", na=False)]
        
        print("\nAvailable 2026 Expiries:")
        print(chain_2026["expiry"].unique())
        
        # Select target expiry: 27MAR26 (most liquid) or 20FEB26 (exact match but likely illiquid)
        # Check volume for 20FEB26
        feb_chain = chain_2026[chain_2026["expiry"] == "2026-02-20"]
        mar_chain = chain_2026[chain_2026["expiry"] == "2026-03-27"]
        
        target_chain = feb_chain if not feb_chain.empty else mar_chain
        target_expiry = target_chain.iloc[0]["expiry"]
        print(f"\nUsing Target Expiry: {target_expiry}")
        
        strikes = [100000, 120000, 150000, 200000, 250000, 300000]
        
        print(f"\n=== Deribit Implied Touch Probability (Fair Value) ===")
        print(f"Strategy: Credit Spread (Sell K / Buy Next K). Stop Loss at 50% max payout.")
        
        for k in strikes:
            # Find closest available strike >= K
            calls = target_chain[target_chain["type"] == "call"].sort_values("strike")
            candidates = calls[calls["strike"] >= k]
            
            if candidates.empty:
                print(f"Strike {k}: No options available.")
                continue
                
            short_leg = candidates.iloc[0]
            k_short = short_leg["strike"]
            
            # Find next strike up (Long Leg)
            long_candidates = calls[calls["strike"] > k_short]
            if long_candidates.empty:
                print(f"Strike {k}: No upper leg available.")
                continue
                
            long_leg = long_candidates.iloc[0]
            k_long = long_leg["strike"]
            
            # Credit Calculation
            # Sell Bid, Buy Ask (Conservative)
            p_short = short_leg["bid"]
            p_long = long_leg["ask"]
            
            if pd.isna(p_short) or pd.isna(p_long):
                print(f"Strike {k}: No bid/ask quotes.")
                continue
            
            index_price = short_leg["underlying_price"]
            credit_btc = p_short - p_long
            credit_usd = credit_btc * index_price
            width = k_long - k_short
            
            if credit_usd <= 0:
                print(f"Strike {k}: Negative credit (Bid/Ask spread too wide).")
                continue
            
            # Implied Touch Probability
            prob_touch = (2 * credit_usd) / width
            
            print(f"Strike ${k_short:,.0f} (Spread: ${k_short/1000:.0f}k-${k_long/1000:.0f}k):")
            print(f"  Credit: ${credit_usd:.2f} | Width: ${width:,.0f}")
            print(f"  Implied Touch Prob: {prob_touch:.2%}")
            print(f"  Fair Value for 'No Touch': {1 - prob_touch:.2%}")
            print("-" * 30)

if __name__ == "__main__":
    analyzer = Feb2026TouchAnalyzer()
    analyzer.analyze()
