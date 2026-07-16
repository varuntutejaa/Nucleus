# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 16:13:58 2026

@author: DELL
"""

import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

from dashboard.utils import load_data


# ==========================================================
# NETWORK TOPOLOGY
# ==========================================================

def show_network():

    st.title("🌐 Infrastructure Network")

    st.caption("Interactive Infrastructure Topology")

    data = load_data()

    incidents = data["incident_summary.csv"]

    stats = data["incident_statistics.csv"]

    # ------------------------------------------------------

    G = nx.Graph()

    hosts = sorted(

        incidents["host"].unique()

    )

    for host in hosts:

        G.add_node(host)

    # ------------------------------------------------------
    # SIMPLE CONNECTIONS
    # (Replace later with real dependencies if available)
    # ------------------------------------------------------

    for i in range(len(hosts)-1):

        G.add_edge(

            hosts[i],

            hosts[i+1]

        )

    pos = nx.spring_layout(

        G,

        seed=42,

        k=1.2

    )

    # ==========================================================
    # NODE COLORS (Health Status)
    # ==========================================================

    node_x = []
    node_y = []
    node_color = []
    node_size = []
    node_text = []

    for node in G.nodes():

        x, y = pos[node]

        node_x.append(x)
        node_y.append(y)

        row = stats[stats["host"] == node]

        if not row.empty:

            incidents_count = int(row.iloc[0]["incidents"])
            confidence = float(row.iloc[0]["avg_confidence"])

        else:

            incidents_count = 0
            confidence = 0

        # --------------------------------------------------
        # HEALTH STATUS
        # --------------------------------------------------

        if confidence >= 0.80:

            color = "#22C55E"      # Green

        elif confidence >= 0.50:

            color = "#F59E0B"      # Yellow

        else:

            color = "#EF4444"      # Red

        node_color.append(color)

        node_size.append(

            25 + incidents_count * 0.3

        )

        node_text.append(

            f"""
Host : {node}

Incidents : {incidents_count}

Confidence : {confidence:.2f}
"""
        )

    # ==========================================================
    # EDGES
    # ==========================================================

    edge_x = []
    edge_y = []

    for edge in G.edges():

        x0, y0 = pos[edge[0]]

        x1, y1 = pos[edge[1]]

        edge_x.extend(

            [x0, x1, None]

        )

        edge_y.extend(

            [y0, y1, None]

        )

    edge_trace = go.Scatter(

        x=edge_x,

        y=edge_y,

        mode="lines",

        line=dict(

            width=2,

            color="#64748B"

        ),

        hoverinfo="none"

    )

    # ==========================================================
    # NODES
    # ==========================================================

    node_trace = go.Scatter(

        x=node_x,

        y=node_y,

        mode="markers+text",

        text=list(G.nodes()),

        textposition="top center",

        hovertext=node_text,

        hoverinfo="text",

        marker=dict(

            size=node_size,

            color=node_color,

            line=dict(

                width=2,

                color="white"

            )

        )

    )

    # ==========================================================
    # FIGURE
    # ==========================================================

    fig = go.Figure(

        data=[edge_trace, node_trace]

    )

    fig.update_layout(

        template="plotly_dark",

        height=700,

        paper_bgcolor="#0F172A",

        plot_bgcolor="#0F172A",

        margin=dict(

            l=20,

            r=20,

            t=40,

            b=20

        ),

        xaxis=dict(

            showgrid=False,

            zeroline=False,

            visible=False

        ),

        yaxis=dict(

            showgrid=False,

            zeroline=False,

            visible=False

        )

    )

    st.plotly_chart(

        fig,

        width="stretch"

    )

    # ==========================================================
    # HOST INVESTIGATION
    # ==========================================================

    st.write("")

    st.markdown("## 🔍 Host Investigation")

    selected_host = st.selectbox(

        "Select Host",

        sorted(hosts)

    )

    # ------------------------------------------------------

    host_stats = stats[
        stats["host"] == selected_host
    ]

    host_incidents = incidents[
        incidents["host"] == selected_host
    ]

    if host_stats.empty:

        st.warning("No information available.")

        return

    host_stats = host_stats.iloc[0]

    # ==========================================================
    # KPI CARDS
    # ==========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🚨 Incidents",
        int(host_stats["incidents"])
    )

    c2.metric(
        "📢 Alerts",
        int(host_stats["alerts"])
    )

    c3.metric(
        "🎯 Confidence",
        f"{host_stats['avg_confidence']:.2f}"
    )

    c4.metric(
        "⏱ Avg Duration",
        f"{host_stats['avg_duration']:.1f}s"
    )

    st.write("")

    # ==========================================================
    # HEALTH GAUGE + AI ANALYSIS
    # ==========================================================

    confidence = float(host_stats["avg_confidence"])

    health = min(
        100,
        confidence * 100
    )

    left, right = st.columns([1, 2])

    with left:

        fig = go.Figure(

            go.Indicator(

                mode="gauge+number",

                value=health,

                title={"text": "Health"},

                gauge={

                    "axis": {"range": [0, 100]},

                    "bar": {"color": "green"},

                    "steps": [

                        {"range": [0, 50], "color": "#EF4444"},

                        {"range": [50, 80], "color": "#F59E0B"},

                        {"range": [80, 100], "color": "#22C55E"}

                    ]

                }

            )

        )

        fig.update_layout(

            template="plotly_dark",

            height=350,

            paper_bgcolor="#0F172A"

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    with right:

        st.subheader("🤖 AI Infrastructure Analysis")

        recommendation = "Continue Monitoring"

        if confidence < 0.50:

            recommendation = "Immediate Investigation Required"

        elif confidence < 0.80:

            recommendation = "Review Infrastructure"

        st.info(f"""

### Host Summary

**Host:** {selected_host}

This host generated **{int(host_stats['incidents'])} incidents**
containing **{int(host_stats['alerts'])} alerts**.

Average incident confidence is **{confidence:.2f}**.

Average incident duration is **{host_stats['avg_duration']:.1f} seconds**.

### Recommendation

{recommendation}

""")

    # ==========================================================
    # INCIDENT TABLE
    # ==========================================================

    st.write("")

    st.subheader("📋 Incidents")

    st.dataframe(

        host_incidents,

        width="stretch",

        hide_index=True

    )

    # ==========================================================
    # TOP UNHEALTHY HOSTS
    # ==========================================================

    st.write("")

    st.markdown("## 🚨 Infrastructure Risk Ranking")

    ranking = stats.copy()

    # Calculate health score
    ranking["health_score"] = (
        ranking["avg_confidence"] * 100
    ).round(1)

    ranking = ranking.sort_values(
        by=[
            "health_score",
            "incidents"
        ],
        ascending=[True, False]
    )

    display_cols = []

    preferred = [

        "host",

        "health_score",

        "incidents",

        "alerts",

        "avg_alerts",

        "avg_duration",

        "avg_confidence"

    ]

    for col in preferred:

        if col in ranking.columns:

            display_cols.append(col)

    st.dataframe(

        ranking[display_cols],

        width="stretch",

        hide_index=True,

        height=350

    )

    # ==========================================================
    # DOWNLOAD REPORT
    # ==========================================================

    csv = ranking.to_csv(index=False).encode("utf-8")

    st.download_button(

        "📥 Download Network Report",

        csv,

        "network_health_report.csv",

        "text/csv"

    )

    st.write("")

    # ==========================================================
    # EXECUTIVE AI SUMMARY
    # ==========================================================

    st.markdown("## 🤖 AI Executive Summary")

    highest_incidents = stats.loc[
        stats["incidents"].idxmax()
    ]

    highest_alerts = stats.loc[
        stats["alerts"].idxmax()
    ]

    highest_conf = stats.loc[
        stats["avg_confidence"].idxmax()
    ]

    lowest_health = ranking.iloc[0]

    st.success(f"""

### Infrastructure Overview

A total of **{len(stats)} infrastructure hosts** are currently monitored.

---

### Highest Incident Volume

**{highest_incidents['host']}**

Incidents : **{int(highest_incidents['incidents'])}**

---

### Highest Alert Volume

**{highest_alerts['host']}**

Alerts : **{int(highest_alerts['alerts'])}**

---

### Most Reliable Host

**{highest_conf['host']}**

Confidence : **{highest_conf['avg_confidence']:.2f}**

---

### Highest Risk Host

**{lowest_health['host']}**

Health Score : **{lowest_health['health_score']:.1f}%**

---

Overall infrastructure health appears stable, although hosts with lower health scores should be prioritised for investigation before additional incidents propagate through dependent services.

""")

    # ==========================================================
    # RECOMMENDATIONS
    # ==========================================================

    st.write("")

    st.markdown("## 💡 Recommended Actions")

    recommendations = [

        "Investigate the highest-risk host before secondary alerts propagate.",

        "Review hosts generating excessive alert volumes for noisy monitoring rules.",

        "Monitor confidence trends to identify deteriorating services early.",

        "Validate CPU, Memory and Disk metrics on affected hosts.",

        "Inspect recent deployments affecting high-incident hosts.",

        "Use correlated incidents rather than individual alerts for troubleshooting."

    ]

    for item in recommendations:

        st.success("✅ " + item)

    st.divider()

    st.caption(
        "SentinelAI • Infrastructure Network Topology • Enterprise AIOps Platform"
    )