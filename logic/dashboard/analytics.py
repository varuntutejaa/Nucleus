import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard.utils import load_data


# ==========================================================
# PAGE STYLE
# ==========================================================

st.markdown("""
<style>

.title{
    font-size:38px;
    font-weight:700;
    color:white;
}

.subtitle{
    color:#94A3B8;
    font-size:18px;
}

.metric-card{

    background:#1E293B;

    border-left:6px solid #10B981;

    padding:18px;

    border-radius:14px;

    box-shadow:0px 4px 12px rgba(0,0,0,.30);

}

.metric-title{

    color:#CBD5E1;

    font-size:15px;

}

.metric-value{

    color:white;

    font-size:34px;

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


# ==========================================================
# ANALYTICS PAGE
# ==========================================================

def show_analytics():

    data = load_data()

    alerts = data["alerts.csv"]

    incidents = data["incident_summary.csv"]

    roots = data["root_cause.csv"]

    suppressed = data["suppressed_alerts.csv"]

    stats = data["incident_statistics.csv"]

    # ------------------------------------------------------

    st.markdown(

        '<div class="title">📊 Analytics Dashboard</div>',

        unsafe_allow_html=True

    )

    st.markdown(

        '<div class="subtitle">Infrastructure Intelligence & Performance Analytics</div>',

        unsafe_allow_html=True

    )

    st.write("")

    # ======================================================
    # KPI VALUES
    # ======================================================

    total_alerts = len(alerts)

    total_incidents = len(incidents)

    total_roots = len(roots)

    total_suppressed = len(suppressed)

    reduction = 100 * total_suppressed / total_alerts

    avg_confidence = stats["avg_confidence"].mean()

    # ======================================================
    # KPI CARDS
    # ======================================================

    c1,c2,c3,c4,c5 = st.columns(5)

    cards = [

        ("🚨 Alerts",f"{total_alerts:,}"),

        ("🔗 Incidents",f"{total_incidents:,}"),

        ("🔥 RCA",f"{total_roots:,}"),

        ("🚫 Suppressed",f"{total_suppressed:,}"),

        ("🎯 Confidence",f"{avg_confidence:.2f}")

    ]

    for col,(title,value) in zip([c1,c2,c3,c4,c5],cards):

        with col:

            st.markdown(f"""

            <div class="metric-card">

            <div class="metric-title">{title}</div>

            <div class="metric-value">{value}</div>

            </div>

            """,unsafe_allow_html=True)

    st.write("")
    # ======================================================
    # FIRST ROW
    # ======================================================

    left, right = st.columns(2)

    # ------------------------------------------------------
    # ALERT TIMELINE
    # ------------------------------------------------------

    with left:

        st.markdown(
            '<div class="section-title">📈 Alert Timeline</div>',
            unsafe_allow_html=True
        )

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

            yaxis_title="Alert Count"

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    # ------------------------------------------------------
    # SEVERITY DISTRIBUTION
    # ------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">🥧 Alert Severity</div>',

            unsafe_allow_html=True

        )

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

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A"

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    st.write()

    # ======================================================
    # SECOND ROW
    # ======================================================

    left, right = st.columns(2)

    # ------------------------------------------------------
    # ROOT CAUSE DISTRIBUTION
    # ------------------------------------------------------

    with left:

        st.markdown(

            '<div class="section-title">🔥 Root Cause Distribution</div>',

            unsafe_allow_html=True

        )

        metric_df = (

            roots["metric"]

            .value_counts()

            .head(10)

            .reset_index()

        )

        metric_df.columns = [

            "Metric",

            "Incidents"

        ]

        fig = px.bar(

            metric_df,

            x="Incidents",

            y="Metric",

            orientation="h",

            text="Incidents",

            color="Incidents",

            color_continuous_scale="Reds"

        )

        fig.update_layout(

            template="plotly_dark",

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            coloraxis_showscale=False,

            yaxis=dict(

                categoryorder="total ascending"

            )

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    # ------------------------------------------------------
    # INCIDENTS PER HOST
    # ------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">🖥 Incidents by Host</div>',

            unsafe_allow_html=True

        )

        host_df = (

            incidents["host"]

            .value_counts()

            .head(10)

            .reset_index()

        )

        host_df.columns = [

            "Host",

            "Incidents"

        ]

        fig = px.bar(

            host_df,

            x="Host",

            y="Incidents",

            text="Incidents",

            color="Incidents",

            color_continuous_scale="Blues"

        )

        fig.update_layout(

            template="plotly_dark",

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            coloraxis_showscale=False

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    st.write()
    # ======================================================
    # THIRD ROW
    # ======================================================

    left, center, right = st.columns(3)

    # ------------------------------------------------------
    # SYSTEM HEALTH
    # ------------------------------------------------------

    with left:

        st.markdown(
            '<div class="section-title">💚 System Health</div>',
            unsafe_allow_html=True
        )

        health = (
            reduction * 0.6 +
            avg_confidence * 100 * 0.4
        )

        health = min(100, health)

        fig = px.pie(

            names=["Healthy", "Remaining"],

            values=[health, 100-health],

            hole=0.80

        )

        fig.update_layout(

            template="plotly_dark",

            height=340,

            showlegend=False,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            annotations=[

                dict(

                    text=f"<b>{health:.1f}%</b>",

                    x=0.5,

                    y=0.5,

                    showarrow=False,

                    font=dict(

                        size=30,

                        color="white"

                    )

                )

            ]

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    # ------------------------------------------------------
    # ALERT REDUCTION
    # ------------------------------------------------------

    with center:

        st.markdown(

            '<div class="section-title">📉 Alert Reduction</div>',

            unsafe_allow_html=True

        )

        fig = px.pie(

            names=[

                "Suppressed",

                "Remaining"

            ],

            values=[

                total_suppressed,

                total_alerts-total_suppressed

            ],

            hole=0.80

        )

        fig.update_layout(

            template="plotly_dark",

            height=340,

            showlegend=False,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            annotations=[

                dict(

                    text=f"<b>{reduction:.2f}%</b>",

                    x=0.5,

                    y=0.5,

                    showarrow=False,

                    font=dict(

                        size=30,

                        color="white"

                    )

                )

            ]

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    # ------------------------------------------------------
    # CONFIDENCE DISTRIBUTION
    # ------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">🎯 Confidence</div>',

            unsafe_allow_html=True

        )

        fig = px.histogram(

            stats,

            x="avg_confidence",

            nbins=20,

            color_discrete_sequence=["#10B981"]

        )

        fig.update_layout(

            template="plotly_dark",

            height=340,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A"

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    st.write()

    # ======================================================
    # CORRELATION EFFICIENCY
    # ======================================================

    st.markdown(

        '<div class="section-title">⚡ Correlation Efficiency</div>',

        unsafe_allow_html=True

    )

    efficiency = pd.DataFrame({

        "Stage":[

            "Raw Alerts",

            "Correlated Incidents",

            "Root Causes"

        ],

        "Count":[

            total_alerts,

            total_incidents,

            total_roots

        ]

    })

    fig = px.funnel(

        efficiency,

        x="Count",

        y="Stage"

    )

    fig.update_layout(

        template="plotly_dark",

        height=420,

        paper_bgcolor="#0F172A",

        plot_bgcolor="#0F172A"

    )

    st.plotly_chart(

        fig,

        width="stretch"

    )

    st.write()

    # ======================================================
    # AI EXECUTIVE SUMMARY
    # ======================================================

    st.markdown(

        '<div class="section-title">🤖 AI Executive Summary</div>',

        unsafe_allow_html=True

    )

    top_host = incidents["host"].mode().iloc[0]

    top_metric = roots["metric"].mode().iloc[0]

    st.success(f"""

### Infrastructure Performance Summary

A total of **{total_alerts:,} alerts** were analysed.

The correlation engine reduced them to **{total_incidents:,} incidents**.

Root Cause Analysis identified **{total_roots:,} primary failures**.

A total of **{total_suppressed:,} alerts** were automatically suppressed, achieving an **alert reduction of {reduction:.2f}%**.

The most affected host is **{top_host}**.

The dominant failure category is **{top_metric}**.

Average incident confidence across the platform is **{avg_confidence:.2f}**.

Overall platform health is estimated at **{health:.1f}%**.

""")

    st.divider()

    st.caption(

        "SentinelAI • Executive Analytics Dashboard"

    )