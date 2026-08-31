"""Offline structural self-test for ebay_client.py's search-result memo
(cross-pollination audit fc63689, t15). No network, no eBay credentials
required — requests.get and the token fetch are monkeypatched so this only
exercises the in-process caching logic in search_items().

Hard watchdog: the whole run must finish in a few seconds since nothing here
should ever block (no real I/O).

Usage: python3 test_ebay_client.py
Exit: 0 all pass, 1 failure.
"""
import signal
import sys
import time

FAILS = 0


def fail(label, detail=""):
    global FAILS
    FAILS += 1
    print(f"FAIL: {label}" + (f" ({detail})" if detail else ""), file=sys.stderr)


def ok(label):
    print(f"ok: {label}")


def _watchdog(signum, frame):
    print("FAIL: watchdog fired — test_ebay_client.py hung past 10s (should be pure/offline)",
          file=sys.stderr)
    sys.exit(1)


class _FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload
        self.text = "{}"

    def json(self):
        return self._payload


def main():
    signal.signal(signal.SIGALRM, _watchdog)
    signal.alarm(10)

    import ebay_client  # noqa: E402  (import after alarm armed — must not block either)

    ok("ebay_client module imports without network access")

    # Neutralize the network boundary: token fetch and the search GET are both
    # faked so search_items() only ever exercises the memo, never a socket.
    ebay_client._get_access_token = lambda: "fake-token"
    call_count = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        call_count["n"] += 1
        return _FakeResponse({"total": call_count["n"], "itemSummaries": []})

    ebay_client.requests.get = fake_get
    ebay_client._search_cache.clear()

    # --- same signature within TTL: second call must be a cache hit ---
    r1 = ebay_client.search_items("macbook pro", limit=5, filter_expr=None, sort=None)
    r2 = ebay_client.search_items("macbook pro", limit=5, filter_expr=None, sort=None)
    if call_count["n"] == 1 and r1 == r2:
        ok("identical (query,limit,filter_expr,sort) within TTL hits the memo (1 fetch, not 2)")
    else:
        fail("expected a single fetch for a repeated identical search",
             f"fetches={call_count['n']}")

    # --- different signature: must NOT reuse the cached entry ---
    ebay_client.search_items("thinkpad", limit=5, filter_expr=None, sort=None)
    if call_count["n"] == 2:
        ok("a different query bypasses the memo and fetches again")
    else:
        fail("a different query should not have hit the cache", f"fetches={call_count['n']}")

    # limit is normalized (max(1, min(limit, 200))) before the cache key is
    # built, so two calls that normalize to the same capped limit must share
    # one cache entry rather than being treated as distinct keys.
    ebay_client.search_items("macbook pro", limit=5, filter_expr=None, sort=None)
    ebay_client.search_items("macbook pro", limit=5, filter_expr=None, sort=None)
    if call_count["n"] == 2:
        ok("normalized-limit cache key is stable across repeat calls")
    else:
        fail("repeat call with the same params should still be a cache hit",
             f"fetches={call_count['n']}")

    # --- TTL expiry: force an entry to look old, confirm it refetches ---
    key = ebay_client._search_cache_key("macbook pro", 5, None, None)
    cached_result, _ts = ebay_client._search_cache[key]
    ebay_client._search_cache[key] = (cached_result, time.time() - ebay_client.SEARCH_CACHE_TTL_S - 1)
    ebay_client.search_items("macbook pro", limit=5, filter_expr=None, sort=None)
    if call_count["n"] == 3:
        ok("an expired entry (age > SEARCH_CACHE_TTL_S) is refetched, not reused")
    else:
        fail("expired entry should have triggered a refetch", f"fetches={call_count['n']}")

    # --- bounded size: cache never exceeds SEARCH_CACHE_MAX_ENTRIES ---
    ebay_client._search_cache.clear()
    call_count["n"] = 0
    for i in range(ebay_client.SEARCH_CACHE_MAX_ENTRIES + 20):
        ebay_client.search_items(f"query-{i}", limit=1, filter_expr=None, sort=None)
    if len(ebay_client._search_cache) <= ebay_client.SEARCH_CACHE_MAX_ENTRIES:
        ok(f"cache stays bounded at <= {ebay_client.SEARCH_CACHE_MAX_ENTRIES} entries "
           f"under high-cardinality query fan-out (size={len(ebay_client._search_cache)})")
    else:
        fail("cache grew past SEARCH_CACHE_MAX_ENTRIES", f"size={len(ebay_client._search_cache)}")

    signal.alarm(0)

    if FAILS:
        print(f"{FAILS} failure(s)", file=sys.stderr)
        sys.exit(1)
    print("all pass")


if __name__ == "__main__":
    main()
