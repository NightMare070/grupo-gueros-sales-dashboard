import pyodbc
import json
import pandas as pd
from datetime import datetime, timedelta

# Configuration from sucursales-grupo-gueros
branches = [
    {"name": "Centeno", "server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Dibujantes", "server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    {"name": "GC1", "server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    {"name": "GC2", "server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    {"name": "GC3", "server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    {"name": "Xochimilco Uno", "server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    {"name": "Xochimilco Dos", "server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    {"name": "La Nueva", "server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf"},
    {"name": "Los Güeros", "server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Sur 16", "server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    {"name": "Monarca", "server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
    {"name": "Mineros", "server": "25.27.27.7\\SQLEXPRESS,1400", "db": "MINEROS"},
]

USER = 'usuarioconsulta'
PWD = 'Hermes2026*'
# For ODBC 18 compatibility
CONN_STR_TEMPLATE = "Driver={{ODBC Driver 18 for SQL Server}};Server={server};Database={db};UID={user};PWD={pwd};Encrypt=no;TrustServerCertificate=yes;"

# Date logic: Yesterday
yesterday_sql = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

results = {
    "date": yesterday_sql,
    "branch_totals": {},
    "product_details": []
}

for b in branches:
    conn_str = CONN_STR_TEMPLATE.format(server=b['server'], db=b['db'], user=USER, pwd=PWD)
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        
        # Total sales for the branch
        query_total = f"SELECT SUM(CAST(Total AS FLOAT)) as Total FROM rventas WHERE Fecha = '{yesterday_sql}' AND Nombre <> 'FALTANTES EMPLEADOS'"
        total_df = pd.read_sql(query_total, conn)
        total_val = float(total_df['Total'].iloc[0]) if total_df['Total'].iloc[0] is not None else 0.0
        results["branch_totals"][b['name']] = total_val
        
        # Detailed sales for products
        query_detail = f"SELECT Articulo, Descripcion, SUM(CAST(Total AS FLOAT)) as Total FROM rventas WHERE Fecha = '{yesterday_sql}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Articulo, Descripcion"
        detail_df = pd.read_sql(query_detail, conn)
        
        for _, row in detail_df.iterrows():
            results["product_details"].append({
                "branch": b['name'],
                "articulo": row['Articulo'],
                "descripcion": row['Descripcion'],
                "total": float(row['Total'])
            })
        
        conn.close()
        print(f"Successfully extracted {b['name']}")
    except Exception as e:
        print(f"Error extracting {b['name']}: {e}")

with open('yesterday_sales_raw.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print("Extraction complete. Saved to yesterday_sales_raw.json")
