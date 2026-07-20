from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file
)

import mysql.connector
import pandas as pd
import os

from werkzeug.utils import secure_filename

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

app = Flask(__name__)

app.secret_key = "employee_management_system"

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- MySQL Connection ----------------

db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="HEMUs@1234",
    database="employee_db"
)

# ---------------- Home ----------------

@app.route("/")
def home():
    return render_template("login.html")


# ---------------- Login ----------------

@app.route("/login", methods=["POST"])
def login():

    username = request.form["username"]
    password = request.form["password"]

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM admin
        WHERE username=%s
        AND password=%s
        """,
        (username, password)
    )

    admin = cursor.fetchone()

    cursor.close()

    if admin:

        session["admin"] = admin["username"]

        flash("Login Successful", "success")

        return redirect(url_for("dashboard"))

    flash("Invalid Username or Password", "danger")

    return redirect(url_for("home"))


# ---------------- Logout ----------------

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged Out Successfully", "success")

    return redirect(url_for("home"))


# ---------------- Dashboard ----------------

@app.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect(url_for("home"))

    cursor = db.cursor(dictionary=True)

    # Total Employees
    cursor.execute("SELECT COUNT(*) AS total FROM employees")
    total_employees = cursor.fetchone()["total"]

    # Departments
    cursor.execute("SELECT COUNT(DISTINCT department) AS total FROM employees")
    total_departments = cursor.fetchone()["total"]

    # Average Salary
    cursor.execute("SELECT AVG(salary) AS avg_salary FROM employees")
    avg_salary = cursor.fetchone()["avg_salary"] or 0

    # Highest Salary
    cursor.execute("SELECT MAX(salary) AS highest_salary FROM employees")
    highest_salary = cursor.fetchone()["highest_salary"] or 0

    # Lowest Salary
    cursor.execute("SELECT MIN(salary) AS lowest_salary FROM employees")
    lowest_salary = cursor.fetchone()["lowest_salary"] or 0

    # Recent Employees
    cursor.execute("""
        SELECT *
        FROM employees
        ORDER BY id DESC
        LIMIT 5
    """)
    recent_employees = cursor.fetchall()

    # Department Count
    cursor.execute("""
        SELECT department,
               COUNT(*) AS total
        FROM employees
        GROUP BY department
    """)

    department_data = cursor.fetchall()

    departments = []
    department_counts = []

    for row in department_data:
        departments.append(row["department"])
        department_counts.append(row["total"])

    cursor.close()

    return render_template(
        "dashboard.html",
        total_employees=total_employees,
        total_departments=total_departments,
        avg_salary=round(avg_salary,2),
        highest_salary=highest_salary,
        lowest_salary=lowest_salary,
        recent_employees=recent_employees,
        departments=departments,
        department_counts=department_counts
    )


# ---------------- Add Employee ----------------

@app.route("/add_employee")
def add_employee():

    if "admin" not in session:
        return redirect(url_for("home"))

    return render_template("add_employee.html")

# ---------------- Save Employee ----------------

@app.route("/save_employee", methods=["POST"])
def save_employee():

    if "admin" not in session:
        return redirect(url_for("home"))

    full_name = request.form["full_name"]
    email = request.form["email"]
    phone = request.form["phone"]
    department = request.form["department"]
    designation = request.form["designation"]
    salary = request.form["salary"]
    hire_date = request.form["hire_date"]
    address = request.form["address"]
    status = request.form["status"]

    image = ""

    if "image" in request.files:

        file = request.files["image"]

        if file.filename != "":

            filename = secure_filename(file.filename)

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            image = filename

    cursor = db.cursor()

    sql = """
    INSERT INTO employees
    (
        full_name,
        email,
        phone,
        department,
        designation,
        salary,
        hire_date,
        address,
        image,
        status
    )
    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        full_name,
        email,
        phone,
        department,
        designation,
        salary,
        hire_date,
        address,
        image,
        status
    )

    cursor.execute(sql, values)

    db.commit()

    cursor.close()

    flash("Employee Added Successfully", "success")

    return redirect(url_for("employees"))

# ---------------- View Employee ----------------

@app.route("/employees")
def employees():

    if "admin" not in session:
        return redirect(url_for("home"))

    search = request.args.get("search", "")

    cursor = db.cursor(dictionary=True)

    if search:

        value = "%" + search + "%"

        cursor.execute(
            """
            SELECT *
            FROM employees
            WHERE
            full_name LIKE %s
            OR email LIKE %s
            OR department LIKE %s
            OR designation LIKE %s
            ORDER BY id DESC
            """,
            (value, value, value, value)
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM employees
            ORDER BY id DESC
            """
        )

    employee_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "employees.html",
        employees=employee_list,
        search=search
    )

# ---------------- Edit Employee ----------------

@app.route("/edit_employee/<int:id>")
def edit_employee(id):

    if "admin" not in session:
        return redirect(url_for("home"))

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM employees WHERE id=%s",
        (id,)
    )

    employee = cursor.fetchone()

    cursor.close()

    return render_template(
        "edit_employee.html",
        employee=employee
    )

# ---------------- Delete Employee ----------------

@app.route("/delete_employee/<int:id>")
def delete_employee(id):

    if "admin" not in session:
        return redirect(url_for("home"))

    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM employees WHERE id=%s",
        (id,)
    )

    db.commit()

    cursor.close()

    flash("Employee Deleted Successfully", "success")
    return redirect(url_for("employees"))

# ---------------- Update Employee -----------------


@app.route("/update_employee/<int:id>", methods=["POST"])
def update_employee(id):

    if "admin" not in session:
        return redirect(url_for("home"))

    full_name = request.form["full_name"]
    email = request.form["email"]
    phone = request.form["phone"]
    department = request.form["department"]
    designation = request.form["designation"]
    salary = request.form["salary"]
    hire_date = request.form["hire_date"]
    address = request.form["address"]
    status = request.form["status"]

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT image FROM employees WHERE id=%s",
        (id,)
    )

    employee = cursor.fetchone()

    image = employee["image"]

    if "image" in request.files:

        file = request.files["image"]

        if file.filename != "":

            filename = secure_filename(file.filename)

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            image = filename

    cursor = db.cursor()

    sql = """
    UPDATE employees
    SET
        full_name=%s,
        email=%s,
        phone=%s,
        department=%s,
        designation=%s,
        salary=%s,
        hire_date=%s,
        address=%s,
        image=%s,
        status=%s
    WHERE id=%s
    """

    values = (
        full_name,
        email,
        phone,
        department,
        designation,
        salary,
        hire_date,
        address,
        image,
        status,
        id
    )

    cursor.execute(sql, values)

    db.commit()

    cursor.close()

    flash("Employee Updated Successfully", "success")

    return redirect(url_for("employees"))

 # ---------------- Reports----------------

@app.route("/reports")
def reports():

    if "admin" not in session:
        return redirect(url_for("home"))

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) total FROM employees")
    total_employees = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(DISTINCT department) total FROM employees")
    total_departments = cursor.fetchone()["total"]

    cursor.execute("SELECT AVG(salary) avg_salary FROM employees")
    avg_salary = cursor.fetchone()["avg_salary"] or 0

    cursor.execute("SELECT MAX(salary) highest_salary FROM employees")
    highest_salary = cursor.fetchone()["highest_salary"] or 0

    cursor.execute("SELECT MIN(salary) lowest_salary FROM employees")
    lowest_salary = cursor.fetchone()["lowest_salary"] or 0

    cursor.execute("""
        SELECT department,
               COUNT(*) total
        FROM employees
        GROUP BY department
    """)

    department_report = cursor.fetchall()

    cursor.close()

    return render_template(
        "reports.html",
        total_employees=total_employees,
        total_departments=total_departments,
        avg_salary=round(avg_salary,2),
        highest_salary=highest_salary,
        lowest_salary=lowest_salary,
        department_report=department_report
    )
 # ---------------- Excel----------------
@app.route("/export_excel")
def export_excel():

    if "admin" not in session:
        return redirect(url_for("home"))

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT full_name,email,phone,department,designation,salary,hire_date,status
        FROM employees
    """)

    data = cursor.fetchall()
    cursor.close()

    df = pd.DataFrame(data)

    filepath = "employees.xlsx"
    df.to_excel(filepath, index=False, engine="openpyxl")

    return send_file(
        filepath,
        as_attachment=True,
        download_name="employees.xlsx"
    )

 # ---------------- Export Employees to PDF ----------------
@app.route("/export_pdf")
def export_pdf():

    if "admin" not in session:
        return redirect(url_for("home"))

    cursor = db.cursor()

    cursor.execute("""
        SELECT full_name,email,phone,department,designation,salary,status
        FROM employees
    """)

    employees = cursor.fetchall()
    cursor.close()

    filepath = "employees.pdf"

    pdf = SimpleDocTemplate(filepath, pagesize=letter)

    data = [[
        "Name","Email","Phone",
        "Department","Designation",
        "Salary","Status"
    ]]

    for row in employees:
        data.append(list(row))

    table = Table(data)

    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('BACKGROUND',(0,1),(-1,-1),colors.beige),
        ('ALIGN',(0,0),(-1,-1),'CENTER')
    ]))

    pdf.build([table])

    return send_file(
        filepath,
        as_attachment=True,
        download_name="employees.pdf"
    )
if __name__ == "__main__":
    app.run(debug=True) 