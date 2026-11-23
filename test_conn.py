import pyodbc
import sys

USER = 'usuarioconsulta'
PWD = 'Hermes2026*'
# Centeno
SERVER = '25.66.11.46\\SQLEXPRESS,1400'
DB = 'C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf'

conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DB};UID={USER};PWD={PWD};Encrypt=no;TrustServerCertificate=yes;"

print(f"Testing connection to Centeno...")
print(f"Conn Str: {conn_str}")

try:
    conn = pyodbc.connect(conn_str, timeout=10)
    print("Connection successful!")
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 * FROM rventas")
    row = cursor.fetchone()
    print(f"Query successful! Row: {row}")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)
