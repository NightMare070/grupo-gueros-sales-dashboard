import json
import pyodbc
import pandas as pd
from datetime import datetime, timedelta
import os

# Configuration
today = datetime(2026, 10, 8)
yesterday = today - timedelta(days=1)
date_str_sql = yesterday.strftime('%Y%m%d')
date_str_json = yesterday.strftime('%Y-%m-%d')

branches_config = [
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
    {"name": "Mineros", "server": "25.27.27\\SQLEXPRESS,1400", "db": "MINEROS"},
]

uid = "usuarioconsulta"
pwd = "Hermes2026*"

# Load Categories from Brain
cat_path = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'
category_map = {}
if os.path.exists(cat_path):
    with open(cat_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        current_cat = None
        for line in lines:
            line = line.strip()
            if line.startswith('## ') and not line.startswith('## CATEGORIA'):
                current_cat = line.replace('## ', '').strip()
            elif line.startswith('- ') and current_cat:
                subcat = line.replace('- ', '').strip()
                category_map[subcat] = current_cat

def get_category_info(desc):
    desc_upper = desc.upper()
    sorted_subcats = sorted(category_map.keys(), key=len, reverse=True)
    for sub in sorted_subcats:
        if sub.upper() in desc_upper:
            return category_map[sub], sub
    return "OTROS", "OTROS"

results = {
    "date": date_str_json,
    "totals": {},
    "products": []
}

for b in branches_config:
    conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={b['server']};DATABASE={b['db']};UID={uid};PWD={pwd};Encrypt=no;TrustServerCertificate=yes;"
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        
        # Total
        query_total = f"SELECT SUM(CAST(Total AS FLOAT)) as total FROM rventas WHERE Fecha = '{date_str_sql}' AND Nombre <> 'FALTANTES EMPLEADOS'"
        df_total = pd.read_sql(query_total, conn)
        total_val = float(df_total['total'].iloc[0]) if df_total['total'].iloc[0] is not None else 0.0
        results["totals"][b['name']] = total_val
        
        # Products
        query_prods = f"SELECT Descripcion, Cantidad, Total FROM rventas WHERE Fecha = '{date_str_sql}' AND Nombre <> 'FALTANTES EMPLEADOS'"
        df_prods = pd.read_sql(query_prods, conn)
        
        for _, row in df_prods.iterrows():
            desc = str(row['Descripcion'])
            cat, subcat = get_category_info(desc)
            results["products"].append({
                "Sucursal": b['name'],
                "Fecha": date_str_json,
                "Descripcion": desc,
                "Cantidad": float(row['Cantidad']),
                "Total": float(row['Total']),
                "categoria": cat,
                "subcategoria": subcat
            })
        conn.close()
    except Exception as e:
        print(f"Error in {b['name']}: {e}")
        results["totals"][b['name']] = 0.0

with open('extraction_temp.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=4, ensure_ascii=False)
