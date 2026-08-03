import io
import csv
import openpyxl
from flask import send_file

class ReportExporter:

    @staticmethod
    def export_to_csv(data: list[dict], filename: str):
        """Generates an in-memory CSV file stream."""
        if not data:
            return None, "No data to export"

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

        mem = io.BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        return mem, f"{filename}.csv"

    @staticmethod
    def export_to_excel(data: list[dict], sheet_name: str, filename: str):
        """Generates a styled in-memory Excel spreadsheet."""
        if not data:
            return None, "No data to export"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        # Write Header
        headers = list(data[0].keys())
        ws.append(headers)

        # Write Rows
        for row in data:
            ws.append(list(row.values()))

        mem = io.BytesIO()
        wb.save(mem)
        mem.seek(0)
        return mem, f"{filename}.xlsx"