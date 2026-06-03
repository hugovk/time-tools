"""
Create timesheet from Toggl CSV export.

For example:

https://track.toggl.com/reports/detailed/period/prevMonth > ↓ > CSV

uv run timesheet.py Toggl_time_entries_2025-01-01_to_2025-01-31.csv

uv run timesheet.py Toggl_time_entries_2025-01-01_to_2025-01-31.csv --pdf
"""

import argparse
import csv
import datetime as dt
from collections import defaultdict
from typing import Any

from prettytable import PrettyTable
from prettytable import TableStyle as PrettyTableStyle

# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "prettytable>=3.14",
#   "reportlab",
#   "rich",
# ]
# ///


def read_csv(filename: str) -> list[dict[str, Any]]:
    with open(filename, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_duration(duration_str: str) -> dt.timedelta:
    hours, minutes, seconds = map(int, duration_str.split(":"))
    return dt.timedelta(hours=hours, minutes=minutes, seconds=seconds)


def format_duration(duration: dt.timedelta) -> str:
    total_minutes = duration.total_seconds() // 60
    hours, minutes = divmod(total_minutes, 60)
    return f"{int(hours):02}:{int(minutes):02}"


def get_day_suffix(day: int) -> str:
    if 4 <= day <= 20 or 24 <= day <= 30:
        return "th"
    else:
        return ["st", "nd", "rd"][day % 10 - 1]


def create_pdf(table: PrettyTable, filename: str, name: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    pdf = SimpleDocTemplate(filename, pagesize=landscape(A4))
    elements = []

    # Calculate the last month
    current_date = dt.datetime.now()
    last_month = current_date.replace(day=1) - dt.timedelta(days=1)
    last_month_name = last_month.strftime("%B %Y")

    # Add title
    styles = getSampleStyleSheet()
    title_style_26pt = ParagraphStyle(
        "Title26pt", parent=styles["Title"], fontSize=26, fontName="Helvetica"
    )
    title_style_15pt_grey = ParagraphStyle(
        "Title15ptGrey",
        parent=styles["Title"],
        fontSize=15,
        textColor=colors.HexColor("#6f6f6f"),
        fontName="Helvetica",
    )

    elements.append(Paragraph(f"{last_month_name} Timesheet", title_style_26pt))
    elements.append(Spacer(1, 6))
    current_date = dt.datetime.now()
    formatted_date = f"{current_date.day}{get_day_suffix(current_date.day)} {current_date.strftime('%B %Y')}"
    elements.append(
        Paragraph(
            f"Sovereign Tech Fellowship, {name}, {formatted_date}",
            title_style_15pt_grey,
        )
    )

    # Convert PrettyTable to list of lists
    table_data = [table.field_names] + table.rows

    # Create a table with the data
    pdf_table = Table(table_data, repeatRows=1)

    # Set the style for the table
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, 0), 1, colors.black),  # Header row grid
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            # Underline above total row
        ]
    )

    # Add conditional row separators
    previous_date = None
    for i, row in enumerate(table.rows, start=1):
        current_date = row[0]
        if previous_date and current_date != previous_date:
            style.add("LINEABOVE", (0, i), (-1, i), 1, colors.black)
        previous_date = current_date

    pdf_table.setStyle(style)

    # Add the table to the elements
    elements.append(pdf_table)

    # Build the PDF
    pdf.build(elements)
    print(f"PDF report saved to {filename}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read in a CSV file and produce a report showing daily reports"
    )
    parser.color = True
    parser.add_argument("filename", help="CSV file to read")
    parser.add_argument("-n", "--name", default="Hugo van Kemenade", help="Your name")
    parser.add_argument(
        "--html",
        action="store_true",
        help="Output the report in HTML format",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Output the report in PDF format",
    )
    parser.add_argument(
        "--no-project",
        action="store_true",
        help="Hide the project column",
    )
    args = parser.parse_args()

    data = read_csv(args.filename)

    # Group each day by client, project, and task,
    # and show the total duration for each task.
    grouped = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dt.timedelta)))
    )
    for row in data:
        start_date = dt.datetime.strptime(row["Start date"], "%Y-%m-%d")
        task = row["Description"]
        duration = parse_duration(row["Duration"])
        grouped[start_date][row["Client"]][row["Project"]][task] += duration

    table = PrettyTable()
    table.set_style(PrettyTableStyle.SINGLE_BORDER)
    table.field_names = ["Date", "Project", "Area", "Task", "hh:mm"]

    total_duration = dt.timedelta()
    for start_date, clients in sorted(grouped.items()):
        for client, projects in sorted(clients.items(), key=lambda x: x[0].lower()):
            for project, tasks in sorted(projects.items(), key=lambda x: x[0].lower()):
                for task, duration in sorted(tasks.items(), key=lambda x: x[0].lower()):
                    table.add_row(
                        [
                            start_date.strftime("%Y-%m-%d"),
                            client,
                            project,
                            task,
                            format_duration(duration),
                        ]
                    )
                    total_duration += duration
        table.add_divider()

    # Add total row
    table.add_row(["Total", "", "", "", format_duration(total_duration)])

    if args.no_project:
        table.del_column("Project")
    if args.html:
        print(table.get_html_string())
    elif args.pdf:
        # save as yyyy-mm-STF-timesheet.pdf where yyyy-mm is the last month
        last_month = dt.datetime.now().replace(day=1) - dt.timedelta(days=1)
        filename = f"{last_month.strftime('%Y-%m')}-STF-timesheet.pdf"
        create_pdf(table, filename, args.name)
    else:
        print(table)


if __name__ == "__main__":
    main()
