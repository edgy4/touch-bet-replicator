import math
from scipy.stats import norm

class BlackScholesModels:
    """
    Standard Financial Engineering Models for Option Pricing.
    Reference: Hull, "Options, Futures, and Other Derivatives".
    """

    @staticmethod
    def one_touch_probability(S, K, T, sigma, r=0.04):
        """
        Calculate the Risk-Neutral Probability that the price touches K
        at any time during [0, T]. (One-Touch Digital).
        
        Assumes Geometric Brownian Motion.
        
        S: Current Spot Price
        K: Target Strike Price
        T: Time to Expiry (years)
        sigma: Implied Volatility (decimal)
        r: Risk-free Interest Rate (decimal)
        
        Returns: Probability (0.0 to 1.0)
        """
        if T <= 0: return 1.0 if (S >= K) else 0.0
        if sigma <= 0: return 1.0 if (S >= K) else 0.0
        
        # Up-and-In (Target > Spot)
        if K > S:
            mu = r - 0.5 * sigma**2
            lambda_val = math.sqrt(mu**2 + 2 * sigma**2 * r) # This is for rebate?
            # Wait, standard formula for "Hit Probability" (Risk Neutral) is simpler:
            
            # P(Max >= K) = N(d1) + (K/S)^(1 - 2r/sigma^2) * N(d2)
            # Note: This is the probability under the risk-neutral measure Q.
            # If the option pays $1 IMMEDIATELY upon touch, this is the Fair Value.
            # If it pays $1 at Expiry, we discount by e^-rT.
            # Polymarket usually pays immediately (or resolution is triggered).
            
            # Standard Barrier Formula terms:
            arg1 = (math.log(S / K) + (r - 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            arg2 = (math.log(S / K) - (r - 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            
            # Adjust power term carefully
            # Exponent = 1 - 2r/sigma^2
            try:
                power_term = (K / S) ** (1 - (2 * r) / (sigma**2))
            except ZeroDivisionError:
                return 0.0
            
            prob = norm.cdf(arg2) + power_term * norm.cdf(arg2) 
            
            # Wait, checking sources.
            # Reiner and Rubinstein (1991):
            # Price of One-Touch (pays 1 at hit) = (K/S)^(mu+lambda) * N(z) + (K/S)^(mu-lambda) * N(z-2...)
            # The simplified version for P(S_max > K) is:
            # P = N(h1) + (S/K)^(1 - 2r/s^2) * N(h2) ?? No.
            
            # Let's use the standard reflection principle result for Drifted Brownian Motion.
            # For drift mu = r - 0.5*sigma^2:
            # P(Hit K) = N(d_minus) + (K/S)^(2*mu/sigma^2) * N(d_minus + ...)
            
            # Let's stick to the analytically robust one often used in quant libs:
            # Standard Reiner-Rubinstein for "Pay at Hit":
            # A = (K/S)^alpha * N(d3) + (K/S)^beta * N(d4)
            # Where alpha, beta depend on r and sigma.
            
            # However, for simplicity and robustness, we will use the Spread Replication approximation
            # as the PRIMARY actionable signal, and this BS Probability as a "Theoretical Anchor".
            # Let's use the standard "Probability of touching barrier" formula:
            
            mu = r - 0.5 * sigma**2
            a = mu / sigma**2
            
            z = (math.log(K / S) - mu * T) / (sigma * math.sqrt(T))
            y = (math.log(K / S) + mu * T) / (sigma * math.sqrt(T)) # Corrected sign
            
            # P = N(-z) + (K/S)^(2*mu/sigma^2) * N(-y)
            # This is for S < K (Up-and-In)
            
            term1 = norm.cdf(-z)
            term2 = (K / S) ** (2 * a) * norm.cdf(-y)
            
            return term1 + term2

        # Down-and-In (Target < Spot)
        else:
            # Symmetric logic
            mu = r - 0.5 * sigma**2
            a = mu / sigma**2
            
            z = (math.log(K / S) - mu * T) / (sigma * math.sqrt(T))
            y = (math.log(K / S) + mu * T) / (sigma * math.sqrt(T))
            
            # Flip signs for Down barrier
            # P = N(z) + (K/S)^(2a) * N(y)
            
            term1 = norm.cdf(z)
            term2 = (K / S) ** (2 * a) * norm.cdf(y)
            
            return term1 + term2

