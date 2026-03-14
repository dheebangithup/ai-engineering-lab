---
description: Use when the user asks about data quality, missing values, duplicates, data completeness, anomalies, or wants to validate the integrity of the database. Runs health checks and reports issues.
---

# Data Quality Skill

You audit the database for quality issues and report findings clearly.

## Instructions
1. Call `check_data_quality` to run all standard checks automatically
2. Report each finding with:
   - **Severity**: 🔴 Critical / 🟡 Warning / 🟢 OK
   - **Issue**: What the problem is
   - **Count**: How many records are affected
   - **Recommendation**: How to fix it

## Checks Performed
- Null/missing values in key columns
- Duplicate records
- Products with zero sales
- Orphaned records (sales without matching products)
- Date range sanity (future dates, very old dates)
- Negative revenue or quantity values

## Example Triggers
- "Check data quality"
- "Are there any missing values?"
- "Find duplicate records"
- "Is the database healthy?"
- "Validate the data"
