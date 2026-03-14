---
description: Use when the user wants to export, download, save, or write data to a file. Supports CSV and JSON export formats. Always query the database first, then export the results.
---

# Data Exporter Skill

You export query results to files so the user can use data outside the agent.

## Instructions
1. First use the **SQL Analyst skill** to retrieve the data via `execute_sql_query`
2. Then call `export_to_csv` or `export_to_json` with appropriate filename and the SQL query
3. Tell the user the **exact file path** where the export was saved
4. Suggest meaningful filenames based on the content (e.g., `top_products_march_2025.csv`)

## Supported Formats
- **CSV** — best for spreadsheets (Excel, Google Sheets)
- **JSON** — best for APIs or further processing

## Example Triggers
- "Export the top products to a CSV"
- "Save revenue by category as JSON"
- "Download last month's sales data"
