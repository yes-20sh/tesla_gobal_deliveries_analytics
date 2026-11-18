"""
Script 02: Post-ETL Data Validation & Integrity Audit
Project: Tesla Global Deliveries & Business Performance Analytics Initiative
Author: Yashraj Singh Solanki
"""

import os
import sys
import pandas as pd
import numpy as np


def run_post_etl_validation():
    print("=" * 80)
    print("TESLA ANALYTICS PIPELINE: POST-ETL DATA VALIDATION & STAR SCHEMA AUDIT")
    print("=" * 80)

    # Load processed star schema
    fact_path = "data/processed/fact_deliveries.csv"
    date_path = "data/processed/dim_date.csv"
    model_path = "data/processed/dim_model.csv"
    region_path = "data/processed/dim_region.csv"

    for p in [fact_path, date_path, model_path, region_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing required processed file: {p}")

    fact = pd.read_csv(fact_path)
    dim_date = pd.read_csv(date_path)
    dim_model = pd.read_csv(model_path)
    dim_region = pd.read_csv(region_path)

    print(f"Loaded fact_deliveries: {fact.shape[0]} rows, {fact.shape[1]} columns")
    print(f"Loaded dim_date:        {dim_date.shape[0]} rows (144 calendar months)")
    print(f"Loaded dim_model:       {dim_model.shape[0]} rows (5 approved models)")
    print(f"Loaded dim_region:      {dim_region.shape[0]} rows (4 approved regions)")
    print("-" * 80)

    checks = []

    # Check 1: Referential Integrity - DateKey
    missing_dates = ~fact["DateKey"].isin(dim_date["DateKey"])
    c1_pass = missing_dates.sum() == 0
    checks.append(("Referential Integrity (DateKey)", c1_pass, f"Unmatched keys: {missing_dates.sum()}"))

    # Check 2: Referential Integrity - ModelKey
    missing_models = ~fact["ModelKey"].isin(dim_model["ModelKey"])
    c2_pass = missing_models.sum() == 0
    checks.append(("Referential Integrity (ModelKey)", c2_pass, f"Unmatched keys: {missing_models.sum()}"))

    # Check 3: Referential Integrity - RegionKey
    missing_regions = ~fact["RegionKey"].isin(dim_region["RegionKey"])
    c3_pass = missing_regions.sum() == 0
    checks.append(("Referential Integrity (RegionKey)", c3_pass, f"Unmatched keys: {missing_regions.sum()}"))

    # Check 4: Null Values in Fact Table
    fact_nulls = fact.isnull().sum().sum()
    c4_pass = fact_nulls == 0
    checks.append(("Fact Table Completeness (Zero Nulls)", c4_pass, f"Null cells found: {fact_nulls}"))

    # Check 5: Volumetric Tie-Out (Raw vs Fact)
    df_raw_1 = pd.read_csv("data/raw/tesla_deliveries_dataset_2015_2025.csv")
    df_raw_2 = pd.read_csv("data/raw/tesla_deliveries_dataset_2026.csv")
    raw_deliveries = df_raw_1["Estimated_Deliveries"].sum() + df_raw_2["Estimated_Deliveries"].sum()
    fact_deliveries = fact["Estimated_Deliveries"].sum()
    del_diff = abs(raw_deliveries - fact_deliveries)
    c5_pass = del_diff == 0
    checks.append(("Volumetric Tie-Out (Deliveries)", c5_pass, f"Raw: {raw_deliveries:,} | Fact: {fact_deliveries:,} | Diff: {del_diff}"))

    # Check 6: Volumetric Tie-Out (Production)
    raw_production = df_raw_1["Production_Units"].sum() + df_raw_2["Production_Units"].sum()
    fact_production = fact["Production_Units"].sum()
    prod_diff = abs(raw_production - fact_production)
    c6_pass = prod_diff == 0
    checks.append(("Volumetric Tie-Out (Production)", c6_pass, f"Raw: {raw_production:,} | Fact: {fact_production:,} | Diff: {prod_diff}"))

    # Check 7: Financial Integrity (Estimated Revenue)
    recalculated_rev = fact["Estimated_Deliveries"] * fact["Avg_Price_USD"]
    rev_diff = np.max(np.abs(fact["Est_Revenue_USD"] - recalculated_rev))
    c7_pass = rev_diff < 0.01
    checks.append(("Financial Calculation Parity (Revenue)", c7_pass, f"Max difference: ${rev_diff:.4f}"))

    # Check 8: Operational Sanity (Inventory Gap Formula)
    gap_check = fact["Production_Units"] - fact["Estimated_Deliveries"]
    gap_diff = np.max(np.abs(fact["Inventory_Gap"] - gap_check))
    c8_pass = gap_diff == 0
    checks.append(("Operational KPI Formula (Inventory Gap)", c8_pass, f"Max difference: {gap_diff}"))

    # Check 9: Model Classification Governance (Model S & X are Premium, others 'To classify')
    s_x_premium = fact[fact["Model"].isin(["Model S", "Model X"])]["Business_Segment"].eq("Premium").all()
    others_to_classify = fact[~fact["Model"].isin(["Model S", "Model X"])]["Business_Segment"].eq("To classify").all()
    c9_pass = s_x_premium and others_to_classify
    checks.append(("BRD Segment Governance (Model S/X Premium)", c9_pass, "Model S/X = Premium; Model 3/Y/Cybertruck = To classify"))

    # Print summary scorecard
    all_passed = True
    for test_name, passed, detail in checks:
        status_str = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"{status_str:<8} | {test_name:<42} | {detail}")

    print("-" * 80)
    if all_passed:
        print("ALL 9 POST-ETL INTEGRITY AUDIT CHECKS PASSED WITH ZERO DISCREPANCIES.")
    else:
        print("WARNING: ONE OR MORE INTEGRITY CHECKS FAILED.")
    print("=" * 80)

    # Write summary log
    os.makedirs("data/working", exist_ok=True)
    with open("data/working/validation_summary.txt", "w", encoding="utf-8") as f:
        f.write("TESLA POST-ETL DATA VALIDATION AUDIT REPORT\n")
        f.write(f"Timestamp: {pd.Timestamp.now()}\n")
        f.write("-" * 80 + "\n")
        for test_name, passed, detail in checks:
            f.write(f"{'[PASS]' if passed else '[FAIL]':<8} | {test_name:<42} | {detail}\n")
        f.write("-" * 80 + "\n")
        f.write(f"Overall Result: {'SUCCESS - FULLY VALIDATED' if all_passed else 'FAILED'}\n")


if __name__ == "__main__":
    run_post_etl_validation()
