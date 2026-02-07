import requests
import re
from datetime import datetime
import pandas as pd
from deribit_connector import DeribitConnector

class PolymarketTouchScanner:
    GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"

    def __init__(self):
        self.deribit = DeribitConnector("BTC")
        self.option_chain = pd.DataFrame()

    def fetch_polymarket_touch_markets(self):
        """Fetch active 'Touch' markets from Polymarket with pagination"""
        markets = []
        offset = 0
        limit = 500
        
        print("Fetching ALL Polymarket active markets...")
        
        while True:
            params = {
                "active": "true",
                "closed": "false",
                "limit": limit,
                "offset": offset,
                "order": "volume24hr",
                "ascending": "false"
            }
            try:
                resp = requests.get(self.GAMMA_API_URL, params=params)
                batch = resp.json()
                if not batch: break
                markets.extend(batch)
                offset += limit
                print(f"Fetched {len(markets)} markets...", end='\r')
                if len(markets) >= 3000: break # Increased limit for long-tail
            except Exception as e:
                print(f"Error fetching Polymarket: {e}")
                break
        
        print(f"\nTotal Markets Fetched: {len(markets)}")
        
        touch_markets = []
        for m in markets:
            question = m.get("question", "")
            # Filter for "What price will Bitcoin hit in February 2026?"
            if "What price will Bitcoin hit in February 2026?" in question:
                touch_markets.append(m)
            # Or general pattern
            elif ("BTC" in question or "Bitcoin" in question) and ("hit" in question or "reach" in question or "above" in question):
                touch_markets.append(m)
        
        return touch_markets

    def parse_market_details(self, market):
        """Extract Strike and Expiry from market question/description"""
        question = market.get("question", "")
        description = market.get("description", "")
        end_date_iso = market.get("endDate") # ISO format: 2024-02-29T23:59:00Z
        
        # Default strike parsing for "Will BTC hit $X"
        strike_match = re.search(r'\$([\d,]+)', question)
        strike = float(strike_match.group(1).replace(",", "")) if strike_match else None
        
        # Special parsing for "What price will Bitcoin hit in February 2026?"
        # The market might be a Group market where outcomes are strikes ($100k, $120k).
        # OR it might be individual markets: "Will Bitcoin hit $100k in Feb 2026?"
        # The user linked a Group market. Polymarket API returns Group markets differently.
        # If it's a Group Market, outcomes might be ["$100k", "$120k", "No Touch"].
        # But usually Group Markets are split into individual "Binary Markets" in the API list.
        # So we might see "Will Bitcoin hit $100k in Feb 2026?" as a separate item.
        
        # Let's check if the strike is in the outcome name if not in question
        if strike is None:
             # Check outcomes
             pass

        if not strike:
            return None
        
        # Extract Expiry Date
        if end_date_iso:
            try:
                expiry = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except ValueError:
                return None
        else:
            return None

        # Get Current Price of "Yes"
        try:
            prices = eval(market.get("outcomePrices", "[]"))
            yes_price = float(prices[0]) # Assuming Yes is first
        except:
            yes_price = 0.0

        return {
            "id": market.get("id"),
            "question": question,
            "strike": strike,
            "expiry": expiry,
            "poly_price": yes_price,
            "url": f"https://polymarket.com/event/{market.get('slug')}"
        }

    def find_arbitrage(self):
        """Scan for arbitrage opportunities"""
        print("Fetching Deribit Option Chain...")
        self.option_chain = self.deribit.get_option_chain_summary()
        if self.option_chain.empty:
            print("Failed to fetch Deribit data.")
            return

        print("Fetching Polymarket Touch Markets...")
        poly_markets = self.fetch_polymarket_touch_markets()
        print(f"Found {len(poly_markets)} potential Touch markets.")

        opportunities = []

        for m in poly_markets:
            details = self.parse_market_details(m)
            if not details: continue
            
            strike = details["strike"]
            expiry = details["expiry"]
            poly_price = details["poly_price"]
            
            # Find matching Deribit options
            # We need Call options with Expiry <= Poly Expiry (or close)
            # Actually, for Touch options, any expiry is valid as long as it covers the period?
            # No, if Poly expires Feb 28, we need Deribit options expiring ON or AFTER Feb 28 to hedge properly?
            # Wait. If Deribit expires BEFORE Poly, and BTC hits after Deribit expires but before Poly expires, we lose hedge.
            # So we need Deribit expiry >= Poly expiry.
            
            # Filter chain for matching expiry
            # Simplified: look for exact date or next available
            
            relevant_opts = self.option_chain[self.option_chain["expiry"] >= expiry]
            if relevant_opts.empty:
                continue
                
            # Sort by expiry to find closest
            relevant_opts = relevant_opts.sort_values("expiry")
            closest_expiry = relevant_opts.iloc[0]["expiry"]
            
            # Get Calls for closest expiry
            calls = relevant_opts[(relevant_opts["expiry"] == closest_expiry) & (relevant_opts["type"] == "call")]
            
            # Find strikes around target K
            # We want a vertical spread: Buy Call(K-Width), Sell Call(K+Width)
            # Or just use the ATM/OTM Call price as a proxy for probability?
            # A Binary Call probability is approx Delta (N(d2)).
            # Or simpler: Price of Call Spread / Width.
            
            # Let's find strikes closest to K
            calls = calls.sort_values("strike")
            
            # Find strike just below and just above K
            # We need strictly less than or equal to strike
            lower_candidates = calls[calls["strike"] <= strike]
            upper_candidates = calls[calls["strike"] > strike]
            
            if lower_candidates.empty or upper_candidates.empty:
                continue
                
            lower_strike = lower_candidates.iloc[-1]
            upper_strike = upper_candidates.iloc[0]
            
            k_lower = lower_strike["strike"]
            k_upper = upper_strike["strike"]
            
            # Use ASK prices if available (conservative execution), else mark
            # For arbitrage detection, we want to know if Poly (Buy) < Deribit (Sell Spread).
            # To Sell Spread on Deribit: Sell Lower Call (Bid), Buy Upper Call (Ask).
            # Cost to enter short spread = Premium Received = Bid_Lower - Ask_Upper.
            # But here we are comparing Poly Price vs Theoretical European Price.
            # Let's use Mark Price for initial scan.
            
            p_lower_btc = lower_strike["mark_price"]
            p_upper_btc = upper_strike["mark_price"]
            
            # Handle potential None values
            if p_lower_btc is None or p_upper_btc is None:
                continue
                
            # Underlying price (Index)
            index_price = lower_strike.get("underlying_price") or upper_strike.get("underlying_price")
            if not index_price: continue
            
            p_lower_usd = p_lower_btc * index_price
            p_upper_usd = p_upper_btc * index_price
            
            width = k_upper - k_lower
            if width <= 0: continue
            
            # Spread Value (Cost to Buy)
            spread_value_usd = p_lower_usd - p_upper_usd
            
            # Implied Probability (Binary Price)
            euro_binary_price = spread_value_usd / width
            
            # Sanity Check: Price must be between 0 and 1
            if euro_binary_price < 0 or euro_binary_price > 1.05: # Allow small error
                 # If > 1, it implies arbitrage within Deribit itself or bad data
                 # print(f"DEBUG: {details['question']} - Impossible Price {euro_binary_price:.2f} (Spread: {spread_value_usd:.2f}, Width: {width})")
                 continue
            
            # Compare
            # Theory: Touch Price (Poly) should be >= European Price (Deribit)
            # Arbitrage: If Poly < Deribit, it's undervalued (Buy Poly).
            # Wait. Touch >= European is always true.
            # So if Poly < European, Poly is DEFINITELY cheap.
            # Why? Because Touch includes the probability of hitting K and then dropping back. European excludes that.
            
            diff = euro_binary_price - poly_price
            
            # Print analysis for all valid comparisons
            print(f"Analyzed: {details['question']}")
            print(f"  Poly (Touch): {poly_price:.3f} | Deribit (Euro): {euro_binary_price:.3f}")
            print(f"  Ratio: {poly_price/euro_binary_price if euro_binary_price > 0 else 'inf':.2f}x | Diff: {diff:.3f}")
            print(f"  Expiry: {expiry} | Strike: {strike} | Spread: {k_lower}-{k_upper}")
            print("-" * 30)

            if diff > 0.05: # 5% edge (Poly CHEAPER than Euro - Strong Buy)
                opportunities.append({
                    "type": "Buy Poly (Undervalued)",
                    "question": details["question"],
                    "strike": strike,
                    "expiry": expiry,
                    "poly_price": poly_price,
                    "deribit_euro_price": euro_binary_price,
                    "edge": diff,
                    "deribit_expiry": closest_expiry,
                    "spread": f"{k_lower}-{k_upper}"
                })
            elif poly_price > euro_binary_price * 2.5 and euro_binary_price > 0.05:
                # If Poly is > 2.5x Euro, it might be overpriced (Short Poly?)
                # Theoretical max for Touch/Euro is ~2.0 (Reflection Principle).
                # If > 2.0, likely overpriced.
                opportunities.append({
                    "type": "Sell Poly (Overpriced)",
                    "question": details["question"],
                    "strike": strike,
                    "expiry": expiry,
                    "poly_price": poly_price,
                    "deribit_euro_price": euro_binary_price,
                    "edge": poly_price - euro_binary_price,
                    "deribit_expiry": closest_expiry,
                    "spread": f"{k_lower}-{k_upper}",
                    "description": m.get("description", "No description")
                })

        # Report
        print(f"\nFound {len(opportunities)} Interesting Opportunities:")
        for op in opportunities:
            print(f"[{op['type']}] {op['question']}")
            print(f"  Poly: ${op['poly_price']:.3f} | Deribit Euro: ${op['deribit_euro_price']:.3f}")
            print(f"  Edge: {op['edge']*100:.1f}% | Strike: {op['strike']} | Spread: {op['spread']}")
            if op.get("description"):
                print(f"  Rules: {op['description'][:200]}...") # Truncate description
            print("-" * 50)

if __name__ == "__main__":
    scanner = PolymarketTouchScanner()
    scanner.find_arbitrage()
