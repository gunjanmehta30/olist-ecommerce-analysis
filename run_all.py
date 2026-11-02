
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
extra = ["--sample"] if "--sample" in sys.argv else []
for script, args in [("build_database.py", extra), ("run_analysis.py", []), ("build_dashboard.py", [])]:
    print(f"\n=== {script} ===")
    subprocess.run([sys.executable, str(SRC / script), *args], check=True, cwd=SRC)
print("\nAll done. Open outputs/dashboard.html and reports/insights_report.md")
