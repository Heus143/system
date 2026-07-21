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

from pymongo import MongoClient
from bson.objectid import ObjectId

from werkzeug.utils import secure_filename

from io import BytesIO

import pandas as pd
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle
)

app = Flask(__name__)

app.secret_key = "employee_management_system"

# ===============================
# Upload Folder
# ===============================

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ===============================
# MongoDB Connection
# ===============================

MONGO_URI = "mongodb+srv://hemu37731_db_user:HEMANTHDIVVELA@cluster0.shbmhyx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)

db = client["employee_db"]

employees_collection = db["employees"]

admin_collection = db["admin"]

# ===============================
# Home
# ===============================

@app.route("/")
def home():
    return render_template("login.html")


# ===============================
# Login
# ===============================

@app.route("/login", methods=["POST"])
def login():

    username = request.form["username"]
    password = request.form["password"]

    admin = admin_collection.find_one(
        {
            "username": username,
            "password": password
        }
    )

    if admin:

        session["admin"] = admin["username"]

        flash("Login Successful", "success")

        return redirect(url_for("dashboard"))

    flash("Invalid Username or Password", "danger")

    return redirect(url_for("home"))


# ===============================
# Logout
# ===============================

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged Out Successfully", "success")

    return redirect(url_for("home"))
# ===============================
# Dashboard
# ===============================

@app.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect(url_for("home"))

    total_employees = employees_collection.count_documents({})

    departments = employees_collection.distinct("department")

    total_departments = len(departments)

    employees = list(employees_collection.find())

    if employees:

        salaries = [
            float(emp.get("salary", 0) or 0)
            for emp in employees
        ]

        avg_salary = sum(salaries) / len(salaries)

        highest_salary = max(salaries)

        lowest_salary = min(salaries)

    else:

        avg_salary = 0

        highest_salary = 0

        lowest_salary = 0

    recent_employees = list(

        employees_collection.find()

        .sort("_id", -1)

        .limit(5)

    )

    department_counts = []

    for dept in departments:

        department_counts.append(

            employees_collection.count_documents(

                {

                    "department": dept

                }

            )

        )

    return render_template(

        "dashboard.html",

        total_employees=total_employees,

        total_departments=total_departments,

        avg_salary=round(avg_salary, 2),

        highest_salary=highest_salary,

        lowest_salary=lowest_salary,

        recent_employees=recent_employees,

        departments=departments,

        department_counts=department_counts

    )


# ===============================
# Add Employee
# ===============================

@app.route("/add_employee")
def add_employee():

    if "admin" not in session:

        return redirect(url_for("home"))

    return render_template("add_employee.html")


# ===============================
# Save Employee
# ===============================

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

    employee = {

        "full_name": full_name,

        "email": email,

        "phone": phone,

        "department": department,

        "designation": designation,

        "salary": float(salary) if salary else 0,

        "hire_date": hire_date,

        "address": address,

        "image": image,

        "status": status

    }

    employees_collection.insert_one(employee)

    flash("Employee Added Successfully", "success")

    return redirect(url_for("employees"))
# =====================================================
# View Employees
# =====================================================

@app.route("/employees")
def employees():

    if "admin" not in session:
        return redirect(url_for("home"))

    search = request.args.get("search", "").strip()

    if search:

        employee_list = list(
            employees_collection.find(
                {
                    "$or": [
                        {
                            "full_name": {
                                "$regex": search,
                                "$options": "i"
                            }
                        },
                        {
                            "email": {
                                "$regex": search,
                                "$options": "i"
                            }
                        },
                        {
                            "department": {
                                "$regex": search,
                                "$options": "i"
                            }
                        },
                        {
                            "designation": {
                                "$regex": search,
                                "$options": "i"
                            }
                        }
                    ]
                }
            ).sort("_id", -1)
        )

    else:

        employee_list = list(
            employees_collection.find().sort("_id", -1)
        )

    return render_template(
        "employees.html",
        employees=employee_list,
        search=search
    )


# =====================================================
# Edit Employee
# =====================================================

@app.route("/edit_employee/<id>")
def edit_employee(id):

    if "admin" not in session:
        return redirect(url_for("home"))

    try:

        employee = employees_collection.find_one(
            {
                "_id": ObjectId(id)
            }
        )

        if employee is None:
            flash("Employee Not Found", "danger")
            return redirect(url_for("employees"))

    except Exception:

        flash("Invalid Employee ID", "danger")
        return redirect(url_for("employees"))

    return render_template(
        "edit_employee.html",
        employee=employee
    )


# =====================================================
# Update Employee
# =====================================================

@app.route("/update_employee/<id>", methods=["POST"])
def update_employee(id):

    if "admin" not in session:
        return redirect(url_for("home"))

    try:

        employee = employees_collection.find_one(
            {
                "_id": ObjectId(id)
            }
        )

        if employee is None:
            flash("Employee Not Found", "danger")
            return redirect(url_for("employees"))

    except Exception:

        flash("Invalid Employee ID", "danger")
        return redirect(url_for("employees"))

    image = employee.get("image", "")

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

    employees_collection.update_one(

        {
            "_id": ObjectId(id)
        },

        {
            "$set": {

                "full_name": request.form["full_name"],

                "email": request.form["email"],

                "phone": request.form["phone"],

                "department": request.form["department"],

                "designation": request.form["designation"],

                "salary": float(request.form["salary"])
                if request.form["salary"] else 0,

                "hire_date": request.form["hire_date"],

                "address": request.form["address"],

                "status": request.form["status"],

                "image": image

            }
        }

    )

    flash("Employee Updated Successfully", "success")

    return redirect(url_for("employees"))


# =====================================================
# Delete Employee
# =====================================================

@app.route("/delete_employee/<id>")
def delete_employee(id):

    if "admin" not in session:
        return redirect(url_for("home"))

    try:

        employees_collection.delete_one(
            {
                "_id": ObjectId(id)
            }
        )

        flash("Employee Deleted Successfully", "success")

    except Exception:

        flash("Employee Not Found", "danger")

    return redirect(url_for("employees"))
# =====================================================
# Reports
# =====================================================

@app.route("/reports")
def reports():

    if "admin" not in session:
        return redirect(url_for("home"))

    employees = list(employees_collection.find())

    total_employees = len(employees)

    departments = employees_collection.distinct("department")

    total_departments = len(departments)

    if employees:

        salaries = [
            float(emp.get("salary", 0) or 0)
            for emp in employees
        ]

        avg_salary = sum(salaries) / len(salaries)

        highest_salary = max(salaries)

        lowest_salary = min(salaries)

    else:

        avg_salary = 0
        highest_salary = 0
        lowest_salary = 0

    department_report = []

    for dept in departments:

        department_report.append({

            "department": dept,

            "total": employees_collection.count_documents(
                {
                    "department": dept
                }
            )

        })

    return render_template(

        "reports.html",

        total_employees=total_employees,

        total_departments=total_departments,

        avg_salary=round(avg_salary, 2),

        highest_salary=highest_salary,

        lowest_salary=lowest_salary,

        department_report=department_report

    )


# =====================================================
# Export Excel
# =====================================================

@app.route("/export_excel")
def export_excel():

    if "admin" not in session:
        return redirect(url_for("home"))

    employees = list(

        employees_collection.find(
            {},
            {
                "_id": 0
            }
        )

    )

    df = pd.DataFrame(employees)

    filepath = "employees.xlsx"

    df.to_excel(
        filepath,
        index=False,
        engine="openpyxl"
    )

    return send_file(

        filepath,

        as_attachment=True,

        download_name="employees.xlsx"

    )


# =====================================================
# Export PDF
# =====================================================

@app.route("/export_pdf")
def export_pdf():

    if "admin" not in session:
        return redirect(url_for("home"))

    employees = list(

        employees_collection.find()

    )

    filepath = "employees.pdf"

    pdf = SimpleDocTemplate(

        filepath,

        pagesize=letter

    )

    data = [[

        "Name",

        "Email",

        "Phone",

        "Department",

        "Designation",

        "Salary",

        "Status"

    ]]

    for emp in employees:

        data.append([

            emp.get("full_name", ""),

            emp.get("email", ""),

            emp.get("phone", ""),

            emp.get("department", ""),

            emp.get("designation", ""),

            emp.get("salary", ""),

            emp.get("status", "")

        ])

    table = Table(data)

    table.setStyle(

        TableStyle([

            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),

            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

            ("GRID", (0, 0), (-1, -1), 1, colors.black),

            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),

            ("ALIGN", (0, 0), (-1, -1), "CENTER")

        ])

    )

    pdf.build([table])

    return send_file(

        filepath,

        as_attachment=True,

        download_name="employees.pdf"

    )


# =====================================================
# Run Flask App
# =====================================================

if __name__ == "__main__":

    app.run(debug=True)