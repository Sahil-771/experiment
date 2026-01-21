from flask import Flask, render_template, request,redirect
import sqlite3
from flask import send_file
from flask import send_file
from openpyxl import Workbook
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from flask import send_file



app = Flask(__name__)

def get_db():
    return sqlite3.connect("database.db")

@app.route("/", methods=["GET","POST"])
def index():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        customer_id = request.form["customer_id"]
        amount = request.form["amount"]

        cur.execute(
            "INSERT INTO records (customer_id, amount) values (?,?)",
            (customer_id, amount)
        )
        conn.commit()
        return redirect("/")
    
    cur.execute("SELECT * FROM records ORDER BY id DESC")
    records = cur.fetchall()
    conn.close()

    return render_template("index.html", records=records)


@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    customer_id = request.form["customer_id"]
    start_date = request.form["start_date"]
    end_date = request.form["end_date"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT date(date), amount
        FROM records
        WHERE customer_id = ?
        AND date(date) BETWEEN date(?) AND date(?)
        ORDER BY date ASC
    """, (customer_id, start_date, end_date))

    rows = cur.fetchall()
    conn.close()

    # Create PDF in memory
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(
        f"<b>Milk Dairy Records</b><br/>Customer ID: {customer_id}<br/>"
        f"Period: {start_date} to {end_date}",
        styles["Title"]
    ))

    elements.append(Paragraph("<br/>", styles["Normal"]))

    # Table data
    table_data = [["Date", "Amount (₹)"]]
    total_amount = 0

    for row in rows:
        table_data.append([row[0], row[1]])
        total_amount += row[1]

    table_data.append(["TOTAL", total_amount])

    table = Table(table_data, colWidths=[250, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))

    elements.append(table)

    pdf.build(elements)
    buffer.seek(0)

    filename = f"customer_{customer_id}_{start_date}_to_{end_date}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


# ---------------- FILTER PAGE ----------------
@app.route("/filter", methods=["GET", "POST"])
def filter_page():
    records = []
    total_amount = 0
    customer_id = ""
    start_date = ""
    end_date = ""

    if request.method == "POST":
        customer_id = request.form["customer_id"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, date, amount
            FROM records
            WHERE customer_id = ?
            AND date(date) BETWEEN date(?) AND date(?)
            ORDER BY date ASC
        """, (customer_id, start_date, end_date))

        records = cur.fetchall()

        cur.execute("""
            SELECT SUM(amount)
            FROM records
            WHERE customer_id = ?
            AND date(date) BETWEEN date(?) AND date(?)
        """, (customer_id, start_date, end_date))

        total_amount = cur.fetchone()[0] or 0
        conn.close()

    return render_template(
        "filter.html",
        records=records,
        total_amount=total_amount,
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date
    )

@app.route("/delete/<int:record_id>", methods=["POST"])
def delete_record(record_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/export", methods=["POST"])
def export_excel():
    customer_id = request.form["customer_id"]
    start_date = request.form["start_date"]
    end_date = request.form["end_date"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT date(date), amount
        FROM records
        WHERE customer_id = ?
        AND date(date) BETWEEN date(?) AND date(?)
        ORDER BY date ASC
    """, (customer_id, start_date, end_date))

    rows = cur.fetchall()
    conn.close()

    # ✅ Create Excel in memory (NOT on disk)
    wb = Workbook()
    ws = wb.active
    ws.title = "Filtered Records"

    ws.append(["Customer ID", "Date", "Amount (₹)"])

    total_amount = 0
    for row in rows:
        ws.append([customer_id, row[0], row[1]])
        total_amount += row[1]

    ws.append(["", "TOTAL", total_amount])

    # Save to memory
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    filename = f"customer_{customer_id}_{start_date}_to_{end_date}.xlsx"

    return send_file(
        file_stream,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

