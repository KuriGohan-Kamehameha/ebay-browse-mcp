"""eBay Browse API MCP server. Exposes two tools: search_ebay, get_item_details.

Works with any MCP-compatible host (Claude Desktop, Cursor, VS Code Copilot,
Cline, Continue, Zed, Windsurf, LM Studio, Goose, etc).
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ebay_client import ENV, MARKETPLACE, get_item, search_items

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
        returned, and items list. Each item includes "item_id" which can
        be passed to get_item_details for the full record.
    """
    raw = search_items(query=query, limit=limit, filter_expr=filter_expr, sort=sort)

    items = []
    for it in raw.get("itemSummaries", []):
        price = it.get("price") or {}
        seller = it.get("seller") or {}
        items.append({
            "item_id": it.get("itemId"),
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


@mcp.tool()
def get_item_details(item_id: str, fieldgroups: Optional[str] = None) -> dict:
    """Retrieve full details of a specific eBay item.

    Use this when search_ebay has surfaced an item and you need richer
    information: full description, item specifics (aspects), shipping
    options, return policy, all images, seller details, etc.

    Args:
        item_id: REST item identifier from search_ebay's "item_id" field
            (format: "v1|<numeric>|0"). Legacy numeric IDs alone are not
            accepted by this endpoint.
        fieldgroups: Optional response shaping.
            - None (default): full item details
            - "COMPACT": small subset for change detection (price,
              availability, revision id, top-rated status)
            - "PRODUCT": default plus product catalogue info

    Returns:
        Simplified dict with the most useful fields: title, price,
        condition, description, item specifics, images, shipping options,
        return policy, seller, location, and url. The "raw" key holds the
        full Browse API response in case anything was filtered out.
    """
    raw = get_item(item_id=item_id, fieldgroups=fieldgroups)

    price = raw.get("price") or {}
    seller = raw.get("seller") or {}
    location = raw.get("itemLocation") or {}
    primary_image = (raw.get("image") or {}).get("imageUrl")
    additional_images = [
        img.get("imageUrl")
        for img in (raw.get("additionalImages") or [])
        if img.get("imageUrl")
    ]

    # Item specifics (aspects) are returned as a list of {name, value} dicts
    aspects = {}
    for aspect in raw.get("localizedAspects") or []:
        name = aspect.get("name")
        value = aspect.get("value")
        if name and value is not None:
            aspects[name] = value

    shipping_options = []
    for opt in raw.get("shippingOptions") or []:
        cost = opt.get("shippingCost") or {}
        shipping_options.append({
            "type": opt.get("type"),
            "cost": cost.get("value"),
            "currency": cost.get("currency"),
            "min_estimated_delivery": opt.get("minEstimatedDeliveryDate"),
            "max_estimated_delivery": opt.get("maxEstimatedDeliveryDate"),
        })

    return_terms = raw.get("returnTerms") or {}

    return {
        "environment": ENV,
        "marketplace": MARKETPLACE,
        "item_id": raw.get("itemId"),
        "legacy_item_id": raw.get("legacyItemId"),
        "title": raw.get("title"),
        "subtitle": raw.get("subtitle"),
        "short_description": raw.get("shortDescription"),
        "description": raw.get("description"),
        "price": price.get("value"),
        "currency": price.get("currency"),
        "condition": raw.get("condition"),
        "condition_id": raw.get("conditionId"),
        "brand": raw.get("brand"),
        "mpn": raw.get("mpn"),
        "category_path": raw.get("categoryPath"),
        "buying_options": raw.get("buyingOptions"),
        "estimated_availabilities": raw.get("estimatedAvailabilities"),
        "aspects": aspects,
        "images": ([primary_image] if primary_image else []) + additional_images,
        "seller": {
            "username": seller.get("username"),
            "feedback_pct": seller.get("feedbackPercentage"),
            "feedback_score": seller.get("feedbackScore"),
        },
        "item_location": {
            "country": location.get("country"),
            "city": location.get("city"),
            "postal_code": location.get("postalCode"),
        },
        "shipping_options": shipping_options,
        "return_terms": {
            "returns_accepted": return_terms.get("returnsAccepted"),
            "return_period": (return_terms.get("returnPeriod") or {}).get("value"),
            "refund_method": return_terms.get("refundMethod"),
            "return_shipping_cost_payer": return_terms.get("returnShippingCostPayer"),
        },
        "url": raw.get("itemWebUrl"),
    }


if __name__ == "__main__":
    mcp.run()
