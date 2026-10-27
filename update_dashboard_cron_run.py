
import pyodbc
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# 1. Configuration
TARGET_DATE_ISO = '2026-10-26'
TARGET_DATE_SQL = '20261026'
REPO_PATH = r'C:\Users\agente\dashboard_repo'
DATA_FILE = os.path.join(REPO_PATH, 'dashboard_data.json')

branches_config = {
    "Centeno": {"server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    "Dibujantes": {"server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    "GC1": {"server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    "GC2": {"server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    "GC3": {"server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    "Xochimilco 1": {"server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    "Xochimilco 2": {"server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    "La Nueva": {"server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf"},
    "Los Güeros": {"server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    "Sur 16": {"server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    "Monarca": {"server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
    "Mineros": {"server": "25.27.27.7\\SQLEXPRESS,1400", "db": "MINEROS"},
}

CAT_MAP = {
    "ACEITE": "ABARROTES", "ADEREZOS": "ABARROTES", "AGUA": "ABARROTES", "ARROZ": "ABARROTES",
    "ATE": "ABARROTES", "AZUCAR": "ABARROTES", "BEBIBLE": "ABARROTES", "BEBIDA": "ABARROTES",
    "CAFÉ": "ABARROTES", "CAJETA": "ABARROTES", "CATSUP": "ABARROTES", "CHOCOLATE": "ABARROTES",
    "CROUTON": "ABARROTES", "ENLATADO": "ABARROTES", "FRITURA": "ABARROTES", "GELATINA": "ABARROTES",
    "HARINA": "ABARROTES", "HUEVO": "ABARROTES", "LECHERA": "ABARROTES", "MAIZ": "ABARROTES",
    "MAYONESA": "ABARROTES", "MERMELADA": "ABARROTES", "MOSTAZA": "ABARROTES", "PALOMITAS": "ABARROTES",
    "PAN": "ABARROTES", "PAN MOLIDO": "ABARROTES", "POSTRE": "ABARROTES", "SAL": "ABARROTES",
    "SAZONADOR": "ABARROTES", "SEMILLA": "ABARROTES", "SOPA": "ABARROTES", "SUSTITUTO DE CREMA": "ABARROTES",
    "TORTILLA": "ABARROTES", "TOSTADA": "ABARROTES", "TOTOPO": "ABARROTES", "VINAGRE": "ABARROTES",
    "CHISTORRA": "CARNES FRIAS Y EMBUTIDOS", "CHORIZO": "CARNES FRIAS Y EMBUTIDOS", "CHULETA": "CARNES FRIAS Y EMBUTIDOS",
    "JAMON": "CARNES FRIAS Y EMBUTIDOS", "LONGANIZA": "CARNES FRIAS Y EMBUTIDOS", "MORTADELA": "CARNES FRIAS Y EMBUTIDOS",
    "PECHUGA": "CARNES FRIAS Y EMBUTIDOS", "PEPERONI": "CARNES FRIAS Y EMBUTIDOS", "PIERNA ESPAÑOLA": "CARNES FRIAS Y EMBUTIDOS",
    "PIMIENTO": "CARNES FRIAS Y EMBUTIDOS", "QUESO DE PUERCO": "CARNES FRIAS Y EMBUTIDOS", "REBANADO": "CARNES FRIAS Y EMBUTIDOS",
    "Salami": "CARNES FRIAS Y EMBUTIDOS", "SALCHICHA": "CARNES FRIAS Y EMBUTIDOS", "TOCINETA": "CARNES FRIAS Y EMBUTIDOS",
    "TOCINO": "CARNES FRIAS Y EMBUTIDOS", "ALITA": "CONGELADOS", "AROS DE CEBOLLA": "CONGELADOS",
    "BONELES": "CONGELADOS", "DEDOS": "CONGELADOS", "HAMBURGUESA": "CONGELADOS", "NUGGET": "CONGELADOS",
    "PALITOS de QUESO": "CONGELADOS", "PALOMITAS de POLLO": "CONGELADOS", "PAPA CONGELADA": "CONGELADOS",
    "TENDERS": "CONGELADOS", "TILAPIA": "CONGELADOS", "ALUMINIO": "DESECHABLE", "BOLSA": "DESECHABLE",
    "CHAROLA": "DESECHABLE", "CONTENEDOR": "DESECHABLE", "DESECHABLE": "DESECHABLE", "PLATO": "DESECHABLE",
    "SERVILLETA": "DESECHABLE", "TAPA": "DESECHABLE", "TENEDOR": "DESECHABLE", "VASO": "DESECHABLE",
    "VELA": "DESECHABLE", "BEBIBLE": "LACTEOS Y DERIVADOS", "BEBIDA": "LACTEOS Y DERIVADOS",
    "CAJETA": "LACTEOS Y DERIVADOS", "CHANTILLY": "LACTEOS Y DERIVADOS", "CREMA": "LACTEOS Y DERIVADOS",
    "CREMA BATIDA": "LACTEOS Y DERIVADOS", "CREMA VEGETAL": "LACTEOS Y DERIVADOS", "DULCIMA": "LACTEOS Y DERIVADOS",
    "LECHE": "LACTEOS Y DERIVADOS", "LECHERA": "LACTEOS Y DERIVADOS", "MANTEQUILLA": "LACTEOS Y DERIVADOS",
    "MARGARINA": "LACTEOS Y DERIVADOS", "MERMELADA": "LACTEOS Y DERIVADOS", "MIEL": "LACTEOS Y DERIVADOS",
    "PANELA": "LACTEOS Y DERIVADOS", "PARMESANO": "LACTEOS Y DERIVADOS", "POSTRE": "LACTEOS Y DERIVADOS",
    "PROMO": "LACTEOS Y DERIVADOS", "QUESO AMARILLO": "LACTEOS Y DERIVADOS", "QUESO CREMA": "LACTEOS Y DERIVADOS",
    "YOGURT": "LACTEOS Y DERIVADOS", "CLORO": "PRODUCTO DE LIMPIEZA", "JABON": "PRODUCTO DE LIMPIEZA",
    "JABON LIQUIDO": "PRODUCTO DE LIMPIEZA", "PAPEL": "PRODUCTO DE LIMPIEZA", "AMARILLO LIQUIDO": "QUESOS Y DERIVADOS",
    "AMARILLO REBANADO": "QUESOS Y DERIVADOS", "BARRA": "QUESOS Y DERIVADOS", "CANASTO": "QUESOS Y DERIVADOS",
    "COTIJA": "QUESOS Y DERIVADOS", "DOBLE CREMA": "QUESOS Y DERIVADOS", "GOUDA": "QUESOS Y DERIVADOS",
    "MANCHEGO": "QUESOS Y DERIVADOS", "MENONA": "QUESOS Y DERIVADOS", "MOZARELLA": "QUESOS Y DERIVADOS",
    "NATILLA": "QUESOS Y DERIVADOS", "PANELA": "QUESOS Y DERIVADOS", "PARMESANO": "QUESOS Y DERIVADOS",
    "QUESO AMARILLO": "QUESOS Y DERIVADOS", "QUESO CHIHUAHUA": "QUESOS Y DERIVADOS", "QUESO COTTAGE": "QUESOS Y DERIVADOS",
    "QUESO CREMA": "QUESOS Y DERIVADOS", "QUESO de CABRA": "QUESOS Y DERIVADOS", "QUESO LIQUIDO": "QUESOS Y DERIVADOS",
    "QUESO OAXACA": "QUESOS Y DERIVADOS", "QUESO PARMESANO": "QUESOS Y DERIVADOS", "QUESO RALLADO": "QUESOS Y DERIVADOS",
    "REBANADO": "QUESOS Y DERIVADOS", "SINCHO": "QUESOS Y DERIVADOS",
}

def assign_category(description):
    desc_u = description.upper()
    sorted_subcats = sorted(CAT_MAP.keys(), key=len, reverse=True)
    for subcat in sorted_subcats:
        if subcat in desc_u:
            return CAT_MAP[subcat], subcat
    return "OTROS", "OTROS"

branch_totals = {}
detailed_products = []

for branch_name, config in branches_config.items():
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={config['server']};DATABASE={config['db']};"
        f"UID=usuarioconsulta;PWD=Hermes2026*;"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        total_q = f"SELECT SUM(CAST(Total AS FLOAT)) as Total FROM rventas WHERE Fecha = '{TARGET_DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'"
        res = conn.execute(total_q).fetchone()
        branch_totals[branch_name] = float(res[0]) if res[0] is not None else 0.0
        prod_q = f"SELECT Articulo, Descripcion, SUM(CAST(Total AS FLOAT)) as Total FROM rventas WHERE Fecha = '{TARGET_DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Articulo, Descripcion"
        prods = conn.execute(prod_q).fetchall()
        for p in prods:
            cat, subcat = assign_category(p.Descripcion)
            detailed_products.append({
                "Sucursal": branch_name,
                "Fecha": TARGET_DATE_ISO,
                "Descripcion": p.Descripcion,
                "Total": float(p.Total),
                "categoria": cat,
                "subcategoria": subcat
            })
        conn.close()
    except Exception as e:
        print(f"Error in {branch_name}: {e}")

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

if TARGET_DATE_ISO not in data['dates']:
    data['dates'].append(TARGET_DATE_ISO)

for b_data in data['branches']:
    name = b_data['name']
    lookup_name = name
    if name == "G. Cremero I": lookup_name = "GC1"
    elif name == "G. Cremero II": lookup_name = "GC2"
    elif name == "G. Cremero III": lookup_name = "GC3"
    elif name == "La Gran Monarca": lookup_name = "Monarca"
    elif name == "Xochimilco Uno": lookup_name = "Xochimilco 1"
    elif name == "Xochimilco Dos": lookup_name = "Xochimilco 2"
    val = branch_totals.get(lookup_name, 0.0)
    b_data['values'].append(val)

data['products'].extend(detailed_products)

with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Successfully updated dashboard_data.json")
