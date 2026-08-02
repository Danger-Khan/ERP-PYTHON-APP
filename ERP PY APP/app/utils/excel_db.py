import os
import shutil
import openpyxl
from datetime import datetime
from filelock import FileLock
from config import Config

class ExcelDB:
    """Abstract database handler. Replace this class to migrate to SQL later."""
    
    def __init__(self, table_name: str):
        self.filepath = os.path.join(Config.DATA_DIR, f"{table_name}.xlsx")
        self.lockpath = f"{self.filepath}.lock"

    def _backup(self):
        """Creates a timestamped backup before any write operation."""
        if os.path.exists(self.filepath):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{timestamp}_{os.path.basename(self.filepath)}"
            shutil.copy2(self.filepath, os.path.join(Config.BACKUP_DIR, backup_filename))

    def get_all(self) -> list[dict]:
        """Reads Excel safely and returns a list of dictionaries."""
        if not os.path.exists(self.filepath):
            return []
            
        with FileLock(self.lockpath):
            try:
                wb = openpyxl.load_workbook(self.filepath, data_only=True)
                sheet = wb.active
                rows = list(sheet.iter_rows(values_only=True))
                
                if not rows or len(rows) < 2:
                    return []
                    
                headers = [str(h) for h in rows[0]]
                return [dict(zip(headers, row)) for row in rows[1:]]
            except Exception as e:
                # Log corruption detection here
                raise RuntimeError(f"Database read error: {str(e)}")

    def save_record(self, record: dict, id_field: str = 'id'):
        """Inserts or updates a record transactionally."""
        with FileLock(self.lockpath):
            self._backup()
            wb = openpyxl.load_workbook(self.filepath) if os.path.exists(self.filepath) else openpyxl.Workbook()
            sheet = wb.active

            # Handle empty sheet
            if sheet.max_row == 1 and sheet.cell(1, 1).value is None:
                sheet.append(list(record.keys()))

            headers = [str(cell.value) for cell in sheet[1]]
            existing_id_col = headers.index(id_field) + 1 if id_field in headers else None

            # Check for update
            updated = False
            if existing_id_col:
                for row_idx in range(2, sheet.max_row + 1):
                    if str(sheet.cell(row_idx, existing_id_col).value) == str(record.get(id_field)):
                        for col_idx, key in enumerate(headers, 1):
                            sheet.cell(row_idx, col_idx).value = record.get(key, "")
                        updated = True
                        break

            # Insert if not updated
            if not updated:
                row_data = [record.get(h, "") for h in headers]
                sheet.append(row_data)

            wb.save(self.filepath)

def initialize_database():
    """Generates default tables if they don't exist."""
    required_tables = ['users', 'customers', 'orders', 'employees', 'inventory']
    for table in required_tables:
        db = ExcelDB(table)
        if not os.path.exists(db.filepath):
            wb = openpyxl.Workbook()
            wb.save(db.filepath)