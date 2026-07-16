# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 16:25:02 2026

@author: DELL
"""

import streamlit as st
import pandas as pd

from dashboard.utils import load_data

import plotly.express as px
def show_reports():

    st.title("📄 Reports")

    st.caption("Generate Executive Infrastructure Reports")

    data = load_data()

    alerts = data["alerts.csv"]

    incidents = data["incident_summary.csv"]

    roots = data["root_cause.csv"]

    suppressed = data["suppressed_alerts.csv"]

    stats = data["incident_statistics.csv"]

    total_alerts = len(alerts)

    total_incidents = len(incidents)

    total_roots = len(roots)

    reduction = (

        len(suppressed)

        / total_alerts

    ) * 100

    avg_conf = stats["avg_confidence"].mean()

    c1,c2,c3,c4,c5 = st.columns(5)

    c1.metric("Alerts",total_alerts)

    c2.metric("Incidents",total_incidents)

    c3.metric("Root Causes",total_roots)

    c4.metric("Reduction",f"{reduction:.2f}%")

    c5.metric("Confidence",f"{avg_conf:.2f}")

    st.write("")
    # ======================================================
    # REPORT TYPE
    # ======================================================

    report_type = st.selectbox(

        "Select Report",

        [

            "Executive Report",

            "Incident Report",

            "Root Cause Report",

            "Host Health Report"

        ]

    )

    st.write("")

    # ======================================================
    # REPORT PREVIEW
    # ======================================================

    st.subheader("📄 Report Preview")

    if report_type == "Executive Report":

        preview = pd.DataFrame({

            "Metric":[

                "Total Alerts",

                "Correlated Incidents",

                "Root Causes",

                "Suppressed Alerts",

                "Alert Reduction",

                "Average Confidence"

            ],

            "Value":[

                total_alerts,

                total_incidents,

                total_roots,

                len(suppressed),

                f"{reduction:.2f}%",

                f"{avg_conf:.2f}"

            ]

        })

    elif report_type == "Incident Report":

        preview = incidents.head(20)

    elif report_type == "Root Cause Report":

        preview = roots.head(20)

    else:

        preview = stats

    st.dataframe(

        preview,

        width="stretch",

        hide_index=True,

        height=450

    )

    st.write("")

    # ======================================================
    # AI REPORT SUMMARY
    # ======================================================

    st.subheader("🤖 Executive Summary")

    if report_type == "Executive Report":

        st.success(f"""

### Infrastructure Overview

• Total alerts processed: **{total_alerts:,}**

• Correlated incidents: **{total_incidents:,}**

• Root causes identified: **{total_roots:,}**

• Duplicate alerts suppressed: **{len(suppressed):,}**

• Alert reduction achieved: **{reduction:.2f}%**

• Average confidence: **{avg_conf:.2f}**

The alert correlation engine significantly reduced operator workload by suppressing duplicate alerts while preserving incident-level visibility.

""")

    elif report_type == "Incident Report":

        st.info("""

This report contains all correlated incidents including:

• Host

• Alert Count

• Duration

• Severity

• Root Cause

• Confidence

""")

    elif report_type == "Root Cause Report":

        st.info("""

This report summarizes all detected root causes.

Each record contains:

• Host

• Metric

• Severity

• Root Cause Score

• Timestamp

""")

    else:

        st.info("""

This report summarizes infrastructure health.

It includes:

• Incident count

• Alert count

• Confidence

• Duration

• Health indicators

""")

    st.write("")
    # ======================================================
    # EXPORT REPORTS
    # ======================================================

    st.subheader("📥 Export Reports")

    # Select dataset based on report type
    if report_type == "Executive Report":

        export_df = preview.copy()

    elif report_type == "Incident Report":

        export_df = incidents.copy()

    elif report_type == "Root Cause Report":

        export_df = roots.copy()

    else:

        export_df = stats.copy()

    # ------------------------------------------------------
    # CSV DOWNLOAD
    # ------------------------------------------------------

    csv = export_df.to_csv(index=False).encode("utf-8")

    # ------------------------------------------------------
    # JSON DOWNLOAD
    # ------------------------------------------------------

    json_data = export_df.to_json(
        orient="records",
        indent=4
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.download_button(

            "📄 Download CSV",

            csv,

            report_type.replace(" ", "_") + ".csv",

            "text/csv"

        )

    with c2:

        st.download_button(

            "📋 Download JSON",

            json_data,

            report_type.replace(" ", "_") + ".json",

            "application/json"

        )

    # ------------------------------------------------------
    # PDF GENERATION
    # ------------------------------------------------------

    with c3:

        if st.button("📑 Generate PDF"):

            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle
            )

            from reportlab.lib import colors

            from reportlab.lib.styles import getSampleStyleSheet

            pdf_name = report_type.replace(" ", "_") + ".pdf"

            doc = SimpleDocTemplate(pdf_name)

            styles = getSampleStyleSheet()

            elements = []

            elements.append(
                Paragraph(
                    "<b>SentinelAI Report</b>",
                    styles["Title"]
                )
            )

            elements.append(
                Spacer(1, 20)
            )

            elements.append(
                Paragraph(
                    f"<b>Report Type:</b> {report_type}",
                    styles["Normal"]
                )
            )

            elements.append(
                Paragraph(
                    f"<b>Total Alerts:</b> {total_alerts}",
                    styles["Normal"]
                )
            )

            elements.append(
                Paragraph(
                    f"<b>Total Incidents:</b> {total_incidents}",
                    styles["Normal"]
                )
            )

            elements.append(
                Paragraph(
                    f"<b>Root Causes:</b> {total_roots}",
                    styles["Normal"]
                )
            )

            elements.append(
                Paragraph(
                    f"<b>Alert Reduction:</b> {reduction:.2f}%",
                    styles["Normal"]
                )
            )

            elements.append(
                Paragraph(
                    f"<b>Average Confidence:</b> {avg_conf:.2f}",
                    styles["Normal"]
                )
            )

            elements.append(
                Spacer(1, 20)
            )

            # Show first 15 rows
            table_data = [

                export_df.columns.tolist()

            ]

            table_data += export_df.head(15).values.tolist()

            table = Table(table_data)

            table.setStyle(

                TableStyle([

                    ("BACKGROUND",(0,0),(-1,0),colors.grey),

                    ("TEXTCOLOR",(0,0),(-1,0),colors.whitesmoke),

                    ("GRID",(0,0),(-1,-1),1,colors.black),

                    ("BACKGROUND",(0,1),(-1,-1),colors.beige),

                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")

                ])

            )

            elements.append(table)

            doc.build(elements)

            with open(pdf_name, "rb") as f:

                st.download_button(

                    "⬇ Download PDF",

                    f,

                    pdf_name,

                    mime="application/pdf"

                )

            st.success("PDF Generated Successfully!")
    # ======================================================
    # REPORT ANALYTICS
    # ======================================================

    st.write("")

    st.subheader("📊 Executive Analytics")

    left, right = st.columns(2)

    # ------------------------------------------------------
    # Executive KPI Chart
    # ------------------------------------------------------

    with left:

        executive = pd.DataFrame({

            "Metric":[

                "Alerts",

                "Incidents",

                "Root Causes",

                "Suppressed"

            ],

            "Count":[

                total_alerts,

                total_incidents,

                total_roots,

                len(suppressed)

            ]

        })

        fig = px.bar(

            executive,

            x="Metric",

            y="Count",

            text="Count",

            color="Metric"

        )

        fig.update_layout(

            template="plotly_dark",

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            showlegend=False

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    # ------------------------------------------------------
    # Alert Reduction
    # ------------------------------------------------------

    with right:

        fig = px.pie(

            names=[

                "Suppressed",

                "Remaining"

            ],

            values=[

                len(suppressed),

                total_alerts-len(suppressed)

            ],

            hole=0.65

        )

        fig.update_layout(

            template="plotly_dark",

            height=420,

            paper_bgcolor="#0F172A",

            plot_bgcolor="#0F172A",

            annotations=[

                dict(

                    text=f"{reduction:.2f}%",

                    x=0.5,

                    y=0.5,

                    showarrow=False,

                    font=dict(

                        size=28,

                        color="white"

                    )

                )

            ]

        )

        st.plotly_chart(

            fig,

            width="stretch"

        )

    st.write("")
    # ======================================================
    # AI RECOMMENDATIONS
    # ======================================================

    st.subheader("🤖 AI Recommendations")

    recommendations = [

        "Continue using alert correlation to reduce alert fatigue.",

        "Investigate hosts with the highest incident counts first.",

        "Prioritize Critical severity incidents.",

        "Review monitoring thresholds to eliminate noisy alerts.",

        "Monitor confidence trends for early anomaly detection.",

        "Generate executive reports weekly for management review."

    ]

    for rec in recommendations:

        st.success("✅ " + rec)

    st.write("")
    # ======================================================
    # REPORT INFORMATION
    # ======================================================

    from datetime import datetime

    st.subheader("📑 Report Information")

    report_info = pd.DataFrame({

        "Property":[

            "Generated",

            "Report",

            "Platform",

            "Version",

            "Prepared By"

        ],

        "Value":[

            datetime.now().strftime("%d-%m-%Y %H:%M:%S"),

            report_type,

            "SentinelAI",

            "1.0",

            "Alert Correlation Engine"

        ]

    })

    st.table(report_info)

    st.write("")
    # ======================================================
    # FOOTER
    # ======================================================

    st.divider()

    st.caption(
        "SentinelAI • Enterprise Reporting Module • AIOps Platform"
    )