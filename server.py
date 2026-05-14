"""eBay Browse API MCP server. Exposes one tool: search_ebay.

Works with any MCP-compatible host (Claude Desktop, Cursor, VS Code Copilot,
Cline, Continue, Zed, Windsurf, LM Studio, Goose, etc).
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ebay_client import ENV, MARKETPLACE, search_items

mcp = FastMCP("ebay-browse")


@mcp.tool()
def search_ebay(
    query: str,
    limit: int = 10,
    filter_expr: Optional[str] = None,
    sort: Optional[str] = None,
) -> dict:
    """Search eBay listings via the Browse API.

    Args:
        query: Search keywords. Examples: "macbook pro m3 64gb",
            "tesla model 3 floor mats", "vintage rolex".
        limit: Maximum results to return (1-200, default 10).
        filter_expr: Browse API filter syntax. Examples:
            - "price:[100..500],priceCurrency:GBP"   (price range)
            - "conditions:{NEW}"                      (new items only)
            - "buyingOptions:{FIXED_PRICE}"           (Buy It Now only)
            - "itemLocationCountry:GB"                (UK sellers only)
            Combine with commas.
        sort: "price" (ascending), "-price" (descending),
            "newlyListed", "endingSoonest". Default is Best Match.

    Returns:
        Simplified dict with: environment, marketplace, query, total,
        returned, and items list (title, price, condition, seller, url, image).
    """
    raw = search_items(query=query, limit=limit, filter_expr=filter_expr, sort=sort)

    items = []
    for it in raw.get("itemSummaries", []):
        price = it.get("price") or {}
        seller = it.get("seller") or {}
        items.append({
            "title": it.get("title"),
            "price": price.get("value"),
            "currency": price.get("currency"),
            "condition": it.get("condition"),
            "seller_username": seller.get("username"),
            "seller_feedback_pct": seller.get("feedbackPercentage"),
            "seller_feedback_score": seller.get("feedbackScore"),
            "item_location": (it.get("itemLocation") or {}).get("country"),
            "url": it.get("itemWebUrl"),
            "image": (it.get("image") or {}).get("imageUrl"),
        })

    return {
        "environment": ENV,
        "marketplace": MARKETPLACE,
        "query": query,
        "total": raw.get("total", 0),
        "returned": len(items),
        "items": items,
    }


if __name__ == "__main__":
    mcp.run()
