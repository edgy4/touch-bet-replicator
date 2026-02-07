import pandas as pd
import numpy as np
from datetime import datetime
from deribit_connector import DeribitConnector
from polymarket_touch_scanner import PolymarketTouchScanner
from bs_models import BlackScholesModels

class TouchReplicator:
    """
    Replicates Polymarket 'Touch' bets using Deribit Option Chains.
    Implements methodologies from Dimitris Andreou (Spread Replication)
    and Black-Scholes (Analytical).
    """
    
    def __init__(self):
        self.poly_scanner = PolymarketTouchScanner()
        self.deribit = DeribitConnector("BTC")
        self.option_chain = pd.DataFrame()
        self.risk_free_rate = 0.04 # Estimating 4% risk free rate

    def get_time_to_expiry(self, expiry_str):
        """Calculate years to expiry"""
        try:
            exp_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            delta = exp_date - datetime.now()
            return max(0.001, delta.days / 365.0)
        except:
            return 0.0

    def calculate_deribit_metrics(self, strike, expiry, poly_type="Up"):
        """
        Calculate implied probabilities using Deribit data.
        Returns: { 'bs_prob': float, 'spread_prob': float, 'details': dict }
        """
        if self.option_chain.empty: return None

        # Filter for relevant expiry
        relevant_opts = self.option_chain[self.option_chain["expiry"] >= expiry].sort_values("expiry")
        if relevant_opts.empty: return None
        
        target_expiry = relevant_opts.iloc[0]["expiry"]
        chain = relevant_opts[relevant_opts["expiry"] == target_expiry]
        
        # Get Spot Price (Index)
        spot = chain.iloc[0]["underlying_price"]
        if not spot: return None
        
        # 1. Analytical Black-Scholes Probability
        # Need Implied Volatility at the Strike
        # Find option closest to strike
        
        # If Target > Spot (Call side)
        target_opt = chain.iloc[(chain['strike'] - strike).abs().argsort()[:1]]
        if target_opt.empty: return None
        
        iv = target_opt.iloc[0]["mark_iv"] / 100.0 # Convert to decimal
        T = self.get_time_to_expiry(target_expiry)
        
        bs_prob = BlackScholesModels.one_touch_probability(
            S=spot, K=strike, T=T, sigma=iv, r=self.risk_free_rate
        )
        
        # 2. Spread Replication (Andreou Method)
        # Construct Vertical Credit Spread centered around K (or just above/below)
        # Andreou: "Vertical Spread Value at Touch ~ 50% of Width"
        # Strategy: Sell Spread (Credit).
        # Implied Prob = 2 * Credit / Width
        
        # Find strikes for spread: [K-1000, K+1000] if possible, or closest
        calls = chain[chain["type"] == "call"].sort_values("strike")
        
        # Find strike just below and just above K
        lower_candidates = calls[calls["strike"] <= strike]
        upper_candidates = calls[calls["strike"] > strike]
        
        if lower_candidates.empty or upper_candidates.empty:
            return {"bs_prob": bs_prob, "spread_prob": None, "details": {"iv": iv, "T": T}}
            
        short_leg = lower_candidates.iloc[-1] # Sell (Bid)
        long_leg = upper_candidates.iloc[0]   # Buy (Ask)
        
        k_short = short_leg["strike"]
        k_long = long_leg["strike"]
        
        # Check liquidity
        if pd.isna(short_leg["bid"]) or pd.isna(long_leg["ask"]):
             return {"bs_prob": bs_prob, "spread_prob": None, "details": {"iv": iv, "T": T}}

        # Credit Calculation (BTC -> USD)
        credit_btc = short_leg["bid"] - long_leg["ask"]
        credit_usd = credit_btc * spot
        width = k_long - k_short
        
        spread_prob = 0.0
        if width > 0 and credit_usd > 0:
            # Formula: P = 2 * Credit / Width
            spread_prob = (2 * credit_usd) / width
            
        return {
            "bs_prob": bs_prob,
            "spread_prob": spread_prob,
            "details": {
                "iv": iv, 
                "T": T, 
                "spread": f"{k_short}-{k_long}",
                "credit": credit_usd,
                "spot": spot
            }
        }

    def scan(self):
        print("=== Touch Bet Replicator (v2.0) ===")
        print("Fetching Deribit Data...")
        self.option_chain = self.deribit.get_option_chain_summary()
        
        print("Fetching Polymarket Data...")
        poly_markets = self.poly_scanner.fetch_polymarket_touch_markets()
        
        opportunities = []
        
        print(f"\nScanning {len(poly_markets)} Markets...\n")
        
        for m in poly_markets:
            details = self.poly_scanner.parse_market_details(m)
            if not details: continue
            
            strike = details["strike"]
            poly_prob = details["poly_price"]
            
            # Skip expired
            if details["expiry"] < datetime.now().strftime("%Y-%m-%d"): continue

            metrics = self.calculate_deribit_metrics(strike, details["expiry"])
            if not metrics: continue
            
            bs_prob = metrics["bs_prob"]
            spread_prob = metrics["spread_prob"]
            
            # Comparison Logic
            # If Poly > Models => Buy NO
            # If Poly < Models => Buy YES (Rare)
            
            # Use Spread Prob as the "Execution" benchmark
            # Use BS Prob as the "Theoretical" benchmark
            
            ref_prob = spread_prob if spread_prob else bs_prob
            diff = poly_prob - ref_prob
            
            # Display
            print(f"Market: {details['question']}")
            print(f"  Expiry: {details['expiry']} | Strike: {strike}")
            print(f"  Polymarket: {poly_prob:.1%}")
            print(f"  Deribit BS: {bs_prob:.1%} (IV: {metrics['details']['iv']:.1%})")
            if spread_prob:
                print(f"  Deribit Spread: {spread_prob:.1%} (Spread: {metrics['details']['spread']})")
            print(f"  Edge: {diff*100:.1f}%")
            
            if diff > 0.10:
                print("  >>> SIGNAL: BUY NO (Overpriced)")
                opportunities.append(details)
            
            print("-" * 30)

if __name__ == "__main__":
    scanner = TouchReplicator()
    scanner.scan()
