# ebay-browse-mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.27+-green.svg)](https://modelcontextprotocol.io)
[![eBay Browse API](https://img.shields.io/badge/eBay-Browse%20API-e53238.svg)](https://developer.ebay.com/api-docs/buy/browse/overview.html)

Minimal MCP server for searching eBay listings via the [Browse API](https://developer.ebay.com/api-docs/buy/browse/overview.html). Communicates over stdio JSON-RPC, so it works with any MCP-compatible host (Claude Desktop, Claude Code, Cursor, VS Code Copilot, Cline, Continue, Zed, Windsurf, LM Studio, Goose, and others).

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
2. Generate an Application Keyset (both sandbox and production keysets are available)
3. Enable OAuth for the keyset on the eBay developer portal
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

### Sandbox vs production

- **`EBAY_ENV=sandbox`** routes requests to `api.sandbox.ebay.com`. Sandbox listings are synthetic test data, not real inventory. Start here to verify your OAuth flow and integration end-to-end with no approval friction.
- **`EBAY_ENV=production`** routes to `api.ebay.com` and returns real eBay listings. To use production you must:
  1. Use the production keyset credentials (different `CLIENT_ID` and `CLIENT_SECRET` than sandbox)
  2. Comply with eBay's [marketplace account deletion notification](https://developer.ebay.com/marketplace-account-deletion) process, or apply for an exemption if you do not store eBay user data
  3. Enable OAuth on the production keyset

Switching environments is a one-line change to `.env`. The credentials for each environment are separate and not interchangeable.

## Test the client directly

```bash
.venv/bin/python ebay_client.py "macbook pro m4 max 64gb"
```

Expected output: a list of items with title, price, and URL.

## Register with your MCP host

The server speaks stdio JSON-RPC. Add it to your host's MCP configuration with two values:

- **command**: absolute path to the venv Python (`/absolute/path/to/ebay-browse-mcp/.venv/bin/python`)
- **args**: `["/absolute/path/to/ebay-browse-mcp/server.py"]`

### Claude Desktop / Claude Code / Cursor / Windsurf / LM Studio / Cherry Studio / Goose

These hosts share the `mcpServers` JSON shape. Add the block below to the relevant config file and restart the host.

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

Config file locations:

| Host | Path |
| --- | --- |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor (global) | `~/.cursor/mcp.json` |
| Cursor (per project) | `.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Claude Code | `claude mcp add ebay-browse /absolute/path/to/.venv/bin/python /absolute/path/to/server.py` (CLI) |

### VS Code Copilot

VS Code uses `servers` (not `mcpServers`) under the `mcp` section of `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "ebay-browse": {
        "command": "/absolute/path/to/ebay-browse-mcp/.venv/bin/python",
        "args": ["/absolute/path/to/ebay-browse-mcp/server.py"]
      }
    }
  }
}
```

### Zed

Zed uses `context_servers` in `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "ebay-browse": {
      "command": {
        "path": "/absolute/path/to/ebay-browse-mcp/.venv/bin/python",
        "args": ["/absolute/path/to/ebay-browse-mcp/server.py"]
      }
    }
  }
}
```

### Continue, Cline and others

Continue (`~/.continue/config.json`) uses an `mcpServers` array; Cline uses `cline_mcp_settings.json` with the same shape as Claude Desktop. Check your host's documentation for the exact file path. The command and args are always the same.

Once registered, restart the host and the `search_ebay` tool becomes available.

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
├── evaluation.xml       10 read-only LLM eval questions
├── ebay_client.py       Browse API client (no MCP dependency)
└── server.py            FastMCP server, wraps ebay_client.search_items
```

## Evaluation

`evaluation.xml` contains 10 read-only questions designed for LLM evaluation harnesses. Questions target stable response properties (shape, field values, filter behaviour) rather than specific listings, because eBay inventory changes constantly. Each question has a single verifiable string answer.

## Comparison with similar projects

Three open-source eBay MCP servers exist as of mid-2026. They target different use cases. Pick the one that fits yours:

| | **ebay-browse-mcp** (this) | [YosefHayim/ebay-mcp](https://github.com/YosefHayim/ebay-mcp) | [CooKey-Monster/EbayMcpServer](https://github.com/CooKey-Monster/EbayMcpServer) |
| --- | --- | --- | --- |
| **Best for** | Buyers: searching public listings | Sellers: managing inventory, orders, ads | Minimal auction listing |
| **eBay API** | Browse API (buyer-side) | Sell APIs (seller-side) | Browse API, single endpoint |
| **Tools** | 1 (`search_ebay`) with filters, sort, pagination | 325 tools, 100% Sell API coverage | 1 (`list_auction`) |
| **Language** | Python | TypeScript / Node 18+ | Python (uv) |
| **Setup** | venv + pip + `.env` | `npm install -g ebay-mcp` + interactive wizard | `uv pip install` |
| **Auth** | Client credentials | Client credentials + user OAuth (refresh tokens, 10k-50k req/day) | Client credentials |
| **Active maintenance** | Yes | Yes (frequent releases) | No (2 commits, stale) |
| **Footprint** | ~190 lines of code | 30+ files, src/api + src/tools + src/auth + scripts | ~5 files |

**Pick `ebay-browse-mcp` (this project) if:** you want an LLM to search eBay listings with filters (price range, condition, location, sort), with minimal setup and a small surface area. The goal is a focused tool that does one thing well.

**Pick YosefHayim/ebay-mcp if:** you run an eBay store and want an LLM to manage your inventory, fulfil orders, run marketing campaigns, or pull analytics. It is the most complete Sell-API integration available.

**Pick CooKey-Monster/EbayMcpServer if:** you want the absolute minimum dependency footprint and only need a single keyword lookup. Note that the repo has not been updated for over a year as of mid-2026.

## License

MIT
