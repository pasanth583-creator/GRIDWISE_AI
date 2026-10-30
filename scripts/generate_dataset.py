"""
GRIDWISE AI - Dataset Generation Script
Executes the complete generation pipeline for campus demand, solar, prices, and 500 scenarios.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.data_generation import run_full_data_generation

if __name__ == "__main__":
    print("===================================================================")
    print("GRIDWISE AI - PHASE 3: DATASET GENERATION & SCENARIO ENGINE")
    print("===================================================================")
    result = run_full_data_generation()
    print("\nSummary of Generated Records:")
    for key, count in result["record_counts"].items():
        print(f"  - {key}: {count:,} records")
    print("\nValidation Status:", result["validation_report"]["status"])
    print("===================================================================")

