import pyodbc
try:
    drivers = [d for d in pyodbc.drivers()]
    print(f"Drivers: {drivers}")
except Exception as e:
    print(f"Error: {e}")
