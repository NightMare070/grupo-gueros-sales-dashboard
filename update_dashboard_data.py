import pyodbc
import pandas as pd
import json
import os
import sys
from datetime import datetime, timedelta

# Configuration from sucursales-grupo-gueros
branches = [
    {"name": "Centeno", "server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Dibujantes", "server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    {"name": "G. Cremero I", "server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    {"name": "G. Cremero II", "server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    {"name": "G. Cremero III", "server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    {"name": "Xochimilco Uno", "server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    {"name": "Xochimilco Dos", "server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    {"name": "La Nueva", "server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf"},
    {"name": "Los Güeros", "server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Sur 16", "server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    {"name": "La Gran Monarca", "server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
]

USER = "usuarioconsulta"
PASSWORD = "Hermes2026*"
CONN_STR_TEMPLATE = "DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db};UID={user};PWD={pwd};Encrypt=no;TrustServerCertificate=yes;"
FILE_PATH = "C:/Users/agente/dashboard_repo/dashboard_data.json"
MAPPING_PATH = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Business\Suppliers\Product-Supplier-Mapping.md"

def load_supplier_mapping():
    mapping = {}
    if not os.path.exists(MAPPING_PATH):
        print(f"Warning: Mapping file not found at {MAPPING_PATH}")
        return mapping
    with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('|---') or 'Proveedor' in line:
                continue
            if '|' in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 3:
                    supp = parts[0]
                    desc = parts[1]
                    key = parts[2].replace('`', '')
                    mapping.setdefault(desc, set()).add(supp)
                    mapping.setdefault(key, set()).add(supp)
    return mapping

def update_for_date(target_date_str):
    sql_date = target_date_str.replace("-", "")
    iso_date = target_date_str

    if not os.path.exists(FILE_PATH):
        print(f"Error: {FILE_PATH} not found")
        return 0

    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if iso_date not in data.get('dates', []):
        if 'dates' not in data:
            data['dates'] = []
        data['dates'].append(iso_date)

    supplier_map = load_supplier_mapping()
    
    new_records_count = 0
    for b in branches:
        conn_str = CONN_STR_TEMPLATE.format(server=b['server'], db=b['db'], user=USER, pwd=PASSWORD)
        try:
            query = f"""
            SELECT Descripcion, SUM(CAST(Cantidad AS FLOAT)) as Cantidad, SUM(CAST(Total AS FLOAT)) as Total
            FROM rventas
            WHERE Fecha = '{sql_date}' 
            AND Nombre <> 'FALTANTES EMPLEADOS'
            AND Descripcion NOT LIKE '%PROM%' 
            AND Descripcion NOT LIKE '%bloq%'
            GROUP BY Descripcion
            """
            with pyodbc.connect(conn_str, timeout=10) as conn:
                df = pd.read_sql(query, conn)
                for _, row in df.iterrows():
                    desc = row['Descripcion']
                    suppliers = supplier_map.get(desc, [])
                    if suppliers:
                        s_list = sorted(list(suppliers))
                        prov = s_list[0] if len(s_list) == 1 else s_list
                    else:
                        prov = "Desconocido"

                    data['products'].append({
                        "Sucursal": b['name'],
                        "Fecha": iso_date,
                        "Descripcion": desc,
                        "Cantidad": float(row['Cantidad']),
                        "Total": float(row['Total']),
                        "proveedor": prov
                    })
                    new_records_count += 1
        except Exception as e:
            print(f"Error extracting from {b['name']} for {iso_date}: {e}")

    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Successfully added {new_records_count} records for {iso_date} with supplier info")
    return new_records_count

if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_to_update = sys.argv[1]
        update_for_date(date_to_update)
    else:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        update_for_date(yesterday)
