# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 11:49:16 2026

@author: DELL
"""

"""
Alert Rules
"""

ALERT_RULES = {

    # ================= OS ==================

    "CPU_util_pct": {
        "operator": ">",
        "threshold": 0.90,
        "severity": "Critical",
        "message": "High CPU Utilization"
    },

    "Processor_load_5_min": {
        "operator": ">",
        "threshold": 0.80,
        "severity": "Warning",
        "message": "High Processor Load"
    },

    "MEM_real_util": {
        "operator": ">",
        "threshold": 0.90,
        "severity": "Critical",
        "message": "High Memory Utilization"
    },

    "Sent_errors_packets": {
        "operator": ">",
        "threshold": 0,
        "severity": "Critical",
        "message": "Network Packet Errors"
    },

    "Receive_errors_packets": {
        "operator": ">",
        "threshold": 0,
        "severity": "Critical",
        "message": "Incoming Packet Errors"
    },

    # ================= Oracle ==================

    "Sess_Connect": {
        "operator": ">",
        "threshold": 500,
        "severity": "Warning",
        "message": "Too Many Database Sessions"
    },

    "DbTime": {
        "operator": ">",
        "threshold": 1000,
        "severity": "Critical",
        "message": "Database Response Time High"
    }
}