import pandas as pd
from deribit_connector import DeribitConnector
from polymarket_touch_scanner import PolymarketTouchScanner

class TouchReplicator:
    def __init__(self):
        self.poly_scanner = PolymarketTouchScanner()
        self.deribit = DeribitConnector("BTC")
        self.option_chain = pd.DataFrame()

    def calculate_synthetic_prob(self, strike, expiry):
        """
        Calculate implied probability of touch using Deribit Credit Spreads.
        Strategy: Sell Call(K) / Buy Call(K+Width).
        """
        if self.option_chain.empty: return None

        # Filter for relevant expiration (>= Poly expiry)
        relevant_opts = self.option_chain[self.option_chain["expiry"] >= expiry]
        if relevant_opts.empty: return None
        
        relevant_opts = relevant_opts.sort_values("expiry")
        target_expiry = relevant_opts.iloc[0]["expiry"]
        
        chain = relevant_opts[relevant_opts["expiry"] == target_expiry]
        
        # Find Call options for Credit Spread (Short K, Long K+Width)
        calls = chain[chain["type"] == "call"].sort_values("strike")
        
        # Find strike closest to K
        candidates = calls[calls["strike"] >= strike]
        if candidates.empty: return None
        
        short_leg = candidates.iloc[0] # Sell this (Strike K)
        k_short = short_leg["strike"]
        
        # Find long leg (next strike up)
        long_candidates = calls[calls["strike"] > k_short]
        if long_candidates.empty: return None
        
        long_leg = long_candidates.iloc[0] # Buy this (Strike K+Width)
        k_long = long_leg["strike"]
        
        # Calculate Credit Received (Premium)
        # Sell Bid (conservative), Buy Ask (conservative)
        # Wait. To open a credit spread, we Sell (Bid) and Buy (Ask).
        # We want to receive credit.
        
        p_short = short_leg["bid"] # Selling
        p_long = long_leg["ask"]   # Buying
        
        if pd.isna(p_short) or pd.isna(p_long): return None
        
        # Underlying Price (Index)
        index_price = short_leg["underlying_price"]
        
        credit_btc = p_short - p_long
        credit_usd = credit_btc * index_price
        
        width = k_long - k_short
        
        if credit_usd <= 0: return None # No credit (or negative due to spread)
        
        # Implied Touch Probability (Dimitris Andreou Formula)
        # P(Touch) = 2 * Premium / Width
        
        prob_touch = (2 * credit_usd) / width
        
        return {
            "prob": prob_touch,
            "credit": credit_usd,
            "width": width,
            "spread": f"{k_short}-{k_long}",
            "expiry": target_expiry
        }

    def scan(self):
        print("Fetching Deribit Data...")
        self.option_chain = self.deribit.get_option_chain_summary()
        
        print("Fetching Polymarket Data...")
        poly_markets = self.poly_scanner.fetch_polymarket_touch_markets()
        
        opportunities = []
        
        for m in poly_markets:
            details = self.poly_scanner.parse_market_details(m)
            if not details: continue
            
            strike = details["strike"]
            expiry = details["expiry"]
            poly_price = details["poly_price"] # P(Touch) according to Poly
            
            # Skip if expiry is too far (Deribit liquidity issues)
            # or too close (< 1 day)
            
            deribit_data = self.calculate_synthetic_prob(strike, expiry)
            
            if not deribit_data: continue
            
            deribit_prob = deribit_data["prob"]
            
            # Comparison
            # If Poly Price (Implied Prob) > Deribit Prob + Edge:
            # Poly thinks touch is MORE likely than Deribit.
            # "No Touch" on Poly is cheap.
            # Strategy: Buy "No" on Poly.
            
            diff = poly_price - deribit_prob
            
            print(f"Market: {details['question']}")
            print(f"  Poly P(Touch): {poly_price:.2%}")
            print(f"  Deribit P(Touch): {deribit_prob:.2%} (Credit: ${deribit_data['credit']:.2f}, Width: ${deribit_data['width']:.0f})")
            print(f"  Diff: {diff*100:.1f}%")
            
            if diff > 0.10: # 10% edge
                opportunities.append({
                    "question": details["question"],
                    "strike": strike,
                    "poly_prob": poly_price,
                    "deribit_prob": deribit_prob,
                    "edge": diff,
                    "action": "BUY NO (Polymarket)",
                    "spread": deribit_data["spread"]
                })
            
            print("-" * 40)
            
        print(f"\nFound {len(opportunities)} High-Conviction Opportunities:")
        for op in opportunities:
            print(f"[{op['action']}] {op['question']}")
            print(f"  Edge: {op['edge']*100:.1f}% (Poly: {op['poly_prob']:.0%} vs Deribit: {op['deribit_prob']:.0%})")
            print(f"  Ref Spread: {op['spread']}")

if __name__ == "__main__":
    scanner = TouchReplicator()
    scanner.scan()
