import pyodbc
import sys

def test_conn(server, db):
    conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db};UID=usuarioconsulta;PWD=Hermes2026*;Encrypt=no;TrustServerCertificate=yes;"
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        print(f"SUCCESS: {server}")
        conn.close()
    except Exception as e:
        print(f"FAILED: {server} - {str(e)}")

# Test a couple of servers
test_conn("25.66.11.46\\SQLEXPRESS,1400", "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf")
test_conn("25.47.107.243\\SQLEXPRESS,1400", "ACULCO")
