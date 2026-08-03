import os
import sqlite3
from config import Config
from app.utils.excel_db import ExcelDB

def migrate_excel_to_sqlite(sqlite_db_name: str = "atelier_database.db"):
    """Reads all Excel sheets and creates a relational SQLite database file."""
    sqlite_path = os.path.join(Config.DATA_DIR, sqlite_db_name)
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    tables = ['users', 'customers', 'orders', 'employees', 'inventory']

    print(f"📦 Starting migration from Excel files to SQLite DB: {sqlite_path}")

    for table in tables:
        excel_db = ExcelDB(table)
        data = excel_db.get_all()

        if not data:
            print(f"⚠️ Table '{table}' has no data. Skipping creation.")
            continue

        # Extract column names from first record
        columns = list(data[0].keys())
        
        # Drop table if exists
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        # Create table schema (Defaulting to TEXT for flexibility)
        col_defs = ", ".join([f'"{col}" TEXT' for col in columns])
        create_sql = f"CREATE TABLE {table} ({col_defs});"
        cursor.execute(create_sql)

        # Insert records
        placeholders = ", ".join(["?" for _ in columns])
        insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"

        for record in data:
            values = [str(record.get(col, "")) for col in columns]
            cursor.execute(insert_sql, values)

        print(f"✅ Migrated {len(data)} rows to table '{table}'")

    conn.commit()
    conn.close()
    print("🎉 Excel to SQLite Migration completed successfully!")

if __name__ == '__main__':
    migrate_excel_to_sqlite()