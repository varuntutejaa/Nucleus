import streamlit as st
import pandas as pd

from dashboard.utils import load_data


def show_incidents():

    st.title("🔗 Incident Explorer")

    data = load_data()

    alerts = data["correlated_alerts.csv"]

    roots = data["root_cause.csv"]

    summary = data["incident_root_summary.csv"]

    # ---------------------------------------------

    incident_ids = sorted(
        alerts["incident_id"].unique()
    )

    incident = st.selectbox(

        "Select Incident",

        incident_ids

    )

    # ---------------------------------------------

    incident_alerts = alerts[
        alerts["incident_id"] == incident
    ]

    root = roots[
        roots["incident_id"] == incident
    ]

    summary_row = summary[
        summary["incident_id"] == incident
    ]
    st.write("")

    # ======================================================
    # INCIDENT SUMMARY
    # ======================================================

    if not summary_row.empty:

        summary_row = summary_row.iloc[0]

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "🖥 Host",
                summary_row["host"]
            )

            st.metric(
                "🔥 Root Cause",
                summary_row["root_metric"]
            )

        with col2:

            st.metric(
                "🚨 Alerts",
                int(summary_row["alerts"])
            )

            st.metric(
                "🚫 Suppressed",
                int(summary_row["suppressed"])
            )

        with col3:

            st.metric(
                "⚠ Severity",
                summary_row["severity"]
            )

            st.metric(
                "🎯 Root Score",
                f'{summary_row["root_score"]:.2f}'
            )

    st.divider()

    # ======================================================
    # ROOT CAUSE CARD
    # ======================================================

    st.subheader("🔥 Root Cause")

    if not root.empty:

        root = root.iloc[0]

        st.success(f"""
### {root['metric']}

**Host:** {root['host']}

**Severity:** {root['severity']}

**Metric Value:** {root['value']}

**Root Score:** {root['root_score']:.2f}
""")

    st.divider()

    # ======================================================
    # INCIDENT TIMELINE
    # ======================================================

    st.subheader("📋 Alert Timeline")

    timeline = incident_alerts.copy()

    timeline["timestamp"] = pd.to_datetime(
        timeline["timestamp"]
    )

    timeline = timeline.sort_values("timestamp")

    cols = [
        c for c in [
            "timestamp",
            "metric",
            "severity",
            "value",
            "source"
        ]
        if c in timeline.columns
    ]

    st.dataframe(
        timeline[cols],
        use_container_width=True,
        hide_index=True
    )
    st.divider()

    # ======================================================
    # INCIDENT CONFIDENCE
    # ======================================================

    left, right = st.columns([1,2])

    with left:

        st.subheader("🎯 Confidence")

        confidence = float(summary_row["root_score"]) * 100

        st.progress(confidence / 100)

        st.metric(
            "Confidence",
            f"{confidence:.1f}%"
        )

    # ======================================================
    # AI EXPLANATION
    # ======================================================

    with right:

        st.subheader("🤖 AI Incident Explanation")

        root_metric = summary_row["root_metric"]

        host = summary_row["host"]

        alerts_count = int(summary_row["alerts"])

        severity = summary_row["severity"]

        explanation = f"""
The correlation engine grouped **{alerts_count} related alerts**
into a single incident on **{host}**.

The earliest and highest-ranked alert was
**{root_metric}**, which was identified as the
most probable root cause.

The alert has **{severity}** severity and achieved a
confidence score of **{confidence:.1f}%** based on:

• Alert severity

• Temporal ordering

• Metric frequency

• Metric priority

All remaining alerts in this incident are treated as
secondary symptoms and were automatically suppressed.
"""

        st.info(explanation)

    st.divider()

    # ======================================================
    # RECOMMENDED ACTIONS
    # ======================================================

    st.subheader("💡 Recommended Actions")

    metric = str(root_metric).lower()

    recommendations = []

    if "cpu" in metric:

        recommendations = [

            "Investigate high CPU-consuming processes.",

            "Check for recent deployments or traffic spikes.",

            "Review application and system logs.",

            "Verify resource allocation and scaling policies."

        ]

    elif "memory" in metric:

        recommendations = [

            "Check memory utilization trends.",

            "Look for memory leaks.",

            "Restart affected services if required.",

            "Increase available memory if usage remains high."

        ]

    elif "disk" in metric:

        recommendations = [

            "Inspect disk utilization.",

            "Remove unnecessary files.",

            "Verify disk I/O performance.",

            "Check storage health."

        ]

    elif "redis" in metric:

        recommendations = [

            "Check Redis availability.",

            "Inspect Redis logs.",

            "Verify client connectivity.",

            "Monitor cache hit ratio."

        ]

    elif "oracle" in metric:

        recommendations = [

            "Review Oracle alert logs.",

            "Check active sessions.",

            "Verify database performance.",

            "Inspect slow queries."

        ]

    else:

        recommendations = [

            "Inspect the affected service.",

            "Review application logs.",

            "Verify recent infrastructure changes.",

            "Monitor system metrics."

        ]

    for rec in recommendations:

        st.success("✅ " + rec)

    st.divider()

    # ======================================================
    # RAW ALERTS
    # ======================================================

    with st.expander("📄 View All Correlated Alerts"):

        st.dataframe(

            incident_alerts,

            use_container_width=True,

            hide_index=True

        )