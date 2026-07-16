# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 14:23:50 2026

@author: DELL
"""

import pandas as pd
import streamlit as st
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent

DATA_PATH = BASE_PATH / "data" / "alerts"

@st.cache_data
def load_data():

    data = {}

    files = [
        "alerts.csv",
        "correlated_alerts.csv",
        "incident_summary.csv",
        "incident_statistics.csv",
        "root_cause.csv",
        "suppressed_alerts.csv",
        "incident_root_summary.csv"
    ]

    for file in files:

        path = DATA_PATH / file

        if path.exists():

            data[file] = pd.read_csv(path)

        else:

            data[file] = pd.DataFrame()

    return data