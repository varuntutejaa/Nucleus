import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard.utils import load_data


def show_suppression():

    st.title("🛡 Alert Suppression")

    st.caption("Duplicate Alert Reduction Analysis")

    data = load_data()

    alerts = data["alerts.csv"]
    suppressed = data["suppressed_alerts.csv"]
    incidents = data["incident_summary.csv"]

    total_alerts = len(alerts)
    suppressed_alerts = len(suppressed)
    remaining = total_alerts - suppressed_alerts
    reduction = (suppressed_alerts / total_alerts) * 100

    # ======================================================
    # KPI CARDS
    # ======================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("🚨 Total Alerts", f"{total_alerts:,}")
    c2.metric("🛡 Suppressed", f"{suppressed_alerts:,}")
    c3.metric("🔗 Remaining", f"{remaining:,}")
    c4.metric("📉 Reduction", f"{reduction:.2f}%")

    st.divider()

    # ======================================================
    # CHARTS
    # ======================================================

    left, right = st.columns(2)

    with left:

        df = pd.DataFrame({

            "Type": [

                "Suppressed",

                "Remaining"

            ],

            "Count": [

                suppressed_alerts,

                remaining

            ]

        })

        fig = px.pie(

            df,

            names="Type",

            values="Count",

            hole=0.6,

            title="Alert Reduction"

        )

        fig.update_layout(template="plotly_dark")

        st.plotly_chart(fig, width="stretch")

    with right:

        fig = px.bar(

            x=["Original Alerts", "Correlated Incidents"],

            y=[

                total_alerts,

                len(incidents)

            ],

            text=[

                total_alerts,

                len(incidents)

            ],

            title="Before vs After Correlation"

        )

        fig.update_layout(template="plotly_dark")

        st.plotly_chart(fig, width="stretch")

    st.divider()

    # ======================================================
    # SUPPRESSED ALERTS TABLE
    # ======================================================

    st.subheader("📋 Suppressed Alerts")

    st.dataframe(

        suppressed,

        width="stretch",

        hide_index=True,

        height=450

    )

    st.divider()

    st.success(f"""

### Suppression Summary

• Total Alerts Processed: **{total_alerts:,}**

• Suppressed Alerts: **{suppressed_alerts:,}**

• Remaining Alerts: **{remaining:,}**

• Alert Reduction Achieved: **{reduction:.2f}%**

The suppression engine successfully removed duplicate and derivative alerts while preserving the primary alert for each correlated incident.

""")