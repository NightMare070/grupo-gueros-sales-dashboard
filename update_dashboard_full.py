import subprocess
import sys
import os
from datetime import datetime, timedelta

# Paths
REPO_DIR = r"C:\Users\agente\dashboard_repo"
UPDATE_DATA_SCRIPT = os.path.join(REPO_DIR, "update_dashboard_data.py")
CONVERT_SCRIPT = os.path.join(REPO_DIR, "convert_data.js")

def run_command(cmd, cwd=REPO_DIR):
    print(f"Executing: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error executing {cmd}: {result.stderr}")
        return False, result.stderr
    return True, result.stdout

def main():
    # 1. Update the master JSON data (Daily fetch)
    # Default to yesterday for the cron
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"--- Step 1: Updating data for {yesterday} ---")
    # We call the python script. 
    # Note: we use sys.executable to ensure we use the same python environment
    success, output = run_command(f"{sys.executable} update_dashboard_data.py {yesterday}")
    if not success:
        print("Failed to update data. Stopping.")
        return

    print(output)

    # 2. Convert data to summary and CSV
    print("\n--- Step 2: Converting data for Dashboard ---")
    success, output = run_command(f"node convert_data.js")
    if not success:
        print("Failed to convert data. Stopping.")
        return
    print(output)

    # 3. Push only specific files to GitHub
    print("\n--- Step 3: Pushing summaries to GitHub ---")
    # We only add and push products.csv and dashboard_resumen.json
    git_cmd = (
        "git add productos.csv dashboard_resumen.json && "
        "git commit -m 'Actualización automática de datos del dashboard: '"+ yesterday + " && "
        "git push origin master"
    )
    success, output = run_command(git_cmd)
    if not success:
        print("Failed to push to GitHub.")
        print(output)
    else:
        print("Successfully pushed updates to GitHub.")
        print(output)

if __name__ == "__main__":
    main()
