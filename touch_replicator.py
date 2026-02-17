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
        # If Target > Spot (Call side)
        target_opt = chain.iloc[(chain['strike'] - strike).abs().argsort()[:1]]
        if target_opt.empty: return None
        
        iv = target_opt.iloc[0]["mark_iv"] / 100.0 # Convert to decimal
        T = self.get_time_to_expiry(target_expiry)
        
        bs_prob = BlackScholesModels.one_touch_probability(
            S=spot, K=strike, T=T, sigma=iv, r=self.risk_free_rate
        )
        
        # 2. Spread Replication (Andreou Method)
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
        
        if pd.isna(short_leg["bid"]) or pd.isna(long_leg["ask"]):
             return {"bs_prob": bs_prob, "spread_prob": None, "details": {"iv": iv, "T": T}}

        credit_btc = short_leg["bid"] - long_leg["ask"]
        credit_usd = credit_btc * spot
        width = k_long - k_short
        
        spread_prob = 0.0
        if width > 0 and credit_usd > 0:
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

    def scan(self, html_output=False):
        print("=== Touch Bet Replicator (v2.0) ===")
        print("Fetching Deribit Data...")
        self.option_chain = self.deribit.get_option_chain_summary()
        
        print("Fetching Polymarket Data...")
        poly_markets = self.poly_scanner.fetch_polymarket_touch_markets()
        
        scan_results = []
        
        print(f"\nScanning {len(poly_markets)} Markets...\n")
        
        for m in poly_markets:
            details = self.poly_scanner.parse_market_details(m)
            if not details: continue
            
            strike = details["strike"]
            poly_prob = details["poly_price"]
            
            if details["expiry"] < datetime.now().strftime("%Y-%m-%d"): continue

            metrics = self.calculate_deribit_metrics(strike, details["expiry"])
            if not metrics: continue
            
            bs_prob = metrics["bs_prob"]
            spread_prob = metrics["spread_prob"]
            
            ref_prob = spread_prob if spread_prob else bs_prob
            diff = poly_prob - ref_prob
            
            result_item = {
                "market": details["question"],
                "expiry": details["expiry"],
                "strike": strike,
                "poly_prob": poly_prob,
                "bs_prob": bs_prob,
                "spread_prob": spread_prob,
                "iv": metrics['details']['iv'],
                "edge": diff,
                "url": details["url"],
                "spread_details": metrics['details']['spread'] if spread_prob else "N/A"
            }
            scan_results.append(result_item)

        # --- SORTING BY EDGE DESCENDING ---
        scan_results.sort(key=lambda x: x["edge"], reverse=True)

        # Print sorted results to terminal
        for r in scan_results:
            print(f"Market: {r['market']}")
            print(f"  Expiry: {r['expiry']} | Strike: {r['strike']}")
            print(f"  Polymarket: {r['poly_prob']:.1%}")
            print(f"  Deribit BS: {r['bs_prob']:.1%} (IV: {r['iv']:.1%})")
            if r['spread_prob']:
                print(f"  Deribit Spread: {r['spread_prob']:.1%} (Spread: {r['spread_details']})")
            print(f"  Edge: {r['edge']*100:.1f}%")
            
            if r['edge'] > 0.10:
                print("  >>> SIGNAL: BUY NO (Overpriced)")
            print("-" * 30)
            
        if html_output:
            self.generate_html(scan_results)

    def generate_html(self, results):
        """Generate a simple dashboard HTML file"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Touch Bet Arbitrage Scanner</title>
            <style>
                body { font-family: sans-serif; padding: 20px; background: #f0f2f5; }
                h1 { color: #333; }
                .disclaimer { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin-bottom: 20px; border-radius: 5px; color: #856404; }
                .card { background: white; padding: 15px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .signal { color: green; font-weight: bold; }
                .metric { margin: 5px 0; }
                .btn { display: inline-block; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px; }
                .instructions { margin-top: 15px; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #ccc; }
                .instructions h4 { margin-top: 0; color: #444; }
                .risk-warning
