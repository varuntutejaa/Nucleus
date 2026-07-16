import streamlit as st
import plotly.express as px
import pandas as pd

from dashboard.utils import load_data


# ============================================================
# PROFESSIONAL CSS
# ============================================================

st.markdown("""
<style>

.main{
    background:#0F172A;
}

.block-container{
    padding-top:2rem;
    padding-bottom:1rem;
}

.big-title{
    font-size:40px;
    font-weight:700;
    color:white;
}

.subtitle{
    font-size:18px;
    color:#94A3B8;
}

.metric-card{
    background:#1E293B;
    padding:18px;
    border-radius:16px;
    border-left:6px solid #3B82F6;
    box-shadow:0px 4px 12px rgba(0,0,0,0.25);
}

.metric-title{
    color:#CBD5E1;
    font-size:16px;
}

.metric-value{
    color:white;
    font-size:36px;
    font-weight:bold;
}

.section-title{
    color:white;
    font-size:24px;
    font-weight:bold;
    margin-top:20px;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# DASHBOARD
# ============================================================

def show_dashboard():

    data = load_data()

    alerts = data["alerts.csv"]

    incidents = data["incident_summary.csv"]

    roots = data["root_cause.csv"]

    suppressed = data["suppressed_alerts.csv"]

    statistics = data["incident_statistics.csv"]

    # ------------------------------------------------------

    total_alerts = len(alerts)

    total_incidents = len(incidents)

    total_roots = len(roots)

    total_suppressed = len(suppressed)

    reduction = 100 * total_suppressed / total_alerts

    # ------------------------------------------------------

    st.markdown(
        '<div class="big-title">🚨 SentinelAI</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Intelligent Alert Correlation & Root Cause Analysis Platform</div>',
        unsafe_allow_html=True
    )

    st.write("")

    # ======================================================
    # KPI CARDS
    # ======================================================

    c1,c2,c3,c4,c5 = st.columns(5)

    with c1:

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🚨 Total Alerts</div>
            <div class="metric-value">{total_alerts:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🔗 Incidents</div>
            <div class="metric-value">{total_incidents:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🔥 Root Causes</div>
            <div class="metric-value">{total_roots:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🚫 Suppressed</div>
            <div class="metric-value">{total_suppressed:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with c5:

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📉 Reduction</div>
            <div class="metric-value">{reduction:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    # ======================================================
    # DASHBOARD CHARTS
    # ======================================================

    left, right = st.columns(2)

    # ------------------------------------------------------
    # ALERT SEVERITY
    # ------------------------------------------------------

    with left:

        st.markdown(
            '<div class="section-title">🥧 Alert Severity Distribution</div>',
            unsafe_allow_html=True
        )

        if not alerts.empty:

            severity = (

                alerts["severity"]

                .value_counts()

                .reset_index()

            )

            severity.columns = [

                "Severity",

                "Count"

            ]

            fig = px.pie(

                severity,

                names="Severity",

                values="Count",

                hole=0.55,

                color="Severity",

                color_discrete_map={

                    "Critical":"#EF4444",

                    "Warning":"#F59E0B",

                    "Info":"#22C55E"

                }

            )

            fig.update_layout(

                template="plotly_dark",

                height=420,

                margin=dict(

                    l=10,

                    r=10,

                    t=20,

                    b=10

                ),

                paper_bgcolor="#0F172A",

                plot_bgcolor="#0F172A"

            )

            st.plotly_chart(

                fig,

                use_container_width=True

            )

    # ------------------------------------------------------
    # TOP ROOT CAUSES
    # ------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">🔥 Top Root Cause Metrics</div>',

            unsafe_allow_html=True

        )

        if not roots.empty:

            metrics = (

                roots["metric"]

                .value_counts()

                .head(10)

                .reset_index()

            )

            metrics.columns = [

                "Metric",

                "Incidents"

            ]

            fig = px.bar(

                metrics,

                x="Incidents",

                y="Metric",

                orientation="h",

                text="Incidents"

            )

            fig.update_layout(

                template="plotly_dark",

                height=420,

                paper_bgcolor="#0F172A",

                plot_bgcolor="#0F172A",

                yaxis=dict(

                    categoryorder="total ascending"

                )

            )

            fig.update_traces(

                textposition="outside"

            )

            st.plotly_chart(

                fig,

                use_container_width=True

            )

    st.write("")

    # ======================================================
    # SECOND ROW
    # ======================================================

    left, right = st.columns(2)

    # ------------------------------------------------------
    # INCIDENTS PER HOST
    # ------------------------------------------------------

    with left:

        st.markdown(

            '<div class="section-title">🖥 Top Incident Hosts</div>',

            unsafe_allow_html=True

        )

        if not incidents.empty:

            hosts = (

                incidents["host"]

                .value_counts()

                .head(10)

                .reset_index()

            )

            hosts.columns = [

                "Host",

                "Incidents"

            ]

            fig = px.bar(

                hosts,

                x="Host",

                y="Incidents",

                text="Incidents"

            )

            fig.update_layout(

                template="plotly_dark",

                height=420,

                paper_bgcolor="#0F172A",

                plot_bgcolor="#0F172A"

            )

            st.plotly_chart(

                fig,

                use_container_width=True

            )

    # ------------------------------------------------------
    # SYSTEM HEALTH
    # ------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">💚 System Health</div>',

            unsafe_allow_html=True

        )

        confidence = 0.60

        if (
            not statistics.empty
            and "avg_confidence" in statistics.columns
        ):

            confidence = statistics[
                "avg_confidence"
            ].mean()

        health = (

            reduction * 0.50 +

            confidence * 100 * 0.50

        )

        fig = px.pie(

            names=[

                "Healthy",

                "Remaining"

            ],

            values=[

                health,

                100-health

            ],

            hole=0.78

        )

        fig.update_layout(

            template="plotly_dark",

            showlegend=False,

            annotations=[

                dict(

                    text=f"<b>{health:.1f}%</b>",

                    x=0.5,

                    y=0.5,

                    showarrow=False,

                    font=dict(

                        size=28,

                        color="white"

                    )

                )

            ],

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A"

        )

        st.plotly_chart(

            fig,

            use_container_width=True

        )
    # ======================================================
    # ALERT TIMELINE
    # ======================================================

    st.write("")

    st.markdown(
        '<div class="section-title">📈 Alert Timeline</div>',
        unsafe_allow_html=True
    )

    if not alerts.empty:

        timeline = alerts.copy()

        timeline["timestamp"] = pd.to_datetime(
            timeline["timestamp"],
            unit="ms",
            errors="coerce"
        )

        timeline = (

            timeline

            .dropna(subset=["timestamp"])

            .set_index("timestamp")

            .resample("5min")

            .size()

            .reset_index(name="Alerts")

        )

        fig = px.line(

            timeline,

            x="timestamp",

            y="Alerts",

            markers=True

        )

        fig.update_layout(

            template="plotly_dark",

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            xaxis_title="Time",

            yaxis_title="Alerts"

        )

        st.plotly_chart(

            fig,

            use_container_width=True

        )

    # ======================================================
    # RECENT ROOT CAUSES
    # ======================================================

    st.write("")

    st.markdown(

        '<div class="section-title">🔥 Recent Root Causes</div>',

        unsafe_allow_html=True

    )

    if not roots.empty:

        display = roots.copy()

        if "timestamp" in display.columns:

            display["timestamp"] = pd.to_datetime(
                display["timestamp"]
            )

            display = display.sort_values(
                "timestamp",
                ascending=False
            )

        columns = [

            c for c in [

                "incident_id",
                "host",
                "metric",
                "severity",
                "root_score",
                "timestamp"

            ] if c in display.columns

        ]

        st.dataframe(

            display[columns].head(15),

            use_container_width=True,

            hide_index=True

        )

    # ======================================================
    # AI INSIGHT PANEL
    # ======================================================

    st.write("")

    st.markdown(

        '<div class="section-title">🤖 AI Operations Insight</div>',

        unsafe_allow_html=True

    )

    if (
        not roots.empty
        and not incidents.empty
    ):

        top_metric = (

            roots["metric"]

            .value_counts()

            .idxmax()

        )

        top_host = (

            incidents["host"]

            .value_counts()

            .idxmax()

        )

        avg_conf = 0.0

        if (
            not statistics.empty
            and "avg_confidence" in statistics.columns
        ):

            avg_conf = statistics[
                "avg_confidence"
            ].mean()

        st.success(

f"""
### AI Summary

• **{total_alerts:,} alerts** were analysed.

• These were reduced to **{total_incidents:,} correlated incidents**.

• **{total_suppressed:,} alerts** were automatically suppressed.

• The most frequent root cause metric is **{top_metric}**.

• The most affected host is **{top_host}**.

• Average incident confidence is **{avg_conf:.2f}**.

Overall, the alert correlation engine achieved an **alert reduction of {reduction:.2f}%**, significantly decreasing operator workload while preserving incident-level visibility.
"""
        )

    # ======================================================
    # FOOTER
    # ======================================================

    st.write("")
    st.divider()

    st.caption(
        "SentinelAI • Intelligent Alert Correlation & Root Cause Analysis Platform"
    )