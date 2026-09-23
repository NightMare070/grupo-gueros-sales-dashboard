import pyodbc
import json
import pandas as pd
from datetime import datetime, timedelta

# Configuration
USER = 'usuarioconsulta'
PASS = 'Hermes2026*'
DATE_STR = '20260922'  # Yesterday relative to session start Sep 23

BRANCHES = [
    {"name": "Centeno", "server": r"25.66.11.46\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    {"name": "Dibujantes", "server": r"25.47.107.243\SQLEXPRESS,1400", "db": "ACULCO"},
    {"name": "G. Cremero I", "server": r"25.58.53.229\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    {"name": "G. Cremero II", "server": r"25.60.248.44\SQLEXPRESS,1400", "db": "GCII"},
    {"name": "G. Cremero III", "server": r"25.36.154.112\SQLEXPRESS,1400", "db": "GCIII"},
    {"name": "Xochimilco Uno", "server": r"25.36.200.140\SQLEXPRESS,1400", "db": "XU"},
    {"name": "Xochimilco Dos", "server": r"25.36.21.81\SQLEXPRESS,1400", "db": "XD"},
    {"name": "La Nueva", "server": r"25.17.7.172\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabases\MyBusinessPOS2010.mdf"},
    {"name": "Los Güeros", "server": r"25.71.106.101\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    {"name": "Sur 16", "server": r"25.36.2.227\SQLEXPRESS,1400", "db": "S16"},
    {"name": "La Gran Monarca", "server": r"25.36.119.112\SQLEXPRESS,1400", "db": "ERMITA"},
    {"name": "Mineros", "server": r"25.27.27.7\SQLEXPRESS,1400", "db": "MINEROS"},
]

def get_conn_str(server, db):
    return (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={db};"
        f"UID={USER};"
        f"PWD={PASS};"
        f"Encrypt=no;"
        f"TrustServerCertificate=yes;"
    )

results = {
    "totals": {},
    "details": []
}

for b in BRANCHES:
    print(f"Processing {b['name']}...")
    try:
        conn_str = get_conn_str(b['server'], b['db'])
        with pyodbc.connect(conn_str, timeout=10) as conn:
            # Total Sales
            query_total = f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{DATE_STR}' AND Nombre <> 'FALTANTES EMPLEADOS'"
            total = conn.execute(query_total).fetchone()[0]
            results["totals"][b['name']] = float(total) if total else 0.0
            
            # Detailed Sales
            query_details = f"SELECT Descripcion, Cantidad, Total, Articulo FROM rventas WHERE Fecha = '{DATE_STR}' AND Nombre <> 'FALTANTES EMPLEADOS'"
            df = pd.read_sql(query_details, conn)
            for _, row in df.iterrows():
                results["details"].append({
                    "Sucursal": b['name'],
                    "Fecha": "2026-09-22",
                    "Descripcion": row['Descripcion'],
                    "Cantidad": float(row['Cantidad']),
                    "Total": float(row['Total']),
                    "Articulo": row['Articulo']
                })
    except Exception as e:
        print(f"Error in {b['name']}: {e}")
        results["totals"][b['name']] = 0.0

with open('yesterday_extraction.json', 'w') as f:
    json.dump(results, f)

print("Extraction complete.")
