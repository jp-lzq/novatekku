import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any

import httpx

from app.core.config import settings

FX_FILE_PATH = os.getenv("FX_CACHE_FILE") or os.path.join(os.path.dirname(__file__), "..", "data", "fx_rates.json")
FX_FILE_PATH = os.path.abspath(FX_FILE_PATH)

DEFAULT_RATES = {
    "USD": {"rate": 155.76, "symbol": "$", "flag": "🇺🇸"},
    "HKD": {"rate": 19.92, "symbol": "HK$", "flag": "🇭🇰"},
    "CNY": {"rate": 22.62, "symbol": "¥", "flag": "🇨🇳"},
    "EUR": {"rate": 183.49, "symbol": "€", "flag": "🇪🇺"},
}

FX_CACHE: Dict[str, Any] = {
    "rates": DEFAULT_RATES,
    "last_updated": None,
}


def _load_from_disk() -> None:
    if not os.path.exists(FX_FILE_PATH):
        return
    try:
        with open(FX_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "rates" in data:
            FX_CACHE["rates"] = data.get("rates", DEFAULT_RATES)
            FX_CACHE["last_updated"] = data.get("last_updated")
    except Exception:
        pass


def _save_to_disk() -> None:
    os.makedirs(os.path.dirname(FX_FILE_PATH), exist_ok=True)
    payload = {
        "rates": FX_CACHE["rates"],
        "last_updated": FX_CACHE["last_updated"],
    }
    with open(FX_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def fetch_fx_rates() -> Dict[str, Any]:
    """Fetch FX rates and return {rates, last_updated}."""
    response = httpx.get(settings.fx_rates_url, timeout=20)
    response.raise_for_status()
    data = response.json()

    rates = data.get("rates", {})
    if not rates:
        raise ValueError("Missing rates in FX response")

    def jpy_per(currency: str) -> float:
        value = rates.get(currency)
        if not value:
            raise ValueError(f"Missing rate for {currency}")
        return round(1 / float(value), 2)

    fresh_rates = {
        "USD": {"rate": jpy_per("USD"), "symbol": "$", "flag": "🇺🇸"},
        "HKD": {"rate": jpy_per("HKD"), "symbol": "HK$", "flag": "🇭🇰"},
        "CNY": {"rate": jpy_per("CNY"), "symbol": "¥", "flag": "🇨🇳"},
        "EUR": {"rate": jpy_per("EUR"), "symbol": "€", "flag": "🇪🇺"},
    }

    return {
        "rates": fresh_rates,
        "last_updated": datetime.now().isoformat(),
    }


def update_fx_rates() -> Dict[str, Any]:
    """Update cache and disk from remote."""
    payload = fetch_fx_rates()
    FX_CACHE["rates"] = payload["rates"]
    FX_CACHE["last_updated"] = payload["last_updated"]
    _save_to_disk()
    return payload


def get_fx_rates() -> Dict[str, Any]:
    if FX_CACHE["last_updated"] is None:
        _load_from_disk()

    # Refresh if older than 2 hours
    last_updated = FX_CACHE.get("last_updated")
    if last_updated:
        try:
            ts = datetime.fromisoformat(last_updated)
            if datetime.now() - ts > timedelta(hours=2):
                return update_fx_rates()
        except Exception:
            pass

    return {
        "rates": FX_CACHE["rates"],
        "last_updated": FX_CACHE.get("last_updated"),
    }


try:
    from celery import shared_task

    @shared_task
    def update_fx_rates_task():
        return update_fx_rates()

except ImportError:
    pass
