import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard.utils import load_data


# ============================================================
# PAGE STYLE
# ============================================================

st.markdown("""
<style>

.title{
    font-size:38px;
    font-weight:700;
    color:white;
}

.subtitle{
    font-size:18px;
    color:#94A3B8;
}

.metric-card{
    background:#1E293B;
    border-left:6px solid #3B82F6;
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


# ============================================================
# ALERT EXPLORER
# ============================================================

def show_alerts():

    data = load_data()

    alerts = data["alerts.csv"].copy()

    st.markdown(
        '<div class="title">🚨 Alert Explorer</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Search, Filter and Investigate Infrastructure Alerts</div>',
        unsafe_allow_html=True
    )

    st.write("")

    # ========================================================
    # FILTERS
    # ========================================================

    c1, c2, c3 = st.columns(3)

    with c1:

        host = st.selectbox(
            "Host",
            ["All"] + sorted(alerts["host"].dropna().unique().tolist())
        )

    with c2:

        severity = st.selectbox(
            "Severity",
            ["All"] + sorted(alerts["severity"].dropna().unique().tolist())
        )

    with c3:

        metric = st.selectbox(
            "Metric",
            ["All"] + sorted(alerts["metric"].dropna().unique().tolist())
        )

    search = st.text_input(
        "🔍 Search Host / Metric / Source"
    )

    # ========================================================
    # FILTER DATA
    # ========================================================

    filtered = alerts.copy()

    if host != "All":
        filtered = filtered[
            filtered["host"] == host
        ]

    if severity != "All":
        filtered = filtered[
            filtered["severity"] == severity
        ]

    if metric != "All":
        filtered = filtered[
            filtered["metric"] == metric
        ]

    if search != "":

        s = search.lower()

        mask = (

            filtered["host"].astype(str).str.lower().str.contains(s)

            |

            filtered["metric"].astype(str).str.lower().str.contains(s)

            |

            filtered["source"].astype(str).str.lower().str.contains(s)

        )

        filtered = filtered[mask]

    # ========================================================
    # KPI
    # ========================================================

    total = len(filtered)

    hosts = filtered["host"].nunique()

    metrics = filtered["metric"].nunique()

    critical = (

        filtered["severity"]

        .astype(str)

        .str.lower()

        .eq("critical")

        .sum()

    )

    a,b,c,d = st.columns(4)

    with a:

        st.markdown(f"""
        <div class="metric-card">
        <div class="metric-title">🚨 Alerts</div>
        <div class="metric-value">{total:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with b:

        st.markdown(f"""
        <div class="metric-card">
        <div class="metric-title">🖥 Hosts</div>
        <div class="metric-value">{hosts}</div>
        </div>
        """, unsafe_allow_html=True)

    with c:

        st.markdown(f"""
        <div class="metric-card">
        <div class="metric-title">📊 Metrics</div>
        <div class="metric-value">{metrics}</div>
        </div>
        """, unsafe_allow_html=True)

    with d:

        st.markdown(f"""
        <div class="metric-card">
        <div class="metric-title">🔥 Critical</div>
        <div class="metric-value">{critical}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    # ========================================================
    # ALERT ANALYTICS
    # ========================================================

    left, right = st.columns(2)

    # --------------------------------------------------------
    # ALERT TIMELINE
    # --------------------------------------------------------

    with left:

        st.markdown(
            '<div class="section-title">📈 Alert Timeline</div>',
            unsafe_allow_html=True
        )

        timeline = filtered.copy()

        if not timeline.empty:

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

    # --------------------------------------------------------
    # SEVERITY DISTRIBUTION
    # --------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">🥧 Severity Distribution</div>',

            unsafe_allow_html=True

        )

        severity_df = (

            filtered["severity"]

            .value_counts()

            .reset_index()

        )

        severity_df.columns = [

            "Severity",

            "Count"

        ]

        fig = px.pie(

            severity_df,

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

    st.write("")

    # ========================================================
    # SECOND ROW
    # ========================================================

    left, right = st.columns(2)

    # --------------------------------------------------------
    # TOP HOSTS
    # --------------------------------------------------------

    with left:

        st.markdown(

            '<div class="section-title">🖥 Top Alert Hosts</div>',

            unsafe_allow_html=True

        )

        host_df = (

            filtered["host"]

            .value_counts()

            .head(10)

            .reset_index()

        )

        host_df.columns = [

            "Host",

            "Alerts"

        ]

        fig = px.bar(

            host_df,

            x="Host",

            y="Alerts",

            text="Alerts",

            color="Alerts",

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

    # --------------------------------------------------------
    # TOP METRICS
    # --------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">📊 Top Alert Metrics</div>',

            unsafe_allow_html=True

        )

        metric_df = (

            filtered["metric"]

            .value_counts()

            .head(10)

            .reset_index()

        )

        metric_df.columns = [

            "Metric",

            "Alerts"

        ]

        fig = px.bar(

            metric_df,

            x="Alerts",

            y="Metric",

            orientation="h",

            text="Alerts",

            color="Alerts",

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

    st.write("")
    # ========================================================
    # ALERT INVESTIGATION
    # ========================================================

    st.markdown(
        '<div class="section-title">📋 Alert Investigation</div>',
        unsafe_allow_html=True
    )

    left, right = st.columns([3,1])

    with left:

        table_search = st.text_input(
            "Search alerts in table",
            key="alert_table_search"
        )

    with right:

        sort_by = st.selectbox(
            "Sort",
            [
                "Latest",
                "Oldest",
                "Highest Value",
                "Lowest Value"
            ]
        )

    table = filtered.copy()

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if table_search:

        s = table_search.lower()

        mask = pd.Series(False, index=table.index)

        for col in ["host", "metric", "severity", "source"]:

            if col in table.columns:

                mask |= (
                    table[col]
                    .astype(str)
                    .str.lower()
                    .str.contains(s)
                )

        table = table[mask]

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    if "timestamp" in table.columns:

        table["timestamp"] = pd.to_datetime(
            table["timestamp"],
            unit="ms",
            errors="coerce"
        )

    if sort_by == "Latest":

        if "timestamp" in table.columns:

            table = table.sort_values(
                "timestamp",
                ascending=False
            )

    elif sort_by == "Oldest":

        if "timestamp" in table.columns:

            table = table.sort_values(
                "timestamp",
                ascending=True
            )

    elif sort_by == "Highest Value":

        if "value" in table.columns:

            table = table.sort_values(
                "value",
                ascending=False
            )

    elif sort_by == "Lowest Value":

        if "value" in table.columns:

            table = table.sort_values(
                "value",
                ascending=True
            )

    # ========================================================
    # ALERT TABLE
    # ========================================================

    preferred = [

        "timestamp",
        "host",
        "metric",
        "severity",
        "value",
        "source"

    ]

    columns = [

        c for c in preferred

        if c in table.columns

    ]

    st.dataframe(

        table[columns],

        width="stretch",

        hide_index=True,

        height=500

    )

    # ========================================================
    # EXPORT
    # ========================================================

    csv = table.to_csv(index=False).encode("utf-8")

    st.download_button(

        "📥 Export Filtered Alerts",

        csv,

        "filtered_alerts.csv",

        "text/csv"

    )

    st.write("")

    # ========================================================
    # CRITICAL ALERTS
    # ========================================================

    st.markdown(

        '<div class="section-title">🚨 Recent Critical Alerts</div>',

        unsafe_allow_html=True

    )

    critical_df = table.copy()

    if "severity" in critical_df.columns:

        critical_df = critical_df[
            critical_df["severity"]
            .astype(str)
            .str.lower()
            .eq("critical")
        ]

    st.dataframe(

        critical_df.head(15),

        width="stretch",

        hide_index=True

    )

    st.write("")

    # ========================================================
    # AI ALERT SUMMARY
    # ========================================================

    st.markdown(

        '<div class="section-title">🤖 AI Alert Summary</div>',

        unsafe_allow_html=True

    )

    if len(table):

        top_host = "N/A"

        if "host" in table.columns:

            top_host = table["host"].mode().iloc[0]

        top_metric = "N/A"

        if "metric" in table.columns:

            top_metric = table["metric"].mode().iloc[0]

        critical_count = 0

        if "severity" in table.columns:

            critical_count = (
                table["severity"]
                .astype(str)
                .str.lower()
                .eq("critical")
                .sum()
            )

        st.info(f"""

### Infrastructure Alert Summary

A total of **{len(table):,}** alerts match the current filters.

The host generating the largest number of alerts is **{top_host}**.

The most frequent alert metric is **{top_metric}**.

There are currently **{critical_count:,} Critical alerts**.

Operators should prioritise investigation of repeated Critical alerts before Warning and Info alerts.

""")

    st.write("")

    # ========================================================
    # RECOMMENDATIONS
    # ========================================================

    st.markdown(

        '<div class="section-title">💡 Recommended Actions</div>',

        unsafe_allow_html=True

    )

    recommendations = [

        "Investigate recurring Critical alerts first.",

        "Review infrastructure changes made in the last deployment window.",

        "Check hosts with repeated CPU, Memory or Disk alerts.",

        "Validate monitoring thresholds to reduce unnecessary alert noise.",

        "Review correlated incidents before investigating individual alerts."

    ]

    for rec in recommendations:

        st.success("✅ " + rec)

    st.divider()

    st.caption(

        "SentinelAI • Alert Explorer • Intelligent AIOps Platform"

    )