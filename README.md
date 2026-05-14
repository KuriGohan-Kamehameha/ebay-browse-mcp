# ebay-browse-mcp

Minimal MCP server for searching eBay listings via the [Browse API](https://developer.ebay.com/api-docs/buy/browse/overview.html). Designed to plug into Claude Desktop (or any MCP host) so an LLM can run searches on your behalf.

## Features

- One tool: `search_ebay` (keyword, filters, sort, pagination via limit)
- OAuth 2.0 client credentials flow, token cached in memory
- Sandbox or production via a single env var
- Pure Python, no framework lock-in beyond the official MCP SDK

## Install

```bash
git clone https://github.com/<your-username>/ebay-browse-mcp.git
cd ebay-browse-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Configure

1. Create an eBay developer account at https://developer.ebay.com
2. Generate an Application Keyset (sandbox or production)
3. Enable OAuth for that keyset on the eBay developer portal
4. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
nano .env
```

```
EBAY_CLIENT_ID=your_app_id_here
EBAY_CLIENT_SECRET=your_cert_id_here
EBAY_MARKETPLACE=EBAY_GB
EBAY_ENV=sandbox
```

> Production keysets require eBay's marketplace account deletion notification setup. If you don't store eBay user data (e.g. you only do public search), apply for the exemption on the developer portal.

## Test the client directly

```bash
.venv/bin/python ebay_client.py "macbook pro m4 max 64gb"
```

Expected output: a list of items with title, price, and URL.

## Register with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` and add the server to the `mcpServers` block:

```json
{
  "mcpServers": {
    "ebay-browse": {
      "command": "/absolute/path/to/ebay-browse-mcp/.venv/bin/python",
      "args": [
        "/absolute/path/to/ebay-browse-mcp/server.py"
      ]
    }
  }
}
```

Restart Claude Desktop. The tool `search_ebay` becomes available.

## Tool: `search_ebay`

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | yes | Search keyword, e.g. `"macbook pro m4 max 64gb"` |
| `limit` | integer | no (default 10) | Number of results, 1-200 |
| `filter_expr` | string | no | Browse API filter syntax, see below |
| `sort` | string | no | `price`, `-price`, `newlyListed`, `endingSoonest` |

### Filter examples

| Goal | `filter_expr` |
| --- | --- |
| Price range in GBP | `price:[100..500],priceCurrency:GBP` |
| New condition only | `conditions:{NEW}` |
| Buy It Now only | `buyingOptions:{FIXED_PRICE}` |
| UK sellers only | `itemLocationCountry:GB` |

Combine with commas: `price:[800..3500],priceCurrency:GBP,itemLocationCountry:GB`.

Full reference: https://developer.ebay.com/api-docs/buy/static/ref-buy-browse-filters.html

## Project structure

```
ebay-browse-mcp/
├── .env.example         template; copy to .env
├── .gitignore
├── README.md
├── requirements.txt
├── ebay_client.py       Browse API client (no MCP dependency)
└── server.py            FastMCP server, wraps ebay_client.search_items
```

## License

MIT
