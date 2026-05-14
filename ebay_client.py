"""eBay Browse API client. Standalone Python, no MCP dependency."""
import os
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# Load .env from the same directory as this file, regardless of CWD
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(_ENV_PATH)

CLIENT_ID = os.environ.get("EBAY_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET", "")
MARKETPLACE = os.environ.get("EBAY_MARKETPLACE", "EBAY_GB")
ENV = os.environ.get("EBAY_ENV", "sandbox").lower()

if ENV == "production":
    BASE = "https://api.ebay.com"
else:
    BASE = "https://api.sandbox.ebay.com"

TOKEN_URL = f"{BASE}/identity/v1/oauth2/token"
SEARCH_URL = f"{BASE}/buy/browse/v1/item_summary/search"

# In-memory token cache (process-local)
_token_cache = {"value": None, "expires_at": 0.0}


def _get_access_token() -> str:
    """Fetch an OAuth application access token via client credentials flow.

    Token is cached in memory and reused until 60s before its expiry.
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set in .env"
        )

    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires_at"]:
        return _token_cache["value"]

    response = requests.post(
        TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Token request failed ({response.status_code}): {response.text[:300]}"
        )
    payload = response.json()
    _token_cache["value"] = payload["access_token"]
    # 60s safety margin before actual expiry
    _token_cache["expires_at"] = now + payload["expires_in"] - 60
    return _token_cache["value"]


def search_items(
    query: str,
    limit: int = 10,
    filter_expr: Optional[str] = None,
    sort: Optional[str] = None,
) -> dict:
    """Search eBay listings via the Browse API.

    Args:
        query: Keyword(s), e.g. "macbook pro m3 64gb".
        limit: Number of results to return (1-200, default 10).
        filter_expr: Browse API filter syntax, e.g.
            "price:[100..500],priceCurrency:GBP,conditions:{NEW}"
        sort: "price" (ascending), "-price" (descending),
            "newlyListed", or "endingSoonest". Default is Best Match.

    Returns:
        Raw Browse API response dict (itemSummaries, total, etc).
    """
    params = {"q": query, "limit": max(1, min(limit, 200))}
    if filter_expr:
        params["filter"] = filter_expr
    if sort:
        params["sort"] = sort

    token = _get_access_token()
    response = requests.get(
        SEARCH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE,
            "Content-Type": "application/json",
        },
        params=params,
        timeout=15,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Search failed ({response.status_code}): {response.text[:500]}"
        )
    return response.json()


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "iphone"
    print(f"[env: {ENV}, marketplace: {MARKETPLACE}]")
    print(f"Searching: {q}\n")
    result = search_items(q, limit=3)
    print(f"Total: {result.get('total', 0)}")
    print(f"Returned: {len(result.get('itemSummaries', []))}\n")
    for item in result.get("itemSummaries", []):
        price = item.get("price", {})
        print(f"- {item.get('title', '')[:80]}")
        print(f"  {price.get('value', '?')} {price.get('currency', '?')}")
        print(f"  {item.get('itemWebUrl', '')}\n")
