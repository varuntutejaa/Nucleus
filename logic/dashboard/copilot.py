# -*- coding: utf-8 -*-
"""
SentinelAI Copilot
"""

import streamlit as st
import pandas as pd

from dashboard.utils import load_data


# ==========================================================
# COPILOT
# ==========================================================

def show_copilot():

    st.title("🤖 SentinelAI Copilot")

    st.caption(
        "AI Assistant for Infrastructure Operations"
    )

    # ======================================================
    # LOAD DATA
    # ======================================================

    data = load_data()

    alerts = data["alerts.csv"]

    incidents = data["incident_summary.csv"]

    roots = data["root_cause.csv"]

    suppressed = data["suppressed_alerts.csv"]

    stats = data["incident_statistics.csv"]

    # ======================================================
    # BASIC METRICS
    # ======================================================

    total_alerts = len(alerts)

    total_incidents = len(incidents)

    total_roots = len(roots)

    total_suppressed = len(suppressed)

    reduction = (

        total_suppressed

        /

        total_alerts

    ) * 100

    avg_confidence = (

        stats["avg_confidence"]

        .mean()

    )

    top_metric = (

        roots["metric"]

        .value_counts()

        .idxmax()

    )

    top_host = (

        stats

        .sort_values(

            "incidents",

            ascending=False

        )

        .iloc[0]["host"]

    )

    # ======================================================
    # KPI CARDS
    # ======================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(

        "🚨 Alerts",

        f"{total_alerts:,}"

    )

    c2.metric(

        "🔗 Incidents",

        f"{total_incidents:,}"

    )

    c3.metric(

        "🔥 Root Causes",

        f"{total_roots:,}"

    )

    c4.metric(

        "🎯 Confidence",

        f"{avg_confidence:.2f}"

    )

    st.write("")

    # ======================================================
    # EXECUTIVE SUMMARY
    # ======================================================

    st.success(f"""

### Infrastructure Summary

Alerts Processed

**{total_alerts:,}**

---

Correlated Incidents

**{total_incidents:,}**

---

Root Causes

**{total_roots:,}**

---

Alert Reduction

**{reduction:.2f}%**

---

Average Confidence

**{avg_confidence:.2f}**

---

Most Active Host

**{top_host}**

---

Top Root Cause

**{top_metric}**

""")

    st.write("")

    # ======================================================
    # SMART RECOMMENDATIONS
    # ======================================================

    st.subheader("💡 Suggested Actions")

    metric = str(top_metric).lower()

    if "cpu" in metric:

        st.info("""
### CPU Recommendations

• Investigate CPU-intensive processes

• Review recent deployments

• Verify autoscaling policies

• Check application logs

• Restart overloaded services if necessary
""")

    elif "memory" in metric:

        st.info("""
### Memory Recommendations

• Check memory utilization

• Look for memory leaks

• Restart affected services

• Increase memory allocation if required

• Review container/JVM limits
""")

    elif "disk" in metric:

        st.info("""
### Disk Recommendations

• Inspect disk usage

• Check I/O performance

• Remove temporary files

• Verify storage health

• Monitor filesystem growth
""")

    elif "redis" in metric:

        st.info("""
### Redis Recommendations

• Check Redis latency

• Verify client connections

• Inspect Redis logs

• Review cache hit ratio

• Check memory fragmentation
""")

    elif "oracle" in metric:

        st.info("""
### Oracle Recommendations

• Review Oracle alert logs

• Check active sessions

• Inspect slow queries

• Verify tablespace usage

• Check listener status
""")

    else:

        st.info("""
### General Recommendations

• Review infrastructure health

• Inspect correlated incidents

• Check application logs

• Validate monitoring thresholds

• Continue monitoring
""")

    st.write("")

    # ======================================================
    # ASK SENTINELAI
    # ======================================================

    st.subheader("💬 Ask SentinelAI")

    question = st.text_input(

        "Ask a question",

        placeholder="Example: Which host has the most incidents?"

    )

    st.write("")

    # ======================================================
    # QUICK QUESTIONS
    # ======================================================

    st.subheader("⚡ Quick Questions")

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        if st.button("🏆 Top Host"):

            question = "top host"

    with c2:

        if st.button("🔥 Root Causes"):

            question = "root causes"

    with c3:

        if st.button("🚨 Critical Alerts"):

            question = "critical alerts"

    with c4:

        if st.button("📊 Infrastructure Summary"):

            question = "summary"

    st.write("")

    # ======================================================
    # CONVERSATION MEMORY
    # ======================================================

    if "history" not in st.session_state:

        st.session_state.history = []

    # ======================================================
    # AI RESPONSE ENGINE
    # ======================================================

    if question:

        st.session_state.history.append(question)

        q = question.lower().strip()

        st.subheader("🤖 SentinelAI Response")

        # ==================================================
        # INFRASTRUCTURE SUMMARY
        # ==================================================

        if any(x in q for x in [

            "summary",

            "overview",

            "status",

            "health"

        ]):

            st.success(f"""
### Infrastructure Summary

🚨 Total Alerts : **{total_alerts:,}**

🔗 Correlated Incidents : **{total_incidents:,}**

🔥 Root Causes : **{total_roots:,}**

📉 Alert Reduction : **{reduction:.2f}%**

🎯 Average Confidence : **{avg_confidence:.2f}**

Infrastructure Status : 🟢 Stable

Recommendation :

Continue monitoring high-volume hosts.
""")

        # ==================================================
        # TOP HOST
        # ==================================================

        elif any(x in q for x in [

            "top host",

            "most incidents",

            "highest incidents"

        ]):

            row = stats.sort_values(

                "incidents",

                ascending=False

            ).iloc[0]

            st.success(f"""
### Host With Maximum Incidents

Host : **{row['host']}**

Incidents : **{int(row['incidents'])}**

Alerts : **{int(row['alerts'])}**

Average Confidence : **{row['avg_confidence']:.2f}**

Recommendation :

Investigate this host first.
""")

        # ==================================================
        # MOST ALERTS
        # ==================================================

        elif any(x in q for x in [

            "most alerts",

            "highest alerts"

        ]):

            row = stats.sort_values(

                "alerts",

                ascending=False

            ).iloc[0]

            st.success(f"""
### Host Generating Maximum Alerts

Host : **{row['host']}**

Alerts : **{int(row['alerts'])}**

Incidents : **{int(row['incidents'])}**
""")

        # ==================================================
        # HEALTHIEST HOST
        # ==================================================

        elif any(x in q for x in [

            "healthy",

            "best host",

            "highest confidence"

        ]):

            row = stats.sort_values(

                "avg_confidence",

                ascending=False

            ).iloc[0]

            st.success(f"""
### Healthiest Host

Host : **{row['host']}**

Confidence : **{row['avg_confidence']:.2f}**

Incidents : **{int(row['incidents'])}**
""")

        # ==================================================
        # HIGHEST RISK HOST
        # ==================================================

        elif any(x in q for x in [

            "risk",

            "unhealthy",

            "lowest confidence",

            "worst host"

        ]):

            row = stats.sort_values(

                "avg_confidence"

            ).iloc[0]

            st.error(f"""
### Highest Risk Host

Host : **{row['host']}**

Confidence : **{row['avg_confidence']:.2f}**

Incidents : **{int(row['incidents'])}**

Recommendation :

Immediate investigation recommended.
""")

        # ==================================================
        # ROOT CAUSES
        # ==================================================

        elif "root" in q:

            st.write("### Top Root Causes")

            rc = (
                roots["metric"]
                .value_counts()
                .reset_index()
            )

            rc.columns = [
                "Metric",
                "Occurrences"
            ]

            st.dataframe(
                rc,
                width="stretch",
                hide_index=True
            )

        # ==================================================
        # CPU ISSUES
        # ==================================================

        elif "cpu" in q:

            cpu = roots[
                roots["metric"]
                .astype(str)
                .str.contains(
                    "cpu",
                    case=False,
                    na=False
                )
            ]

            if cpu.empty:

                st.warning("No CPU related root causes found.")

            else:

                st.dataframe(
                    cpu,
                    width="stretch",
                    hide_index=True
                )

        # ==================================================
        # MEMORY ISSUES
        # ==================================================

        elif "memory" in q:

            mem = roots[
                roots["metric"]
                .astype(str)
                .str.contains(
                    "memory",
                    case=False,
                    na=False
                )
            ]

            if mem.empty:

                st.warning("No Memory related issues found.")

            else:

                st.dataframe(
                    mem,
                    width="stretch",
                    hide_index=True
                )

        # ==================================================
        # DISK ISSUES
        # ==================================================

        elif "disk" in q:

            disk = roots[
                roots["metric"]
                .astype(str)
                .str.contains(
                    "disk",
                    case=False,
                    na=False
                )
            ]

            if disk.empty:

                st.warning("No Disk related issues found.")

            else:

                st.dataframe(
                    disk,
                    width="stretch",
                    hide_index=True
                )

        # ==================================================
        # REDIS ISSUES
        # ==================================================

        elif "redis" in q:

            redis = roots[
                roots["metric"]
                .astype(str)
                .str.contains(
                    "redis",
                    case=False,
                    na=False
                )
            ]

            if redis.empty:

                st.warning("No Redis issues found.")

            else:

                st.dataframe(
                    redis,
                    width="stretch",
                    hide_index=True
                )

        # ==================================================
        # ORACLE ISSUES
        # ==================================================

        elif "oracle" in q:

            oracle = roots[
                roots["metric"]
                .astype(str)
                .str.contains(
                    "oracle",
                    case=False,
                    na=False
                )
            ]

            if oracle.empty:

                st.warning("No Oracle issues found.")

            else:

                st.dataframe(
                    oracle,
                    width="stretch",
                    hide_index=True
                )

        # ==================================================
        # CRITICAL ALERTS
        # ==================================================

        elif "critical" in q:

            critical = alerts[
                alerts["severity"]
                .astype(str)
                .str.lower()
                .eq("critical")
            ]

            st.write(f"### Critical Alerts ({len(critical)})")

            st.dataframe(
                critical.head(25),
                width="stretch",
                hide_index=True
            )

        # ==================================================
        # LONGEST INCIDENT
        # ==================================================

        elif "longest" in q or "duration" in q:

            row = stats.sort_values(
                "avg_duration",
                ascending=False
            ).iloc[0]

            st.success(f"""
### Longest Running Incident

Host : **{row['host']}**

Average Duration : **{row['avg_duration']:.1f} seconds**

Incidents : **{int(row['incidents'])}**

Alerts : **{int(row['alerts'])}**
""")

        # ==================================================
        # ALERT REDUCTION
        # ==================================================

        elif "reduction" in q or "suppression" in q:

            st.info(f"""
### Alert Correlation Efficiency

Original Alerts

**{total_alerts:,}**

Suppressed Alerts

**{total_suppressed:,}**

Reduction Achieved

**{reduction:.2f}%**

The alert correlation engine successfully removed duplicate alerts while preserving incident visibility.
""")

        # ==================================================
        # INCIDENT STATISTICS
        # ==================================================

        elif "statistics" in q or "stats" in q:

            st.write("### Incident Statistics")

            st.dataframe(
                stats,
                width="stretch",
                hide_index=True
            )

        # ==================================================
        # TOP 10 HOSTS
        # ==================================================

        elif "top 10" in q or "hosts" in q:

            top = stats.sort_values(
                "incidents",
                ascending=False
            ).head(10)

            st.write("### Top Infrastructure Hosts")

            st.dataframe(
                top,
                width="stretch",
                hide_index=True
            )

        # ==================================================
        # RECOMMENDATIONS
        # ==================================================

        elif any(word in q for word in [

            "recommend",

            "recommendation",

            "next",

            "investigate",

            "action"

        ]):

            st.success("""
### Recommended Actions

1. Investigate the host with the highest incident count.

2. Review CPU, Memory and Disk metrics.

3. Check recent deployments.

4. Review correlated incidents before individual alerts.

5. Validate monitoring thresholds.

6. Continue monitoring infrastructure health.
""")

        # ==================================================
        # HELP
        # ==================================================

        else:

            st.warning("""
I can answer questions such as:

• summary

• top host

• most incidents

• most alerts

• healthiest host

• unhealthy host

• root causes

• cpu issues

• memory issues

• disk issues

• redis issues

• oracle issues

• critical alerts

• incident statistics

• longest incident

• alert reduction

• recommendations

• top 10 hosts
""")

    # ======================================================
    # CONVERSATION HISTORY
    # ======================================================

    st.divider()

    st.subheader("📝 Conversation History")

    if st.session_state.history:

        for i, msg in enumerate(st.session_state.history, start=1):

            st.write(f"**{i}.** {msg}")

    else:

        st.caption("No questions asked yet.")

    st.write("")

    history_text = "\n".join(st.session_state.history)

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(

            "📥 Export Conversation",

            history_text,

            "sentinelai_conversation.txt",

            "text/plain"

        )

    with col2:

        if st.button("🗑️ Clear Conversation"):

            st.session_state.history = []

            st.rerun()

    st.divider()

    st.caption(
        "🤖 SentinelAI Copilot • Rule-Based AI Assistant • Future LLM Ready"
    )