import pyodbc
import json
from datetime import datetime, timedelta

# Configuration from skills
CREDENTIALS = {
    "uid": "usuarioconsulta",
    "pwd": "Hermes2026*",
}

BRANCHES = [
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

# Dynamic Date Calculation
yesterday = datetime.now() - timedelta(days=1)
TARGET_DATE_SQL = yesterday.strftime('%Y%m%d')
TARGET_DATE_ISO = yesterday.strftime('%Y-%m-%d')

def get_sales(branch):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={branch['server']};"
        f"DATABASE={branch['db']};"
        f"UID={CREDENTIALS['uid']};"
        f"PWD={CREDENTIALS['pwd']};"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    
    query = f"""
    SELECT 
        Descripcion, 
        SUM(CAST(Cantidad AS FLOAT)) as Cantidad, 
        SUM(CAST(Total AS FLOAT)) as Total 
    FROM rventas 
    WHERE Fecha = '{TARGET_DATE_SQL}' 
      AND Nombre <> 'FALTANTES EMPLEADOS'
      AND Descripcion NOT LIKE '%PROM%' 
      AND Descripcion NOT LIKE '%bloq%'
    GROUP BY Descripcion
    """
    
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "Sucursal": branch['name'],
                "Fecha": TARGET_DATE_ISO,
                "Descripcion": row[0],
                "Cantidad": float(row[1]) if row[1] else 0.0,
                "Total": float(row[2]) if row[2] else 0.0
            })
        return results
    except Exception as e:
        print(f"Error querying {branch['name']}: {e}")
        return []

def main():
    all_products = []
    for branch in BRANCHES:
        print(f"Processing {branch['name']}...")
        data = get_sales(branch)
        all_products.extend(data)
    
    with open("extracted_sales.json", "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f"Successfully extracted {len(all_products)} records.")

if __name__ == "__main__":
    main()
