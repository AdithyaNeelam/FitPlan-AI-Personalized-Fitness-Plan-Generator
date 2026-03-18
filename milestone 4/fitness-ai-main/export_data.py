# export_data.py
import sqlite3
import json
import os

print("📤 Exporting data from SQLite...")

# Connect to SQLite
sqlite_conn = sqlite3.connect('fitness.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# Get all tables
tables = ['user', 'user_progress', 'workout_schedule', 'workout_log', 'meal_log', 'user_settings', 'achievement']
data = {}

for table in tables:
    try:
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()
        data[table] = [dict(row) for row in rows]
        print(f"✅ Exported {len(rows)} rows from {table}")
    except:
        print(f"⚠️ Table {table} not found, skipping...")
        data[table] = []

# Save to JSON file
with open('backup_data.json', 'w') as f:
    json.dump(data, f, indent=2, default=str)

print("✅ Data exported to backup_data.json")
sqlite_conn.close()