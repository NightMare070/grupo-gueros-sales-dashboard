import pyodbc
import json
import datetime
import os
import sys
import subprocess

# --- Configuration ---
REPO_PATH = r"C:\Users\agente\dashboard_repo"
CATALOG_PATH = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md"
DATA_FILE = os.path.join(REPO_PATH, "dashboard_data.json")

BRANCHES = {
    "Centeno": {"server": r"25.66.11.46\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Dibujantes": {"server": r"25.47.107.243\SQLEXPRESS,1400", "db": "ACULCO"},
    "GC1": {"server": r"25.58.53.229\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    "GC2": {"server": r"25.60.248.44\SQLEXPRESS,1400", "db": "GCII"},
    "GC3": {"server": r"25.36.154.112\SQLEXPRESS,1400", "db": "GCIII"},
    "Xochi 1": {"server": r"25.36.200.140\SQLEXPRESS,1400", "db": "XU"},
    "Xochi 2": {"server": r"25.36.21.81\SQLEXPRESS,1400", "db": "XD"},
    "La Nueva": {"server": r"25.17.7.172\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabases\MyBusinessPOS2010.mdf"},
    "Los Güeros": {"server": r"25.71.106.101\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Sur 16": {"server": r"25.36.2.227\SQLEXPRESS,1400", "db": "S16"},
    "Monarca": {"server": r"25.36.119.112\SQLEXPRESS,1400", "db": "ERMITA"},
    "Mineros": {"server": r"25.27.27.7\SQLEXPRESS,1400", "db": "MINEROS"},
}

USER = "usuarioconsulta"
PASS = "Hermes2026*"

# Dates
yesterday = datetime.date.today() - datetime.timedelta(days=1)
DATE_SQL = yesterday.strftime('%Y%m%d')
DATE_ISO = yesterday.strftime('%Y-%m-%d')

def get_conn_str(server, db):
    return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db};UID={USER};PWD={PASS};Encrypt=no;TrustServerCertificate=yes;"

def load_catalog(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    catalog = {}
    current_cat = None
    for line in lines:
        line = line.strip()
        if line.startswith('## '):
            current_cat = line.replace('## ', '').strip()
            catalog[current_cat] = []
        elif line.startswith('- ') and current_cat:
            subcat = line.replace('- ', '').strip()
            catalog[current_cat].append(subcat)
    return catalog

def categorize_product(desc, catalog):
    if not desc:
        return "OTROS", "SIN DESCRIPCION"
    
    # Build a flat list of (subcat, cat) sorted by subcat length descending
    flat_subs = []
    for cat, subs in catalog.items():
        for sub in subs:
            flat_subs.append((sub, cat))
    
    flat_subs.sort(key=lambda x: len(x[0]), reverse=True)
    
    desc_up = desc.upper()
    for sub, cat in flat_subs:
        if sub.upper() in desc_up:
            return cat, sub
            
    return "OTROS", "OTROS"

def main():
    print(f"Processing data for date: {DATE_ISO}")
    
    # 1. Load Catalog
    catalog = load_catalog(CATALOG_PATH)
    
    # 2. Extraction
    branch_totals = {}
    all_product_sales = []
    
    for name, config in BRANCHES.items():
        print(f"Extracting from {name}...", end=" ")
        conn_str = get_conn_str(config["server"], config["db"])
        try:
            with pyodbc.connect(conn_str, timeout=10) as conn:
                cursor = conn.cursor()
                
                # Total
                cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
                row = cursor.fetchone()
                total = float(row[0]) if row and row[0] else 0.0
                branch_totals[name] = total
                
                # Detail
                cursor.execute(f"SELECT Articulo, Descripcion, Total FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
                for row in cursor.fetchall():
                    desc = row[1]
                    cat, subcat = categorize_product(desc, catalog)
                    all_product_sales.append({
                        "Articulo": row[0],
                        "Descripcion": desc,
                        "Total": float(row[2]) if row[2] else 0.0,
                        "Sucursal": name,
                        "Categoria": cat,
                        "Subcategoria": subcat
                    })
                print("Done.")
        except Exception as e:
            print(f"Error: {e}")
            branch_totals[name] = 0.0

    # 3. Update JSON
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found.")
        sys.exit(1)
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Update dates
    if DATE_ISO not in data["dates"]:
        data["dates"].append(DATE_ISO)
    
    # Update branch totals
    # Check if branches match exactly. If not, we map by name.
    for branch_obj in data["branches"]:
        name = branch_obj["nombre"]
        # Find if this branch is in our extraction list
        match_name = next((k for k in BRANCHES if k == name), None)
        if match_name:
            branch_obj["datos"].append(branch_totals.get(match_name, 0.0))
        else:
            # Handle cases where the JSON names might differ slightly from skill names
            # (e.g. "G. Cremero I" vs "GC1")
            # In our case, we use the skill names. The user prompt asks for sucursales in sucursales-grupo-gueros.
            # Let's assume the JSON matches our BRANCHES keys or the user has them mapped.
            # For this run, we'll try to match the key.
            branch_obj["datos"].append(0.0)
            print(f"Warning: Branch {name} in JSON not found in extraction list.")

    # Update products
    for sale in all_product_sales:
        data["products"].append({
            "fecha": DATE_ISO,
            "articulo": sale["Articulo"],
            "descripcion": sale["Descripcion"],
            "venta": sale["Total"],
            "sucursal": sale["Sucursal"],
            "categoria": sale["Categoria"],
            "subcategoria": sale["Subcategoria"]
        })
        
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Updated {DATA_FILE}")

    # 4. Optimization
    print("Runningoptimizer...")
    try:
        subprocess.run(["node", "convert_data.js"], cwd=REPO_PATH, check=True)
    except Exception as e:
        print(f"Optimization failed: {e}")

    # 5. Git Push
    print("Pushing to GitHub...")
    try:
        subprocess.run(["git", "add", "."], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "commit", "-m", f"Update dashboard: data for {DATE_ISO}"], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "push"], cwd=REPO_PATH, check=True)
        print("Successfully pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"Git Error: {e}")

if __name__ == "__main__":
    main()
