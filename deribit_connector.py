import requests
import pandas as pd
from datetime import datetime
import time

class DeribitConnector:
    BASE_URL = "https://www.deribit.com/api/v2"

    def __init__(self, currency="BTC"):
        self.currency = currency

    def get_ticker_by_currency(self, currency="BTC"):
        """Fetch all tickers for a currency to get mark price and IV"""
        url = f"{self.BASE_URL}/public/get_book_summary_by_currency?currency={currency}&kind=option"
        try:
            resp = requests.get(url)
            return resp.json().get("result", [])
        except Exception as e:
            print(f"Error fetching ticker for {currency}: {e}")
            return []

    def parse_expiry(self, expiry_str):
        """Parse DDMMMYY (e.g. 28MAR25) to YYYY-MM-DD"""
        try:
            # Deribit format: 28MAR25
            dt = datetime.strptime(expiry_str, "%d%b%y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    def get_option_chain_summary(self):
        """
        Fetch summary of all option instruments for the currency (mark_price, bid, ask, open_interest, mark_iv).
        Returns a DataFrame.
        """
        try:
            url = f"{self.BASE_URL}/public/get_book_summary_by_currency?currency={self.currency}&kind=option"
            resp = requests.get(url)
            if resp.status_code != 200:
                print(f"Error fetching summaries: {resp.text}")
                return pd.DataFrame()
            
            summaries = resp.json().get("result", [])
        except Exception as e:
            print(f"Error fetching summaries: {e}")
            return pd.DataFrame()

        data = []
        for item in summaries:
            # Instrument name format: BTC-28MAR25-100000-C
            name = item["instrument_name"]
            parts = name.split("-")
            if len(parts) < 4: continue
            
            expiry_str = parts[1] # e.g. 28MAR25
            try:
                strike = float(parts[2])
            except ValueError:
                continue
                
            opt_type = "call" if parts[3] == "C" else "put"
            expiry_date = self.parse_expiry(expiry_str)
            
            data.append({
                "instrument": name,
                "expiry": expiry_date,
                "strike": strike,
                "type": opt_type,
                "mark_price": item.get("mark_price"), # In BTC
                "bid": item.get("bid_price"),
                "ask": item.get("ask_price"),
                "mark_iv": item.get("mark_iv"),
                "underlying_price": item.get("underlying_price"), # Index price
                "open_interest": item.get("open_interest"),
                "volume_usd": item.get("volume_usd_24h")
            })
            
        df = pd.DataFrame(data)
        return df

if __name__ == "__main__":
    dc = DeribitConnector("BTC")
    df = dc.get_option_chain_summary()
    print(df.head())
    print(f"Total Options: {len(df)}")
