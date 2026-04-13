import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import pytz
import plotly.express as px
import os
import hashlib
import shutil
import zipfile
import io

# ==================== 1. ڈیٹا بیس سیٹ اپ ====================
DB_NAME = 'old.jamia_millia_banat_v1.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def column_exists(table, column):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in c.fetchall()]
    conn.close()
    return column in columns

def add_column_if_not_exists(table, column, col_type):
    if not column_exists(table, column):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            conn.commit()
        except:
            pass
        conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        password TEXT
    )''')
    add_column_if_not_exists('teachers', 'dept', 'TEXT')
    add_column_if_not_exists('teachers', 'phone', 'TEXT')
    add_column_if_not_exists('teachers', 'address', 'TEXT')
    add_column_if_not_exists('teachers', 'id_card', 'TEXT')
    add_column_if_not_exists('teachers', 'photo', 'TEXT')
    add_column_if_not_exists('teachers', 'joining_date', 'DATE')
    
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        father_name TEXT,
        mother_name TEXT,
        dob DATE,
        admission_date DATE,
        exit_date DATE,
        exit_reason TEXT,
        id_card TEXT,
        photo TEXT,
        phone TEXT,
        address TEXT,
        teacher_name TEXT,
        dept TEXT,
        class TEXT,
        section TEXT,
        roll_no TEXT
    )''')
    add_column_if_not_exists('students', 'roll_no', 'TEXT')
    
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        student_id INTEGER,
        t_name TEXT,
        surah TEXT,
        a_from TEXT,
        a_to TEXT,
        sq_p TEXT,
        sq_a INTEGER,
        sq_m INTEGER,
        m_p TEXT,
        m_a INTEGER,
        m_m INTEGER,
        attendance TEXT,
        principal_note TEXT,
        lines INTEGER,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('hifz_records', 'student_id', 'INTEGER')
    add_column_if_not_exists('hifz_records', 'lines', 'INTEGER')
    add_column_if_not_exists('hifz_records', 'cleanliness', 'TEXT')
    
    c.execute('''CREATE TABLE IF NOT EXISTS qaida_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        student_id INTEGER,
        t_name TEXT,
        lesson_no TEXT,
        total_lines INTEGER,
        details TEXT,
        attendance TEXT,
        principal_note TEXT,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('qaida_records', 'student_id', 'INTEGER')
    add_column_if_not_exists('qaida_records', 'cleanliness', 'TEXT')
    
    c.execute('''CREATE TABLE IF NOT EXISTS general_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        student_id INTEGER,
        t_name TEXT,
        dept TEXT,
        book_subject TEXT,
        today_lesson TEXT,
        homework TEXT,
        performance TEXT,
        attendance TEXT,
        cleanliness TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('general_education', 'student_id', 'INTEGER')
    add_column_if_not_exists('general_education', 'attendance', 'TEXT')
    add_column_if_not_exists('general_education', 'cleanliness', 'TEXT')
    
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        a_date DATE,
        arrival TEXT,
        departure TEXT,
        actual_arrival TEXT,
        actual_departure TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        reason TEXT,
        start_date DATE,
        back_date DATE,
        status TEXT,
        request_date DATE,
        l_type TEXT,
        days INTEGER,
        notification_seen INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        dept TEXT,
        exam_type TEXT,
        from_para INTEGER,
        to_para INTEGER,
        book_name TEXT,
        amount_read TEXT,
        start_date TEXT,
        end_date TEXT,
        total_days INTEGER,
        q1 INTEGER,
        q2 INTEGER,
        q3 INTEGER,
        q4 INTEGER,
        q5 INTEGER,
        total INTEGER,
        grade TEXT,
        status TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('exams', 'student_id', 'INTEGER')
    add_column_if_not_exists('exams', 'amount_read', 'TEXT')
    add_column_if_not_exists('exams', 'total_days', 'INTEGER')
    
    c.execute('''CREATE TABLE IF NOT EXISTS passed_paras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        para_no INTEGER,
        book_name TEXT,
        passed_date DATE,
        exam_type TEXT,
        grade TEXT,
        marks INTEGER,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    add_column_if_not_exists('passed_paras', 'student_id', 'INTEGER')
    add_column_if_not_exists('passed_paras', 'book_name', 'TEXT')
    add_column_if_not_exists('passed_paras', 'marks', 'INTEGER')
    
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        day TEXT,
        period TEXT,
        book TEXT,
        room TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        message TEXT,
        target TEXT,
        created_at DATETIME,
        seen INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        timestamp DATETIME,
        details TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS staff_monitoring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_name TEXT,
        date DATE,
        note_type TEXT,
        description TEXT,
        action_taken TEXT,
        status TEXT,
        created_by TEXT,
        created_at DATETIME
    )''')
    
    conn.commit()
    
    # مائیگریشن: پرانے ریکارڈز میں cleanliness کالم شامل کریں
    if column_exists('hifz_records', 's_name') and column_exists('hifz_records', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM hifz_records WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE hifz_records SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE hifz_records SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    if column_exists('qaida_records', 's_name') and column_exists('qaida_records', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM qaida_records WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE qaida_records SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE qaida_records SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    if column_exists('general_education', 's_name') and column_exists('general_education', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM general_education WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE general_education SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE general_education SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    if column_exists('exams', 's_name') and column_exists('exams', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM exams WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE exams SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE exams SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    if column_exists('passed_paras', 's_name') and column_exists('passed_paras', 'f_name'):
        c.execute("SELECT id, s_name, f_name FROM passed_paras WHERE student_id IS NULL")
        old_records = c.fetchall()
        for rec_id, s_name, f_name in old_records:
            student = c.execute("SELECT id FROM students WHERE name=? AND father_name=?", (s_name, f_name)).fetchone()
            if student:
                c.execute("UPDATE passed_paras SET student_id=? WHERE id=?", (student[0], rec_id))
            else:
                c.execute("INSERT INTO students (name, father_name) VALUES (?,?)", (s_name, f_name))
                new_id = c.lastrowid
                c.execute("UPDATE passed_paras SET student_id=? WHERE id=?", (new_id, rec_id))
        conn.commit()
    
    admin_hash = hash_password("jamia123")
    admin_exists = c.execute("SELECT 1 FROM teachers WHERE name='admin'").fetchone()
    if not admin_exists:
        c.execute("INSERT INTO teachers (name, password, dept) VALUES (?,?,?)", ("admin", admin_hash, "Admin"))
    conn.commit()
    conn.close()

init_db()

# ==================== 2. ہیلپر فنکشنز ====================
def log_audit(user, action, details=""):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO audit_log (user, action, timestamp, details) VALUES (?,?,?,?)",
                     (user, action, datetime.now(), details))
        conn.commit()
        conn.close()
    except: pass

def get_pk_time():
    tz = pytz.timezone('Asia/Karachi')
    return datetime.now(tz).strftime("%I:%M %p")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def get_grade_from_mistakes(total_mistakes):
    if total_mistakes <= 2: return "ممتاز"
    elif total_mistakes <= 5: return "جید جداً"
    elif total_mistakes <= 8: return "جید"
    elif total_mistakes <= 12: return "مقبول"
    else: return "دوبارہ کوشش کریں"

def calculate_grade_with_attendance(attendance, sabaq_nagha, sq_nagha, m_nagha, sq_mistakes, m_mistakes):
    if attendance == "غیر حاضر":
        return "غیر حاضر"
    if attendance == "رخصت":
        return "رخصت"
    nagha_count = sum([sabaq_nagha, sq_nagha, m_nagha])
    if nagha_count == 1:
        return "ناقص (ناغہ)"
    elif nagha_count == 2:
        return "کمزور (ناغہ)"
    elif nagha_count == 3:
        return "ناکام (مکمل ناغہ)"
    total_mistakes = sq_mistakes + m_mistakes
    if total_mistakes <= 2:
        return "ممتاز"
    elif total_mistakes <= 5:
        return "جید جداً"
    elif total_mistakes <= 8:
        return "جید"
    elif total_mistakes <= 12:
        return "مقبول"
    else:
        return "دوبارہ کوشش کریں"

def cleanliness_to_score(clean):
    if clean == "بہترین":
        return 3
    elif clean == "بہتر":
        return 2
    elif clean == "ناقص":
        return 1
    else:
        return 0

def generate_exam_result_card(exam_row):
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>رزلٹ کارڈ - {exam_row['s_name']}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        .card {{ border: 2px solid #8B008B; border-radius: 15px; padding: 20px; max-width: 600px; margin: auto; }}
        h2 {{ text-align: center; color: #8B008B; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #fce4ec; }}
        .footer {{ margin-top: 20px; display: flex; justify-content: space-between; }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
            <h3>رزلٹ کارڈ</h3>
            <p><b>نام:</b> {exam_row['s_name']} بنت {exam_row['f_name']}</p>
            <p><b>شناختی نمبر:</b> {exam_row.get('roll_no', '')}</p>
            <p><b>امتحان کی قسم:</b> {exam_row['exam_type']}</p>
            {f"<p><b>پارہ:</b> {exam_row['from_para']} تا {exam_row['to_para']}</p>" if exam_row.get('from_para') else ""}
            {f"<p><b>کتاب:</b> {exam_row.get('book_name', '')}</p>" if exam_row.get('book_name') else ""}
            {f"<p><b>مقدار خواندگی:</b> {exam_row.get('amount_read', '')}</p>" if exam_row.get('amount_read') else ""}
            <p><b>تاریخ:</b> {exam_row['start_date']} تا {exam_row['end_date']}</p>
            <p><b>کل دن:</b> {exam_row.get('total_days', '')}</p>
            <table>
                <tr><th>سوال</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>کل</th></tr>
                <tr><td style="text-align:center">{exam_row['q1']}</td>
                <td>{exam_row['q2']}</td>
                <td>{exam_row['q3']}</td>
                <td>{exam_row['q4']}</td>
                <td>{exam_row['q5']}</td>
                <td>{exam_row['total']}</td>
                </tr>
            </table>
            <p><b>گریڈ:</b> {exam_row['grade']}</p>
            <div class="footer">
                <span>دستخط معلمہ: _________________</span>
                <span>دستخط مہتممہ: _________________</span>
            </div>
        </div>
        <div class="no-print" style="text-align:center; margin-top:20px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_para_report(student_name, father_name, passed_paras_df):
    if passed_paras_df.empty:
        return "<p>کوئی پاس شدہ پارہ نہیں</p>"
    html_table = passed_paras_df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>پارہ تعلیمی رپورٹ - {student_name}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #8B008B; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #fce4ec; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
            <h3>پارہ تعلیمی رپورٹ</h3>
            <p><b>طالبہ:</b> {student_name} بنت {father_name}</p>
        </div>
        {html_table}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط معلمہ: _______________________</span>
            <span>دستخط مہتممہ: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_html_report(df, title, student_name="", start_date="", end_date="", passed_paras=None):
    html_table = df.to_html(index=False, classes='print-table', border=1, justify='center', escape=False)
    passed_html = ""
    if passed_paras:
        passed_html = f"<div style='margin-top:20px'><b>پاس شدہ پارے:</b> {', '.join(map(str, passed_paras))}</div>"
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>{title}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #8B008B; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #fce4ec; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
            <h3>{title}</h3>
            {f"<p><b>طالبہ:</b> {student_name} &nbsp;&nbsp; <b>تاریخ:</b> {start_date} تا {end_date}</p>" if student_name else ""}
        </div>
        {html_table}
        {passed_html}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط معلمہ: _______________________</span>
            <span>دستخط مہتممہ: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

def generate_timetable_html(df_timetable):
    if df_timetable.empty:
        return "<p>کوئی ٹائم ٹیبل دستیاب نہیں</p>"
    day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
    df_timetable['day_order'] = df_timetable['دن'].map(day_order)
    df_timetable = df_timetable.sort_values(['day_order', 'وقت'])
    pivot = df_timetable.pivot(index='وقت', columns='دن', values='کتاب')
    pivot = pivot.fillna("—")
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>ٹائم ٹیبل</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #8B008B; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #fce4ec; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
            <h3>ٹائم ٹیبل</h3>
        </div>
        {pivot.to_html(classes='print-table', border=1, justify='center', escape=False)}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط معلمہ: _______________________</span>
            <span>دستخط مہتممہ: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

# ==================== 3. اسٹائلنگ (بہتر اور نسائی رنگ) ====================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ للبنات | سمارٹ ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    @font-face {
        font-family: 'Jameel Noori Nastaleeq';
        src: url('https://raw.githubusercontent.com/urdufonts/jameel-noori-nastaleeq/master/JameelNooriNastaleeq.ttf') format('truetype');
        font-weight: normal;
        font-style: normal;
    }
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * {
        font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', 'Arial', sans-serif;
    }
    body { direction: rtl; text-align: right; background: linear-gradient(135deg, #fdf8f5 0%, #fce4ec 100%); }
    .stSidebar { background: linear-gradient(180deg, #8B008B 0%, #4A004A 100%); color: white; }
    .stSidebar * { color: white !important; }
    .stSidebar .stRadio label { color: white !important; font-weight: bold; font-size: 1rem; }
    .stSidebar .stRadio [role="radiogroup"] div { color: white !important; }
    .stSidebar .stRadio [role="radiogroup"] div[data-baseweb="radio"]:hover { background-color: #C71585; border-radius: 5px; }
    .stButton > button { background: linear-gradient(90deg, #8B008B, #C71585); color: white; border-radius: 30px; border: none; padding: 0.5rem 1rem; font-weight: bold; transition: 0.3s; width: 100%; }
    .stButton > button:hover { transform: scale(1.02); background: linear-gradient(90deg, #C71585, #8B008B); }
    .main-header { text-align: center; background: linear-gradient(135deg, #fce4ec, #f8bbd0); padding: 1rem; border-radius: 20px; margin-bottom: 1rem; border-bottom: 4px solid #8B008B; }
    .report-card { background: white; border-radius: 15px; padding: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1rem; border: 1px solid #f8bbd0; }
    .stTabs [data-baseweb="tab"] { border-radius: 30px; padding: 0.5rem 1rem; background-color: #f8bbd0; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #8B008B, #C71585); color: white; }
    .best-student-card {
        background: linear-gradient(135deg, #fff9e6, #ffe6f0);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    .best-student-card:hover { transform: translateY(-5px); }
    .gold { color: #d4af37; }
    .silver { color: #a0a0a0; }
    .bronze { color: #cd7f32; }
    @media (max-width: 768px) {
        .stButton > button { padding: 0.4rem 0.8rem; font-size: 0.8rem; }
        .main-header h1 { font-size: 1.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== 4. لاگ ان ====================
def verify_login(username, password):
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM teachers WHERE name=? AND password=?", (username, password)).fetchone()
    if not res:
        hashed = hash_password(password)
        res = conn.execute("SELECT * FROM teachers WHERE name=? AND password=?", (username, hashed)).fetchone()
    conn.close()
    return res

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ للبنات</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.container():
            st.markdown("<div class='report-card'><h3>🔐 لاگ ان</h3>", unsafe_allow_html=True)
            u = st.text_input("صارف نام")
            p = st.text_input("پاسورڈ", type="password")
            if st.button("داخل ہوں"):
                res = verify_login(u, p)
                if res:
                    st.session_state.logged_in, st.session_state.username = True, u
                    st.session_state.user_type = "admin" if u == "admin" else "teacher"
                    log_audit(u, "Login", f"User type: {st.session_state.user_type}")
                    st.rerun()
                else:
                    st.error("غلط معلومات")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==================== 5. مینو ====================
if st.session_state.user_type == "admin":
    menu = ["📊 ایڈمن ڈیش بورڈ", "📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "📘 پارہ تعلیمی رپورٹ", "🕒 معلمات حاضری", "🏛️ رخصت کی منظوری",
            "👥 یوزر مینجمنٹ", "📚 ٹائم ٹیبل مینجمنٹ", "🔑 پاسورڈ تبدیل کریں", "📋 عملہ نگرانی و شکایات",
            "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس", "🏆 ماہانہ بہترین طالبات", "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 روزانہ سبق اندراج", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
            "🕒 میری حاضری", "📚 میرا ٹائم ٹیبل", "🔑 پاسورڈ تبدیل کریں", "📢 نوٹیفیکیشنز"]

selected = st.sidebar.radio("📌 مینو", menu)

# ==================== 6. ڈیٹا ====================
surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
               "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج",
               "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب",
               "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف",
               "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة",
               "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة",
               "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر",
               "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل",
               "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة",
               "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]
cleanliness_options = ["بہترین", "بہتر", "ناقص"]

# ==================== 7. پاسورڈ تبدیل کرنے کے فنکشنز ====================
def verify_password(user, plain_password):
    conn = get_db_connection()
    res = conn.execute("SELECT password FROM teachers WHERE name=?", (user,)).fetchone()
    conn.close()
    if not res:
        return False
    stored = res[0]
    if stored == plain_password:
        return True
    if stored == hash_password(plain_password):
        return True
    return False

def change_password(user, old_pass, new_pass):
    if not verify_password(user, old_pass):
        return False
    conn = get_db_connection()
    new_hash = hash_password(new_pass)
    conn.execute("UPDATE teachers SET password=? WHERE name=?", (new_hash, user))
    conn.commit()
    conn.close()
    log_audit(user, "Password Changed", "Success")
    return True

def admin_reset_password(teacher_name, new_pass):
    conn = get_db_connection()
    new_hash = hash_password(new_pass)
    conn.execute("UPDATE teachers SET password=? WHERE name=?", (new_hash, teacher_name))
    conn.commit()
    conn.close()
    log_audit(st.session_state.username, "Admin Reset Password", f"Teacher: {teacher_name}")

# ==================== 8. ایڈمن سیکشنز (مؤنث متن کے ساتھ) ====================
# 8.1 ایڈمن ڈیش بورڈ
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = conn.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
    col1, col2 = st.columns(2)
    col1.metric("کل طالبات", total_students)
    col2.metric("کل معلمات", total_teachers)
    conn.close()

# 8.2 یومیہ تعلیمی رپورٹ (مؤنث)
elif selected == "📊 یومیہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📊 یومیہ تعلیمی رپورٹ - صرف دیکھیں")
    with st.sidebar:
        d1 = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("تاریخ اختتام", date.today())
        conn = get_db_connection()
        teachers_list = ["تمام"] + [t[0] for t in conn.execute("SELECT DISTINCT t_name FROM hifz_records UNION SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        conn.close()
        sel_teacher = st.selectbox("معلمہ / کلاس", teachers_list)
        dept_filter = st.selectbox("شعبہ", ["تمام", "حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    combined_df = pd.DataFrame()
    if dept_filter in ["تمام", "حفظ"]:
        conn = get_db_connection()
        try:
            hifz_df = pd.read_sql_query("""
                SELECT h.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام', s.roll_no as 'شناختی نمبر', h.t_name as معلمہ, 
                       'حفظ' as شعبہ, h.surah as 'سبق', h.lines as 'کل ستر',
                       h.sq_p as 'سبقی', h.sq_m as 'سبقی (غلطی)', h.sq_a as 'سبقی (اٹکن)',
                       h.m_p as 'منزل', h.m_m as 'منزل (غلطی)', h.m_a as 'منزل (اٹکن)',
                       h.attendance as حاضری, h.cleanliness as صفائی
                FROM hifz_records h
                JOIN students s ON h.student_id = s.id
                WHERE h.r_date BETWEEN ? AND ?
            """, conn, params=(d1, d2))
            conn.close()
            if not hifz_df.empty:
                if sel_teacher != "تمام":
                    hifz_df = hifz_df[hifz_df['معلمہ'] == sel_teacher]
                combined_df = pd.concat([combined_df, hifz_df], ignore_index=True)
        except Exception as e:
            st.error(f"حفظ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")
    if dept_filter in ["تمام", "قاعدہ"]:
        conn = get_db_connection()
        try:
            qaida_df = pd.read_sql_query("""
                SELECT q.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام', s.roll_no as 'شناختی نمبر', q.t_name as معلمہ,
                       'قاعدہ' as شعبہ, q.lesson_no as 'تختی نمبر', q.total_lines as 'کل لائنیں',
                       q.details as تفصیل, q.attendance as حاضری, q.cleanliness as صفائی
                FROM qaida_records q
                JOIN students s ON q.student_id = s.id
                WHERE q.r_date BETWEEN ? AND ?
            """, conn, params=(d1, d2))
            conn.close()
            if not qaida_df.empty:
                if sel_teacher != "تمام":
                    qaida_df = qaida_df[qaida_df['معلمہ'] == sel_teacher]
                combined_df = pd.concat([combined_df, qaida_df], ignore_index=True)
        except Exception as e:
            st.error(f"قاعدہ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")
    if dept_filter in ["تمام", "درسِ نظامی", "عصری تعلیم"]:
        conn = get_db_connection()
        has_attendance = column_exists('general_education', 'attendance')
        if has_attendance:
            select_cols = """
                g.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام', s.roll_no as 'شناختی نمبر', g.t_name as معلمہ,
                g.dept as شعبہ, g.book_subject as 'کتاب/مضمون', g.today_lesson as 'آج کا سبق',
                g.homework as 'ہوم ورک', g.performance as کارکردگی, g.attendance as حاضری, g.cleanliness as صفائی
            """
        else:
            select_cols = """
                g.r_date as تاریخ, s.name as نام, s.father_name as 'والد کا نام', s.roll_no as 'شناختی نمبر', g.t_name as معلمہ,
                g.dept as شعبہ, g.book_subject as 'کتاب/مضمون', g.today_lesson as 'آج کا سبق',
                g.homework as 'ہوم ورک', g.performance as کارکردگی, '' as حاضری, g.cleanliness as صفائی
            """
        query = f"""
            SELECT {select_cols}
            FROM general_education g
            JOIN students s ON g.student_id = s.id
            WHERE g.r_date BETWEEN ? AND ?
        """
        params = [d1, d2]
        if sel_teacher != "تمام":
            query += " AND g.t_name = ?"
            params.append(sel_teacher)
        if dept_filter != "تمام":
            query += " AND g.dept = ?"
            params.append(dept_filter)
        try:
            gen_df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            if not gen_df.empty:
                combined_df = pd.concat([combined_df, gen_df], ignore_index=True)
        except Exception as e:
            st.error(f"عمومی تعلیم کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")
    if combined_df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        st.success(f"کل {len(combined_df)} ریکارڈ ملے")
        st.dataframe(combined_df, use_container_width=True)
        html_report = generate_html_report(combined_df, "یومیہ تعلیمی رپورٹ", start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
        st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "daily_report.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"):
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)

# 8.3 امتحانی نظام (مؤنث)
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام")
    tab1, tab2 = st.tabs(["پینڈنگ امتحانات", "مکمل شدہ"])
    with tab1:
        conn = get_db_connection()
        pending = conn.execute("""
            SELECT e.id, s.name, s.father_name, s.roll_no, e.dept, e.exam_type, e.from_para, e.to_para, e.book_name, e.amount_read, e.start_date, e.end_date, e.total_days
            FROM exams e
            JOIN students s ON e.student_id = s.id
            WHERE e.status=?
        """, ("پینڈنگ",)).fetchall()
        conn.close()
        if not pending:
            st.info("کوئی پینڈنگ امتحان نہیں")
        else:
            for eid, sn, fn, rn, dept, etype, fp, tp, book, amount, sd, ed, tdays in pending:
                with st.expander(f"{sn} بنت {fn} | شناختی نمبر: {rn} | {dept} | {etype}"):
                    st.write(f"**تاریخ ابتدا:** {sd}")
                    st.write(f"**تاریخ اختتام:** {ed}")
                    st.write(f"**کل دن:** {tdays if tdays else '-'}")
                    if etype == "پارہ ٹیسٹ":
                        st.info(f"پارہ نمبر: {fp} تا {tp}")
                    else:
                        st.info(f"کتاب: {book}")
                        st.info(f"مقدار خواندگی: {amount}")
                    cols = st.columns(5)
                    q1 = cols[0].number_input("س1", 0, 20, key=f"q1_{eid}")
                    q2 = cols[1].number_input("س2", 0, 20, key=f"q2_{eid}")
                    q3 = cols[2].number_input("س3", 0, 20, key=f"q3_{eid}")
                    q4 = cols[3].number_input("س4", 0, 20, key=f"q4_{eid}")
                    q5 = cols[4].number_input("س5", 0, 20, key=f"q5_{eid}")
                    total = q1+q2+q3+q4+q5
                    if total >= 90: g = "ممتاز"
                    elif total >= 80: g = "جید جداً"
                    elif total >= 70: g = "جید"
                    elif total >= 60: g = "مقبول"
                    else: g = "ناکام"
                    st.write(f"کل: {total} | گریڈ: {g}")
                    if st.button("کلیئر کریں", key=f"save_{eid}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("""UPDATE exams SET q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? WHERE id=?""",
                                  (q1,q2,q3,q4,q5,total,g,"مکمل", date.today(), eid))
                        if g != "ناکام":
                            stud_id = c.execute("SELECT student_id FROM exams WHERE id=?", (eid,)).fetchone()[0]
                            if etype == "پارہ ٹیسٹ" and fp:
                                for para in range(fp, tp+1):
                                    existing = c.execute("SELECT 1 FROM passed_paras WHERE student_id=? AND para_no=?", (stud_id, para)).fetchone()
                                    if not existing:
                                        c.execute("INSERT INTO passed_paras (student_id, para_no, passed_date, exam_type, grade, marks) VALUES (?,?,?,?,?,?)",
                                                  (stud_id, para, date.today(), etype, g, total))
                            else:
                                existing = c.execute("SELECT 1 FROM passed_paras WHERE student_id=? AND book_name=?", (stud_id, book)).fetchone()
                                if not existing:
                                    c.execute("INSERT INTO passed_paras (student_id, book_name, passed_date, exam_type, grade, marks) VALUES (?,?,?,?,?,?)",
                                              (stud_id, book, date.today(), etype, g, total))
                        conn.commit()
                        conn.close()
                        st.success("امتحان کلیئر کر دیا گیا")
                        st.rerun()
    with tab2:
        conn = get_db_connection()
        hist = pd.read_sql_query("""
            SELECT s.name as 'نام', s.father_name as 'والد کا نام', s.roll_no as 'شناختی نمبر', e.dept as شعبہ, e.exam_type as 'امتحان قسم', 
                   e.from_para as 'پارہ سے', e.to_para as 'پارہ تک', e.book_name as 'کتاب', e.amount_read as 'مقدار', 
                   e.start_date as 'تاریخ شروع', e.end_date as 'تاریخ ختم', e.total as 'کل نمبر', e.grade as 'گریڈ'
            FROM exams e
            JOIN students s ON e.student_id = s.id
            WHERE e.status='مکمل'
            ORDER BY e.end_date DESC
        """, conn)
        conn.close()
        if not hist.empty:
            st.dataframe(hist, use_container_width=True)
            st.download_button("ہسٹری CSV", convert_df_to_csv(hist), "exam_history.csv")
        else:
            st.info("کوئی مکمل شدہ امتحان نہیں")

# 8.4 عملہ نگرانی و شکایات (مؤنث)
elif selected == "📋 عملہ نگرانی و شکایات" and st.session_state.user_type == "admin":
    st.header("📋 عملہ نگرانی و شکایات")
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ دیکھیں"])
    with tab1:
        with st.form("new_monitoring"):
            conn = get_db_connection()
            staff_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
            conn.close()
            if not staff_list:
                st.warning("کوئی معلمہ/عملہ موجود نہیں۔ پہلے معلمات رجسٹر کریں۔")
            else:
                staff_name = st.selectbox("عملہ کا نام", staff_list)
                note_date = st.date_input("تاریخ", date.today())
                note_type = st.selectbox("نوعیت", ["یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
                description = st.text_area("تفصیل", height=150)
                action_taken = st.text_area("کیا کارروائی کی گئی؟", height=100)
                status = st.selectbox("حالت", ["زیر التواء", "حل شدہ", "زیر غور"])
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("""INSERT INTO staff_monitoring 
                                (staff_name, date, note_type, description, action_taken, status, created_by, created_at)
                                VALUES (?,?,?,?,?,?,?,?)""",
                              (staff_name, note_date, note_type, description, action_taken, status, st.session_state.username, datetime.now()))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state.username, "Staff Monitoring Added", f"{staff_name} - {note_type}")
                    st.success("اندراج محفوظ ہو گیا")
                    st.rerun()
    with tab2:
        st.subheader("فلٹرز")
        conn = get_db_connection()
        staff_names = ["تمام"] + [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        conn.close()
        filter_staff = st.selectbox("عملہ فلٹر کریں", staff_names)
        filter_type = st.selectbox("نوعیت فلٹر کریں", ["تمام", "یادداشت", "شکایت", "تنبیہ", "تعریف", "کارکردگی جائزہ"])
        start_date = st.date_input("تاریخ از", date.today() - timedelta(days=30))
        end_date = st.date_input("تاریخ تا", date.today())
        query = "SELECT id, staff_name as 'عملہ کا نام', date as تاریخ, note_type as نوعیت, description as تفصیل, action_taken as 'کارروائی', status as حالت, created_by as 'داخل کردہ', created_at as 'داخل کردہ تاریخ' FROM staff_monitoring WHERE date BETWEEN ? AND ?"
        params = [start_date, end_date]
        if filter_staff != "تمام":
            query += " AND staff_name = ?"
            params.append(filter_staff)
        if filter_type != "تمام":
            query += " AND note_type = ?"
            params.append(filter_type)
        query += " ORDER BY date DESC"
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        if df.empty:
            st.info("کوئی ریکارڈ موجود نہیں")
        else:
            st.dataframe(df, use_container_width=True)
            csv = convert_df_to_csv(df)
            st.download_button("📥 CSV ڈاؤن لوڈ کریں", csv, "staff_monitoring.csv", "text/csv")
            html_report = generate_html_report(df, "عملہ نگرانی و شکایات رپورٹ")
            st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "staff_monitoring_report.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)
            with st.expander("⚠️ ریکارڈ حذف کریں"):
                record_id = st.number_input("ریکارڈ ID درج کریں", min_value=1, step=1)
                if st.button("حذف کریں"):
                    conn = get_db_connection()
                    conn.execute("DELETE FROM staff_monitoring WHERE id=?", (record_id,))
                    conn.commit()
                    conn.close()
                    st.success("ریکارڈ حذف کر دیا گیا")
                    st.rerun()

# 8.5 ماہانہ رزلٹ کارڈ (مؤنث)
elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.header("📜 ماہانہ رزلٹ کارڈ")
    conn = get_db_connection()
    students_list = conn.execute("SELECT id, name, father_name, roll_no, dept FROM students").fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی طالبہ نہیں")
    else:
        student_names = [f"{s[1]} بنت {s[2]} (شناختی نمبر: {s[3]}) - {s[4]}" for s in students_list]
        sel = st.selectbox("طالبہ منتخب کریں", student_names)
        parts = sel.split(" بنت ")
        s_name = parts[0]
        rest = parts[1]
        f_name, rest2 = rest.split(" (شناختی نمبر: ")
        roll_no, dept = rest2.split(") - ")
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        student_id = [s[0] for s in students_list if s[1] == s_name and s[2] == f_name][0]
        if dept == "حفظ":
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, attendance as حاضری, surah as 'سبق', lines as 'کل ستر',
                                      sq_p as 'سبقی', sq_m as 'سبقی (غلطی)', sq_a as 'سبقی (اٹکن)',
                                      m_p as 'منزل', m_m as 'منزل (غلطی)', m_a as 'منزل (اٹکن)',
                                      cleanliness as صفائی
                                      FROM hifz_records WHERE student_id=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(student_id, start, end))
            conn.close()
            if not df.empty:
                grades = []
                for idx, row in df.iterrows():
                    att = row['حاضری']
                    sabaq_nagha = (row['سبق'] == "ناغہ" or row['سبق'] == "یاد نہیں")
                    sq_nagha = (row['سبقی'] == "ناغہ" or row['سبقی'] == "یاد نہیں")
                    m_nagha = (row['منزل'] == "ناغہ" or row['منزل'] == "یاد نہیں")
                    sq_m = row['سبقی (غلطی)'] if pd.notna(row['سبقی (غلطی)']) else 0
                    m_m = row['منزل (غلطی)'] if pd.notna(row['منزل (غلطی)']) else 0
                    grade = calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, sq_m, m_m)
                    grades.append(grade)
                df['درجہ'] = grades
                st.dataframe(df[['تاریخ', 'حاضری', 'سبق', 'سبقی', 'منزل', 'صفائی', 'درجہ']], use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (حفظ)", student_name=f"{s_name} بنت {f_name}",
                                            start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"):
                    st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
        elif dept == "قاعدہ":
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, lesson_no as 'تختی نمبر', total_lines as 'کل لائنیں',
                                      details as تفصیل, attendance as حاضری, cleanliness as صفائی
                                      FROM qaida_records WHERE student_id=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(student_id, start, end))
            conn.close()
            if df.empty:
                st.warning("کوئی ریکارڈ نہیں")
            else:
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ (قاعدہ)", student_name=f"{s_name} بنت {f_name}",
                                            start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_qaida_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"):
                    st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)
        else:
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, book_subject as 'کتاب/مضمون', today_lesson as 'آج کا سبق',
                                      homework as 'ہوم ورک', performance as کارکردگی, cleanliness as صفائی
                                      FROM general_education WHERE student_id=? AND dept=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(student_id, dept, start, end))
            conn.close()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                html = generate_html_report(df, "ماہانہ رزلٹ کارڈ", student_name=f"{s_name} بنت {f_name}",
                                            start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"))
                st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
                if st.button("🖨️ پرنٹ کریں"):
                    st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# 8.6 پارہ تعلیمی رپورٹ (مؤنث)
elif selected == "📘 پارہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📘 پارہ تعلیمی رپورٹ")
    conn = get_db_connection()
    students_list = conn.execute("SELECT id, name, father_name FROM students WHERE dept='حفظ'").fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی حفظ کی طالبہ نہیں")
    else:
        student_names = [f"{s[1]} بنت {s[2]}" for s in students_list]
        sel = st.selectbox("طالبہ منتخب کریں", student_names)
        s_name, f_name = sel.split(" بنت ")
        student_id = [s[0] for s in students_list if s[1] == s_name and s[2] == f_name][0]
        conn = get_db_connection()
        passed_df = pd.read_sql_query("""SELECT para_no as 'پارہ نمبر', passed_date as 'تاریخ پاس', 
                                         exam_type as 'امتحان قسم', grade as 'گریڈ', marks as 'نمبر'
                                         FROM passed_paras WHERE student_id=? AND para_no IS NOT NULL
                                         ORDER BY para_no""", conn, params=(student_id,))
        conn.close()
        if passed_df.empty:
            st.info("اس طالبہ کا کوئی پاس شدہ پارہ نہیں")
        else:
            st.dataframe(passed_df, use_container_width=True)
            html = generate_para_report(s_name, f_name, passed_df)
            st.download_button("📥 رپورٹ ڈاؤن لوڈ کریں", html, f"Para_Report_{s_name}.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# 8.7 معلمات حاضری
elif selected == "🕒 معلمات حاضری" and st.session_state.user_type == "admin":
    st.header("معلمات حاضری ریکارڈ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as معلمہ, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

# 8.8 رخصت کی منظوری
elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری")
    conn = get_db_connection()
    try:
        pending = conn.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE ?", ('%پینڈنگ%',)).fetchall()
    except:
        pending = []
    conn.close()
    if not pending:
        st.info("کوئی پینڈنگ درخواست نہیں")
    else:
        for l_id, t_n, l_t, reas, s_d, dys in pending:
            with st.expander(f"{t_n} | {l_t} | {dys} دن"):
                st.write(f"وجہ: {reas}")
                col1, col2 = st.columns(2)
                if col1.button("✅ منظور", key=f"app_{l_id}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (l_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()
                if col2.button("❌ مسترد", key=f"rej_{l_id}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE leave_requests SET status='مسترد' WHERE id=?", (l_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()

# 8.9 یوزر مینجمنٹ (مؤنث)
elif selected == "👥 یوزر مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("👥 یوزر مینجمنٹ")
    tab1, tab2 = st.tabs(["معلمات", "طالبات"])
    with tab1:
        st.subheader("موجودہ معلمات")
        conn = get_db_connection()
        columns = ["id", "name", "password", "dept", "phone", "address", "id_card", "joining_date"]
        existing_cols = []
        for col in columns:
            if column_exists("teachers", col):
                existing_cols.append(col)
        query = f"SELECT {', '.join(existing_cols)} FROM teachers WHERE name!='admin'"
        teachers_df = pd.read_sql_query(query, conn)
        conn.close()
        if not teachers_df.empty:
            edited_teachers = st.data_editor(teachers_df, num_rows="dynamic", use_container_width=True, key="teachers_edit")
            if st.button("معلمات میں تبدیلیاں محفوظ کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                old_ids = set(teachers_df['id'])
                new_ids = set(edited_teachers['id']) if 'id' in edited_teachers.columns else set()
                deleted_ids = old_ids - new_ids
                for did in deleted_ids:
                    c.execute("DELETE FROM teachers WHERE id=?", (did,))
                for _, row in edited_teachers.iterrows():
                    if pd.isna(row['id']) or row['id'] == 0 or row['id'] == '':
                        col_names = [col for col in existing_cols if col != 'id']
                        placeholders = ",".join(["?" for _ in col_names])
                        values = [row[col] for col in col_names]
                        if 'password' in col_names:
                            pwd_index = col_names.index('password')
                            if values[pwd_index]:
                                values[pwd_index] = hash_password(values[pwd_index])
                        c.execute(f"INSERT INTO teachers ({','.join(col_names)}) VALUES ({placeholders})", values)
                    else:
                        set_clause = ",".join([f"{col}=?" for col in existing_cols if col != 'id'])
                        values = []
                        for col in existing_cols:
                            if col != 'id':
                                val = row[col]
                                if col == 'password' and val:
                                    val = hash_password(val)
                                values.append(val)
                        values.append(row['id'])
                        c.execute(f"UPDATE teachers SET {set_clause} WHERE id=?", values)
                conn.commit()
                conn.close()
                st.success("تبدیلیاں محفوظ ہو گئیں")
                st.rerun()
        else:
            st.info("کوئی معلمہ موجود نہیں")
        with st.expander("➕ نئی معلمہ رجسٹر کریں"):
            with st.form("new_teacher_form"):
                name = st.text_input("معلمہ کا نام*")
                password = st.text_input("پاسورڈ*", type="password")
                dept = st.selectbox("شعبہ", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                id_card = st.text_input("شناختی کارڈ نمبر")
                joining_date = st.date_input("تاریخ شمولیت", date.today())
                photo = st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                if st.form_submit_button("رجسٹر کریں"):
                    if name and password:
                        conn = get_db_connection()
                        c = conn.cursor()
                        try:
                            photo_path = None
                            if photo:
                                os.makedirs("uploads", exist_ok=True)
                                photo_path = f"uploads/teacher_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                                with open(photo_path, "wb") as f:
                                    f.write(photo.getbuffer())
                            c.execute("INSERT INTO teachers (name, password, dept, phone, address, id_card, joining_date, photo) VALUES (?,?,?,?,?,?,?,?)",
                                      (name, hash_password(password), dept, phone, address, id_card, joining_date, photo_path))
                            conn.commit()
                            st.success("معلمہ کامیابی سے رجسٹر ہو گئی")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("یہ نام پہلے سے موجود ہے")
                        finally:
                            conn.close()
                    else:
                        st.error("نام اور پاسورڈ ضروری ہیں")
    with tab2:
        st.subheader("موجودہ طالبات (شناختی نمبر تبدیل کریں)")
        conn = get_db_connection()
        all_columns = ["id", "name", "father_name", "mother_name", "dob", "admission_date", "exit_date", "exit_reason",
                       "id_card", "phone", "address", "teacher_name", "dept", "class", "section", "roll_no"]
        existing_cols = []
        for col in all_columns:
            if column_exists("students", col):
                existing_cols.append(col)
        query = f"SELECT {', '.join(existing_cols)} FROM students"
        students_df = pd.read_sql_query(query, conn)
        conn.close()
        if not students_df.empty:
            edited_students = st.data_editor(students_df, num_rows="dynamic", use_container_width=True, key="students_edit")
            if st.button("طالبات میں تبدیلیاں محفوظ کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                old_ids = set(students_df['id'])
                new_ids = set(edited_students['id']) if 'id' in edited_students.columns else set()
                deleted_ids = old_ids - new_ids
                for did in deleted_ids:
                    c.execute("DELETE FROM students WHERE id=?", (did,))
                for _, row in edited_students.iterrows():
                    if pd.isna(row['id']) or row['id'] == 0 or row['id'] == '':
                        col_names = [col for col in existing_cols if col != 'id']
                        placeholders = ",".join(["?" for _ in col_names])
                        values = []
                        for col in col_names:
                            val = row[col]
                            if col in ['dob', 'admission_date', 'exit_date']:
                                if pd.notna(val) and val:
                                    if isinstance(val, (date, datetime)):
                                        val = val.strftime("%Y-%m-%d")
                                    else:
                                        val = str(val)
                                else:
                                    val = None
                            values.append(val)
                        c.execute(f"INSERT INTO students ({','.join(col_names)}) VALUES ({placeholders})", values)
                    else:
                        set_clause = ",".join([f"{col}=?" for col in existing_cols if col != 'id'])
                        values = []
                        for col in existing_cols:
                            if col != 'id':
                                val = row[col]
                                if col in ['dob', 'admission_date', 'exit_date']:
                                    if pd.notna(val) and val:
                                        if isinstance(val, (date, datetime)):
                                            val = val.strftime("%Y-%m-%d")
                                        else:
                                            val = str(val)
                                    else:
                                        val = None
                                values.append(val)
                        values.append(row['id'])
                        c.execute(f"UPDATE students SET {set_clause} WHERE id=?", values)
                conn.commit()
                conn.close()
                st.success("تبدیلیاں محفوظ ہو گئیں")
                st.rerun()
        else:
            st.info("کوئی طالبہ موجود نہیں")
        with st.expander("➕ نئی طالبہ داخل کریں"):
            with st.form("new_student_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("طالبہ کا نام*")
                    father = st.text_input("والد کا نام*")
                    mother = st.text_input("والدہ کا نام")
                    dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=365*10))
                    admission_date = st.date_input("تاریخ داخلہ", date.today())
                    roll_no = st.text_input("شناختی نمبر (اختیاری)", placeholder="مثلاً: 2024-001")
                with col2:
                    dept = st.selectbox("شعبہ*", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
                    class_name = st.text_input("کلاس (عصری تعلیم کے لیے)")
                    section = st.text_input("سیکشن")
                    conn = get_db_connection()
                    teachers_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                    conn.close()
                    teacher = st.selectbox("معلمہ*", teachers_list) if teachers_list else st.text_input("معلمہ کا نام*")
                id_card = st.text_input("B-Form / شناختی کارڈ نمبر")
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                photo = st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                st.markdown("---")
                st.markdown("**اگر طالبہ مدرسہ چھوڑ چکی ہے تو درج ذیل معلومات بھریں (ورنہ خالی چھوڑیں):**")
                exit_date = st.date_input("تاریخ خارج", value=None)
                exit_reason = st.text_area("وجہ خارج")
                if st.form_submit_button("داخلہ کریں"):
                    if name and father and teacher and dept:
                        conn = get_db_connection()
                        c = conn.cursor()
                        try:
                            photo_path = None
                            if photo:
                                os.makedirs("uploads", exist_ok=True)
                                photo_path = f"uploads/student_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                                with open(photo_path, "wb") as f:
                                    f.write(photo.getbuffer())
                            c.execute("""INSERT INTO students 
                                        (name, father_name, mother_name, dob, admission_date, exit_date, exit_reason,
                                         id_card, phone, address, teacher_name, dept, class, section, photo, roll_no)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (name, father, mother, dob, admission_date, exit_date, exit_reason,
                                       id_card, phone, address, teacher, dept, class_name, section, photo_path, roll_no))
                            conn.commit()
                            st.success("طالبہ کامیابی سے داخل ہو گئی")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {str(e)}")
                        finally:
                            conn.close()
                    else:
                        st.error("نام، ولدیت، معلمہ اور شعبہ ضروری ہیں")

# 8.10 ٹائم ٹیبل مینجمنٹ (مؤنث)
elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("📚 ٹائم ٹیبل مینجمنٹ")
    conn = get_db_connection()
    teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
    conn.close()
    if not teachers:
        st.warning("پہلے معلمات رجسٹر کریں")
    else:
        sel_t = st.selectbox("معلمہ منتخب کریں", teachers)
        conn = get_db_connection()
        tt_df = pd.read_sql_query("SELECT id, day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(sel_t,))
        conn.close()
        if not tt_df.empty:
            st.subheader("موجودہ ٹائم ٹیبل")
            day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
            tt_df['day_order'] = tt_df['دن'].map(day_order)
            tt_df = tt_df.sort_values(['day_order', 'وقت'])
            st.dataframe(tt_df[['دن', 'وقت', 'کتاب', 'کمرہ']], use_container_width=True)
        with st.expander("➕ نیا پیریڈ شامل کریں"):
            with st.form("add_period"):
                col1, col2 = st.columns(2)
                day = col1.selectbox("دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                period = col2.text_input("وقت (مثلاً 08:00-09:00)")
                book = st.text_input("کتاب / مضمون")
                room = st.text_input("کمرہ نمبر")
                if st.form_submit_button("شامل کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                              (sel_t, day, period, book, room))
                    conn.commit()
                    conn.close()
                    st.success("پیریڈ شامل کر دیا گیا")
                    st.rerun()
        if not tt_df.empty:
            with st.expander("🔄 پورے ہفتے میں نقل کریں"):
                source_day = st.selectbox("منبع دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"], key="copy_source")
                target_days = st.multiselect("نقل کرنے کے لیے دن", ["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"], default=["ہفتہ", "اتوار", "پیر", "منگل", "بدھ", "جمعرات"])
                if st.button("نقل کریں"):
                    conn = get_db_connection()
                    source_periods = conn.execute("SELECT period, book, room FROM timetable WHERE t_name=? AND day=?", (sel_t, source_day)).fetchall()
                    if source_periods:
                        for d in target_days:
                            conn.execute("DELETE FROM timetable WHERE t_name=? AND day=?", (sel_t, d))
                        for d in target_days:
                            for period, book, room in source_periods:
                                conn.execute("INSERT INTO timetable (t_name, day, period, book, room) VALUES (?,?,?,?,?)",
                                            (sel_t, d, period, book, room))
                        conn.commit()
                        st.success(f"{source_day} کے پیریڈز {', '.join(target_days)} میں نقل ہو گئے")
                    else:
                        st.warning(f"{source_day} کے لیے کوئی پیریڈ نہیں")
                    conn.close()
                    st.rerun()

# 8.11 پاسورڈ تبدیل کریں
elif selected == "🔑 پاسورڈ تبدیل کریں":
    st.header("🔑 پاسورڈ تبدیل کریں")
    if st.session_state.user_type == "admin":
        conn = get_db_connection()
        teachers = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        conn.close()
        if teachers:
            selected_teacher = st.selectbox("معلمہ منتخب کریں", teachers)
            new_pass = st.text_input("نیا پاسورڈ", type="password")
            confirm_pass = st.text_input("پاسورڈ کی تصدیق کریں", type="password")
            if st.button("پاسورڈ تبدیل کریں"):
                if new_pass and new_pass == confirm_pass:
                    admin_reset_password(selected_teacher, new_pass)
                    st.success(f"{selected_teacher} کا پاسورڈ تبدیل کر دیا گیا")
                else:
                    st.error("پاسورڈ میل نہیں کھاتے")
        else:
            st.info("کوئی دوسری معلمہ موجود نہیں")
    else:
        old_pass = st.text_input("پرانا پاسورڈ", type="password")
        new_pass = st.text_input("نیا پاسورڈ", type="password")
        confirm_pass = st.text_input("نیا پاسورڈ دوبارہ", type="password")
        if st.button("اپنا پاسورڈ تبدیل کریں"):
            if old_pass and new_pass and new_pass == confirm_pass:
                if change_password(st.session_state.username, old_pass, new_pass):
                    st.success("پاسورڈ تبدیل ہو گیا۔ براہ کرم دوبارہ لاگ ان کریں")
                    st.session_state.logged_in = False
                    st.rerun()
                else:
                    st.error("پرانا پاسورڈ غلط ہے")
            else:
                st.error("نیا پاسورڈ اور تصدیق ایک جیسی ہونی چاہیے")

# 8.12 نوٹیفیکیشنز
elif selected == "📢 نوٹیفیکیشنز":
    st.header("نوٹیفیکیشن سینٹر")
    if st.session_state.user_type == "admin":
        with st.form("new_notif"):
            title = st.text_input("عنوان")
            msg = st.text_area("پیغام")
            target = st.selectbox("بھیجیں", ["تمام", "معلمات", "طالبات"])
            if st.form_submit_button("بھیجیں"):
                conn = get_db_connection()
                conn.execute("INSERT INTO notifications (title, message, target, created_at) VALUES (?,?,?,?)",
                             (title, msg, target, datetime.now()))
                conn.commit()
                conn.close()
                st.success("نوٹیفکیشن بھیج دیا گیا")
    conn = get_db_connection()
    if st.session_state.user_type == "admin":
        notifs = conn.execute("SELECT title, message, created_at FROM notifications ORDER BY created_at DESC LIMIT 10").fetchall()
    else:
        notifs = conn.execute("SELECT title, message, created_at FROM notifications WHERE target IN ('تمام','معلمات') ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    for n in notifs:
        st.info(f"**{n[0]}**\n\n{n[1]}\n\n*{n[2]}*")

# 8.13 تجزیہ و رپورٹس
elif selected == "📈 تجزیہ و رپورٹس" and st.session_state.user_type == "admin":
    st.header("تجزیہ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ FROM t_attendance", conn)
    if not df.empty:
        fig = px.bar(df, x='تاریخ', title="معلمات کی حاضری")
        st.plotly_chart(fig)
    conn.close()

# 8.14 ماہانہ بہترین طالبات (مؤنث اور نیا رنگ)
elif selected == "🏆 ماہانہ بہترین طالبات" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>🏆 ماہانہ بہترین طالبات</h1><p>تعلیمی اور صفائی کی بنیاد پر بہترین کارکردگی</p></div>", unsafe_allow_html=True)
    
    # مہینہ منتخب کریں
    col1, col2 = st.columns(2)
    with col1:
        month_year = st.date_input("مہینہ منتخب کریں", date.today().replace(day=1), key="month_picker")
    start_date = month_year.replace(day=1)
    if month_year.month == 12:
        end_date = month_year.replace(year=month_year.year+1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = month_year.replace(month=month_year.month+1, day=1) - timedelta(days=1)
    
    st.markdown(f"### 📅 {start_date.strftime('%B %Y')} کے لیے نتائج")
    
    conn = get_db_connection()
    # تمام طالبات حاصل کریں
    students = conn.execute("SELECT id, name, father_name, roll_no, dept FROM students").fetchall()
    conn.close()
    
    if not students:
        st.warning("کوئی طالبہ موجود نہیں")
    else:
        # ہر طالبہ کے لیے تعلیمی اوسط اور صفائی اوسط نکالیں
        student_scores = []
        for sid, name, father, roll, dept in students:
            conn = get_db_connection()
            # تعلیمی گریڈز حاصل کریں (حفظ کے لیے)
            if dept == "حفظ":
                records = conn.execute("""
                    SELECT attendance, surah, sq_p, m_p, sq_m, m_m 
                    FROM hifz_records 
                    WHERE student_id=? AND r_date BETWEEN ? AND ?
                """, (sid, start_date, end_date)).fetchall()
                grade_scores = []
                for rec in records:
                    att = rec[0]
                    sabaq_nagha = (rec[1] == "ناغہ" or rec[1] == "یاد نہیں")
                    sq_nagha = (rec[2] == "ناغہ" or rec[2] == "یاد نہیں")
                    m_nagha = (rec[3] == "ناغہ" or rec[3] == "یاد نہیں")
                    sq_m = rec[4] if rec[4] else 0
                    m_m = rec[5] if rec[5] else 0
                    grade = calculate_grade_with_attendance(att, sabaq_nagha, sq_nagha, m_nagha, sq_m, m_m)
                    # گریڈ کو نمبر میں تبدیل کریں
                    if grade == "ممتاز":
                        grade_scores.append(100)
                    elif grade == "جید جداً":
                        grade_scores.append(85)
                    elif grade == "جید":
                        grade_scores.append(75)
                    elif grade == "مقبول":
                        grade_scores.append(60)
                    elif grade == "دوبارہ کوشش کریں":
                        grade_scores.append(40)
                    elif grade == "ناقص (ناغہ)":
                        grade_scores.append(30)
                    elif grade == "کمزور (ناغہ)":
                        grade_scores.append(20)
                    elif grade == "ناکام (مکمل ناغہ)":
                        grade_scores.append(10)
                    elif grade == "غیر حاضر":
                        grade_scores.append(0)
                    elif grade == "رخصت":
                        grade_scores.append(50)
                avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                
                # صفائی اوسط
                clean_records = conn.execute("SELECT cleanliness FROM hifz_records WHERE student_id=? AND r_date BETWEEN ? AND ? AND cleanliness IS NOT NULL", (sid, start_date, end_date)).fetchall()
                clean_scores = [cleanliness_to_score(c[0]) for c in clean_records if c[0]]
                avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
                
            elif dept == "قاعدہ":
                records = conn.execute("SELECT attendance FROM qaida_records WHERE student_id=? AND r_date BETWEEN ? AND ?", (sid, start_date, end_date)).fetchall()
                grade_scores = []
                for rec in records:
                    att = rec[0]
                    if att == "حاضر":
                        grade_scores.append(85)
                    elif att == "رخصت":
                        grade_scores.append(50)
                    else:
                        grade_scores.append(0)
                avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                clean_records = conn.execute("SELECT cleanliness FROM qaida_records WHERE student_id=? AND r_date BETWEEN ? AND ? AND cleanliness IS NOT NULL", (sid, start_date, end_date)).fetchall()
                clean_scores = [cleanliness_to_score(c[0]) for c in clean_records if c[0]]
                avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            else:
                records = conn.execute("SELECT attendance, performance FROM general_education WHERE student_id=? AND dept=? AND r_date BETWEEN ? AND ?", (sid, dept, start_date, end_date)).fetchall()
                grade_scores = []
                for rec in records:
                    att = rec[0]
                    perf = rec[1] if rec[1] else ""
                    if att == "حاضر":
                        if perf == "بہت بہتر":
                            grade_scores.append(90)
                        elif perf == "بہتر":
                            grade_scores.append(80)
                        elif perf == "مناسب":
                            grade_scores.append(65)
                        elif perf == "کمزور":
                            grade_scores.append(45)
                        else:
                            grade_scores.append(75)
                    elif att == "رخصت":
                        grade_scores.append(50)
                    else:
                        grade_scores.append(0)
                avg_grade = sum(grade_scores)/len(grade_scores) if grade_scores else 0
                clean_records = conn.execute("SELECT cleanliness FROM general_education WHERE student_id=? AND r_date BETWEEN ? AND ? AND cleanliness IS NOT NULL", (sid, start_date, end_date)).fetchall()
                clean_scores = [cleanliness_to_score(c[0]) for c in clean_records if c[0]]
                avg_clean = sum(clean_scores)/len(clean_scores) if clean_scores else 0
            conn.close()
            student_scores.append({
                "id": sid,
                "name": name,
                "father": father,
                "roll": roll,
                "dept": dept,
                "avg_grade": avg_grade,
                "avg_clean": avg_clean
            })
        
        # تعلیم کے لحاظ سے بہترین
        sorted_grade = sorted(student_scores, key=lambda x: x["avg_grade"], reverse=True)
        # صفائی کے لحاظ سے بہترین
        sorted_clean = sorted(student_scores, key=lambda x: x["avg_clean"], reverse=True)
        
        st.markdown("---")
        st.subheader("📚 تعلیمی کارکردگی کے لحاظ سے بہترین طالبات")
        col1, col2, col3 = st.columns(3)
        for i, student in enumerate(sorted_grade[:3]):
            with [col1, col2, col3][i]:
                medal = ["🥇", "🥈", "🥉"][i]
                color_class = ["gold", "silver", "bronze"][i]
                st.markdown(f"""
                <div class="best-student-card">
                    <h2 class="{color_class}">{medal}</h2>
                    <h3>{student['name']}</h3>
                    <p>والد: {student['father']}</p>
                    <p>شناختی نمبر: {student['roll'] or '-'}</p>
                    <p>شعبہ: {student['dept']}</p>
                    <p>اوسط نمبر: {student['avg_grade']:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🧹 صفائی کے لحاظ سے بہترین طالبات")
        col1, col2, col3 = st.columns(3)
        for i, student in enumerate(sorted_clean[:3]):
            with [col1, col2, col3][i]:
                medal = ["🥇", "🥈", "🥉"][i]
                color_class = ["gold", "silver", "bronze"][i]
                # صفائی اوسط کو فیصد میں تبدیل کریں (3 = 100%)
                clean_percent = (student['avg_clean'] / 3) * 100
                st.markdown(f"""
                <div class="best-student-card">
                    <h2 class="{color_class}">{medal}</h2>
                    <h3>{student['name']}</h3>
                    <p>والد: {student['father']}</p>
                    <p>شناختی نمبر: {student['roll'] or '-'}</p>
                    <p>شعبہ: {student['dept']}</p>
                    <p>صفائی اوسط: {clean_percent:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)
        
        # تمام طالبات کی تفصیلی ٹیبل
        with st.expander("📊 تمام طالبات کی تفصیلی کارکردگی"):
            df_all = pd.DataFrame(student_scores)
            df_all = df_all.rename(columns={
                "name": "نام", "father": "والد کا نام", "roll": "شناختی نمبر", "dept": "شعبہ",
                "avg_grade": "تعلیمی اوسط (%)", "avg_clean": "صفائی اوسط (0-3)"
            })
            df_all["تعلیمی اوسط (%)"] = df_all["تعلیمی اوسط (%)"].round(1)
            df_all["صفائی اوسط (0-3)"] = df_all["صفائی اوسط (0-3)"].round(2)
            st.dataframe(df_all, use_container_width=True)
            st.download_button("📥 CSV ڈاؤن لوڈ کریں", convert_df_to_csv(df_all), "monthly_best_students.csv")

# 8.15 بیک اپ & سیٹنگز
elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ اور سیٹنگز")
    st.subheader("📥 مکمل ڈیٹا بیس بیک اپ")
    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f:
            st.download_button(label="💾 ڈیٹا بیس فائل ڈاؤن لوڈ کریں (.db)", data=f,
                               file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                               mime="application/x-sqlite3")
    else:
        st.warning("ڈیٹا بیس فائل موجود نہیں")
    st.markdown("---")
    st.subheader("🔄 ڈیٹا بیس ریسٹور کریں (پوری .db فائل)")
    st.warning("⚠️ احتیاط: موجودہ ڈیٹا ختم ہو جائے گا! پہلے بیک اپ ضرور لیں۔")
    uploaded_db = st.file_uploader("پہلے سے محفوظ کردہ .db فائل منتخب کریں", type=["db"], key="db_upload")
    if uploaded_db is not None:
        confirm = st.checkbox("میں سمجھ گیا ہوں کہ موجودہ ڈیٹا ختم ہو جائے گا")
        if confirm and st.button("ریسٹور کریں (پوری ڈیٹا بیس)"):
            if os.path.exists(DB_NAME):
                shutil.copy(DB_NAME, f"{DB_NAME}_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            with open(DB_NAME, "wb") as f:
                f.write(uploaded_db.getbuffer())
            st.success("ڈیٹا بیس ریسٹور کر دیا گیا۔ براہ کرم ایپ کو دوبارہ چلائیں (ری لوڈ کریں)۔")
            st.rerun()
    st.markdown("---")
    st.subheader("📄 CSV فائلوں کا بیک اپ (زپ میں ڈاؤن لوڈ)")
    if st.button("💾 تمام ٹیبلز کی CSV بیک اپ (زپ) بنائیں"):
        tables = ["teachers", "students", "hifz_records", "qaida_records", "general_education", "t_attendance", "exams", "passed_paras", "timetable", "leave_requests", "notifications", "audit_log", "staff_monitoring"]
        conn = get_db_connection()
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for t in tables:
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    zip_file.writestr(f"{t}.csv", csv_data)
                except Exception as e:
                    st.warning(f"ٹیبل {t} کی بیک اپ میں خرابی: {str(e)}")
        conn.close()
        zip_buffer.seek(0)
        st.download_button(label="📥 CSV بیک اپ زپ ڈاؤن لوڈ کریں", data=zip_buffer,
                           file_name=f"backup_tables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                           mime="application/zip")
    st.markdown("---")
    st.subheader("📤 CSV فائل اپ لوڈ کر کے ڈیٹا ریسٹور کریں")
    st.info("یہاں آپ کسی ایک ٹیبل کی CSV فائل (پہلے بنائی گئی) اپ لوڈ کر سکتے ہیں۔ ڈیٹا خود بخود متعلقہ ٹیبل میں شامل ہو جائے گا۔")
    table_options = {
        "معلمات (teachers)": "teachers",
        "طالبات (students)": "students",
        "حفظ ریکارڈ (hifz_records)": "hifz_records",
        "قاعدہ ریکارڈ (qaida_records)": "qaida_records",
        "عمومی تعلیم (general_education)": "general_education",
        "امتحانات (exams)": "exams",
        "پاس شدہ پارے (passed_paras)": "passed_paras",
        "ٹائم ٹیبل (timetable)": "timetable",
        "رخصت درخواستیں (leave_requests)": "leave_requests",
        "نوٹیفیکیشنز (notifications)": "notifications",
        "عملہ نگرانی (staff_monitoring)": "staff_monitoring"
    }
    selected_table_display = st.selectbox("ٹیبل منتخب کریں", list(table_options.keys()))
    selected_table = table_options[selected_table_display]
    uploaded_csv = st.file_uploader("CSV فائل منتخب کریں (UTF-8 encoding)", type=["csv"], key="csv_upload")
    if uploaded_csv is not None:
        try:
            df = pd.read_csv(uploaded_csv)
            st.write("اپ لوڈ کی گئی CSV میں پہلی 5 قطاریں:")
            st.dataframe(df.head())
            upload_mode = st.radio("اپ لوڈ موڈ:", ["موجودہ ڈیٹا میں شامل کریں (Append)", "موجودہ ڈیٹا کو حذف کر کے نیا ڈالیں (Replace)"])
            if st.button("ڈیٹا ریسٹور کریں"):
                conn = get_db_connection()
                c = conn.cursor()
                if upload_mode == "موجودہ ڈیٹا کو حذف کر کے نیا ڈالیں (Replace)":
                    c.execute(f"DELETE FROM {selected_table}")
                    st.warning(f"{selected_table_display} کا پرانا ڈیٹا حذف کر دیا گیا۔")
                columns = df.columns.tolist()
                placeholders = ','.join(['?' for _ in columns])
                query = f"INSERT INTO {selected_table} ({','.join(columns)}) VALUES ({placeholders})"
                for _, row in df.iterrows():
                    c.execute(query, tuple(row[col] for col in columns))
                conn.commit()
                conn.close()
                log_audit(st.session_state.username, "CSV Restore", f"Table: {selected_table}, Mode: {upload_mode}")
                st.success(f"ڈیٹا کامیابی سے {selected_table_display} میں محفوظ ہو گیا۔")
                st.rerun()
        except Exception as e:
            st.error(f"خرابی: {str(e)}۔ یقینی بنائیں کہ CSV فائل صحیح فارمیٹ میں ہے۔")
    st.markdown("---")
    with st.expander("آڈٹ لاگ"):
        conn = get_db_connection()
        logs = pd.read_sql_query("SELECT user, action, timestamp, details FROM audit_log ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        st.dataframe(logs)

# ==================== 9. معلمہ کے سیکشن (مؤنث) ====================
# 9.1 روزانہ سبق اندراج (مؤنث)
if selected == "📝 روزانہ سبق اندراج" and st.session_state.user_type == "teacher":
    st.header("📝 روزانہ سبق اندراج")
    entry_date = st.date_input("تاریخ (جس دن کا اندراج کرنا ہے)", date.today())
    dept = st.selectbox("شعبہ منتخب کریں", ["حفظ", "قاعدہ", "درسِ نظامی", "عصری تعلیم"])
    
    if dept == "حفظ":
        st.subheader("حفظ کا اندراج")
        conn = get_db_connection()
        students = conn.execute("SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='حفظ'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("آپ کی کلاس میں کوئی طالبہ نہیں")
        else:
            for sid, s, f in students:
                key = f"{sid}_{s}_{f}"
                st.markdown(f"### 👤 {s} بنت {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_{key}")
                if att != "حاضر":
                    grade = calculate_grade_with_attendance(att, False, False, False, 0, 0)
                    st.info(f"**اس طالبہ کا درجہ:** {grade}")
                    if st.button(f"محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            c.execute("""INSERT INTO hifz_records 
                                        (r_date, student_id, t_name, surah, lines, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance, cleanliness)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (entry_date, sid, st.session_state.username, "غائب", 0, "غائب", 0, 0, "غائب", 0, 0, att, cleanliness))
                            conn.commit()
                            st.success("محفوظ ہو گیا")
                        conn.close()
                    st.markdown("---")
                    continue
                # سبق
                st.write("**سبق**")
                col1, col2 = st.columns(2)
                sabaq_nagha = col1.checkbox("ناغہ", key=f"sabaq_nagha_{key}")
                sabaq_yad_nahi = col2.checkbox("یاد نہیں", key=f"sabaq_yad_{key}")
                if sabaq_nagha or sabaq_yad_nahi:
                    sabaq_text = "ناغہ" if sabaq_nagha else "یاد نہیں"
                    lines = 0
                else:
                    surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{key}")
                    a_from = st.text_input("آیت (سے)", key=f"af_{key}")
                    a_to = st.text_input("آیت (تک)", key=f"at_{key}")
                    sabaq_text = f"{surah}: {a_from}-{a_to}"
                    lines = st.number_input("کل ستر (لائنوں کی تعداد)", min_value=0, value=0, key=f"lines_{key}")
                # سبقی
                st.write("**سبقی**")
                col1, col2 = st.columns(2)
                sq_nagha = col1.checkbox("ناغہ", key=f"sq_nagha_{key}")
                sq_yad_nahi = col2.checkbox("یاد نہیں", key=f"sq_yad_{key}")
                if sq_nagha or sq_yad_nahi:
                    sq_text = "ناغہ" if sq_nagha else "یاد نہیں"
                    sq_parts = [sq_text]
                    sq_a = 0
                    sq_m = 0
                else:
                    if f"sq_rows_{key}" not in st.session_state:
                        st.session_state[f"sq_rows_{key}"] = 1
                    sq_parts = []
                    sq_a = 0
                    sq_m = 0
                    for i in range(st.session_state[f"sq_rows_{key}"]):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", paras, key=f"sqp_{key}_{i}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{key}_{i}")
                        a = cols[2].number_input("اٹکن", 0, key=f"sqa_{key}_{i}")
                        e = cols[3].number_input("غلطی", 0, key=f"sqe_{key}_{i}")
                        sq_parts.append(f"{p}:{v}")
                        sq_a += a
                        sq_m += e
                    if st.button("➕", key=f"add_sq_{key}", help="مزید سبقی پارہ شامل کریں"):
                        st.session_state[f"sq_rows_{key}"] += 1
                        st.rerun()
                # منزل
                st.write("**منزل**")
                col1, col2 = st.columns(2)
                m_nagha = col1.checkbox("ناغہ", key=f"m_nagha_{key}")
                m_yad_nahi = col2.checkbox("یاد نہیں", key=f"m_yad_{key}")
                if m_nagha or m_yad_nahi:
                    m_text = "ناغہ" if m_nagha else "یاد نہیں"
                    m_parts = [m_text]
                    m_a = 0
                    m_m = 0
                else:
                    if f"m_rows_{key}" not in st.session_state:
                        st.session_state[f"m_rows_{key}"] = 1
                    m_parts = []
                    m_a = 0
                    m_m = 0
                    for j in range(st.session_state[f"m_rows_{key}"]):
                        cols = st.columns([2,2,1,1])
                        p = cols[0].selectbox("پارہ", paras, key=f"mp_{key}_{j}")
                        v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{key}_{j}")
                        a = cols[2].number_input("اٹکن", 0, key=f"ma_{key}_{j}")
                        e = cols[3].number_input("غلطی", 0, key=f"me_{key}_{j}")
                        m_parts.append(f"{p}:{v}")
                        m_a += a
                        m_m += e
                    if st.button("➕", key=f"add_m_{key}", help="مزید منزل پارہ شامل کریں"):
                        st.session_state[f"m_rows_{key}"] += 1
                        st.rerun()
                sabaq_nagha_bool = sabaq_nagha or sabaq_yad_nahi
                sq_nagha_bool = sq_nagha or sq_yad_nahi
                m_nagha_bool = m_nagha or m_yad_nahi
                grade = calculate_grade_with_attendance(att, sabaq_nagha_bool, sq_nagha_bool, m_nagha_bool, sq_m, m_m)
                st.info(f"**اس طالبہ کا درجہ:** {grade}")
                if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                    if chk:
                        st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                    else:
                        c.execute("""INSERT INTO hifz_records 
                                    (r_date, student_id, t_name, surah, lines, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance, cleanliness)
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                  (entry_date, sid, st.session_state.username, sabaq_text, lines,
                                   " | ".join(sq_parts), sq_a, sq_m,
                                   " | ".join(m_parts), m_a, m_m, att, cleanliness))
                        conn.commit()
                        log_audit(st.session_state.username, "Hifz Entry", f"{s} {entry_date}")
                        st.success("محفوظ ہو گیا")
                    conn.close()
                st.markdown("---")
    
    elif dept == "قاعدہ":
        st.subheader("قاعدہ (نورانی قاعدہ / نماز) کا اندراج")
        conn = get_db_connection()
        students = conn.execute("SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='قاعدہ'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("آپ کی کلاس میں کوئی طالبہ نہیں")
        else:
            for sid, s, f in students:
                key = f"{sid}_{s}_{f}"
                st.markdown(f"### 👤 {s} بنت {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_{key}")
                if att == "حاضر":
                    col1, col2 = st.columns(2)
                    nagha = col1.checkbox("ناغہ", key=f"nagha_{key}")
                    yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_nahi_{key}")
                    if nagha or yad_nahi:
                        lesson_no = "ناغہ" if nagha else "یاد نہیں"
                        total_lines = 0
                        details = ""
                    else:
                        lesson_type = st.radio("نوعیت", ["نورانی قاعدہ", "نماز (حنفی)"], key=f"lesson_type_{key}", horizontal=True)
                        if lesson_type == "نورانی قاعدہ":
                            lesson_no = st.text_input("تختی نمبر / سبق نمبر", key=f"lesson_{key}")
                            total_lines = st.number_input("کل لائنیں", min_value=0, value=0, key=f"lines_{key}")
                            details = ""
                        else:
                            lesson_no = st.selectbox("سبق منتخب کریں", [
                                "وضو کا طریقہ", "غسل کا طریقہ", "تیمم کا طریقہ",
                                "اذان و اقامت", "نماز کا طریقہ (مسنون)", "دعائے ثنا",
                                "سورہ فاتحہ", "سورہ اخلاص", "قنوت دعا", "تشہد", "درود شریف", "دعائے ختم نماز"
                            ], key=f"lesson_{key}")
                            total_lines = st.number_input("کل لائنیں (اگر کوئی ہوں)", min_value=0, value=0, key=f"lines_{key}")
                            details = st.text_area("تفصیل / نوٹ", key=f"details_{key}")
                    if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM qaida_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            c.execute("""INSERT INTO qaida_records 
                                        (r_date, student_id, t_name, lesson_no, total_lines, details, attendance, cleanliness)
                                        VALUES (?,?,?,?,?,?,?,?)""",
                                      (entry_date, sid, st.session_state.username, lesson_no, total_lines, details, att, cleanliness))
                            conn.commit()
                            log_audit(st.session_state.username, "Qaida Entry", f"{s} {entry_date}")
                            st.success("محفوظ ہو گیا")
                        conn.close()
                else:
                    if st.button(f"غیر حاضر / رخصت محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM qaida_records WHERE r_date=? AND student_id=?", (entry_date, sid)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے (تاریخ {entry_date})")
                        else:
                            c.execute("""INSERT INTO qaida_records 
                                        (r_date, student_id, t_name, lesson_no, total_lines, details, attendance, cleanliness)
                                        VALUES (?,?,?,?,?,?,?,?)""",
                                      (entry_date, sid, st.session_state.username, "غائب", 0, "", att, cleanliness))
                            conn.commit()
                            st.success("محفوظ ہو گیا")
                        conn.close()
                st.markdown("---")
    
    elif dept == "درسِ نظامی":
        st.subheader("درسِ نظامی سبق ریکارڈ")
        conn = get_db_connection()
        students = conn.execute("SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='درسِ نظامی'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("کوئی طالبہ نہیں")
        else:
            with st.form("dars_form"):
                records = []
                for sid, s, f in students:
                    st.markdown(f"### {s} بنت {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_dars_{sid}", horizontal=True)
                    cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_dars_{sid}")
                    if att == "حاضر":
                        col1, col2 = st.columns(2)
                        nagha = col1.checkbox("ناغہ", key=f"nagha_dars_{sid}")
                        yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_dars_{sid}")
                        if nagha or yad_nahi:
                            book = "ناغہ" if nagha else "یاد نہیں"
                            lesson = "ناغہ" if nagha else "یاد نہیں"
                            perf = "ناغہ" if nagha else "یاد نہیں"
                        else:
                            book = st.text_input("کتاب کا نام", key=f"book_{sid}")
                            lesson = st.text_area("آج کا سبق", key=f"lesson_{sid}")
                            perf = st.select_slider("کارکردگی", ["بہت بہتر", "بہتر", "مناسب", "کمزور"], key=f"perf_{sid}")
                        records.append((entry_date, sid, st.session_state.username, "درسِ نظامی", book, lesson, "", perf, att, cleanliness))
                    else:
                        records.append((entry_date, sid, st.session_state.username, "درسِ نظامی", "غائب", "غائب", "", "غائب", att, cleanliness))
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, student_id, t_name, dept, book_subject, today_lesson, performance, attendance, cleanliness) VALUES (?,?,?,?,?,?,?,?,?)",
                                  rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")
    
    elif dept == "عصری تعلیم":
        st.subheader("عصری تعلیم ڈائری")
        conn = get_db_connection()
        students = conn.execute("SELECT id, name, father_name FROM students WHERE teacher_name=? AND dept='عصری تعلیم'", (st.session_state.username,)).fetchall()
        conn.close()
        if not students:
            st.info("کوئی طالبہ نہیں")
        else:
            with st.form("school_form"):
                records = []
                for sid, s, f in students:
                    st.markdown(f"### {s} بنت {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_school_{sid}", horizontal=True)
                    cleanliness = st.selectbox("صفائی کا معیار", cleanliness_options, key=f"clean_school_{sid}")
                    if att == "حاضر":
                        col1, col2 = st.columns(2)
                        nagha = col1.checkbox("ناغہ", key=f"nagha_school_{sid}")
                        yad_nahi = col2.checkbox("یاد نہیں", key=f"yad_school_{sid}")
                        if nagha or yad_nahi:
                            subject = "ناغہ" if nagha else "یاد نہیں"
                            topic = "ناغہ" if nagha else "یاد نہیں"
                            hw = "ناغہ" if nagha else "یاد نہیں"
                        else:
                            subject = st.selectbox("مضمون", ["اردو", "انگلش", "ریاضی", "سائنس", "اسلامیات", "سماجی علوم"], key=f"sub_{sid}")
                            topic = st.text_input("عنوان", key=f"topic_{sid}")
                            hw = st.text_area("ہوم ورک", key=f"hw_{sid}")
                        records.append((entry_date, sid, st.session_state.username, "عصری تعلیم", subject, topic, hw, "", att, cleanliness))
                    else:
                        records.append((entry_date, sid, st.session_state.username, "عصری تعلیم", "غائب", "غائب", "غائب", "", att, cleanliness))
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, student_id, t_name, dept, book_subject, today_lesson, homework, performance, attendance, cleanliness) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                  rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")

# 9.2 امتحانی درخواست (مؤنث)
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    st.subheader("امتحان کے لیے طالبہ نامزد کریں")
    conn = get_db_connection()
    students = conn.execute("SELECT id, name, father_name, dept FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
    conn.close()
    if not students:
        st.warning("کوئی طالبہ نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s[1]} بنت {s[2]} ({s[3]})" for s in students]
            sel = st.selectbox("طالبہ", s_list)
            s_name, rest = sel.split(" بنت ")
            f_name, dept = rest.split(" (")
            dept = dept.replace(")", "")
            student_id = [s[0] for s in students if s[1] == s_name and s[2] == f_name][0]
            exam_type = st.selectbox("امتحان کی قسم", ["پارہ ٹیسٹ", "ماہانہ", "سہ ماہی", "سالانہ"])
            start_date = st.date_input("تاریخ ابتدا", date.today())
            end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
            total_days = (end_date - start_date).days + 1
            st.write(f"**کل دن:** {total_days}")
            from_para = 0
            to_para = 0
            book_name = ""
            amount_read = ""
            if exam_type == "پارہ ٹیسٹ":
                col1, col2 = st.columns(2)
                from_para = col1.number_input("پارہ نمبر (شروع)", min_value=1, max_value=30, value=1)
                to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=from_para)
            else:
                if dept == "حفظ":
                    col1, col2 = st.columns(2)
                    from_para = col1.number_input("پارہ نمبر (شروع)", min_value=1, max_value=30, value=1)
                    to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=min(from_para+4,30))
                    amount_read = st.text_input("مقدار خواندگی (مثلاً: 5 پارے, 10 سورتیں)", placeholder="مقدار")
                else:
                    col1, col2 = st.columns(2)
                    book_name = col1.text_input("کتاب کا نام", placeholder="مثلاً: نحو میر, قدوری")
                    amount_read = col2.text_input("مقدار خواندگی", placeholder="مثلاً: باب اول تا باب پنجم")
            if st.form_submit_button("بھیجیں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("""INSERT INTO exams 
                            (student_id, dept, exam_type, from_para, to_para, book_name, amount_read, start_date, end_date, total_days, status)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                          (student_id, dept, exam_type, from_para, to_para, book_name, amount_read, start_date, end_date, total_days, "پینڈنگ"))
                conn.commit()
                conn.close()
                st.success("درخواست بھیج دی گئی")

# 9.3 رخصت کی درخواست
elif selected == "📩 رخصت کی درخواست" and st.session_state.user_type == "teacher":
    st.header("📩 رخصت کی درخواست")
    with st.form("leave_request_form"):
        l_type = st.selectbox("رخصت کی نوعیت", ["بیماری", "ضروری کام", "ہنگامی", "دیگر"])
        start_date = st.date_input("تاریخ آغاز", date.today())
        days = st.number_input("دنوں کی تعداد", min_value=1, max_value=30, value=1)
        back_date = start_date + timedelta(days=days-1)
        st.write(f"واپسی کی تاریخ: {back_date}")
        reason = st.text_area("تفصیلی وجہ")
        if st.form_submit_button("درخواست جمع کریں"):
            if reason:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("""INSERT INTO leave_requests 
                            (t_name, l_type, start_date, days, reason, status, notification_seen, request_date)
                            VALUES (?,?,?,?,?,?,?,?)""",
                          (st.session_state.username, l_type, start_date, days, reason, "پینڈنگ", 0, date.today()))
                conn.commit()
                conn.close()
                log_audit(st.session_state.username, "Leave Requested", f"{l_type} for {days} days")
                st.success("درخواست بھیج دی گئی۔ منتظمین جلد جواب دیں گے۔")
            else:
                st.error("براہ کرم وجہ تحریر کریں")

# 9.4 میری حاضری
elif selected == "🕒 میری حاضری" and st.session_state.user_type == "teacher":
    st.header("🕒 میری حاضری")
    today = date.today()
    conn = get_db_connection()
    rec = conn.execute("SELECT arrival, departure FROM t_attendance WHERE t_name=? AND a_date=?", (st.session_state.username, today)).fetchone()
    conn.close()
    if not rec:
        col1, col2 = st.columns(2)
        arr_date = col1.date_input("تاریخ", today)
        arr_time = col2.time_input("آمد کا وقت", datetime.now().time())
        if st.button("آمد درج کریں"):
            time_str = arr_time.strftime("%I:%M %p")
            conn = get_db_connection()
            conn.execute("INSERT INTO t_attendance (t_name, a_date, arrival, actual_arrival) VALUES (?,?,?,?)",
                         (st.session_state.username, arr_date, time_str, get_pk_time()))
            conn.commit()
            conn.close()
            st.success("آمد درج ہو گئی")
            st.rerun()
    elif rec and rec[1] is None:
        st.success(f"آمد: {rec[0]}")
        dep_time = st.time_input("رخصت کا وقت", datetime.now().time())
        if st.button("رخصت درج کریں"):
            time_str = dep_time.strftime("%I:%M %p")
            conn = get_db_connection()
            conn.execute("UPDATE t_attendance SET departure=?, actual_departure=? WHERE t_name=? AND a_date=?",
                         (time_str, get_pk_time(), st.session_state.username, today))
            conn.commit()
            conn.close()
            st.success("رخصت درج ہو گئی")
            st.rerun()
    else:
        st.success(f"آمد: {rec[0]} | رخصت: {rec[1]}")

# 9.5 میرا ٹائم ٹیبل
elif selected == "📚 میرا ٹائم ٹیبل" and st.session_state.user_type == "teacher":
    st.header("📚 میرا ٹائم ٹیبل")
    conn = get_db_connection()
    tt_df = pd.read_sql_query("SELECT day as دن, period as وقت, book as کتاب, room as کمرہ FROM timetable WHERE t_name=?", conn, params=(st.session_state.username,))
    conn.close()
    if tt_df.empty:
        st.info("ابھی آپ کا ٹائم ٹیبل ترتیب نہیں دیا گیا")
    else:
        day_order = {"ہفتہ": 0, "اتوار": 1, "پیر": 2, "منگل": 3, "بدھ": 4, "جمعرات": 5}
        tt_df['day_order'] = tt_df['دن'].map(day_order)
        tt_df = tt_df.sort_values(['day_order', 'وقت'])
        pivot = tt_df.pivot(index='وقت', columns='دن', values='کتاب').fillna("—")
        st.dataframe(pivot, use_container_width=True)
        html_timetable = generate_timetable_html(tt_df)
        st.download_button("📥 HTML ڈاؤن لوڈ کریں", html_timetable, f"Timetable_{st.session_state.username}.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"):
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_timetable}`);w.print();</script>", height=0)

# ==================== 10. لاگ آؤٹ ====================
st.sidebar.divider()
if st.sidebar.button("🚪 لاگ آؤٹ"):
    st.session_state.logged_in = False
    st.rerun()
