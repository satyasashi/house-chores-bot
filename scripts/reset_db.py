import os

DB_PATH = "instance/app.db"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("✅ Deleted instance/app.db")
else:
    print("No DB file found, nothing to delete.")
