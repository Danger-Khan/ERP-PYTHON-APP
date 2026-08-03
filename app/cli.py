import argparse
import sys
from app.utils.excel_db import ExcelDB, initialize_database
from app.security.auth import hash_password
from app.utils.migrator import migrate_excel_to_sqlite
from app.services.backup_service import BackupEngine

def main():
    parser = argparse.ArgumentParser(description="Atelier Management System CLI Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    # Command: init
    subparsers.add_parser("init", help="Initialize Excel database tables")

    # Command: create-admin
    admin_parser = subparsers.add_parser("create-admin", help="Create a new administrator account")
    admin_parser.add_argument("--username", required=True, help="Admin username")
    admin_parser.add_argument("--password", required=True, help="Admin password")

    # Command: migrate
    subparsers.add_parser("migrate", help="Migrate Excel data to SQLite database")

    # Command: backup
    subparsers.add_parser("backup", help="Trigger full system zip backup")

    args = parser.parse_args()

    if args.command == "init":
        initialize_database()
        print("✅ Database files initialized successfully.")

    elif args.command == "create-admin":
        users_db = ExcelDB('users')
        users = users_db.get_all()
        
        if any(u.get('username') == args.username for u in users):
            print(f"❌ Error: Username '{args.username}' already exists.")
            sys.exit(1)

        new_user = {
            "id": f"ADM-{len(users) + 1:03d}",
            "username": args.username,
            "password_hash": hash_password(args.password),
            "role": "Administrator",
            "created_at": "CLI-Generated"
        }
        users_db.save_record(new_user, id_field='id')
        print(f"🎉 Administrator account '{args.username}' created successfully!")

    elif args.command == "migrate":
        migrate_excel_to_sqlite()

    elif args.command == "backup":
        path = BackupEngine.create_full_backup()
        print(f"📦 Backup created successfully at: {path}")

    else:
        parser.print_help()

if __name__ == '__main__':
    main()