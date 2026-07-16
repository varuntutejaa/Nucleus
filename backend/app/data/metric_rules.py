"""
Threshold rules for turning raw AIOps2020 metric readings into alerts.

Ported from a companion rule-based prototype (see README.md "Bringing your
own dataset") that was run directly against the real AIOps2020 challenge
dataset (2020_MM_DD/.../os_linux.csv, db_oracle_11g.csv, ...). Each rule maps
one metric name to a threshold, a severity, and a human-readable message --
mirroring how a real monitoring system's alerting rules work: a handful of
static thresholds per metric, not a learned model.
"""
import operator

_OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
}

ALERT_RULES = {
    # ================= OS =================
    # CPU_util_pct/MEM_real_util are on a 0-100 scale in the real dataset
    # (median CPU reading ~2.8, median MEM reading ~55) -- the original
    # prototype used a 0.90 threshold meant for a 0-1 fraction, which fires
    # on almost any nonzero reading. Corrected to 90 (percent) here so "high
    # utilization" actually means high utilization.
    "CPU_util_pct": {
        "operator": ">", "threshold": 90,
        "severity": "critical", "message": "High CPU Utilization",
    },
    "Processor_load_5_min": {
        "operator": ">", "threshold": 0.80,
        "severity": "warning", "message": "High Processor Load",
    },
    "MEM_real_util": {
        "operator": ">", "threshold": 90,
        "severity": "critical", "message": "High Memory Utilization",
    },
    "Sent_errors_packets": {
        "operator": ">", "threshold": 0,
        "severity": "critical", "message": "Network Packet Errors",
    },
    "Receive_errors_packets": {
        "operator": ">", "threshold": 0,
        "severity": "critical", "message": "Incoming Packet Errors",
    },
    # ================= Oracle =================
    "Sess_Connect": {
        "operator": ">", "threshold": 500,
        "severity": "warning", "message": "Too Many Database Sessions",
    },
    "DbTime": {
        "operator": ">", "threshold": 1000,
        "severity": "critical", "message": "Database Response Time High",
    },
}


def evaluate(value: float, rule: dict) -> bool:
    return _OPS[rule["operator"]](float(value), rule["threshold"])
