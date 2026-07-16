import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard.utils import load_data


# ==========================================================
# STYLE
# ==========================================================

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

    border-left:6px solid #22C55E;

    padding:18px;

    border-radius:14px;

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
# HOST HEALTH
# ==========================================================

def show_hosts():

    data = load_data()

    incidents = data["incident_summary.csv"]

    roots = data["root_cause.csv"]

    stats = data["incident_statistics.csv"]

    st.markdown(
        '<div class="title">🖥 Host Health Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Infrastructure Health & Incident Monitoring</div>',
        unsafe_allow_html=True
    )

    st.write("")

    # ------------------------------------------------------

    hosts = sorted(
        incidents["host"].unique().tolist()
    )

    selected = st.selectbox(

        "Select Host",

        ["All"] + hosts

    )

    # ------------------------------------------------------

    df = incidents.copy()

    if selected != "All":

        df = df[df["host"] == selected]

    # ------------------------------------------------------

    total_hosts = incidents["host"].nunique()

    total_incidents = len(df)

    avg_conf = stats["avg_confidence"].mean()

    avg_alerts = stats["avg_alerts"].mean()

    health = min(
        100,
        avg_conf * 100 * 0.6 +
        40
    )

    # ------------------------------------------------------

    c1,c2,c3,c4 = st.columns(4)

    cards = [

        ("🖥 Hosts",total_hosts),

        ("🔗 Incidents",total_incidents),

        ("🎯 Avg Confidence",f"{avg_conf:.2f}"),

        ("💚 Health",f"{health:.1f}%")

    ]

    for col,(title,value) in zip([c1,c2,c3,c4],cards):

        with col:

            st.markdown(f"""

            <div class="metric-card">

            <div class="metric-title">{title}</div>

            <div class="metric-value">{value}</div>

            </div>

            """,unsafe_allow_html=True)

    st.write()
    # ======================================================
    # FIRST ROW
    # ======================================================

    left, right = st.columns(2)

    # ------------------------------------------------------
    # INCIDENTS PER HOST
    # ------------------------------------------------------

    with left:

        st.markdown(
            '<div class="section-title">🖥 Incidents per Host</div>',
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

    # ------------------------------------------------------
    # HOST HEALTH GAUGE
    # ------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">💚 Infrastructure Health</div>',

            unsafe_allow_html=True

        )

        fig = px.pie(

            names=[

                "Healthy",

                "Risk"

            ],

            values=[

                health,

                100-health

            ],

            hole=0.80

        )

        fig.update_layout(

            template="plotly_dark",

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            showlegend=False,

            annotations=[

                dict(

                    text=f"<b>{health:.1f}%</b>",

                    x=0.5,

                    y=0.5,

                    showarrow=False,

                    font=dict(

                        size=32,

                        color="white"

                    )

                )

            ]

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
    # ALERTS PER HOST
    # ------------------------------------------------------

    with left:

        st.markdown(

            '<div class="section-title">📈 Average Alerts per Incident</div>',

            unsafe_allow_html=True

        )

        plot_df = stats.copy()

        plot_df = plot_df.sort_values(

            "avg_alerts",

            ascending=False

        )

        fig = px.bar(

            plot_df,

            x="host",

            y="avg_alerts",

            text="avg_alerts",

            color="avg_alerts",

            color_continuous_scale="Viridis"

        )

        fig.update_layout(

            template="plotly_dark",

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            coloraxis_showscale=False,

            xaxis_title="Host",

            yaxis_title="Average Alerts"

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    # ------------------------------------------------------
    # CONFIDENCE BY HOST
    # ------------------------------------------------------

    with right:

        st.markdown(

            '<div class="section-title">🎯 Average Confidence by Host</div>',

            unsafe_allow_html=True

        )

        conf_df = stats.sort_values(

            "avg_confidence",

            ascending=False

        )

        fig = px.bar(

            conf_df,

            x="host",

            y="avg_confidence",

            text="avg_confidence",

            color="avg_confidence",

            color_continuous_scale="Greens"

        )

        fig.update_layout(

            template="plotly_dark",

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            coloraxis_showscale=False,

            xaxis_title="Host",

            yaxis_title="Confidence"

        )

        fig.update_traces(

            texttemplate="%{text:.2f}",

            textposition="outside"

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    st.write()
    # ======================================================
    # HOST INVESTIGATION
    # ======================================================

    st.markdown(
        '<div class="section-title">🖥 Host Investigation</div>',
        unsafe_allow_html=True
    )

    left, right = st.columns([3,1])

    with left:

        search = st.text_input(
            "🔍 Search Host",
            key="host_search"
        )

    with right:

        sort = st.selectbox(

            "Sort By",

            [

                "Highest Confidence",

                "Most Incidents",

                "Most Alerts"

            ]

        )

    table = stats.copy()

    # ------------------------------------------------------

    if search:

        table = table[
            table["host"]
            .astype(str)
            .str.lower()
            .str.contains(search.lower())
        ]

    # ------------------------------------------------------

    if sort == "Highest Confidence":

        table = table.sort_values(

            "avg_confidence",

            ascending=False

        )

    elif sort == "Most Incidents":

        table = table.sort_values(

            "incidents",

            ascending=False

        )

    elif sort == "Most Alerts":

        table = table.sort_values(

            "alerts",

            ascending=False

        )

    st.dataframe(

        table,

        width="stretch",

        hide_index=True,

        height=450

    )

    # ======================================================
    # EXPORT
    # ======================================================

    csv = table.to_csv(index=False).encode("utf-8")

    st.download_button(

        "📥 Export Host Report",

        csv,

        "host_health.csv",

        "text/csv"

    )

    st.write()
    # ======================================================
    # AI HOST INSIGHTS
    # ======================================================

    st.markdown(

        '<div class="section-title">🤖 AI Host Insights</div>',

        unsafe_allow_html=True

    )

    top_incident = stats.sort_values(

        "incidents",

        ascending=False

    ).iloc[0]

    top_alert = stats.sort_values(

        "alerts",

        ascending=False

    ).iloc[0]

    top_conf = stats.sort_values(

        "avg_confidence",

        ascending=False

    ).iloc[0]

    st.success(f"""

### Infrastructure Summary

The infrastructure currently contains **{len(stats)} monitored hosts**.

**Highest Incident Host**

• {top_incident['host']}

• {int(top_incident['incidents'])} incidents

---

**Highest Alert Volume**

• {top_alert['host']}

• {int(top_alert['alerts'])} alerts

---

**Highest Confidence**

• {top_conf['host']}

• {top_conf['avg_confidence']:.2f}

---

The infrastructure remains stable with an estimated health score of **{health:.1f}%**.

""")
    # ======================================================
    # RECOMMENDATIONS
    # ======================================================

    st.markdown(

        '<div class="section-title">💡 Recommended Actions</div>',

        unsafe_allow_html=True

    )

    recommendations = [

        "Investigate hosts generating repeated incidents.",

        "Review high alert-volume hosts for noisy monitoring rules.",

        "Check CPU, Memory and Disk utilization on affected hosts.",

        "Inspect application logs before restarting services.",

        "Verify recent deployments on unhealthy hosts.",

        "Monitor hosts with confidence greater than 0.90 first."

    ]

    for item in recommendations:

        st.success("✅ " + item)

    st.write()
    # ======================================================
    # TOP HOSTS
    # ======================================================

    st.markdown(

        '<div class="section-title">🏆 Top Infrastructure Hosts</div>',

        unsafe_allow_html=True

    )

    ranking = stats.sort_values(

        [

            "incidents",

            "alerts"

        ],

        ascending=False

    )

    st.dataframe(

        ranking.head(10),

        width="stretch",

        hide_index=True

    )

    st.divider()

    st.caption(

        "SentinelAI • Host Health Dashboard"

    )