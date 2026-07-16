# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 14:01:03 2026

@author: DELL
"""

import streamlit as st
from streamlit_option_menu import option_menu

from dashboard.dashboard import show_dashboard
from dashboard.alerts import show_alerts
from dashboard.incidents import show_incidents
from dashboard.rootcause import show_rootcause
from dashboard.suppression import show_suppression
from dashboard.analytics import show_analytics
from dashboard.hosts import show_hosts
from dashboard.copilot import show_copilot
st.set_page_config(
    page_title="AIOps Alert Correlation Platform",
    page_icon="🚨",
    layout="wide"
)

# ------------------------------------------------------

st.title("🚨 AIOps Alert Correlation & Root Cause Analysis")

# ------------------------------------------------------

with st.sidebar:

    selected = option_menu(

        menu_title="Navigation",

        options=[
            "Dashboard",
            "Alerts",
            "Incidents",
            "Root Cause",
            "Suppression",
            "Analytics",
            "Host Health",
            "AI Copilot"
        ],

        icons=[
            "speedometer2",
            "bell",
            "diagram-3",
            "fire",
            "shield-check",
            "bar-chart",
            "server"
        ],

        default_index=0
    )

# ------------------------------------------------------

if selected == "Dashboard":

    show_dashboard()

elif selected == "Alerts":

    show_alerts()

elif selected == "Incidents":

    show_incidents()

elif selected == "Root Cause":

    show_rootcause()

elif selected == "Suppression":

    show_suppression()

elif selected == "Analytics":

    show_analytics()

elif selected == "Host Health":

    show_hosts()

elif selected == "AI Copilot":

    show_copilot()