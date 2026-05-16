from tkinter import *
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
from fpdf import FPDF
from datetime import datetime
from math import sin, cos, radians
import os
import sqlite3


PROJECT_DIR = r"C:\Users\HP\OneDrive\Desktop\SRM"
DB_PATH = os.path.join(PROJECT_DIR, "rms.db")
IMAGES_DIR = os.path.join(PROJECT_DIR, "images")
REPORTS_DIR = os.path.join(PROJECT_DIR, "reports")
PASS_THRESHOLD = 35.0
APP_TITLE = "School Result Management System"
APP_TAGLINE = "Role-based academic management for teachers and students"
DEFAULT_USERS = (
    ("teacher", "teacher123", "teacher"),
)

os.makedirs(REPORTS_DIR, exist_ok=True)


def db_connect():
    return sqlite3.connect(DB_PATH)


def clear_root(root):
    for widget in root.winfo_children():
        widget.destroy()


def open_login(root):
    clear_root(root)
    LoginWindow(root)


def authenticate_user(username, password):
    try:
        with db_connect() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT role FROM users WHERE username=? AND password=?",
                (username, password),
            )
            row = cur.fetchone()
            if row:
                return row[0]
    except sqlite3.Error:
        pass

    for default_username, default_password, role in DEFAULT_USERS:
        if username == default_username and password == default_password:
            return role
    return None


def normalize_student_key(value):
    if value in (None, "", "Select"):
        return None
    text = str(value)
    if " | " in text:
        text = text.split(" | ", 1)[0]
    try:
        return int(text)
    except ValueError:
        return None


def student_display(sid, roll, name="", class_name="", section=""):
    parts = [str(sid), f"Roll {roll}"]
    if name:
        parts.append(str(name))
    class_section = " / ".join(v for v in (str(class_name or ""), str(section or "")) if v)
    if class_section:
        parts.append(class_section)
    return " | ".join(parts)


def create_db():
    try:
        with db_connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS course(
                    cid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    duration TEXT,
                    charges TEXT,
                    description TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS student(
                    sid INTEGER PRIMARY KEY AUTOINCREMENT,
                    roll TEXT,
                    name TEXT,
                    email TEXT,
                    gender TEXT,
                    dob TEXT,
                    contact TEXT,
                    admission TEXT,
                    course TEXT,
                    state TEXT,
                    city TEXT,
                    pin TEXT,
                    address TEXT,
                    class_name TEXT,
                    section TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS result(
                    rid INTEGER PRIMARY KEY AUTOINCREMENT,
                    sid INTEGER,
                    name TEXT,
                    course TEXT,
                    subject TEXT,
                    marks_ob INTEGER,
                    full_marks INTEGER,
                    per REAL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollment(
                    eid INTEGER PRIMARY KEY AUTOINCREMENT,
                    sid INTEGER,
                    cid INTEGER,
                    UNIQUE(sid, cid)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users(
                    uid INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT,
                    sid INTEGER
                )
                """
            )
            cur.executemany(
                "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                DEFAULT_USERS,
            )

            cur.execute("PRAGMA table_info(student)")
            cols = [r[1] for r in cur.fetchall()]
            if "sid" not in cols:
                cur.execute("ALTER TABLE student RENAME TO student_old")
                cur.execute(
                    """
                    CREATE TABLE student(
                        sid INTEGER PRIMARY KEY AUTOINCREMENT,
                        roll TEXT,
                        name TEXT,
                        email TEXT,
                        gender TEXT,
                        dob TEXT,
                        contact TEXT,
                        admission TEXT,
                        course TEXT,
                        state TEXT,
                        city TEXT,
                        pin TEXT,
                        address TEXT,
                        class_name TEXT,
                        section TEXT
                    )
                    """
                )
                class_expr = "class_name" if "class_name" in cols else "''"
                section_expr = "section" if "section" in cols else "''"
                cur.execute(
                    f"""
                    INSERT INTO student
                    (sid, roll, name, email, gender, dob, contact, admission, course, state, city, pin, address, class_name, section)
                    SELECT roll, CAST(roll AS TEXT), name, email, gender, dob, contact, admission, course, state, city, pin, address,
                           {class_expr}, {section_expr}
                    FROM student_old
                    """
                )
                cur.execute("DROP TABLE student_old")
                cols = ["sid", "roll", "name", "email", "gender", "dob", "contact", "admission", "course", "state", "city", "pin", "address", "class_name", "section"]
            if "class_name" not in cols:
                cur.execute("ALTER TABLE student ADD COLUMN class_name TEXT")
            if "section" not in cols:
                cur.execute("ALTER TABLE student ADD COLUMN section TEXT")
            cur.execute("PRAGMA table_info(enrollment)")
            enrollment_cols = [r[1] for r in cur.fetchall()]
            if "sid" not in enrollment_cols:
                cur.execute("ALTER TABLE enrollment RENAME TO enrollment_old")
                cur.execute(
                    """
                    CREATE TABLE enrollment(
                        eid INTEGER PRIMARY KEY AUTOINCREMENT,
                        sid INTEGER,
                        cid INTEGER,
                        UNIQUE(sid, cid)
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT OR IGNORE INTO enrollment (sid, cid)
                    SELECT s.sid, e.cid
                    FROM enrollment_old e
                    JOIN student s ON CAST(s.roll AS TEXT)=CAST(e.roll AS TEXT)
                    """
                )
                cur.execute("DROP TABLE enrollment_old")
            cur.execute("PRAGMA table_info(result)")
            result_cols = [r[1] for r in cur.fetchall()]
            if "sid" not in result_cols:
                cur.execute("ALTER TABLE result RENAME TO result_old")
                cur.execute(
                    """
                    CREATE TABLE result(
                        rid INTEGER PRIMARY KEY AUTOINCREMENT,
                        sid INTEGER,
                        name TEXT,
                        course TEXT,
                        subject TEXT,
                        marks_ob INTEGER,
                        full_marks INTEGER,
                        per REAL
                    )
                    """
                )
                cur.execute(
                    """
                    INSERT INTO result (rid, sid, name, course, subject, marks_ob, full_marks, per)
                    SELECT r.rid, s.sid, r.name, r.course, r.subject, r.marks_ob, r.full_marks, r.per
                    FROM result_old r
                    LEFT JOIN student s ON CAST(s.roll AS TEXT)=CAST(r.roll AS TEXT)
                    """
                )
                cur.execute("DROP TABLE result_old")
            cur.execute("PRAGMA table_info(users)")
            user_cols = [r[1] for r in cur.fetchall()]
            if "sid" not in user_cols:
                cur.execute("ALTER TABLE users ADD COLUMN sid INTEGER")
            cur.execute("DELETE FROM users WHERE role='student' AND sid IS NULL")
            if "course" in cols:
                cur.execute(
                    "SELECT sid, course FROM student WHERE course IS NOT NULL AND TRIM(course) <> ''"
                )
                rows = cur.fetchall()
                for sid, course_name in rows:
                    cur.execute("SELECT cid FROM course WHERE name=?", (course_name,))
                    res = cur.fetchone()
                    if res:
                        cid = res[0]
                    else:
                        cur.execute(
                            "INSERT OR IGNORE INTO course (name, duration, charges, description) VALUES (?, '', '', '')",
                            (course_name,),
                        )
                        cur.execute("SELECT cid FROM course WHERE name=?", (course_name,))
                        cid = cur.fetchone()[0]
                    cur.execute(
                        "INSERT OR IGNORE INTO enrollment (sid, cid) VALUES (?, ?)",
                        (sid, cid),
                    )
            con.commit()
    except sqlite3.OperationalError as ex:
        if "readonly" not in str(ex).lower():
            raise


class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} - Login")
        self.root.geometry("980x620+180+90")
        self.root.config(bg="#151515")
        self.root.resizable(False, False)

        self.active_role = "teacher"
        self.var_username = StringVar()
        self.var_password = StringVar()
        self.var_show_password = IntVar(value=0)

        outer = Frame(self.root, bg="#151515")
        outer.place(relwidth=1, relheight=1)

        Label(
            outer,
            text=APP_TITLE.upper(),
            font=("goudy old style", 28, "bold"),
            bg="#151515",
            fg="#f7c948",
        ).pack(pady=(45, 8))

        Label(
            outer,
            text=APP_TAGLINE,
            font=("goudy old style", 14),
            bg="#151515",
            fg="#f4f4f4",
        ).pack()

        Label(
            outer,
            text="College Demo Flow: Login -> Role Access -> Results and Reports",
            font=("goudy old style", 12, "bold"),
            bg="#151515",
            fg="#d6b04a",
        ).pack(pady=(8, 0))

        card = Frame(outer, bg="#2a2a2a", bd=2, relief=RIDGE, highlightbackground="#f7c948", highlightthickness=2)
        card.place(relx=0.5, rely=0.54, anchor=CENTER, width=430, height=400)

        topbar = Frame(card, bg="#f7c948", height=52)
        topbar.pack(fill=X)

        self.btn_teacher = Button(
            topbar,
            text="Teacher Login",
            command=lambda: self.switch_role("teacher"),
            font=("goudy old style", 14, "bold"),
            bd=0,
            cursor="hand2",
        )
        self.btn_teacher.place(x=0, y=0, width=215, height=52)

        self.btn_student = Button(
            topbar,
            text="Student Login",
            command=lambda: self.switch_role("student"),
            font=("goudy old style", 14, "bold"),
            bd=0,
            cursor="hand2",
        )
        self.btn_student.place(x=215, y=0, width=215, height=52)

        self.lbl_heading = Label(card, text="", font=("goudy old style", 18, "bold"), bg="#2a2a2a", fg="white")
        self.lbl_heading.place(x=35, y=76)
        self.lbl_hint = Label(card, text="", font=("goudy old style", 11), bg="#2a2a2a", fg="#d7d7d7")
        self.lbl_hint.place(x=35, y=108)

        Label(card, text="Username", font=("goudy old style", 13, "bold"), bg="#2a2a2a", fg="white").place(x=35, y=145)
        self.txt_username = Entry(card, textvariable=self.var_username, font=("goudy old style", 14), bg="#fdf3bf", fg="#222222")
        self.txt_username.place(x=35, y=175, width=360, height=34)

        Label(card, text="Password", font=("goudy old style", 13, "bold"), bg="#2a2a2a", fg="white").place(x=35, y=225)
        self.txt_password = Entry(card, textvariable=self.var_password, show="*", font=("goudy old style", 14), bg="#fdf3bf", fg="#222222")
        self.txt_password.place(x=35, y=255, width=360, height=34)

        Checkbutton(
            card,
            text="Show password",
            variable=self.var_show_password,
            command=self.toggle_password,
            font=("goudy old style", 11),
            bg="#2a2a2a",
            fg="white",
            activebackground="#2a2a2a",
            activeforeground="white",
            selectcolor="#2a2a2a",
        ).place(x=35, y=300)

        Button(
            card,
            text="Login",
            command=self.login,
            font=("goudy old style", 15, "bold"),
            bg="#f7c948",
            fg="#1f1f1f",
            cursor="hand2",
            bd=0,
        ).place(x=35, y=340, width=360, height=38)

        self.lbl_demo = Label(outer, text="", font=("goudy old style", 12), bg="#151515", fg="#e0e0e0")
        self.lbl_demo.pack(side=BOTTOM, pady=26)

        self.switch_role("teacher")

    def switch_role(self, role):
        self.active_role = role
        if role == "teacher":
            self.lbl_heading.config(text="TEACHER SIGN IN")
            self.lbl_hint.config(text="Full access to courses, students, results, reports, class, and section records.")
            self.lbl_demo.config(text="Demo teacher login: teacher / teacher123")
            self.btn_teacher.config(bg="#2a2a2a", fg="#f7c948")
            self.btn_student.config(bg="#c79d1b", fg="#1f1f1f")
            if self.var_username.get().strip() == "":
                self.var_username.set("teacher")
                self.var_password.set("teacher123")
        else:
            self.lbl_heading.config(text="STUDENT SIGN IN")
            self.lbl_hint.config(text="Restricted access for viewing result details and exporting the marksheet PDF.")
            self.lbl_demo.config(text="Use the unique login ID and password created by the teacher.")
            self.btn_student.config(bg="#2a2a2a", fg="#f7c948")
            self.btn_teacher.config(bg="#c79d1b", fg="#1f1f1f")
            if self.var_username.get().strip() in ("", "teacher"):
                self.var_username.set("")
                self.var_password.set("")

    def toggle_password(self):
        self.txt_password.config(show="" if self.var_show_password.get() else "*")

    def login(self):
        username = self.var_username.get().strip()
        password = self.var_password.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Username and password are required", parent=self.root)
            return

        role = authenticate_user(username, password)
        if not role:
            messagebox.showerror("Error", "Invalid username or password", parent=self.root)
            return

        if role != self.active_role:
            messagebox.showerror("Error", f"This account is for {role} login", parent=self.root)
            return

        clear_root(self.root)
        if role == "teacher":
            RMS(self.root, current_user=username, on_logout=lambda: open_login(self.root))
        else:
            StudentPortal(self.root, current_user=username, on_logout=lambda: open_login(self.root))


class Course:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1200x480+200+250")
        self.root.config(bg="white")
        self.root.focus_force()

        Label(
            self.root,
            text="Manage Course Details",
            font=("goudy old style", 20, "bold"),
            bg="#033054",
            fg="white",
        ).place(x=10, y=15, width=1180, height=35)

        self.var_course = StringVar()
        self.var_duration = StringVar()
        self.var_charges = StringVar()
        self.var_search = StringVar()

        Label(self.root, text="Course Name", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=60)
        Label(self.root, text="Duration", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=100)
        Label(self.root, text="Charges", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=140)
        Label(self.root, text="Description", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=180)

        self.txt_courseName = Entry(
            self.root, textvariable=self.var_course, font=("goudy old style", 15, "bold"), bg="lightyellow"
        )
        self.txt_courseName.place(x=150, y=60, width=200)
        Entry(self.root, textvariable=self.var_duration, font=("goudy old style", 15, "bold"), bg="lightyellow").place(
            x=150, y=100, width=200
        )
        Entry(self.root, textvariable=self.var_charges, font=("goudy old style", 15, "bold"), bg="lightyellow").place(
            x=150, y=140, width=200
        )
        self.txt_description = Text(self.root, font=("goudy old style", 15, "bold"), bg="lightyellow")
        self.txt_description.place(x=150, y=180, width=500, height=130)

        Button(self.root, text="Save", command=self.add, font=("goudy old style", 15, "bold"), bg="#2196f3", fg="white").place(
            x=150, y=400, width=110, height=40
        )
        Button(self.root, text="Update", command=self.update, font=("goudy old style", 15, "bold"), bg="#4caf50", fg="white").place(
            x=270, y=400, width=110, height=40
        )
        Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 15, "bold"), bg="#f44336", fg="white").place(
            x=390, y=400, width=110, height=40
        )
        Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 15, "bold"), bg="#607d8b", fg="white").place(
            x=510, y=400, width=110, height=40
        )

        Label(self.root, text="Course Name", font=("goudy old style", 15, "bold"), bg="white").place(x=720, y=60)
        Entry(self.root, textvariable=self.var_search, font=("goudy old style", 15, "bold"), bg="lightyellow").place(
            x=870, y=60, width=180
        )
        Button(self.root, text="Search", command=self.search, font=("goudy old style", 15, "bold"), bg="#03a9f4", fg="white").place(
            x=1070, y=60, width=120, height=28
        )
        self.lbl_course_count = Label(
            self.root,
            text="Selected Course Students: 0",
            font=("goudy old style", 13, "bold"),
            bg="white",
            fg="#033054",
        )
        self.lbl_course_count.place(x=720, y=90, width=300, height=24)

        self.C_Frame = Frame(self.root, bd=2, relief=RIDGE)
        self.C_Frame.place(x=720, y=120, width=470, height=320)

        scrolly = Scrollbar(self.C_Frame, orient=VERTICAL)
        scrollx = Scrollbar(self.C_Frame, orient=HORIZONTAL)
        self.CourseTable = ttk.Treeview(
            self.C_Frame,
            columns=("cid", "name", "duration", "charges", "students", "description"),
            xscrollcommand=scrollx.set,
            yscrollcommand=scrolly.set,
        )
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.CourseTable.xview)
        scrolly.config(command=self.CourseTable.yview)
        self.CourseTable.heading("cid", text="Course ID")
        self.CourseTable.heading("name", text="Name")
        self.CourseTable.heading("duration", text="Duration")
        self.CourseTable.heading("charges", text="Charges")
        self.CourseTable.heading("students", text="Students")
        self.CourseTable.heading("description", text="Description")
        self.CourseTable["show"] = "headings"
        self.CourseTable.column("cid", width=70)
        self.CourseTable.column("name", width=100)
        self.CourseTable.column("duration", width=90)
        self.CourseTable.column("charges", width=80)
        self.CourseTable.column("students", width=70)
        self.CourseTable.column("description", width=150)
        self.CourseTable.pack(fill=BOTH, expand=1)
        self.CourseTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                if self.var_course.get().strip() == "":
                    messagebox.showerror("Error", "Course Name should be required", parent=self.root)
                    return
                cur.execute("SELECT * FROM course WHERE name=?", (self.var_course.get().strip(),))
                if cur.fetchone():
                    messagebox.showerror("Error", "Course Name already present", parent=self.root)
                    return
                cur.execute(
                    "INSERT INTO course (name,duration,charges,description) VALUES(?,?,?,?)",
                    (
                        self.var_course.get().strip(),
                        self.var_duration.get().strip(),
                        self.var_charges.get().strip(),
                        self.txt_description.get("1.0", END).strip(),
                    ),
                )
                con.commit()
            messagebox.showinfo("Success", "Course Added Successfully", parent=self.root)
            self.show()
            self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def search(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute(
                    """
                    SELECT c.cid, c.name, c.duration, c.charges, COUNT(DISTINCT e.sid) AS student_count, c.description
                    FROM course c
                    LEFT JOIN enrollment e ON c.cid = e.cid
                    WHERE c.name LIKE ?
                    GROUP BY c.cid, c.name, c.duration, c.charges, c.description
                    ORDER BY c.name
                    """,
                    (f"%{self.var_search.get().strip()}%",),
                )
                rows = cur.fetchall()
            self.CourseTable.delete(*self.CourseTable.get_children())
            for index, row in enumerate(rows, start=1):
                self.CourseTable.insert("", END, values=(index, row[1], row[2], row[3], row[4], row[5]))
            if len(rows) == 1:
                self.lbl_course_count.config(text=f"Selected Course Students: {rows[0][4]}")
            elif rows:
                self.lbl_course_count.config(text=f"Matched Courses: {len(rows)}")
            else:
                self.lbl_course_count.config(text="Selected Course Students: 0")
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def show(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute(
                    """
                    SELECT c.cid, c.name, c.duration, c.charges, COUNT(DISTINCT e.sid) AS student_count, c.description
                    FROM course c
                    LEFT JOIN enrollment e ON c.cid = e.cid
                    GROUP BY c.cid, c.name, c.duration, c.charges, c.description
                    ORDER BY c.name
                    """
                )
                rows = cur.fetchall()
            self.CourseTable.delete(*self.CourseTable.get_children())
            for index, row in enumerate(rows, start=1):
                self.CourseTable.insert("", END, values=(index, row[1], row[2], row[3], row[4], row[5]))
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def get_data(self, ev):
        self.txt_courseName.config(state="readonly")
        item = self.CourseTable.focus()
        if not item:
            return
        row = self.CourseTable.item(item, "values")
        if not row:
            return
        self.var_course.set(row[1])
        self.var_duration.set(row[2])
        self.var_charges.set(row[3])
        self.txt_description.delete("1.0", END)
        self.txt_description.insert(END, row[5])
        self.lbl_course_count.config(text=f"Selected Course Students: {row[4]}")

    def update(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                if self.var_course.get().strip() == "":
                    messagebox.showerror("Error", "Course Name should be required", parent=self.root)
                    return
                cur.execute("SELECT * FROM course WHERE name=?", (self.var_course.get().strip(),))
                if not cur.fetchone():
                    messagebox.showerror("Error", "Select Course from list", parent=self.root)
                    return
                cur.execute(
                    "UPDATE course SET duration=?,charges=?,description=? WHERE name=?",
                    (
                        self.var_duration.get().strip(),
                        self.var_charges.get().strip(),
                        self.txt_description.get("1.0", END).strip(),
                        self.var_course.get().strip(),
                    ),
                )
                con.commit()
            messagebox.showinfo("Success", "Course Updated Successfully", parent=self.root)
            self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def clear(self):
        self.var_course.set("")
        self.var_duration.set("")
        self.var_charges.set("")
        self.var_search.set("")
        self.lbl_course_count.config(text="Selected Course Students: 0")
        self.txt_description.delete("1.0", END)
        self.txt_courseName.config(state=NORMAL)
        self.show()

    def delete(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                if self.var_course.get().strip() == "":
                    messagebox.showerror("Error", "Course Name should be required", parent=self.root)
                    return
                cur.execute("SELECT cid FROM course WHERE name=?", (self.var_course.get().strip(),))
                row = cur.fetchone()
                if not row:
                    messagebox.showerror("Error", "Please select course from the list", parent=self.root)
                    return
                if messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root):
                    cid = row[0]
                    cur.execute("DELETE FROM enrollment WHERE cid=?", (cid,))
                    cur.execute("DELETE FROM result WHERE course=?", (self.var_course.get().strip(),))
                    cur.execute("DELETE FROM course WHERE cid=?", (cid,))
                    con.commit()
                    messagebox.showinfo("Delete", "Course Deleted Successfully", parent=self.root)
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)


class Student:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Result Management System")
        self.root.geometry("1200x700+200+120")
        self.root.config(bg="white")
        self.root.focus_force()

        self.var_sid = StringVar()
        self.var_roll = StringVar()
        self.var_name = StringVar()
        self.var_email = StringVar()
        self.var_gender = StringVar()
        self.var_dob = StringVar()
        self.var_contact = StringVar()
        self.var_a_date = StringVar()
        self.var_class_name = StringVar()
        self.var_section = StringVar()
        self.var_state = StringVar()
        self.var_city = StringVar()
        self.var_pin = StringVar()
        self.var_search = StringVar()

        self.course_list = []
        self.fetch_course_list()

        Label(
            self.root,
            text="Manage Student Details",
            font=("goudy old style", 20, "bold"),
            bg="#033054",
            fg="white",
        ).place(x=10, y=15, width=1180, height=35)

        Label(self.root, text="Roll No.", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=60)
        self.txt_roll = Entry(self.root, textvariable=self.var_roll, font=("goudy old style", 15, "bold"), bg="lightyellow")
        self.txt_roll.place(x=150, y=60, width=200)

        Label(self.root, text="Name", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=100)
        Entry(self.root, textvariable=self.var_name, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=150, y=100, width=200)
        Label(self.root, text="Email", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=140)
        Entry(self.root, textvariable=self.var_email, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=150, y=140, width=200)

        Label(self.root, text="Gender", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=180)
        self.txt_gender = ttk.Combobox(
            self.root,
            textvariable=self.var_gender,
            values=("Select", "Male", "Female", "Other"),
            font=("goudy old style", 15, "bold"),
            state="readonly",
            justify=CENTER,
        )
        self.txt_gender.place(x=150, y=180, width=200)
        self.txt_gender.current(0)

        Label(self.root, text="D.O.B.", font=("goudy old style", 15, "bold"), bg="white").place(x=360, y=60)
        Entry(self.root, textvariable=self.var_dob, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=480, y=60, width=200)
        Label(self.root, text="Contact", font=("goudy old style", 15, "bold"), bg="white").place(x=360, y=100)
        Entry(self.root, textvariable=self.var_contact, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=480, y=100, width=200)
        Label(self.root, text="Admission", font=("goudy old style", 15, "bold"), bg="white").place(x=360, y=140)
        Entry(self.root, textvariable=self.var_a_date, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=480, y=140, width=200)
        Label(self.root, text="Class", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=220)
        Entry(self.root, textvariable=self.var_class_name, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=150, y=220, width=150)
        Label(self.root, text="Section", font=("goudy old style", 15, "bold"), bg="white").place(x=310, y=220)
        Entry(self.root, textvariable=self.var_section, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=400, y=220, width=90)
        Label(self.root, text="State", font=("goudy old style", 15, "bold"), bg="white").place(x=500, y=220)
        Entry(self.root, textvariable=self.var_state, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=580, y=220, width=110)
        Label(self.root, text="City", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=260)
        Entry(self.root, textvariable=self.var_city, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=150, y=260, width=150)
        Label(self.root, text="Pin", font=("goudy old style", 15, "bold"), bg="white").place(x=310, y=260)
        Entry(self.root, textvariable=self.var_pin, font=("goudy old style", 15, "bold"), bg="lightyellow").place(x=380, y=260, width=120)
        Label(self.root, text="Address", font=("goudy old style", 15, "bold"), bg="white").place(x=10, y=300)
        self.txt_address = Text(self.root, font=("goudy old style", 15, "bold"), bg="lightyellow")
        self.txt_address.place(x=150, y=300, width=540, height=80)

        Button(self.root, text="Save", command=self.add, font=("goudy old style", 15, "bold"), bg="#2196f3", fg="white").place(
            x=150, y=400, width=110, height=40
        )
        Button(self.root, text="Update", command=self.update, font=("goudy old style", 15, "bold"), bg="#4caf50", fg="white").place(
            x=270, y=400, width=110, height=40
        )
        Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 15, "bold"), bg="#f44336", fg="white").place(
            x=390, y=400, width=110, height=40
        )
        Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 15, "bold"), bg="#607d8b", fg="white").place(
            x=510, y=400, width=110, height=40
        )

        Label(self.root, text="Roll No.", font=("goudy old style", 15, "bold"), bg="white").place(x=720, y=60)
        Entry(self.root, textvariable=self.var_search, font=("goudy old style", 15, "bold"), bg="lightyellow").place(
            x=870, y=60, width=180
        )
        Button(self.root, text="Search", command=self.search, font=("goudy old style", 15, "bold"), bg="#03a9f4", fg="white").place(
            x=1070, y=60, width=120, height=28
        )

        Label(self.root, text="Available Courses", font=("goudy old style", 12, "bold"), bg="white").place(x=720, y=100)
        self.cmb_course = ttk.Combobox(self.root, values=self.course_list, font=("goudy old style", 12), state="readonly")
        self.cmb_course.place(x=720, y=130, width=240)
        if self.course_list:
            self.cmb_course.current(0)

        Button(self.root, text="Add Course ->", command=self.add_enrollment, font=("goudy old style", 12), bg="#2196f3", fg="white").place(
            x=980, y=128, width=120, height=28
        )
        Button(self.root, text="<- Remove", command=self.remove_enrollment, font=("goudy old style", 12), bg="#f44336", fg="white").place(
            x=980, y=168, width=120, height=28
        )

        Label(self.root, text="Enrolled Courses", font=("goudy old style", 12, "bold"), bg="white").place(x=720, y=200)
        self.lst_enrolled = Listbox(self.root, selectmode=SINGLE, font=("goudy old style", 12), bd=2, relief=RIDGE)
        self.lst_enrolled.place(x=720, y=230, width=380, height=200)

        self.C_Frame = Frame(self.root, bd=2, relief=RIDGE)
        self.C_Frame.place(x=720, y=440, width=460, height=230)
        scrolly = Scrollbar(self.C_Frame, orient=VERTICAL)
        scrollx = Scrollbar(self.C_Frame, orient=HORIZONTAL)
        self.StudentTable = ttk.Treeview(
            self.C_Frame,
            columns=("sid", "roll", "name", "class_name", "section", "course"),
            xscrollcommand=scrollx.set,
            yscrollcommand=scrolly.set,
        )
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.StudentTable.xview)
        scrolly.config(command=self.StudentTable.yview)
        self.StudentTable.heading("sid", text="ID")
        self.StudentTable.heading("roll", text="Roll No.")
        self.StudentTable.heading("name", text="Name")
        self.StudentTable.heading("class_name", text="Class")
        self.StudentTable.heading("section", text="Section")
        self.StudentTable.heading("course", text="Course(s)")
        self.StudentTable["show"] = "headings"
        self.StudentTable.column("sid", width=55)
        self.StudentTable.column("roll", width=80)
        self.StudentTable.column("name", width=140)
        self.StudentTable.column("class_name", width=100)
        self.StudentTable.column("section", width=90)
        self.StudentTable.column("course", width=240)
        self.StudentTable.pack(fill=BOTH, expand=1)
        self.StudentTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def fetch_course_list(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT name FROM course ORDER BY name")
                rows = cur.fetchall()
                self.course_list = [r[0] for r in rows]
        except Exception as ex:
            messagebox.showerror("Error", f"Error fetching courses: {ex}", parent=self.root)

    def refresh_course_dropdown(self):
        self.fetch_course_list()
        self.cmb_course.config(values=self.course_list)
        if self.course_list and not self.cmb_course.get():
            self.cmb_course.current(0)

    def add_enrollment(self):
        course_name = self.cmb_course.get().strip()
        if not course_name:
            messagebox.showerror("Error", "Select a course to add", parent=self.root)
            return
        if course_name in self.lst_enrolled.get(0, END):
            messagebox.showwarning("Warning", "Course already in enrolled list", parent=self.root)
            return
        self.lst_enrolled.insert(END, course_name)

    def remove_enrollment(self):
        selected = self.lst_enrolled.curselection()
        if not selected:
            messagebox.showerror("Error", "Select an enrolled course to remove", parent=self.root)
            return
        self.lst_enrolled.delete(selected[0])

    def add(self):
        if self.var_roll.get().strip() == "":
            messagebox.showerror("Error", "Roll Number should be required", parent=self.root)
            return
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute(
                    "SELECT 1 FROM student WHERE roll=? AND COALESCE(class_name, '')=? AND COALESCE(section, '')=?",
                    (self.var_roll.get().strip(), self.var_class_name.get().strip(), self.var_section.get().strip()),
                )
                if cur.fetchone():
                    messagebox.showerror("Error", "Roll Number already present for this class and section", parent=self.root)
                    return
                cur.execute(
                    """
                    INSERT INTO student
                    (roll, name, email, gender, dob, contact, admission, course, state, city, pin, address, class_name, section)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        self.var_roll.get().strip(),
                        self.var_name.get().strip(),
                        self.var_email.get().strip(),
                        self.var_gender.get().strip(),
                        self.var_dob.get().strip(),
                        self.var_contact.get().strip(),
                        self.var_a_date.get().strip(),
                        "",
                        self.var_state.get().strip(),
                        self.var_city.get().strip(),
                        self.var_pin.get().strip(),
                        self.txt_address.get("1.0", END).strip(),
                        self.var_class_name.get().strip(),
                        self.var_section.get().strip(),
                    ),
                )
                sid = cur.lastrowid
                for cname in self.lst_enrolled.get(0, END):
                    cur.execute("SELECT cid FROM course WHERE name=?", (cname,))
                    course_row = cur.fetchone()
                    if course_row:
                        cur.execute(
                            "INSERT OR IGNORE INTO enrollment (sid, cid) VALUES (?, ?)",
                            (sid, course_row[0]),
                        )
                con.commit()
            messagebox.showinfo("Success", "Student Added Successfully", parent=self.root)
            self.show()
            self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def search(self):
        roll = self.var_search.get().strip()
        if roll == "":
            messagebox.showerror("Error", "Enter roll to search", parent=self.root)
            return
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT sid FROM student WHERE roll=? ORDER BY sid", (roll,))
                matches = cur.fetchall()
                if not matches:
                    messagebox.showerror("Error", "No student found", parent=self.root)
                    return
                if len(matches) > 1:
                    messagebox.showinfo("Select Student", "More than one student has this roll number. Select the correct row from the list.", parent=self.root)
                    return
                self.load_student(matches[0][0])
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def load_student(self, sid):
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT sid, roll, name, email, gender, dob, contact, admission, course, state, city, pin, address, class_name, section FROM student WHERE sid=?", (sid,))
                row = cur.fetchone()
                if not row:
                    messagebox.showerror("Error", "No student found", parent=self.root)
                    return
                self.var_sid.set(row[0])
                self.var_roll.set(row[1] or "")
                self.var_name.set(row[2] or "")
                self.var_email.set(row[3] or "")
                self.var_gender.set(row[4] or "Select")
                self.var_dob.set(row[5] or "")
                self.var_contact.set(row[6] or "")
                self.var_a_date.set(row[7] or "")
                self.var_state.set(row[9] or "")
                self.var_city.set(row[10] or "")
                self.var_pin.set(row[11] or "")
                self.txt_address.delete("1.0", END)
                self.txt_address.insert(END, row[12] or "")
                self.var_class_name.set(row[13] or "")
                self.var_section.set(row[14] or "")
                self.lst_enrolled.delete(0, END)
                cur.execute(
                    """
                    SELECT c.name FROM enrollment e
                    JOIN course c ON e.cid = c.cid
                    WHERE e.sid = ? ORDER BY c.name
                    """,
                    (sid,),
                )
                for enrolled in cur.fetchall():
                    self.lst_enrolled.insert(END, enrolled[0])
            self.txt_roll.config(state="readonly")
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def show(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute(
                    """
                    SELECT s.sid, s.roll, s.name, COALESCE(s.class_name, ''), COALESCE(s.section, ''),
                           COALESCE(GROUP_CONCAT(c.name, ', '), '')
                    FROM student s
                    LEFT JOIN enrollment e ON s.sid = e.sid
                    LEFT JOIN course c ON e.cid = c.cid
                    GROUP BY s.sid, s.roll, s.name, s.class_name, s.section
                    ORDER BY CAST(s.roll AS INTEGER), s.roll, s.class_name, s.section
                    """
                )
                rows = cur.fetchall()
            self.StudentTable.delete(*self.StudentTable.get_children())
            for row in rows:
                self.StudentTable.insert("", END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def get_data(self, ev):
        item = self.StudentTable.focus()
        if not item:
            return
        values = self.StudentTable.item(item, "values")
        if not values:
            return
        self.var_search.set(values[1])
        self.load_student(values[0])

    def update(self):
        if self.var_roll.get().strip() == "":
            messagebox.showerror("Error", "Roll No. should be required", parent=self.root)
            return
        try:
            with db_connect() as con:
                cur = con.cursor()
                sid = self.var_sid.get().strip()
                cur.execute("SELECT * FROM student WHERE sid=?", (sid,))
                if not cur.fetchone():
                    messagebox.showerror("Error", "Select Student from list", parent=self.root)
                    return
                cur.execute(
                    "SELECT 1 FROM student WHERE sid<>? AND roll=? AND COALESCE(class_name, '')=? AND COALESCE(section, '')=?",
                    (sid, self.var_roll.get().strip(), self.var_class_name.get().strip(), self.var_section.get().strip()),
                )
                if cur.fetchone():
                    messagebox.showerror("Error", "Roll Number already present for this class and section", parent=self.root)
                    return
                cur.execute(
                    """
                    UPDATE student SET name=?, email=?, gender=?, dob=?, contact=?, admission=?, state=?, city=?, pin=?, address=?, class_name=?, section=?
                    WHERE sid=?
                    """,
                    (
                        self.var_name.get().strip(),
                        self.var_email.get().strip(),
                        self.var_gender.get().strip(),
                        self.var_dob.get().strip(),
                        self.var_contact.get().strip(),
                        self.var_a_date.get().strip(),
                        self.var_state.get().strip(),
                        self.var_city.get().strip(),
                        self.var_pin.get().strip(),
                        self.txt_address.get("1.0", END).strip(),
                        self.var_class_name.get().strip(),
                        self.var_section.get().strip(),
                        sid,
                    ),
                )
                cur.execute("DELETE FROM enrollment WHERE sid=?", (sid,))
                for cname in self.lst_enrolled.get(0, END):
                    cur.execute("SELECT cid FROM course WHERE name=?", (cname,))
                    course_row = cur.fetchone()
                    if course_row:
                        cur.execute(
                            "INSERT OR IGNORE INTO enrollment (sid, cid) VALUES (?, ?)",
                            (sid, course_row[0]),
                        )
                con.commit()
            messagebox.showinfo("Success", "Student Updated Successfully", parent=self.root)
            self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def delete(self):
        if self.var_sid.get().strip() == "":
            messagebox.showerror("Error", "Roll No should be required", parent=self.root)
            return
        try:
            with db_connect() as con:
                cur = con.cursor()
                sid = self.var_sid.get().strip()
                cur.execute("SELECT * FROM student WHERE sid=?", (sid,))
                if not cur.fetchone():
                    messagebox.showerror("Error", "Please select student from the list", parent=self.root)
                    return
                if messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root):
                    cur.execute("DELETE FROM enrollment WHERE sid=?", (sid,))
                    cur.execute("DELETE FROM result WHERE sid=?", (sid,))
                    cur.execute("DELETE FROM users WHERE sid=?", (sid,))
                    cur.execute("DELETE FROM student WHERE sid=?", (sid,))
                    con.commit()
            messagebox.showinfo("Delete", "Student Deleted Successfully", parent=self.root)
            self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def clear(self):
        self.var_roll.set("")
        self.var_sid.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_gender.set("Select")
        self.var_dob.set("")
        self.var_contact.set("")
        self.var_a_date.set("")
        self.var_class_name.set("")
        self.var_section.set("")
        self.var_state.set("")
        self.var_city.set("")
        self.var_pin.set("")
        self.var_search.set("")
        self.txt_address.delete("1.0", END)
        self.txt_roll.config(state=NORMAL)
        self.lst_enrolled.delete(0, END)
        self.refresh_course_dropdown()
        self.show()


class Result:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Result Management System")
        self.root.geometry("1280x520+160+220")
        self.root.config(bg="white")
        self.root.focus_force()

        self.var_name = StringVar()
        self.var_roll = StringVar()
        self.var_class_name = StringVar()
        self.var_section = StringVar()
        self.var_course = StringVar()
        self.var_subject = StringVar()
        self.var_marks = StringVar()
        self.var_full_marks = StringVar()
        self.roll_list = []
        self.fetch_roll()

        Label(
            self.root,
            text="Manage Results (Subject-wise)",
            font=("goudy old style", 20, "bold"),
            bg="orange",
            fg="#262626",
        ).place(x=10, y=15, width=1180, height=50)

        Label(self.root, text="Select Student", font=("goudy old style", 20, "bold"), bg="white").place(x=50, y=100)
        Label(self.root, text="Name", font=("goudy old style", 20, "bold"), bg="white").place(x=50, y=160)
        Label(self.root, text="Class", font=("goudy old style", 20, "bold"), bg="white").place(x=50, y=220)
        Label(self.root, text="Section", font=("goudy old style", 20, "bold"), bg="white").place(x=50, y=280)
        Label(self.root, text="Course", font=("goudy old style", 20, "bold"), bg="white").place(x=50, y=340)
        Label(self.root, text="Subject", font=("goudy old style", 20, "bold"), bg="white").place(x=50, y=400)
        Label(self.root, text="Marks Obtained", font=("goudy old style", 20, "bold"), bg="white").place(x=610, y=160)
        Label(self.root, text="Full Marks", font=("goudy old style", 20, "bold"), bg="white").place(x=610, y=220)

        self.txt_student = ttk.Combobox(
            self.root,
            textvariable=self.var_roll,
            values=self.roll_list,
            font=("goudy old style", 15, "bold"),
            state="readonly",
            justify=CENTER,
        )
        self.txt_student.place(x=260, y=100, width=200)
        self.txt_student.set("Select")
        Button(self.root, text="Search", command=self.search_student, font=("goudy old style", 15, "bold"), bg="#03a9f4", fg="white").place(
            x=480, y=100, width=100, height=28
        )

        Entry(self.root, textvariable=self.var_name, font=("goudy old style", 20, "bold"), bg="lightyellow", state="readonly").place(
            x=260, y=160, width=320
        )
        Entry(self.root, textvariable=self.var_class_name, font=("goudy old style", 20, "bold"), bg="lightyellow", state="readonly").place(
            x=260, y=220, width=320
        )
        Entry(self.root, textvariable=self.var_section, font=("goudy old style", 20, "bold"), bg="lightyellow", state="readonly").place(
            x=260, y=280, width=320
        )
        self.txt_course = ttk.Combobox(
            self.root,
            textvariable=self.var_course,
            values=[],
            font=("goudy old style", 20, "bold"),
            state="readonly",
            justify=CENTER,
        )
        self.txt_course.place(x=260, y=340, width=320)

        Entry(self.root, textvariable=self.var_subject, font=("goudy old style", 20, "bold"), bg="lightyellow").place(x=260, y=400, width=320)
        Entry(self.root, textvariable=self.var_marks, font=("goudy old style", 20, "bold"), bg="lightyellow").place(x=800, y=160, width=150)
        Entry(self.root, textvariable=self.var_full_marks, font=("goudy old style", 20, "bold"), bg="lightyellow").place(x=800, y=220, width=150)

        Button(self.root, text="Submit", command=self.add, font=("goudy old style", 15), bg="lightgreen").place(x=300, y=450, width=120, height=35)
        Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 15), bg="lightgray").place(x=430, y=450, width=120, height=35)

        result_image = os.path.join(IMAGES_DIR, "result.jpg")
        if os.path.exists(result_image):
            self.bg_img = Image.open(result_image).resize((290, 240))
            self.bg_img = ImageTk.PhotoImage(self.bg_img)
            Label(self.root, image=self.bg_img, bd=2, relief=RIDGE).place(x=965, y=130)

    def fetch_roll(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT sid, roll, name, COALESCE(class_name, ''), COALESCE(section, '') FROM student ORDER BY CAST(roll AS INTEGER), roll")
                rows = cur.fetchall()
                self.roll_list = [student_display(*r) for r in rows]
        except Exception as ex:
            messagebox.showerror("Error", f"Error fetching rolls: {ex}", parent=self.root)

    def search_student(self):
        sid = normalize_student_key(self.var_roll.get())
        if not sid:
            messagebox.showerror("Error", "Select a student roll", parent=self.root)
            return
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT roll, name, COALESCE(class_name, ''), COALESCE(section, '') FROM student WHERE sid=?", (sid,))
                row = cur.fetchone()
                if not row:
                    messagebox.showerror("Error", "Student not found", parent=self.root)
                    return
                self.var_name.set(row[1])
                self.var_class_name.set(row[2])
                self.var_section.set(row[3])
                cur.execute(
                    """
                    SELECT c.name FROM enrollment e
                    JOIN course c ON e.cid = c.cid
                    WHERE e.sid = ? ORDER BY c.name
                    """,
                    (sid,),
                )
                courses = [r[0] for r in cur.fetchall()]
                if not courses:
                    messagebox.showinfo("Info", "This student is not enrolled in any course. Add enrollment first.", parent=self.root)
                    self.txt_course.config(values=[])
                    self.var_course.set("")
                    return
                self.txt_course.config(values=courses)
                self.txt_course.set(courses[0])
        except Exception as ex:
            messagebox.showerror("Error", f"Error while searching: {ex}", parent=self.root)

    def add(self):
        sid = normalize_student_key(self.var_roll.get())
        if not sid:
            messagebox.showerror("Error", "Select a student roll first", parent=self.root)
            return
        if self.var_name.get().strip() == "":
            messagebox.showerror("Error", "Search the student first", parent=self.root)
            return
        course = self.var_course.get().strip()
        subject = self.var_subject.get().strip()
        marks = self.var_marks.get().strip()
        full = self.var_full_marks.get().strip()
        if course == "":
            messagebox.showerror("Error", "Select course for which you are adding result", parent=self.root)
            return
        if subject == "":
            messagebox.showerror("Error", "Subject is required", parent=self.root)
            return
        try:
            marks_i = int(marks)
            full_i = int(full)
            if full_i <= 0:
                raise ValueError("Full marks must be > 0")
        except Exception as ex:
            messagebox.showerror("Error", f"Invalid marks/full marks: {ex}", parent=self.root)
            return

        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT cid FROM course WHERE name=?", (course,))
                course_row = cur.fetchone()
                if not course_row:
                    messagebox.showerror("Error", "Selected course not found", parent=self.root)
                    return
                cur.execute("SELECT 1 FROM enrollment WHERE sid=? AND cid=?", (sid, course_row[0]))
                if not cur.fetchone():
                    messagebox.showerror("Error", "Student is not enrolled in this course. Add enrollment first.", parent=self.root)
                    return
                cur.execute("SELECT 1 FROM result WHERE sid=? AND course=? AND subject=?", (sid, course, subject))
                if cur.fetchone():
                    messagebox.showerror("Error", "Result for this subject already present for this student", parent=self.root)
                    return
                percent = (marks_i * 100.0) / full_i
                cur.execute(
                    """
                    INSERT INTO result (sid, name, course, subject, marks_ob, full_marks, per)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sid, self.var_name.get().strip(), course, subject, marks_i, full_i, percent),
                )
                con.commit()
            messagebox.showinfo("Success", "Result Added Successfully", parent=self.root)
            self.var_subject.set("")
            self.var_marks.set("")
            self.var_full_marks.set("")
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)

    def clear(self):
        self.var_roll.set("Select")
        self.var_name.set("")
        self.var_class_name.set("")
        self.var_section.set("")
        self.var_course.set("")
        self.var_subject.set("")
        self.var_marks.set("")
        self.var_full_marks.set("")


class Report:
    def __init__(self, root, read_only=False):
        self.root = root
        self.read_only = read_only
        self.root.title("Student Result Management System")
        self.root.geometry("1200x520+200+200")
        self.root.config(bg="white")
        self.root.focus_force()

        Label(
            self.root,
            text="View Student Results (Subject-wise)",
            font=("goudy old style", 20, "bold"),
            bg="orange",
            fg="#262626",
        ).place(x=10, y=15, width=1180, height=50)

        self.var_search = StringVar()
        self.var_class_filter = StringVar()
        self.var_section_filter = StringVar()
        self.selected_rid = ""

        Label(self.root, text="Search By Roll No.", font=("goudy old style", 16, "bold"), bg="white").place(x=200, y=90)
        Entry(self.root, textvariable=self.var_search, font=("goudy old style", 16), bg="lightyellow").place(x=380, y=90, width=180)
        Label(self.root, text="Class", font=("goudy old style", 16, "bold"), bg="white").place(x=580, y=90)
        Entry(self.root, textvariable=self.var_class_filter, font=("goudy old style", 16), bg="lightyellow").place(x=650, y=90, width=100)
        Label(self.root, text="Section", font=("goudy old style", 16, "bold"), bg="white").place(x=770, y=90)
        Entry(self.root, textvariable=self.var_section_filter, font=("goudy old style", 16), bg="lightyellow").place(x=860, y=90, width=80)
        Button(self.root, text="Search", command=self.search, font=("goudy old style", 14, "bold"), bg="#03a9f4", fg="white").place(
            x=960, y=90, width=90, height=30
        )
        Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 14, "bold"), bg="gray", fg="white").place(
            x=1060, y=90, width=90, height=30
        )

        Label(self.root, text="Roll No", font=("goudy old style", 14, "bold"), bg="white").place(x=50, y=150)
        Label(self.root, text="Name", font=("goudy old style", 14, "bold"), bg="white").place(x=250, y=150)
        Label(self.root, text="Class / Section", font=("goudy old style", 14, "bold"), bg="white").place(x=470, y=150)
        Label(self.root, text="Course(s)", font=("goudy old style", 14, "bold"), bg="white").place(x=720, y=150)
        Label(self.root, text="Overall %", font=("goudy old style", 14, "bold"), bg="white").place(x=950, y=150)
        Label(self.root, text="Status", font=("goudy old style", 14, "bold"), bg="white").place(x=1065, y=150)

        self.lbl_roll = Label(self.root, text="", font=("goudy old style", 14, "bold"), bg="white", bd=2, relief=GROOVE)
        self.lbl_roll.place(x=50, y=190, width=150, height=40)
        self.lbl_name = Label(self.root, text="", font=("goudy old style", 14, "bold"), bg="white", bd=2, relief=GROOVE)
        self.lbl_name.place(x=250, y=190, width=220, height=40)
        self.lbl_class_section = Label(self.root, text="", font=("goudy old style", 14, "bold"), bg="white", bd=2, relief=GROOVE)
        self.lbl_class_section.place(x=470, y=190, width=210, height=40)
        self.lbl_course = Label(self.root, text="", font=("goudy old style", 14, "bold"), bg="white", bd=2, relief=GROOVE)
        self.lbl_course.place(x=720, y=190, width=200, height=40)
        self.lbl_overall = Label(self.root, text="", font=("goudy old style", 14, "bold"), bg="white", bd=2, relief=GROOVE)
        self.lbl_overall.place(x=950, y=190, width=95, height=40)
        self.lbl_status = Label(self.root, text="", font=("goudy old style", 15, "bold"), bg="white", fg="white", bd=2, relief=GROOVE)
        self.lbl_status.place(x=1065, y=190, width=85, height=40)

        frame_table = Frame(self.root, bd=2, relief=RIDGE)
        frame_table.place(x=50, y=260, width=1100, height=220)

        cols = ("rid", "subject", "marks", "full", "per")
        self.ResultTable = ttk.Treeview(frame_table, columns=cols, show="headings")
        for col, text, width in zip(
            cols,
            ["ID", "Subject", "Marks Obtained", "Total Marks", "Percentage"],
            [40, 400, 150, 150, 150],
        ):
            self.ResultTable.heading(col, text=text)
            self.ResultTable.column(col, width=width)
        self.ResultTable.pack(fill=BOTH, expand=1)
        self.ResultTable.bind("<ButtonRelease-1>", self.on_select)

        if not self.read_only:
            Button(self.root, text="Delete Selected Subject Result", command=self.delete, font=("goudy old style", 14, "bold"), bg="red", fg="white").place(
                x=50, y=490, width=300, height=35
            )
        Button(self.root, text="Export Student PDF", command=self.export_student_pdf, font=("goudy old style", 14, "bold"), bg="#2196f3", fg="white").place(
            x=380 if not self.read_only else 50, y=490, width=260, height=35
        )

    def search(self):
        roll = self.var_search.get().strip()
        if not roll:
            messagebox.showerror("Error", "Roll No Required", parent=self.root)
            return
        try:
            with db_connect() as con:
                cur = con.cursor()
                query = """
                    SELECT r.*, COALESCE(s.class_name, ''), COALESCE(s.section, '')
                    FROM result r
                    LEFT JOIN student s ON r.sid = s.sid
                    WHERE s.roll=?
                """
                params = [roll]
                if self.var_class_filter.get().strip():
                    query += " AND COALESCE(s.class_name, '') = ?"
                    params.append(self.var_class_filter.get().strip())
                if self.var_section_filter.get().strip():
                    query += " AND COALESCE(s.section, '') = ?"
                    params.append(self.var_section_filter.get().strip())
                query += " ORDER BY r.rid"
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            if not rows:
                messagebox.showerror("Error", "No record found!", parent=self.root)
                self.clear_summary()
                return
            if len({r[1] for r in rows if r[1] is not None}) > 1:
                messagebox.showinfo("Select Student", "More than one student has this roll number. Please enter Class and Section also.", parent=self.root)
                self.clear_summary()
                return

            self.lbl_roll.config(text=roll)
            self.lbl_name.config(text=rows[0][2])
            class_name = rows[0][8] or ""
            section = rows[0][9] or ""
            if class_name and section:
                class_section = f"{class_name} / {section}"
            else:
                class_section = class_name or section
            self.lbl_class_section.config(text=class_section)
            self.lbl_course.config(text=", ".join(sorted({r[3] for r in rows if r[3]})))

            self.ResultTable.delete(*self.ResultTable.get_children())
            total_ob = 0
            total_full = 0
            for row in rows:
                total_ob += int(row[5])
                total_full += int(row[6])
                self.ResultTable.insert("", END, values=(row[0], row[4], row[5], row[6], f"{float(row[7]):.2f}"))
            overall = (total_ob * 100) / total_full if total_full else 0
            status = "PASS" if overall >= PASS_THRESHOLD else "FAIL"
            status_bg = "#2e7d32" if status == "PASS" else "#c62828"
            self.lbl_overall.config(text=f"{overall:.2f}%")
            self.lbl_status.config(text=status, bg=status_bg, fg="white")
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self.root)

    def on_select(self, event):
        values = self.ResultTable.item(self.ResultTable.focus(), "values")
        self.selected_rid = values[0] if values else ""

    def delete(self):
        if self.read_only:
            messagebox.showerror("Error", "Student login cannot delete any subject result", parent=self.root)
            return
        if not self.selected_rid:
            messagebox.showerror("Error", "Select a row to delete!", parent=self.root)
            return
        with db_connect() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM result WHERE rid=?", (self.selected_rid,))
            con.commit()
        messagebox.showinfo("Success", "Subject Result Deleted", parent=self.root)
        self.search()

    def clear_summary(self):
        self.lbl_roll.config(text="")
        self.lbl_name.config(text="")
        self.lbl_class_section.config(text="")
        self.lbl_course.config(text="")
        self.lbl_overall.config(text="")
        self.lbl_status.config(text="", bg="white", fg="white")
        self.ResultTable.delete(*self.ResultTable.get_children())

    def clear(self):
        self.var_search.set("")
        self.var_class_filter.set("")
        self.var_section_filter.set("")
        self.selected_rid = ""
        self.clear_summary()

    def export_student_pdf(self):
        roll = self.lbl_roll.cget("text").strip()
        if not roll:
            messagebox.showerror("Error", "Search student first!", parent=self.root)
            return
        with db_connect() as con:
            cur = con.cursor()
            query = """
                SELECT r.* FROM result r
                JOIN student s ON r.sid = s.sid
                WHERE s.roll=?
            """
            params = [roll]
            if self.var_class_filter.get().strip():
                query += " AND COALESCE(s.class_name, '')=?"
                params.append(self.var_class_filter.get().strip())
            if self.var_section_filter.get().strip():
                query += " AND COALESCE(s.section, '')=?"
                params.append(self.var_section_filter.get().strip())
            query += " ORDER BY r.rid"
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            cur.execute("SELECT COALESCE(class_name, ''), COALESCE(section, '') FROM student WHERE roll=?", (roll,))
            student_meta = cur.fetchone() or ("", "")
        if not rows:
            messagebox.showerror("Error", "No results found", parent=self.root)
            return

        total_ob = sum(int(r[5]) for r in rows)
        total_full = sum(int(r[6]) for r in rows)
        overall = (total_ob * 100) / total_full if total_full else 0
        status = "PASS" if overall >= PASS_THRESHOLD else "FAIL"

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "STUDENT RESULT MARKSHEET", ln=True, align="C")
        pdf.ln(5)

        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 8, f"Roll No : {roll}", ln=True)
        pdf.cell(0, 8, f"Name    : {rows[0][2]}", ln=True)
        pdf.cell(0, 8, f"Class   : {student_meta[0]}", ln=True)
        pdf.cell(0, 8, f"Section : {student_meta[1]}", ln=True)
        pdf.cell(0, 8, f"Courses : {', '.join(sorted({r[3] for r in rows if r[3]}))}", ln=True)
        pdf.cell(0, 8, f"Date    : {datetime.now().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(4)

        pdf.set_font("Arial", "B", 11)
        pdf.cell(15, 10, "SN", 1, 0, "C")
        pdf.cell(95, 10, "SUBJECT", 1, 0, "C")
        pdf.cell(40, 10, "MAX MARKS", 1, 0, "C")
        pdf.cell(40, 10, "OBTAINED", 1, 1, "C")

        pdf.set_font("Arial", "", 11)
        for index, row in enumerate(rows, start=1):
            pdf.cell(15, 8, str(index), 1, 0, "C")
            pdf.cell(95, 8, str(row[4]), 1)
            pdf.cell(40, 8, str(row[6]), 1, 0, "C")
            pdf.cell(40, 8, str(row[5]), 1, 1, "C")

        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"Total Marks : {total_ob} / {total_full}", ln=True)
        pdf.cell(0, 8, f"Percentage  : {overall:.2f}%", ln=True)
        pdf.cell(0, 8, f"Result      : {status}", ln=True)

        filename = os.path.join(REPORTS_DIR, f"{roll}_marksheet.pdf")
        pdf.output(filename)
        messagebox.showinfo("Success", f"PDF Saved:\n{filename}", parent=self.root)


class StudentLoginManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Create Student Login")
        self.root.geometry("900x470+260+220")
        self.root.config(bg="white")
        self.root.focus_force()

        self.var_uid = StringVar()
        self.var_student = StringVar()
        self.var_username = StringVar()
        self.var_password = StringVar()
        self.var_name_search = StringVar()
        self.student_list = []
        self.fetch_students()

        Label(self.root, text="Create Student Login ID", font=("goudy old style", 20, "bold"), bg="#033054", fg="white").place(x=10, y=15, width=880, height=40)
        self.lbl_status = Label(self.root, text="", font=("goudy old style", 12, "bold"), bg="white", fg="#033054")
        self.lbl_status.place(x=30, y=58, width=820, height=22)
        Label(self.root, text="Student", font=("goudy old style", 14, "bold"), bg="white").place(x=30, y=80)
        self.cmb_student = ttk.Combobox(self.root, textvariable=self.var_student, values=self.student_list, font=("goudy old style", 12), state="readonly")
        self.cmb_student.place(x=150, y=80, width=430, height=30)
        Label(self.root, text="Login ID", font=("goudy old style", 14, "bold"), bg="white").place(x=30, y=125)
        Entry(self.root, textvariable=self.var_username, font=("goudy old style", 14), bg="lightyellow").place(x=150, y=125, width=260, height=30)
        Label(self.root, text="Password", font=("goudy old style", 14, "bold"), bg="white").place(x=30, y=170)
        Entry(self.root, textvariable=self.var_password, font=("goudy old style", 14), bg="lightyellow").place(x=150, y=170, width=260, height=30)

        Button(self.root, text="Save", command=self.add, font=("goudy old style", 13, "bold"), bg="#2196f3", fg="white").place(x=150, y=220, width=100, height=35)
        Button(self.root, text="Create All", command=self.create_all_missing, font=("goudy old style", 13, "bold"), bg="#4caf50", fg="white").place(x=260, y=220, width=120, height=35)
        Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 13, "bold"), bg="#f44336", fg="white").place(x=390, y=220, width=100, height=35)
        Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 13, "bold"), bg="#607d8b", fg="white").place(x=500, y=220, width=100, height=35)

        Label(self.root, text="Search Name", font=("goudy old style", 13, "bold"), bg="white").place(x=620, y=83)
        Entry(self.root, textvariable=self.var_name_search, font=("goudy old style", 13), bg="lightyellow").place(x=720, y=82, width=145, height=28)
        Button(self.root, text="Search", command=self.search_by_name, font=("goudy old style", 12, "bold"), bg="#03a9f4", fg="white").place(x=620, y=120, width=105, height=30)
        Button(self.root, text="Show All", command=self.show_all, font=("goudy old style", 12, "bold"), bg="#607d8b", fg="white").place(x=740, y=120, width=105, height=30)

        frame = Frame(self.root, bd=2, relief=RIDGE)
        frame.place(x=30, y=280, width=840, height=165)
        self.LoginTable = ttk.Treeview(frame, columns=("uid", "student", "username", "password"), show="headings")
        for col, text, width in (("uid", "ID", 60), ("student", "Student", 430), ("username", "Login ID", 170), ("password", "Password", 170)):
            self.LoginTable.heading(col, text=text)
            self.LoginTable.column(col, width=width)
        self.LoginTable.pack(fill=BOTH, expand=1)
        self.LoginTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def fetch_students(self):
        with db_connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT s.sid, s.roll, s.name, COALESCE(s.class_name, ''), COALESCE(s.section, '')
                FROM student s
                LEFT JOIN users u ON u.sid = s.sid AND u.role='student'
                WHERE u.uid IS NULL
                ORDER BY CAST(s.roll AS INTEGER), s.roll
                """
            )
            self.student_list = [student_display(*row) for row in cur.fetchall()]

    def add(self):
        sid = normalize_student_key(self.var_student.get())
        username = self.var_username.get().strip()
        password = self.var_password.get().strip()
        if not sid or not username or not password:
            messagebox.showerror("Error", "Student, Login ID and Password are required", parent=self.root)
            return
        with db_connect() as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
            if cur.fetchone():
                messagebox.showerror("Error", "Login ID already exists", parent=self.root)
                return
            cur.execute("SELECT 1 FROM users WHERE role='student' AND sid=?", (sid,))
            if cur.fetchone():
                messagebox.showerror("Error", "This student already has a login ID", parent=self.root)
                return
            cur.execute("INSERT INTO users (username, password, role, sid) VALUES (?, ?, 'student', ?)", (username, password, sid))
            con.commit()
        messagebox.showinfo("Success", "Student login created", parent=self.root)
        self.clear()

    def make_unique_username(self, cur, base):
        username = base
        count = 1
        while True:
            cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
            if not cur.fetchone():
                return username
            count += 1
            username = f"{base}{count}"

    def create_all_missing(self):
        if not messagebox.askyesno("Confirm", "Create login IDs for all students who do not have one?", parent=self.root):
            return
        created = 0
        with db_connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT s.sid, s.roll
                FROM student s
                LEFT JOIN users u ON u.sid = s.sid AND u.role='student'
                WHERE u.uid IS NULL
                ORDER BY CAST(s.roll AS INTEGER), s.roll
                """
            )
            rows = cur.fetchall()
            for sid, roll in rows:
                username = self.make_unique_username(cur, f"student{sid}")
                password = f"roll{roll}{sid}"
                cur.execute("INSERT INTO users (username, password, role, sid) VALUES (?, ?, 'student', ?)", (username, password, sid))
                created += 1
            con.commit()
        messagebox.showinfo("Success", f"{created} student login ID(s) created", parent=self.root)
        self.clear()

    def populate_login_table(self, rows):
        self.LoginTable.delete(*self.LoginTable.get_children())
        for row in rows:
            self.LoginTable.insert("", END, values=(row[0], student_display(row[1], row[2], row[3], row[4], row[5]), row[6], row[7]))

    def show(self):
        with db_connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT u.uid, s.sid, s.roll, s.name, COALESCE(s.class_name, ''), COALESCE(s.section, ''), u.username, u.password
                FROM users u
                JOIN student s ON u.sid = s.sid
                WHERE u.role='student'
                ORDER BY u.uid
                """
            )
            rows = cur.fetchall()
        self.populate_login_table(rows)
        self.lbl_status.config(text=f"Students without login ID: {len(self.student_list)} | Login IDs created: {len(rows)}")

    def search_by_name(self):
        name = self.var_name_search.get().strip()
        if not name:
            messagebox.showerror("Error", "Enter student name to search", parent=self.root)
            return
        with db_connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT u.uid, s.sid, s.roll, s.name, COALESCE(s.class_name, ''), COALESCE(s.section, ''), u.username, u.password
                FROM users u
                JOIN student s ON u.sid = s.sid
                WHERE u.role='student' AND s.name LIKE ?
                ORDER BY s.name, u.uid
                """,
                (f"%{name}%",),
            )
            rows = cur.fetchall()
        self.populate_login_table(rows)
        if rows:
            self.lbl_status.config(text=f"Search results for '{name}': {len(rows)} login ID(s) found")
        else:
            self.lbl_status.config(text=f"No login found for '{name}'")
            messagebox.showinfo("Search", "No login found for this student name", parent=self.root)

    def show_all(self):
        self.var_name_search.set("")
        self.show()

    def get_data(self, event):
        values = self.LoginTable.item(self.LoginTable.focus(), "values")
        if values:
            self.var_uid.set(values[0])
            self.var_student.set(values[1])
            self.var_username.set(values[2])
            self.var_password.set(values[3])

    def delete(self):
        if not self.var_uid.get().strip():
            messagebox.showerror("Error", "Select a login from list", parent=self.root)
            return
        if messagebox.askyesno("Confirm", "Delete this student login?", parent=self.root):
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("DELETE FROM users WHERE uid=? AND role='student'", (self.var_uid.get().strip(),))
                con.commit()
            self.clear()

    def clear(self):
        self.var_uid.set("")
        self.var_student.set("")
        self.var_username.set("")
        self.var_password.set("")
        self.var_name_search.set("")
        self.fetch_students()
        self.cmb_student.config(values=self.student_list)
        self.show()


class StudentPortal:
    def __init__(self, root, current_user, on_logout=None):
        self.root = root
        self.current_user = current_user
        self.on_logout = on_logout
        self.sid = self.fetch_sid()

        self.root.title(f"{APP_TITLE} - Student Portal")
        self.root.geometry("1180x640+170+90")
        self.root.config(bg="#f4f0df")

        header = Frame(self.root, bg="#1f1f1f", height=70)
        header.pack(fill=X)

        Label(
            header,
            text="Student Result Portal",
            font=("goudy old style", 26, "bold"),
            bg="#1f1f1f",
            fg="#f7c948",
        ).place(x=25, y=14)

        Label(
            header,
            text=f"Logged in as: {current_user}",
            font=("goudy old style", 13),
            bg="#1f1f1f",
            fg="white",
        ).place(x=28, y=44)

        Label(
            header,
            text="Result viewing area for students",
            font=("goudy old style", 12, "bold"),
            bg="#1f1f1f",
            fg="#d6b04a",
        ).place(x=330, y=25)

        Button(
            header,
            text="Logout",
            command=self.logout,
            font=("goudy old style", 13, "bold"),
            bg="#f7c948",
            fg="#1f1f1f",
            bd=0,
            cursor="hand2",
        ).place(x=1040, y=16, width=110, height=36)

        body = Frame(self.root, bg="#f4f0df")
        body.pack(fill=BOTH, expand=True, padx=24, pady=24)

        left = Frame(body, bg="#252525", bd=2, relief=RIDGE)
        left.place(x=0, y=0, width=360, height=500)

        Label(
            left,
            text="Student Access Panel",
            font=("goudy old style", 22, "bold"),
            bg="#252525",
            fg="#f7c948",
        ).place(x=28, y=28)

        Label(
            left,
            text="This login is limited to result viewing.\nSearch by roll number, check subject marks, and export the PDF marksheet.",
            font=("goudy old style", 14),
            justify=LEFT,
            bg="#252525",
            fg="#f5f5f5",
        ).place(x=28, y=82)

        Button(
            left,
            text="View Result",
            command=self.open_report,
            font=("goudy old style", 16, "bold"),
            bg="#f7c948",
            fg="#1f1f1f",
            bd=0,
            cursor="hand2",
        ).place(x=30, y=190, width=290, height=48)

        Button(
            left,
            text="Exit",
            command=self.root.destroy,
            font=("goudy old style", 16, "bold"),
            bg="#d9534f",
            fg="white",
            bd=0,
            cursor="hand2",
        ).place(x=30, y=252, width=290, height=48)

        right = Frame(body, bg="#d9c47e", bd=2, relief=RIDGE)
        right.place(x=390, y=0, width=740, height=500)

        Label(
            right,
            text="Result Dashboard",
            font=("goudy old style", 28, "bold"),
            bg="#d9c47e",
            fg="#2b2110",
        ).place(x=34, y=34)

        Label(
            right,
            text="This screen is designed for college presentation and school use.\nIt clearly separates student access from teacher administration.",
            font=("goudy old style", 16),
            justify=LEFT,
            bg="#d9c47e",
            fg="#2b2110",
        ).place(x=34, y=95)

        stats = Frame(right, bg="#2b2110")
        stats.place(x=34, y=200, width=670, height=220)

        total_results = self.fetch_total_results()
        Label(
            stats,
            text=f"Total Results in Database\n[ {total_results} ]",
            font=("goudy old style", 24, "bold"),
            bg="#2b2110",
            fg="#f7c948",
        ).place(relx=0.5, rely=0.5, anchor=CENTER)

    def fetch_total_results(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                if self.sid:
                    cur.execute("SELECT COUNT(*) FROM result WHERE sid=?", (self.sid,))
                else:
                    cur.execute("SELECT COUNT(*) FROM result")
                return cur.fetchone()[0]
        except Exception:
            return 0

    def fetch_sid(self):
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT sid FROM users WHERE username=? AND role='student'", (self.current_user,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def open_report(self):
        report = Report(Toplevel(self.root), read_only=True)
        if self.sid:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT roll, COALESCE(class_name, ''), COALESCE(section, '') FROM student WHERE sid=?", (self.sid,))
                row = cur.fetchone()
            if row:
                report.var_search.set(row[0])
                report.var_class_filter.set(row[1])
                report.var_section_filter.set(row[2])
                report.search()

    def logout(self):
        if self.on_logout:
            self.on_logout()


class RMS:
    def __init__(self, root, current_user="teacher", on_logout=None):
        self.root = root
        self.current_user = current_user
        self.on_logout = on_logout
        self.root.title("Student Result Management System")
        self.root.geometry("1350x700+110+80")
        self.root.config(bg="white")
        self.dark_mode = False
        self.closed = False

        logo_path = os.path.join(IMAGES_DIR, "logo_p.png")
        self.logo_dash = ImageTk.PhotoImage(file=logo_path) if os.path.exists(logo_path) else None

        Label(
            self.root,
            text=APP_TITLE,
            compound=LEFT,
            padx=10,
            image=self.logo_dash,
            font=("goudy old style", 20, "bold"),
            bg="#033054",
            fg="white",
        ).place(x=0, y=0, relwidth=1, height=50)

        menu_frame = LabelFrame(self.root, text="Teacher Control Panel", font=("times new roman", 15), bg="white")
        menu_frame.place(x=10, y=70, width=1330, height=80)

        Button(menu_frame, text="Course", command=self.add_course, font=("goudy old style", 14, "bold"), bg="#0b5377", fg="white").place(
            x=20, y=5, width=155, height=40
        )
        Button(menu_frame, text="Student", command=self.add_student, font=("goudy old style", 14, "bold"), bg="#0b5377", fg="white").place(
            x=185, y=5, width=155, height=40
        )
        Button(menu_frame, text="Result", command=self.add_result, font=("goudy old style", 14, "bold"), bg="#0b5377", fg="white").place(
            x=350, y=5, width=155, height=40
        )
        Button(menu_frame, text="View Result", command=self.add_report, font=("goudy old style", 14, "bold"), bg="#0b5377", fg="white").place(
            x=515, y=5, width=155, height=40
        )
        Button(menu_frame, text="Student Login", command=self.add_student_login, font=("goudy old style", 14, "bold"), bg="#0b5377", fg="white").place(
            x=680, y=5, width=175, height=40
        )
        Button(menu_frame, text="Dark Mode", command=self.toggle_theme, font=("goudy old style", 14, "bold"), bg="#0b5377", fg="white").place(
            x=865, y=5, width=155, height=40
        )
        Button(menu_frame, text="Logout", command=self.logout, font=("goudy old style", 14, "bold"), bg="#0b5377", fg="white").place(
            x=1030, y=5, width=130, height=40
        )
        Button(menu_frame, text="Exit", command=self.exit_app, font=("goudy old style", 14, "bold"), bg="#0b5377", fg="white").place(
            x=1170, y=5, width=130, height=40
        )

        Label(
            self.root,
            text=f"Teacher Login: {self.current_user}",
            font=("goudy old style", 13, "bold"),
            bg="white",
            fg="#033054",
        ).place(x=15, y=155)

        Label(
            self.root,
            text="Manage course, student, result, report, class, and section data from one dashboard.",
            font=("goudy old style", 12, "bold"),
            bg="white",
            fg="#6b5a14",
        ).place(x=15, y=178)

        bg_path = os.path.join(IMAGES_DIR, "bg.png")
        self.bg_img = None
        if os.path.exists(bg_path):
            self.bg_img = Image.open(bg_path).resize((920, 350))
            self.bg_img = ImageTk.PhotoImage(self.bg_img)
            Label(self.root, image=self.bg_img).place(x=400, y=180, width=920, height=350)

        self.lbl_course = Label(self.root, text="Total Courses\n[ 0 ]", font=("goudy old style", 20), bd=10, relief=RIDGE, bg="#e43b06", fg="white")
        self.lbl_course.place(x=400, y=540, width=300, height=100)
        self.lbl_student = Label(self.root, text="Total Students\n[ 0 ]", font=("goudy old style", 20), bd=10, relief=RIDGE, bg="#0676ad", fg="white")
        self.lbl_student.place(x=710, y=540, width=300, height=100)
        self.lbl_result = Label(self.root, text="Total Results\n[ 0 ]", font=("goudy old style", 20), bd=10, relief=RIDGE, bg="#038074", fg="white")
        self.lbl_result.place(x=1020, y=540, width=300, height=100)

        self.lbl = Label(self.root, text="\nClock", font=("Book Antiqua", 25, "bold"), fg="white", compound=BOTTOM, bg="#081923", bd=0)
        self.lbl.place(x=10, y=180, height=450, width=350)
        self.working()

        Label(
            self.root,
            text=f"{APP_TITLE} | College Demo Project",
            font=("goudy old style", 12),
            bg="#262626",
            fg="white",
        ).pack(side=BOTTOM, fill=X)

        self.update_details()

    def add_course(self):
        Course(Toplevel(self.root))

    def add_student(self):
        Student(Toplevel(self.root))

    def add_result(self):
        Result(Toplevel(self.root))

    def add_report(self):
        Report(Toplevel(self.root), read_only=False)

    def add_student_login(self):
        StudentLoginManager(Toplevel(self.root))

    def exit_app(self):
        if messagebox.askyesno("Confirm", "Do you really want to exit?", parent=self.root):
            self.closed = True
            self.root.destroy()

    def logout(self):
        if messagebox.askyesno("Confirm", "Do you want to logout?", parent=self.root):
            self.closed = True
            if self.on_logout:
                self.on_logout()

    def clock_image(self, hr, min_, sec_):
        clock = Image.new("RGB", (400, 400), (8, 25, 35))
        draw = ImageDraw.Draw(clock)
        dial_path = os.path.join(IMAGES_DIR, "c.png")
        if os.path.exists(dial_path):
            bg = Image.open(dial_path).resize((300, 300))
            clock.paste(bg, (50, 50))

        ox, oy = 200, 200
        draw.line((ox, oy, ox + 50 * sin(radians(hr)), oy - 50 * cos(radians(hr))), fill="#DF005E", width=4)
        draw.line((ox, oy, ox + 80 * sin(radians(min_)), oy - 80 * cos(radians(min_))), fill="white", width=3)
        draw.line((ox, oy, ox + 100 * sin(radians(sec_)), oy - 100 * cos(radians(sec_))), fill="yellow", width=2)
        draw.ellipse((195, 195, 210, 210), fill="#1AD5D5")
        return clock

    def working(self):
        if self.closed or not self.lbl.winfo_exists():
            return
        now = datetime.now()
        clock = self.clock_image((now.hour / 12) * 360, (now.minute / 60) * 360, (now.second / 60) * 360)
        self.img = ImageTk.PhotoImage(clock)
        self.lbl.config(image=self.img)
        self.lbl.after(1000, self.working)

    def update_details(self):
        if self.closed or not self.lbl_course.winfo_exists():
            return
        try:
            with db_connect() as con:
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM course")
                courses = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM student")
                students = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM result")
                results = cur.fetchone()[0]
            self.lbl_course.config(text=f"Total Courses\n[{courses}]")
            self.lbl_student.config(text=f"Total Students\n[{students}]")
            self.lbl_result.config(text=f"Total Results\n[{results}]")
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to: {str(ex)}", parent=self.root)
        self.root.after(1500, self.update_details)

    def toggle_theme(self):
        if not self.dark_mode:
            self.root.config(bg="#1e1e1e")
            self.lbl.config(bg="#0f0f0f", fg="white")
            self.lbl_course.config(bg="#444444")
            self.lbl_student.config(bg="#555555")
            self.lbl_result.config(bg="#666666")
            self.dark_mode = True
        else:
            self.root.config(bg="white")
            self.lbl.config(bg="#081923", fg="white")
            self.lbl_course.config(bg="#e43b06")
            self.lbl_student.config(bg="#0676ad")
            self.lbl_result.config(bg="#038074")
            self.dark_mode = False


def main():
    create_db()
    root = Tk()
    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

