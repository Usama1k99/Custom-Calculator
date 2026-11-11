"""
Currency Exchange Engine.
Provides live exchange rate conversions using free public APIs with offline fallback & caching.
Zero external dependencies; uses standard library urllib.request and json.
Zero emojis in all labels and UI text.
"""

import json
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from src.core.config import ConfigManager

PRIMARY_API_URL = "https://open.er-api.com/v6/latest/USD"
FALLBACK_API_URL = "https://api.frankfurter.app/latest?from=USD"

# Comprehensive Currencies with symbols & full names
CURRENCY_METADATA = {
    "USD": ("US Dollar", "$"),
    "EUR": ("Euro", "€"),
    "GBP": ("British Pound", "£"),
    "JPY": ("Japanese Yen", "¥"),
    "CAD": ("Canadian Dollar", "CA$"),
    "AUD": ("Australian Dollar", "A$"),
    "CHF": ("Swiss Franc", "CHF"),
    "CNY": ("Chinese Yuan", "¥"),
    "INR": ("Indian Rupee", "₹"),
    "BRL": ("Brazilian Real", "R$"),
    "RUB": ("Russian Ruble", "₽"),
    "KRW": ("South Korean Won", "₩"),
    "SGD": ("Singapore Dollar", "S$"),
    "NZD": ("New Zealand Dollar", "NZ$"),
    "MXN": ("Mexican Peso", "Mex$"),
    "HKD": ("Hong Kong Dollar", "HK$"),
    "SEK": ("Swedish Krona", "kr"),
    "NOK": ("Norwegian Krone", "kr"),
    "TRY": ("Turkish Lira", "₺"),
    "ZAR": ("South African Rand", "R"),
    "AED": ("UAE Dirham", "AED"),
    "SAR": ("Saudi Riyal", "SAR"),
    "PKR": ("Pakistani Rupee", "PKR"),
    "IDR": ("Indonesian Rupiah", "Rp"),
    "MYR": ("Malaysian Ringgit", "RM"),
    "THB": ("Thai Baht", "฿"),
    "PHP": ("Philippine Peso", "₱"),
    "DKK": ("Danish Krone", "kr"),
    "PLN": ("Polish Zloty", "zł"),
    "ILS": ("Israeli Shekel", "₪"),
    "EGP": ("Egyptian Pound", "E£"),
    "KWD": ("Kuwaiti Dinar", "KD"),
    "QAR": ("Qatari Riyal", "QR"),
    "CLP": ("Chilean Peso", "CLP$"),
    "COP": ("Colombian Peso", "COL$"),
    "VND": ("Vietnamese Dong", "₫"),
}

# Reliable offline fallback rates against 1.0 USD
DEFAULT_OFFLINE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "JPY": 154.0,
    "CAD": 1.38,
    "AUD": 1.52,
    "CHF": 0.88,
    "CNY": 7.23,
    "INR": 84.3,
    "BRL": 5.80,
    "RUB": 98.0,
    "KRW": 1390.0,
    "SGD": 1.32,
    "NZD": 1.67,
    "MXN": 20.1,
    "HKD": 7.77,
    "SEK": 10.8,
    "NOK": 11.0,
    "TRY": 34.5,
    "ZAR": 17.5,
    "AED": 3.67,
    "SAR": 3.75,
    "PKR": 278.0,
    "IDR": 15600.0,
    "MYR": 4.40,
    "THB": 34.2,
    "PHP": 58.5,
    "DKK": 6.89,
    "PLN": 4.02,
    "ILS": 3.72,
    "EGP": 49.2,
    "KWD": 0.31,
    "QAR": 3.64,
    "CLP": 950.0,
    "COP": 4350.0,
    "VND": 25300.0,
}


def format_currency_label(code: str) -> str:
    """Returns human-readable label like 'USD - US Dollar ($)'."""
    meta = CURRENCY_METADATA.get(code)
    if meta:
        name, sym = meta
        return f"{code} - {name} ({sym})"
    return code


def code_from_label(label: str) -> str:
    """Extracts 3-letter currency code from formatted label."""
    return label.split(" - ")[0].strip()


class CurrencyEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_engine()
            return cls._instance

    def _init_engine(self):
        self.config = ConfigManager()
        self.rates = dict(DEFAULT_OFFLINE_RATES)
        self.last_updated_str = "Offline standard rates"
        self.is_fetching = False

        # Load cached rates from config if available
        cached = self.config.get("cached_currency_rates", {})
        cached_time = self.config.get("cached_currency_timestamp", "")
        if cached and isinstance(cached, dict):
            for k, v in cached.items():
                if isinstance(v, (int, float)) and v > 0:
                    self.rates[k] = float(v)
            if cached_time:
                self.last_updated_str = f"Cached ({cached_time})"

    def get_currency_list(self) -> list:
        """Returns ordered list of formatted currency labels."""
        ordered = []
        for code in CURRENCY_METADATA.keys():
            if code in self.rates:
                ordered.append(format_currency_label(code))
        # Add any extra rates returned by API
        for code in sorted(self.rates.keys()):
            label = format_currency_label(code)
            if label not in ordered:
                ordered.append(label)
        return ordered

    def get_rate(self, code: str) -> float:
        """Returns units per 1 USD (e.g. EUR = 0.92 per USD)."""
        return self.rates.get(code, 1.0)

    def convert(self, amount: float, from_code: str, to_code: str) -> float:
        """Converts amount from from_code to to_code using USD as base."""
        r_from = self.get_rate(from_code)
        r_to = self.get_rate(to_code)
        if r_from <= 0:
            return 0.0
        # amount in USD = amount / r_from
        # amount in target = (amount / r_from) * r_to
        return (amount / r_from) * r_to

    def fetch_live_rates_async(self, callback: Optional[Callable[[bool, str], None]] = None):
        """Asynchronously fetches live rates from free public endpoints in a background thread."""
        if self.is_fetching:
            return

        def _worker():
            self.is_fetching = True
            success, msg = self._fetch_live_rates_sync()
            self.is_fetching = False
            if callback:
                try:
                    callback(success, msg)
                except Exception:
                    pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _fetch_live_rates_sync(self) -> Tuple[bool, str]:
        """Attempts primary open.er-api.com endpoint, then frankfurter fallback."""
        # 1. Try Primary: open.er-api.com
        try:
            req = urllib.request.Request(
                PRIMARY_API_URL,
                headers={"User-Agent": "ApexCalculator/1.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    api_rates = data.get("rates", {})
                    if api_rates and len(api_rates) > 10:
                        for k, v in api_rates.items():
                            try:
                                self.rates[k] = float(v)
                            except (ValueError, TypeError):
                                pass
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        self.last_updated_str = f"Live rates ({now_str})"
                        self.config.set("cached_currency_rates", self.rates)
                        self.config.set("cached_currency_timestamp", now_str)
                        return True, self.last_updated_str
        except Exception:
            pass

        # 2. Try Fallback: Frankfurter
        try:
            req = urllib.request.Request(
                FALLBACK_API_URL,
                headers={"User-Agent": "ApexCalculator/1.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    api_rates = data.get("rates", {})
                    if api_rates and len(api_rates) > 5:
                        for k, v in api_rates.items():
                            try:
                                self.rates[k] = float(v)
                            except (ValueError, TypeError):
                                pass
                        self.rates["USD"] = 1.0
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        self.last_updated_str = f"Live rates ({now_str})"
                        self.config.set("cached_currency_rates", self.rates)
                        self.config.set("cached_currency_timestamp", now_str)
                        return True, self.last_updated_str
        except Exception as e:
            return False, f"Could not sync live rates: {str(e)}"

        return False, "Failed to connect to currency servers."
