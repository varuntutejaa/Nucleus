#!/usr/bin/env python3
"""
Sanity check: hits both Nucleus endpoints against a running server and
asserts the response shape matches API_CONTRACT.md, plus a handful of
cross-checks that the numbers are internally consistent (e.g. cluster_count
actually equals len(clusters), every cluster's size equals 1 + len(suppressed)).

Usage:
    python scripts/sanity_check.py [base_url]

Exits non-zero with a clear message on the first failure.
"""
import sys

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

ALERT_FIELDS = {
    "id": str,
    "timestamp": str,
    "timestamp_unix": (int, float),
    "service": str,
    "severity": str,
    "severity_rank": int,
    "message": str,
    "source": str,
}
VALID_SEVERITIES = {"critical", "warning", "info"}

_failures = []
_passed = 0


def check(condition, message):
    global _passed
    if not condition:
        _failures.append(message)
        print(f"  [FAIL] {message}")
    else:
        _passed += 1


def assert_alert_shape(alert, context):
    for field, types in ALERT_FIELDS.items():
        check(field in alert, f"{context}: alert missing field '{field}'")
        if field in alert:
            check(
                isinstance(alert[field], types),
                f"{context}: alert['{field}'] has wrong type ({type(alert[field]).__name__})",
            )
    if "severity" in alert:
        check(
            alert["severity"] in VALID_SEVERITIES,
            f"{context}: unexpected severity '{alert['severity']}'",
        )
    check("incident_id" not in alert, f"{context}: ground-truth 'incident_id' leaked into API response")


def main():
    print(f"Nucleus sanity check against {BASE_URL}\n")

    try:
        raw_resp = httpx.get(f"{BASE_URL}/api/alerts/raw", timeout=30)
    except httpx.ConnectError:
        print(f"Could not connect to {BASE_URL}. Is the backend running?")
        print("  cd backend && uvicorn app.main:app --port 8000")
        sys.exit(2)

    print("GET /api/alerts/raw")
    check(raw_resp.status_code == 200, f"expected 200, got {raw_resp.status_code}")
    raw = raw_resp.json()
    check("alerts" in raw and "count" in raw, "response missing 'alerts' or 'count'")
    check(isinstance(raw.get("alerts"), list), "'alerts' is not a list")
    check(raw.get("count") == len(raw.get("alerts", [])), "'count' does not match len(alerts)")
    check(raw.get("count", 0) > 0, "raw alert stream is empty")
    if raw.get("alerts"):
        assert_alert_shape(raw["alerts"][0], "raw.alerts[0]")
        timestamps = [a["timestamp_unix"] for a in raw["alerts"]]
        check(timestamps == sorted(timestamps), "raw alerts are not sorted ascending by timestamp")
    print(f"  {raw.get('count', 0)} alerts, shape OK")

    print("\nGET /api/alerts/correlated (defaults)")
    corr_resp = httpx.get(f"{BASE_URL}/api/alerts/correlated", timeout=60)
    check(corr_resp.status_code == 200, f"expected 200, got {corr_resp.status_code}")
    corr = corr_resp.json()
    for key in ("clusters", "noise", "metrics"):
        check(key in corr, f"response missing '{key}'")

    metrics = corr.get("metrics", {})
    for key in ("raw_count", "cluster_count", "noise_count", "suppressed_count",
                "reduction_pct", "embedding_backend"):
        check(key in metrics, f"metrics missing '{key}'")

    clusters = corr.get("clusters", [])
    noise = corr.get("noise", [])
    check(metrics.get("raw_count") == raw.get("count"), "metrics.raw_count != raw endpoint count")
    check(metrics.get("cluster_count") == len(clusters), "metrics.cluster_count != len(clusters)")
    check(metrics.get("noise_count") == len(noise), "metrics.noise_count != len(noise)")
    check(0 <= metrics.get("reduction_pct", -1) <= 100, "reduction_pct out of [0, 100] range")

    for c in clusters:
        for field in ("cluster_id", "root_cause", "suppressed", "size", "time_span_seconds", "explanation"):
            check(field in c, f"cluster {c.get('cluster_id')} missing '{field}'")
        check(
            c.get("size") == 1 + len(c.get("suppressed", [])),
            f"cluster {c.get('cluster_id')}: size != 1 + len(suppressed)",
        )
        check(c.get("time_span_seconds", -1) >= 0, f"cluster {c.get('cluster_id')}: negative time_span_seconds")
        if c.get("root_cause"):
            assert_alert_shape(c["root_cause"], f"cluster {c.get('cluster_id')}.root_cause")
        for s in c.get("suppressed", []):
            assert_alert_shape(s, f"cluster {c.get('cluster_id')}.suppressed[]")
    if noise:
        assert_alert_shape(noise[0], "noise[0]")
    print(
        f"  {len(clusters)} clusters, {len(noise)} noise, "
        f"{metrics.get('reduction_pct')}% reduction, shape OK"
    )

    print("\nGET /api/alerts/correlated (custom weights reshape the result)")
    alt_resp = httpx.get(
        f"{BASE_URL}/api/alerts/correlated",
        params={"alpha": 0.9, "beta": 0.05, "gamma": 0.05},
        timeout=60,
    )
    check(alt_resp.status_code == 200, f"expected 200, got {alt_resp.status_code}")
    alt = alt_resp.json()
    check(
        alt.get("metrics", {}).get("weights_used") == {"alpha": 0.9, "beta": 0.05, "gamma": 0.05},
        "weights_used does not echo back the requested alpha/beta/gamma",
    )
    check(
        alt.get("metrics", {}).get("cluster_count") != metrics.get("cluster_count")
        or alt.get("metrics", {}).get("noise_count") != metrics.get("noise_count"),
        "changing alpha/beta/gamma produced an identical result (sliders should reshape clusters)",
    )
    print(f"  weights_used echoed correctly, result reshaped vs defaults")

    print("\nGET /api/alerts/raw?source=dataset (bundled loghub fixture)")
    ds_resp = httpx.get(f"{BASE_URL}/api/alerts/raw", params={"source": "dataset"}, timeout=30)
    check(ds_resp.status_code == 200, f"expected 200, got {ds_resp.status_code}")
    check(ds_resp.json().get("count", 0) > 0, "dataset source returned zero alerts")
    print(f"  {ds_resp.json().get('count', 0)} alerts, shape OK")

    print(f"\n{_passed} checks passed.")
    if _failures:
        print(f"FAILED: {len(_failures)} check(s) failed:")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
