"""
Script 01: Production ETL Pipeline
Phase 4: Data Extraction, Transformation, and Loading
Project: Tesla Global Deliveries & Business Performance Analytics Initiative
Author: Yashraj Singh Solanki
"""

import os
import sys
import logging
from datetime import datetime
import pandas as pd
import numpy as np

# Configure logging
os.makedirs("data/working", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/working/etl_pipeline.log", mode="w", encoding="utf-8")
    ]
)
logger = logging.getLogger("ETL_Pipeline")


def extract_data():
    """4.1 Extract raw datasets and configuration business rules."""
    logger.info("=== STEP 4.1: EXTRACTING DATA ===")
    path_2015_2025 = "data/raw/tesla_deliveries_dataset_2015_2025.csv"
    path_2026 = "data/raw/tesla_deliveries_dataset_2026.csv"
    
    config_path = "config/business_rules.xlsx"
    if not os.path.exists(config_path):
        config_path = "data/raw/business_rules.xlsx"

    logger.info(f"Loading raw file: {path_2015_2025}")
    df_2015_2025 = pd.read_csv(path_2015_2025)
    
    logger.info(f"Loading raw file: {path_2026}")
    df_2026 = pd.read_csv(path_2026)
    
    logger.info(f"Loading business rules: {config_path}")
    business_rules = pd.ExcelFile(config_path)

    logger.info(f"Source 2015-2025 shape: {df_2015_2025.shape}")
    logger.info(f"Source 2026 shape: {df_2026.shape}")
    logger.info(f"Business Rules sheets: {business_rules.sheet_names}")
    
    # Source-to-target audit checks
    logger.info(f"2015-2025 columns: {list(df_2015_2025.columns)}")
    logger.info(f"2026 columns: {list(df_2026.columns)}")
    assert list(df_2015_2025.columns) == list(df_2026.columns), "Column schema mismatch between partitions!"
    
    return df_2015_2025, df_2026, business_rules


def combine_datasets(df_2015_2025, df_2026):
    """4.2 Combine historical and forward horizon datasets."""
    logger.info("=== STEP 4.2: COMBINING DATASETS ===")
    df = pd.concat([df_2015_2025, df_2026], ignore_index=True)
    logger.info(f"Combined dataset shape: {df.shape}")
    
    # Verification of years and months
    years_present = sorted(df["Year"].unique().tolist())
    months_present = sorted(df["Month"].unique().tolist())
    logger.info(f"Verified Years present ({len(years_present)}): {years_present}")
    logger.info(f"Verified Months present ({len(months_present)}): {months_present}")
    assert len(years_present) == 12, "Expected 12 distinct years (2015-2026)!"
    assert len(months_present) == 12, "Expected 12 distinct months (1-12)!"
    
    return df


def standardise_column_formats(df):
    """4.3 Standardise column names, string formats, and numeric types."""
    logger.info("=== STEP 4.3: STANDARDISING COLUMN FORMATS ===")
    # Strip whitespace from column headers
    df.columns = df.columns.str.strip()

    # Standardise string categorical representations
    df["Region"] = df["Region"].str.strip().str.title()
    df["Model"] = df["Model"].str.strip()
    df["Source_Type"] = df["Source_Type"].str.strip()

    # Type coercion for numeric columns
    numeric_columns = [
        "Year",
        "Month",
        "Estimated_Deliveries",
        "Production_Units",
        "Avg_Price_USD",
        "Battery_Capacity_kWh",
        "Range_km",
        "CO2_Saved_tons",
        "Charging_Stations"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    logger.info("Column formats and numeric types successfully standardised.")
    return df


def perform_data_cleaning_and_quarantine(df):
    """4.4 & 4.5 Check missing values, duplicate business keys, and validate boundaries."""
    logger.info("=== STEP 4.4 & 4.5: DATA CLEANING, VALIDATION & QUARANTINE ===")
    os.makedirs("data/quarantine", exist_ok=True)
    
    # Check missing values
    missing_series = df.isnull().sum()
    total_missing = missing_series.sum()
    logger.info(f"Total missing values across all columns: {total_missing}")
    if total_missing > 0:
        logger.warning(f"Missing values by column:\n{missing_series[missing_series > 0]}")

    # Check duplicate business keys
    business_key = ["Year", "Month", "Region", "Model"]
    duplicates = df[df.duplicated(subset=business_key, keep=False)]
    logger.info(f"Duplicate business key records found: {len(duplicates)}")
    duplicates.to_csv("data/quarantine/duplicate_records.csv", index=False)
    logger.info("Duplicate audit log saved to data/quarantine/duplicate_records.csv")

    # Check invalid records based on business rules
    invalid_mask = (
        (df["Estimated_Deliveries"] < 0) |
        (df["Production_Units"] < 0) |
        (df["Avg_Price_USD"] <= 0) |
        (~df["Month"].between(1, 12))
    )
    invalid_records = df[invalid_mask]
    logger.info(f"Invalid domain records found: {len(invalid_records)}")
    invalid_records.to_csv("data/quarantine/invalid_records.csv", index=False)
    logger.info("Invalid audit log saved to data/quarantine/invalid_records.csv")

    # Clean working copy
    df_clean = df.drop(index=invalid_records.index).copy()
    if len(duplicates) > 0:
        # Retention rule: keep first occurrence after quarantine logging
        df_clean = df_clean.drop_duplicates(subset=business_key, keep="first").copy()
        
    logger.info(f"Clean working dataset retained: {df_clean.shape[0]} records.")
    return df_clean


def merge_business_rules(df_clean, business_rules):
    """4.6 Merge business rules and model references."""
    logger.info("=== STEP 4.6: MERGING BUSINESS RULES ===")
    model_rules = pd.read_excel(business_rules, sheet_name="Model_Reference")
    logger.info(f"Model reference rules:\n{model_rules[['Model', 'Business Segment', 'Launch Year']]}")

    # Clean model rule headers
    model_rules.columns = [c.strip().replace(" ", "_") for c in model_rules.columns]
    
    df_clean = df_clean.merge(
        model_rules[["Model", "Business_Segment", "Launch_Year", "Target_Market_Tier"]],
        on="Model",
        how="left",
        validate="many_to_one"
    )
    logger.info(f"Successfully merged business rules. New columns: Business_Segment, Launch_Year, Target_Market_Tier")
    return df_clean


def create_derived_business_metrics(df_clean):
    """4.7 & 4.8 Calculate KPIs, ratios, and chronological date dimension."""
    logger.info("=== STEP 4.7 & 4.8: CALCULATING DERIVED METRICS & DATES ===")
    # Financial metrics
    df_clean["Est_Revenue_USD"] = df_clean["Estimated_Deliveries"] * df_clean["Avg_Price_USD"]
    
    # Operational metrics
    df_clean["Inventory_Gap"] = df_clean["Production_Units"] - df_clean["Estimated_Deliveries"]
    
    # Efficiency metrics with zero-division safeguards
    df_clean["Delivery_Efficiency"] = np.where(
        df_clean["Production_Units"] > 0,
        (df_clean["Estimated_Deliveries"] / df_clean["Production_Units"]) * 100.0,
        0.0
    )
    
    df_clean["Efficiency_km_per_kWh"] = np.where(
        df_clean["Battery_Capacity_kWh"] > 0,
        df_clean["Range_km"] / df_clean["Battery_Capacity_kWh"],
        0.0
    )

    # 4.8 Create standard Date column for time intelligence
    df_clean["Date"] = pd.to_datetime(
        df_clean["Year"].astype("Int64").astype(str)
        + "-"
        + df_clean["Month"].astype("Int64").astype(str).str.zfill(2)
        + "-01",
        errors="coerce"
    )
    logger.info("Derived KPIs (Revenue, Inventory Gap, Efficiency, Efficiency_km_per_kWh, Date) created.")
    return df_clean


def perform_outlier_detection(df_clean):
    """4.9 Multi-tiered Outlier Detection (Global & Grouped IQR)."""
    logger.info("=== STEP 4.9: MULTI-TIERED OUTLIER DETECTION ===")
    # Global IQR on Estimated_Deliveries
    q1 = df_clean["Estimated_Deliveries"].quantile(0.25)
    q3 = df_clean["Estimated_Deliveries"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    df_clean["Delivery_Outlier"] = (
        (df_clean["Estimated_Deliveries"] < lower_bound) |
        (df_clean["Estimated_Deliveries"] > upper_bound)
    )
    logger.info(f"Global Outliers identified (Thresholds: {lower_bound:.1f} - {upper_bound:.1f}): {df_clean['Delivery_Outlier'].sum()} records.")

    # Grouped IQR by Model & Region (localized variance detection per Section 4.9)
    def is_group_outlier(series):
        g_q1 = series.quantile(0.25)
        g_q3 = series.quantile(0.75)
        g_iqr = g_q3 - g_q1
        return (series < (g_q1 - 1.5 * g_iqr)) | (series > (g_q3 + 1.5 * g_iqr))

    df_clean["Delivery_Outlier_Group"] = (
        df_clean.groupby(["Model", "Region"])["Estimated_Deliveries"]
        .transform(is_group_outlier)
    )
    logger.info(f"Grouped Model/Region Outliers identified: {df_clean['Delivery_Outlier_Group'].sum()} records.")
    return df_clean


def build_star_schema_and_load(df_clean):
    """4.10 & 4.11 Create dimensional star schema and export processed data."""
    logger.info("=== STEP 4.10 & 4.11: BUILDING STAR SCHEMA & EXPORTING ===")
    os.makedirs("data/processed", exist_ok=True)

    # 1. Dimension: dim_model
    model_df = df_clean[["Model", "Business_Segment", "Launch_Year", "Target_Market_Tier"]].drop_duplicates().reset_index(drop=True)
    model_df = model_df.sort_values("Model").reset_index(drop=True)
    model_df["ModelKey"] = model_df.index + 1
    dim_model = model_df[["ModelKey", "Model", "Business_Segment", "Launch_Year", "Target_Market_Tier"]]
    
    # 2. Dimension: dim_region
    region_df = df_clean[["Region"]].drop_duplicates().reset_index(drop=True)
    region_codes = {
        "North America": "NA",
        "Europe": "EU",
        "Asia": "APAC",
        "Middle East": "ME"
    }
    region_scopes = {
        "North America": "United States, Canada, Mexico",
        "Europe": "EU-27, United Kingdom, Norway, Switzerland",
        "Asia": "Mainland China, Japan, South Korea, APAC",
        "Middle East": "UAE, Saudi Arabia, Qatar, Israel"
    }
    region_df = region_df.sort_values("Region").reset_index(drop=True)
    region_df["RegionKey"] = region_df.index + 1
    region_df["Region_Code"] = region_df["Region"].map(region_codes)
    region_df["Operating_Scope"] = region_df["Region"].map(region_scopes)
    dim_region = region_df[["RegionKey", "Region", "Region_Code", "Operating_Scope"]]

    # 3. Dimension: dim_date
    date_df = df_clean[["Date", "Year", "Month"]].drop_duplicates().sort_values("Date").reset_index(drop=True)
    date_df["DateKey"] = date_df["Year"] * 10000 + date_df["Month"] * 100 + 1
    date_df["Quarter"] = (date_df["Month"] - 1) // 3 + 1
    date_df["Year_Quarter"] = date_df["Year"].astype(str) + "-Q" + date_df["Quarter"].astype(str)
    date_df["Month_Name"] = date_df["Date"].dt.strftime("%B")
    date_df["Month_Short"] = date_df["Date"].dt.strftime("%b")
    date_df["Is_Quarter_End"] = date_df["Month"].isin([3, 6, 9, 12]).astype(int)
    dim_date = date_df[["DateKey", "Date", "Year", "Quarter", "Year_Quarter", "Month", "Month_Name", "Month_Short", "Is_Quarter_End"]]

    # 4. Central Fact Table: fact_deliveries
    fact = df_clean.merge(dim_model[["Model", "ModelKey"]], on="Model", how="left")
    fact = fact.merge(dim_region[["Region", "RegionKey"]], on="Region", how="left")
    fact = fact.merge(dim_date[["Date", "DateKey"]], on="Date", how="left")

    fact["DeliveryID"] = fact.index + 1
    
    fact_columns = [
        "DeliveryID",
        "DateKey",
        "ModelKey",
        "RegionKey",
        "Date",
        "Year",
        "Month",
        "Region",
        "Model",
        "Business_Segment",
        "Estimated_Deliveries",
        "Production_Units",
        "Avg_Price_USD",
        "Est_Revenue_USD",
        "Inventory_Gap",
        "Delivery_Efficiency",
        "Battery_Capacity_kWh",
        "Range_km",
        "Efficiency_km_per_kWh",
        "CO2_Saved_tons",
        "Charging_Stations",
        "Source_Type",
        "Delivery_Outlier",
        "Delivery_Outlier_Group"
    ]
    fact_deliveries = fact[fact_columns].copy()

    # Save to data/processed
    logger.info("Exporting fact and dimension tables to data/processed/ ...")
    dim_model.to_csv("data/processed/dim_model.csv", index=False)
    dim_region.to_csv("data/processed/dim_region.csv", index=False)
    dim_date.to_csv("data/processed/dim_date.csv", index=False)
    fact_deliveries.to_csv("data/processed/fact_deliveries.csv", index=False)
    
    logger.info(f"dim_model.csv saved: {dim_model.shape}")
    logger.info(f"dim_region.csv saved: {dim_region.shape}")
    logger.info(f"dim_date.csv saved: {dim_date.shape}")
    logger.info(f"fact_deliveries.csv saved: {fact_deliveries.shape}")
    
    logger.info("=== ETL PIPELINE EXECUTION COMPLETED SUCCESSFULLY ===")
    return fact_deliveries, dim_model, dim_region, dim_date


def main():
    logger.info("STARTING TESLA ANALYTICS PRODUCTION ETL PIPELINE")
    df_2015_2025, df_2026, business_rules = extract_data()
    df_combined = combine_datasets(df_2015_2025, df_2026)
    df_standard = standardise_column_formats(df_combined)
    df_clean = perform_data_cleaning_and_quarantine(df_standard)
    df_enriched = merge_business_rules(df_clean, business_rules)
    df_metrics = create_derived_business_metrics(df_enriched)
    df_outliers = perform_outlier_detection(df_metrics)
    fact_deliveries, dim_model, dim_region, dim_date = build_star_schema_and_load(df_outliers)
    print("\nETL Pipeline finished with ZERO errors.")


if __name__ == "__main__":
    main()
