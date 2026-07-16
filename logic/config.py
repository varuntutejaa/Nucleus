# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 11:32:11 2026

@author: DELL
"""

from pathlib import Path

# =====================================================
# DATASET LOCATION
# =====================================================

DATASET_ROOT = Path(r"D:\AIOps挑战赛数据")

# =====================================================
# PROJECT PATHS
# =====================================================

PROJECT_ROOT = Path(__file__).parent

OUTPUT_DIR = PROJECT_ROOT / "outputs"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ALERT_DIR = PROJECT_ROOT / "data" / "alerts"

MODEL_DIR = PROJECT_ROOT / "models"

# Create folders automatically
OUTPUT_DIR.mkdir(exist_ok=True)

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

ALERT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_DIR.mkdir(exist_ok=True)