"""
Script 03: Analytical Runner & Statistical Synthesis
Phase 4 & 5 Core Analytics Engine
Project: Tesla Global Deliveries & Business Performance Analytics Initiative
Author: Yashraj Singh Solanki
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy import stats


def run_full_analysis():
    print("=" * 80)
    print("TESLA GLOBAL DELIVERIES & OPERATIONS ANALYTICS: STATISTICAL REPORT")
    print("=" * 80)

    fact = pd.read_csv("data/processed/fact_deliveries.csv")
    fact["Date"] = pd.to_datetime(fact["Date"])

    # 1. Executive KPIs
    tot_del = fact["Estimated_Deliveries"].sum()
    tot_prod = fact["Production_Units"].sum()
    tot_rev = fact["Est_Revenue_USD"].sum()
    tot_gap = fact["Inventory_Gap"].sum()
    avg_eff = (tot_del / tot_prod) * 100
    avg_price = fact["Avg_Price_USD"].mean()
    tot_co2 = fact["CO2_Saved_tons"].sum()

    print(f"\n1. EXECUTIVE PORTFOLIO SUMMARY (2015 - 2026)")
    print(f"   * Total Delivered Volume:    {tot_del:15,d} units")
    print(f"   * Total Manufactured Output: {tot_prod:15,d} units")
    print(f"   * Net Inventory Buffer Gap:  {tot_gap:15,d} units")
    print(f"   * Overall Delivery Efficiency: {avg_eff:13.2f}%")
    print(f"   * Portfolio Average Price:   ${avg_price:14.2f}")
    print(f"   * Cumulative Est. Revenue:   ${tot_rev:14,.2f}")
    print(f"   * Cumulative CO2 Offset:     {tot_co2:15,.1f} metric tons")

    # 2. Model Performance
    print("\n2. MODEL-BY-MODEL PERFORMANCE SUMMARY")
    m_agg = fact.groupby("Model").agg(
        Deliveries=("Estimated_Deliveries", "sum"),
        Production=("Production_Units", "sum"),
        Revenue=("Est_Revenue_USD", "sum"),
        Avg_Price=("Avg_Price_USD", "mean"),
        Avg_Range=("Range_km", "mean"),
        Delivery_Share=("Estimated_Deliveries", lambda x: (x.sum() / tot_del) * 100)
    ).sort_values("Deliveries", ascending=False)
    m_agg["Efficiency"] = (m_agg["Deliveries"] / m_agg["Production"]) * 100
    print(m_agg.to_string())

    # 3. Regional Performance
    print("\n3. REGIONAL MARKET PERFORMANCE SUMMARY")
    r_agg = fact.groupby("Region").agg(
        Deliveries=("Estimated_Deliveries", "sum"),
        Production=("Production_Units", "sum"),
        Revenue=("Est_Revenue_USD", "sum"),
        Delivery_Share=("Estimated_Deliveries", lambda x: (x.sum() / tot_del) * 100)
    ).sort_values("Deliveries", ascending=False)
    r_agg["Efficiency"] = (r_agg["Deliveries"] / r_agg["Production"]) * 100
    print(r_agg.to_string())

    # 4. Statistical Hypothesis Testing
    print("\n4. STATISTICAL HYPOTHESIS TESTING SUMMARY")
    print("-" * 80)
    
    # Test 1: Quarter-End vs Non-Quarter-End Deliveries
    q_end = fact[fact["Month"].isin([3, 6, 9, 12])]["Estimated_Deliveries"]
    non_q_end = fact[~fact["Month"].isin([3, 6, 9, 12])]["Estimated_Deliveries"]
    t_stat_q, p_val_q = stats.ttest_ind(q_end, non_q_end, equal_var=False)
    print(f"TEST 1: Quarter-End Push Hypothesis (Months 3, 6, 9, 12 vs Other Months)")
    print(f"   * H0: Quarter-end delivery mean = Non-quarter-end delivery mean")
    print(f"   * Q-End Mean: {q_end.mean():.1f} | Non-Q-End Mean: {non_q_end.mean():.1f}")
    print(f"   * Welch's t-statistic: {t_stat_q:.4f}, p-value: {p_val_q:.4e}")
    print(f"   * Result: {'REJECT H0 (Significant difference)' if p_val_q < 0.05 else 'FAIL TO REJECT H0 (No significant difference)'}")

    # Test 2: Regional Pricing ANOVA
    reg_groups = [group["Avg_Price_USD"].values for _, group in fact.groupby("Region")]
    f_stat_p, p_val_p = stats.f_oneway(*reg_groups)
    print(f"\nTEST 2: Regional Pricing Parity (One-Way ANOVA across 4 Regions)")
    print(f"   * H0: Mean vehicle prices are equal across all regions")
    print(f"   * F-statistic: {f_stat_p:.4f}, p-value: {p_val_p:.4e}")
    print(f"   * Result: {'REJECT H0 (Regional price differences exist)' if p_val_p < 0.05 else 'FAIL TO REJECT H0 (Pricing is statistically uniform across regions)'}")

    # Test 3: Charging Stations vs Deliveries Correlation
    corr_c, p_val_c = stats.pearsonr(fact["Charging_Stations"], fact["Estimated_Deliveries"])
    print(f"\nTEST 3: Charging Station Availability vs Vehicle Deliveries")
    print(f"   * H0: Pearson correlation rho = 0")
    print(f"   * Pearson r: {corr_c:.4f}, p-value: {p_val_c:.4e}")
    print(f"   * Result: {'REJECT H0 (Statistically significant relationship)' if p_val_c < 0.05 else 'FAIL TO REJECT H0 (No significant linear relationship)'}")

    # Test 4: Longitudinal Delivery Efficiency (2015-2020 vs 2021-2026)
    eff_early = fact[fact["Year"] <= 2020]["Delivery_Efficiency"]
    eff_late = fact[fact["Year"] >= 2021]["Delivery_Efficiency"]
    t_stat_e, p_val_e = stats.ttest_ind(eff_late, eff_early, equal_var=False)
    print(f"\nTEST 4: Delivery Efficiency Shift (2015-2020 Early Era vs 2021-2026 Mature Era)")
    print(f"   * H0: Delivery efficiency mean in early era = mature era")
    print(f"   * Early Era Mean Efficiency: {eff_early.mean():.2f}% | Mature Era: {eff_late.mean():.2f}%")
    print(f"   * Welch's t-statistic: {t_stat_e:.4f}, p-value: {p_val_e:.4e}")
    print(f"   * Result: {'REJECT H0 (Significant operational shift)' if p_val_e < 0.05 else 'FAIL TO REJECT H0 (No significant operational shift)'}")
    print("=" * 80)

    # Save to file
    os.makedirs("data/working", exist_ok=True)
    with open("data/working/analysis_summary.txt", "w", encoding="utf-8") as f:
        f.write("TESLA GLOBAL DELIVERIES & OPERATIONS ANALYTICS: SUMMARY REPORT\n")
        f.write(f"Generated: {pd.Timestamp.now()}\n")
        f.write(f"Total Deliveries: {tot_del:,}\n")
        f.write(f"Total Production: {tot_prod:,}\n")
        f.write(f"Total Revenue: ${tot_rev:,.2f}\n")
        f.write(f"Quarter-End t-test p-value: {p_val_q:.4e}\n")
        f.write(f"Regional Pricing ANOVA p-value: {p_val_p:.4e}\n")
        f.write(f"Charging Station Pearson r: {corr_c:.4f} (p={p_val_c:.4e})\n")
        f.write(f"Efficiency Shift p-value: {p_val_e:.4e}\n")


if __name__ == "__main__":
    run_full_analysis()
