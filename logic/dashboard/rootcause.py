import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard.utils import load_data


# ============================================================
# PAGE STYLE
# ============================================================

st.markdown("""
<style>

.main{
    background:#0F172A;
}

.block-container{
    padding-top:2rem;
}

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
    border-left:6px solid #EF4444;
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
# ROOT CAUSE PAGE
# ============================================================

def show_rootcause():

    data = load_data()

    roots = data["root_cause.csv"]

    incidents = data["incident_summary.csv"]

    statistics = data["incident_statistics.csv"]

    # --------------------------------------------------------

    st.markdown(
        '<div class="title">🔥 Root Cause Analytics</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">AI-driven Root Cause Investigation Dashboard</div>',
        unsafe_allow_html=True
    )

    st.write("")

    # ========================================================
    # FILTERS
    # ========================================================

    left, right = st.columns(2)

    with left:

        if "host" in roots.columns:

            host = st.selectbox(

                "Select Host",

                ["All"] + sorted(
                    roots["host"].dropna().unique().tolist()
                )

            )

        else:

            host = "All"

    with right:

        if "severity" in roots.columns:

            severity = st.selectbox(

                "Severity",

                ["All"] + sorted(
                    roots["severity"].dropna().unique().tolist()
                )

            )

        else:

            severity = "All"

    # --------------------------------------------------------

    filtered = roots.copy()

    if host != "All":

        filtered = filtered[
            filtered["host"] == host
        ]

    if severity != "All":

        filtered = filtered[
            filtered["severity"] == severity
        ]

    # ========================================================
    # KPI VALUES
    # ========================================================

    total_roots = len(filtered)

    total_hosts = (
        filtered["host"].nunique()
        if "host" in filtered.columns else 0
    )

    critical = 0

    if "severity" in filtered.columns:

        critical = (
            filtered["severity"]
            .astype(str)
            .str.lower()
            .eq("critical")
            .sum()
        )

    avg_confidence = 0

    if (
        not statistics.empty
        and "avg_confidence" in statistics.columns
    ):

        avg_confidence = statistics[
            "avg_confidence"
        ].mean()

    # ========================================================
    # KPI CARDS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(f"""
        <div class="metric-card">
        <div class="metric-title">
        🔥 Root Causes
        </div>

        <div class="metric-value">
        {total_roots:,}
        </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:

        st.markdown(f"""
        <div class="metric-card">
        <div class="metric-title">
        🖥 Hosts
        </div>

        <div class="metric-value">
        {total_hosts}
        </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:

        st.markdown(f"""
        <div class="metric-card">
        <div class="metric-title">
        🚨 Critical
        </div>

        <div class="metric-value">
        {critical}
        </div>
        </div>
        """, unsafe_allow_html=True)

    with c4:

        st.markdown(f"""
        <div class="metric-card">
        <div class="metric-title">
        🎯 Avg Confidence
        </div>

        <div class="metric-value">
        {avg_confidence:.2f}
        </div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    # ========================================================
    # ROOT CAUSE VISUALIZATIONS
    # ========================================================

    left, right = st.columns(2)

    # --------------------------------------------------------
    # ROOT CAUSE DISTRIBUTION
    # --------------------------------------------------------

    with left:

        st.markdown(
            '<div class="section-title">🔥 Root Cause Distribution</div>',
            unsafe_allow_html=True
        )

        if (
            not filtered.empty
            and "metric" in filtered.columns
        ):

            metric_df = (
                filtered["metric"]
                .value_counts()
                .head(10)
                .reset_index()
            )

            metric_df.columns = [
                "Metric",
                "Count"
            ]

            fig = px.bar(
                metric_df,
                x="Count",
                y="Metric",
                orientation="h",
                text="Count",
                color="Count",
                color_continuous_scale="Reds"
            )

            fig.update_layout(
                template="plotly_dark",
                height=430,
                paper_bgcolor="#0F172A",
                plot_bgcolor="#0F172A",
                coloraxis_showscale=False,
                yaxis=dict(categoryorder="total ascending")
            )

            fig.update_traces(
                textposition="outside"
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

        if (
            not filtered.empty
            and "severity" in filtered.columns
        ):

            sev = (
                filtered["severity"]
                .value_counts()
                .reset_index()
            )

            sev.columns = [
                "Severity",
                "Count"
            ]

            fig = px.pie(
                sev,
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
                height=430,
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
    # CONFIDENCE HISTOGRAM
    # --------------------------------------------------------

    with left:

        st.markdown(
            '<div class="section-title">🎯 Confidence Distribution</div>',
            unsafe_allow_html=True
        )

        confidence_column = None

        if "root_score" in filtered.columns:
            confidence_column = "root_score"

        elif "confidence" in filtered.columns:
            confidence_column = "confidence"

        if confidence_column:

            fig = px.histogram(
                filtered,
                x=confidence_column,
                nbins=20,
                color_discrete_sequence=["#3B82F6"]
            )

            fig.update_layout(
                template="plotly_dark",
                height=430,
                paper_bgcolor="#0F172A",
                plot_bgcolor="#0F172A",
                xaxis_title="Confidence",
                yaxis_title="Root Causes"
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

    # --------------------------------------------------------
    # TOP AFFECTED HOSTS
    # --------------------------------------------------------

    with right:

        st.markdown(
            '<div class="section-title">🖥 Top Affected Hosts</div>',
            unsafe_allow_html=True
        )

        if (
            not filtered.empty
            and "host" in filtered.columns
        ):

            host_df = (
                filtered["host"]
                .value_counts()
                .head(10)
                .reset_index()
            )

            host_df.columns = [
                "Host",
                "Root Causes"
            ]

            fig = px.bar(
                host_df,
                x="Host",
                y="Root Causes",
                text="Root Causes",
                color="Root Causes",
                color_continuous_scale="Blues"
            )

            fig.update_layout(
                template="plotly_dark",
                height=430,
                paper_bgcolor="#0F172A",
                plot_bgcolor="#0F172A",
                coloraxis_showscale=False
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

    st.write("")
    # ========================================================
    # ROOT CAUSE INVESTIGATION
    # ========================================================

    st.markdown(
        '<div class="section-title">🔍 Root Cause Investigation</div>',
        unsafe_allow_html=True
    )

    left, right = st.columns([3,1])

    with left:

        search = st.text_input(
            "Search by Host, Metric or Incident ID",
            ""
        )

    with right:

        sort_option = st.selectbox(

            "Sort By",

            [
                "Highest Score",
                "Lowest Score",
                "Latest",
                "Oldest"
            ]

        )

    display = filtered.copy()

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search != "":

        search = search.lower()

        mask = pd.Series(False, index=display.index)

        if "host" in display.columns:

            mask |= (
                display["host"]
                .astype(str)
                .str.lower()
                .str.contains(search)
            )

        if "metric" in display.columns:

            mask |= (
                display["metric"]
                .astype(str)
                .str.lower()
                .str.contains(search)
            )

        if "incident_id" in display.columns:

            mask |= (
                display["incident_id"]
                .astype(str)
                .str.contains(search)
            )

        display = display[mask]

    # --------------------------------------------------------
    # SORTING
    # --------------------------------------------------------

    score_column = None

    if "root_score" in display.columns:

        score_column = "root_score"

    elif "confidence" in display.columns:

        score_column = "confidence"

    if sort_option == "Highest Score" and score_column:

        display = display.sort_values(
            score_column,
            ascending=False
        )

    elif sort_option == "Lowest Score" and score_column:

        display = display.sort_values(
            score_column,
            ascending=True
        )

    elif sort_option == "Latest":

        if "timestamp" in display.columns:

            display = display.sort_values(
                "timestamp",
                ascending=False
            )

    elif sort_option == "Oldest":

        if "timestamp" in display.columns:

            display = display.sort_values(
                "timestamp",
                ascending=True
            )

    # ========================================================
    # TABLE
    # ========================================================

    columns = []

    preferred = [

        "incident_id",

        "host",

        "metric",

        "severity",

        "value",

        "root_score",

        "timestamp"

    ]

    for col in preferred:

        if col in display.columns:

            columns.append(col)

    st.dataframe(

        display[columns],

        width="stretch",

        hide_index=True,

        height=450

    )

    # ========================================================
    # EXPORT
    # ========================================================

    csv = display.to_csv(index=False).encode("utf-8")

    st.download_button(

        "📥 Download Filtered Root Causes",

        csv,

        "root_causes.csv",

        "text/csv"

    )

    st.write("")
    # ========================================================
    # EXECUTIVE INSIGHTS
    # ========================================================

    st.markdown(
        '<div class="section-title">🤖 AI Root Cause Insights</div>',
        unsafe_allow_html=True
    )

    left, right = st.columns([2,1])

    # --------------------------------------------------------
    # AI SUMMARY
    # --------------------------------------------------------

    with left:

        if not display.empty:

            # Top metric
            top_metric = "N/A"
            if "metric" in display.columns:
                top_metric = display["metric"].mode().iloc[0]

            # Top host
            top_host = "N/A"
            if "host" in display.columns:
                top_host = display["host"].mode().iloc[0]

            # Highest confidence
            max_score = 0

            if "root_score" in display.columns:

                max_score = display["root_score"].max()

            elif "confidence" in display.columns:

                max_score = display["confidence"].max()

            critical_percent = 0

            if (
                "severity" in display.columns
                and len(display) > 0
            ):

                critical_percent = (
                    display["severity"]
                    .astype(str)
                    .str.lower()
                    .eq("critical")
                    .mean()
                ) * 100

            st.info(f"""

### AI Executive Summary

A total of **{len(display):,}** root causes match the current filters.

The dominant failure category is **{top_metric}**.

The most affected infrastructure node is **{top_host}**.

Approximately **{critical_percent:.1f}%** of the detected root causes are classified as **Critical**.

The highest confidence root cause achieved a confidence score of **{max_score:.2f}**.

Overall, the correlation and RCA pipeline successfully condensed thousands of alerts into a manageable set of actionable incidents, allowing operators to focus on probable primary failures instead of secondary alert noise.

""")

    # --------------------------------------------------------
    # RECOMMENDED ACTIONS
    # --------------------------------------------------------

    with right:

        st.subheader("💡 Recommended Actions")

        metric = str(top_metric).lower()

        actions = []

        if "cpu" in metric:

            actions = [

                "Investigate CPU intensive processes",

                "Review recent deployments",

                "Inspect application logs",

                "Verify autoscaling policies"

            ]

        elif "memory" in metric:

            actions = [

                "Inspect memory utilization",

                "Check for memory leaks",

                "Restart affected services",

                "Review JVM/container limits"

            ]

        elif "disk" in metric:

            actions = [

                "Check storage utilization",

                "Inspect disk I/O",

                "Review cleanup policies",

                "Verify storage health"

            ]

        elif "redis" in metric:

            actions = [

                "Inspect Redis latency",

                "Check Redis logs",

                "Verify client connections",

                "Review cache performance"

            ]

        elif "oracle" in metric:

            actions = [

                "Inspect Oracle alert log",

                "Check active sessions",

                "Review slow SQL queries",

                "Verify tablespace usage"

            ]

        else:

            actions = [

                "Inspect affected service",

                "Review infrastructure logs",

                "Validate dependencies",

                "Continue monitoring"

            ]

        for action in actions:

            st.success("✅ " + action)

    st.write("")

    # ========================================================
    # TOP 10 HIGH CONFIDENCE INCIDENTS
    # ========================================================

    st.markdown(
        '<div class="section-title">🏆 Highest Confidence Root Causes</div>',
        unsafe_allow_html=True
    )

    top_df = display.copy()

    score_column = None

    if "root_score" in top_df.columns:
        score_column = "root_score"

    elif "confidence" in top_df.columns:
        score_column = "confidence"

    if score_column:

        top_df = top_df.sort_values(
            score_column,
            ascending=False
        )

    cols = []

    preferred = [

        "incident_id",

        "host",

        "metric",

        "severity",

        score_column,

        "timestamp"

    ]

    for c in preferred:

        if c and c in top_df.columns:

            cols.append(c)

    st.dataframe(

        top_df[cols].head(10),

        width="stretch",

        hide_index=True

    )

    st.divider()

    st.caption(
        "SentinelAI • Root Cause Analytics • Intelligent AIOps Platform"
    )