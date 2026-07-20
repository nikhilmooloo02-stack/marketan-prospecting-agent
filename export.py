"""
Exports good-fit clinics with drafted outreach messages to a CSV file,
ready to open in Excel for review.

Usage:
    python export.py                  # exports to prospects_export.csv
    python export.py my_file.csv      # custom output filename
"""
import csv
import sys

from db import get_connection

DEFAULT_FILENAME = "prospects_export.csv"


def export_csv(filename=DEFAULT_FILENAME):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT name, city, address, fit_score, fit_label, fit_reasoning,
               outreach_status, outreach_message
        FROM clinics
        WHERE fit_label = 'good_fit' AND outreach_status != 'duplicate'
        ORDER BY fit_score DESC
        """
    ).fetchall()
    conn.close()

    if not rows:
        print("Nothing to export — no good-fit clinics found.")
        return

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Clinic Name", "City", "Address", "Fit Score", "Fit Label",
            "Why It's a Fit", "Outreach Status", "Outreach Message",
        ])
        for r in rows:
            writer.writerow([
                r["name"], r["city"], r["address"], r["fit_score"],
                r["fit_label"], r["fit_reasoning"],
                r["outreach_status"], r["outreach_message"],
            ])

    print(f"Exported {len(rows)} clinic(s) to {filename}")


if __name__ == "__main__":
    fname = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILENAME
    export_csv(fname)