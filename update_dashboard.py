import pyodbc
import pandas as pd
import json
import os
import re

# --- CONFIGURATION ---
TARGET_DATE_STR = '2026-09-19'
TARGET_DATE_SQL = '20260919'
JSON_PATH = r'C:\Users\agente\dashboard_repo\dashboard_data.json'
CATALOG_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'

# Branch Database Directory
BRANCHES = {
    "Centeno": {"server": "25.66.11.46\\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Dibujantes": {"server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    "GC1": {"server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    "GC2": {"server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    "GC3": {"server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    "Xochimilco 1": {"server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    "Xochimilco 2": {"server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    "La Nueva": {"server": "25.17.7.172\\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabases\MyBusinessPOS2010.mdf"},
    "Los Güeros": {"server": "25.71.106.101\\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Sur 16": {"server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    "Monarca": {"server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
    "Mineros": {"server": "25.27.27.7\\SQLEXPRESS,1400", "db": "MINEROS"},
}

USER = 'usuarioconsulta'
PWD = 'Hermes2026*'

def load_categories():
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    categories = {}
    # Simple regex to find sections like ## Category Name
    sections = re.split(r'\n## ', content)
    for section in sections:
        lines = section.split('\n')
        if not lines: continue
        cat_name = lines[0].strip()
        # Find list items under this category
        for line in lines[1:]:
            if line.strip().startswith('- '):
                prod = line.strip()[2:].strip()
                categories[prod.lower()] = cat_name
    return categories

def get_category_info(prod_name, cat_map):
    prod_lower = prod_name.lower()
    # Match longest keyword first to avoid greedy matching (e.g., 'PAN' vs 'PAN MOLIDO')
    sorted_keywords = sorted(cat_map.keys(), key=len, reverse=True)
    for kw in sorted_keywords:
        if kw in prod_lower:
            return cat_map[kw], "General" # Subcategory simplified for this script
    return "Otros", "Otros"

def extract_sales(branch_name, config):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={config['server']};"
        f"DATABASE={config['db']};"
        f"UID={USER};PWD={PWD};"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    
    query = f"""
    SELECT Descripcion, CAST(Total AS FLOAT) as Total 
    FROM rventas 
    WHERE Fecha = '{TARGET_DATE_SQL}' 
    AND Nombre <> 'FALTANTES EMPLEADOS'
    """
    
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error extracting from {branch_name}: {e}")
        return pd.DataFrame()

def run():
    cat_map = load_categories()
    
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if TARGET_DATE_STR not in data['dates']:
        data['dates'].append(TARGET_DATE_STR)

    daily_products = []
    
    for b_name, b_cfg in BRANCHES.items():
        df = extract_sales(b_name, b_cfg)
        
        # Total for the day for this branch
        total_sales = df['Total'].sum() if not df.empty else 0.0
        
        # Update branches array
        found_branch = False
        for b_entry in data['branches']:
            if b_entry['name'] == b_name:
                b_entry['sales'].append(total_sales)
                found_branch = True
                break
        if not found_branch:
            data['branches'].append({"name": b_name, "sales": [total_sales]})
            
        # Detailed products
        if not df.empty:
            for _, row in df.iterrows():
                desc = str(row['Descripcion'])
                cat, subcat = get_category_info(desc, cat_map)
                daily_products.append({
                    "fecha": TARGET_DATE_STR,
                    "producto": desc,
                    "sucursal": b_name,
                    "monto": row['Total'],
                    "categoria": cat,
                    "subcategoria": subcat
                })

    data['products'].extend(daily_products)
    
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print("Success: dashboard_data.json updated.")

if __name__ == "__main__":
    run()
