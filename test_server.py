"""Offline structural self-test for server.py (cross-pollination audit fc63689,
t5). No network, no eBay credentials required — this only asserts the MCP
surface is wired correctly (tool registration, schemas) and that the one
local pure function (_cap, the t6 output-cap helper) truncates as documented.

Hard watchdog: the whole run must finish in a few seconds since nothing here
should ever block (no I/O). A signal alarm fails loudly instead of hanging if
that assumption is ever violated by a future change.

Usage: python3 test_server.py
Exit: 0 all pass, 1 failure.
"""
import asyncio
import signal
import sys

FAILS = 0


def fail(label, detail=""):
    global FAILS
    FAILS += 1
    print(f"FAIL: {label}" + (f" ({detail})" if detail else ""), file=sys.stderr)


def ok(label):
    print(f"ok: {label}")


def _watchdog(signum, frame):
    print("FAIL: watchdog fired — test_server.py hung past 10s (should be pure/offline)",
          file=sys.stderr)
    sys.exit(1)


def main():
    signal.signal(signal.SIGALRM, _watchdog)
    signal.alarm(10)

    import server  # noqa: E402  (import after alarm armed — module-load must not block either)

    ok("server module imports without network access")

    if getattr(server, "__version__", None):
        ok(f"__version__ present ({server.__version__})")
    else:
        fail("__version__ missing")

    # --- tools/list probe (structural — no tool is actually invoked) ---
    tools = asyncio.run(server.mcp.list_tools())
    names = sorted(t.name for t in tools)
    if names == ["get_item_details", "search_ebay"]:
        ok("tools/list exposes exactly search_ebay + get_item_details")
    else:
        fail("tools/list unexpected set", str(names))

    by_name = {t.name: t for t in tools}
    search_schema = by_name.get("search_ebay").inputSchema if "search_ebay" in by_name else {}
    if "query" in (search_schema.get("required") or []):
        ok("search_ebay schema requires 'query'")
    else:
        fail("search_ebay schema missing required 'query'", str(search_schema))

    item_schema = by_name.get("get_item_details").inputSchema if "get_item_details" in by_name else {}
    if "item_id" in (item_schema.get("required") or []):
        ok("get_item_details schema requires 'item_id'")
    else:
        fail("get_item_details schema missing required 'item_id'", str(item_schema))

    # --- _cap (t6 output cap) pure-function checks ---
    if server._cap(None) is None:
        ok("_cap(None) passes through")
    else:
        fail("_cap(None) should pass through unchanged")

    short = "short text"
    if server._cap(short) == short:
        ok("_cap leaves under-limit text untouched")
    else:
        fail("_cap mutated under-limit text")

    long_text = "x" * (server.MAX_DESCRIPTION_CHARS + 500)
    capped = server._cap(long_text)
    if (
        len(capped) < len(long_text)
        and capped.startswith("x" * 100)
        and "truncated" in capped
    ):
        ok("_cap truncates over-limit text with a visible marker")
    else:
        fail("_cap did not truncate over-limit text as expected")

    signal.alarm(0)

    if FAILS:
        print(f"{FAILS} failure(s)", file=sys.stderr)
        sys.exit(1)
    print("all pass")


if __name__ == "__main__":
    main()
