"""
SafeRoute AI — Data Migration Helper
Copies the existing Bengaluru CSV to the new canonical folder structure.
Run once:  python migrate_data.py
"""
import os, shutil

BASE = os.path.dirname(os.path.abspath(__file__))

src  = os.path.join(BASE, "bangalore_crime_dataset.csv")
dst_dir = os.path.join(BASE, "..", "data", "karnataka", "bengaluru")
dst  = os.path.join(dst_dir, "crime_dataset.csv")

os.makedirs(dst_dir, exist_ok=True)

if not os.path.exists(dst):
    shutil.copy2(src, dst)
    print(f"✅ Copied  {src}")
    print(f"       →  {dst}")
else:
    print(f"✅ Already exists: {dst}")

print("Migration complete.")
