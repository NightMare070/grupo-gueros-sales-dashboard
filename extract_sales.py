import pyodbc
import json
import datetime
import os

# Configuration from Skill
BRANCHES = {
    "Centeno": {"server": "25.66.11.46\SQLEXPRESS,1400", "db": "C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Dibujantes": {"server": "25.47.107.243\SQLEXPRESS,1400", "db": "ACULCO"},
    "G. Cremero I": {"server": "25.58.53.229\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    "G. Cremero II": {"server": "25.60.248.44\SQLEXPRESS,1400", "db": "GCII"},
    "G. Cremero III": {"server": "25.36.154.112\SQLEXPRESS,1400", "db": "GCIII"},
    "Xochimilco Uno": {"server": "25.36.200.140\SQLEXPRESS,1400", "db": "XU"},
    "Xochimilco Dos": {"server": "25.36.21.81\SQLEXPRESS,1400", "db": "XD"},
    "La Nueva": {"server": "25.17.7.172\SQLEXPRESS,1400", "db": "C:\MyBusinessDatabases\MyBusinessPOS2010.mdf"},
    "Los Güeros": {"server": "25.71.106.101\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"}, # Adjusted for escape
    "Sur 16": {"server": "25.36.2.227\SQLEXPRESS,1400", "db": "S16"},
    "La Gran Monarca": {"server": "25.36.119.112\SQLEXPRESS,1400", "db": "ERMITA"},
    "Mineros": {"server": "25.27.27.7\SQLEXPRESS,1400", "db": "MINEROS"},
}

# Fixed DB paths for the problematic ones
BRANCHES["Los Güeros"]["db"] = "C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"

USER = "usuarioconsulta"
PASS = "Hermes2026*"
DATE_STR = "20260929"

def get_conn_str(server, db):
    return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db};UID={USER};PWD={PASS};Encrypt=no;TrustServerCertificate=yes;"

results = {
    "totals": {},
    "details": []
}

for branch, config in BRANCHES.items():
    try:
        conn_str = get_conn_str(config["server"], config["db"])
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            
            # Total Sales
            cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{DATE_STR}' AND Nombre <> 'FALTANTES EMPLEADOS'")
            row = cursor.fetchone()
            total = float(row[0]) if row and row[0] else 0.0
            results["totals"][branch] = total
            
            # Product Details
            cursor.execute(f"SELECT Descripcion, Cantidad, Total FROM rventas WHERE Fecha = '{DATE_STR}' AND Nombre <> 'FALTANTES EMPLEADOS'")
            for row in cursor.fetchall():
                results["details"].append({
                    "Sucursal": branch,
                    "Fecha": "2026-09-29",
                    "Descripcion": row[0],
                    "Cantidad": float(row[1]) if row[1] else 0.0,
                    "Total": float(row[2]) if row[2] else 0.0
                })
    except Exception as e:
        print(f"Error connecting to {branch}: {e}")
        results["totals"][branch] = 0.0

print(json.dumps(results))
EOF"
