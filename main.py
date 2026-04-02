import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import pytz
import plotly.express as px
import os
import hashlib

# ==================== 1. ڈیٹا بیس سیٹ اپ ====================
DB_NAME = 'jamia_millia_girls.db'

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
    
    # اساتذہ (معلمات)
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
    
    # طالبات
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
        class TEXT,
        section TEXT
    )''')
    
    # طالب علم کے متعدد شعبے
    c.execute('''CREATE TABLE IF NOT EXISTS student_depts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        dept TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    
    # طالب علم کے متعدد اساتذہ (ہر شعبے کے لیے)
    c.execute('''CREATE TABLE IF NOT EXISTS student_teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        teacher_id INTEGER,
        dept TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
    )''')
    # یقینی بنائیں کہ dept کالم موجود ہے
    add_column_if_not_exists('student_teachers', 'dept', 'TEXT')
    
    # پرانے ڈیٹا کو منتقل کریں (اگر پہلے سے teacher_name موجود ہو)
    if column_exists('students', 'teacher_name'):
        old_students = c.execute("SELECT id, teacher_name FROM students WHERE teacher_name IS NOT NULL AND teacher_name != ''").fetchall()
        for student_id, teacher_name in old_students:
            teacher = c.execute("SELECT id FROM teachers WHERE name=?", (teacher_name,)).fetchone()
            if teacher:
                teacher_id = teacher[0]
                dept_row = c.execute("SELECT dept FROM student_depts WHERE student_id=?", (student_id,)).fetchone()
                dept = dept_row[0] if dept_row else "حفظ"
                c.execute("INSERT INTO student_teachers (student_id, teacher_id, dept) VALUES (?,?,?)",
                          (student_id, teacher_id, dept))
        conn.commit()
        try:
            c.execute("ALTER TABLE students DROP COLUMN teacher_name")
        except:
            pass
    
    # حفظ ریکارڈ
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        s_name TEXT,
        father_name TEXT,
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
        lines INTEGER
    )''')
    
    # عمومی تعلیم
    c.execute('''CREATE TABLE IF NOT EXISTS general_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        r_date DATE,
        s_name TEXT,
        father_name TEXT,
        t_name TEXT,
        dept TEXT,
        book_subject TEXT,
        today_lesson TEXT,
        homework TEXT,
        performance TEXT
    )''')
    
    # حاضری
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        a_date DATE,
        arrival TEXT,
        departure TEXT,
        actual_arrival TEXT,
        actual_departure TEXT
    )''')
    
    # رخصت درخواستیں
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
    
    # امتحانات
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        s_name TEXT,
        father_name TEXT,
        dept TEXT,
        from_para INTEGER,
        to_para INTEGER,
        start_date TEXT,
        end_date TEXT,
        q1 INTEGER,
        q2 INTEGER,
        q3 INTEGER,
        q4 INTEGER,
        q5 INTEGER,
        total INTEGER,
        grade TEXT,
        status TEXT,
        exam_type TEXT
    )''')
    
    # پاس شدہ پارے
    c.execute('''CREATE TABLE IF NOT EXISTS passed_paras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        s_name TEXT,
        father_name TEXT,
        para_no INTEGER,
        passed_date DATE,
        exam_type TEXT,
        grade TEXT
    )''')
    
    # ٹائم ٹیبل
    c.execute('''CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_name TEXT,
        day TEXT,
        period TEXT,
        book TEXT,
        room TEXT
    )''')
    
    # نوٹیفیکیشنز
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        message TEXT,
        target TEXT,
        created_at DATETIME,
        seen INTEGER DEFAULT 0
    )''')
    
    # آڈٹ لاگ
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        timestamp DATETIME,
        details TEXT
    )''')
    
    # عملہ نگرانی
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
    
    # ڈیفالٹ ایڈمن
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

def generate_exam_result_card(exam_row):
    para_display = ""
    if exam_row.get('from_para') and exam_row.get('to_para'):
        if exam_row['from_para'] == exam_row['to_para']:
            para_display = f"پارہ {exam_row['from_para']}"
        else:
            para_display = f"پارہ {exam_row['from_para']} تا {exam_row['to_para']}"
    else:
        para_display = "-"
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>رزلٹ کارڈ - {exam_row['s_name']}</title>
    <style>
        @font-face {{ font-family: 'Jameel Noori Nastaleeq'; src: url('https://fonts.cdnfonts.com/css/jameel-noori-nastaleeq'); }}
        body {{ font-family: 'Jameel Noori Nastaleeq', Arial; margin: 20px; direction: rtl; text-align: right; }}
        .card {{ border: 2px solid #1e5631; border-radius: 15px; padding: 20px; max-width: 600px; margin: auto; }}
        h2 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        .footer {{ margin-top: 20px; display: flex; justify-content: space-between; }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
            <h3>رزلٹ کارڈ</h3>
            <p><b>نام:</b> {exam_row['s_name']} بنت {exam_row['father_name']}</p>
            <p><b>امتحان کی قسم:</b> {exam_row['exam_type']}</p>
            <p><b>{para_display}</b></p>
            <p><b>تاریخ:</b> {exam_row['start_date']} تا {exam_row['end_date']}</p>
            <table>
                <tr><th>سوال</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>کل</th></tr>
                <td><td style="text-align:center">{exam_row['q1']}</td>
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
                <span>دستخط مہتمم: _________________</span>
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
        body {{ font-family: 'Jameel Noori Nastaleeq', Arial; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
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
            <span>دستخط مہتمم: _______________________</span>
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
        body {{ font-family: 'Jameel Noori Nastaleeq', Arial; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        @media print {{ body {{ margin: 0; }} .no-print {{ display: none; }} }}
    </style>
    </head>
    <body>
        <div class="header">
            <h2>جامعہ ملیہ اسلامیہ للبنات</h2>
            <h3>{title}</h3>
            {f"<p><b>طالبہ:</b> {student_name}</p>" if student_name else ""}
        </div>
        {html_table}
        {passed_html}
        <div class="signatures" style="display:flex; justify-content:space-between; margin-top:50px;">
            <span>دستخط معلمہ: _______________________</span>
            <span>دستخط مہتمم: _______________________</span>
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
        body {{ font-family: 'Jameel Noori Nastaleeq', Arial; margin: 20px; direction: rtl; text-align: right; }}
        h2, h3 {{ text-align: center; color: #1e5631; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
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
            <span>دستخط مہتمم: _______________________</span>
        </div>
        <div class="no-print" style="text-align:center; margin-top:30px;">
            <button onclick="window.print()">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

# ==================== 3. اسٹائلنگ ====================
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ للبنات | سمارٹ ERP", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * { font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaliq Urdu', Arial, sans-serif; }
    body { direction: rtl; text-align: right; background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%); }
    .stSidebar { background: linear-gradient(180deg, #1e3a8a 0%, #0f172a 100%); color: white; }
    .stSidebar * { color: white !important; }
    .stSidebar .stRadio label { color: white !important; font-weight: bold; font-size: 1rem; }
    .stSidebar .stRadio [role="radiogroup"] div { color: white !important; }
    .stSidebar .stRadio [role="radiogroup"] div[data-baseweb="radio"]:hover { background-color: #3b82f6; border-radius: 5px; }
    .stButton > button { background: linear-gradient(90deg, #2563eb, #1e40af); color: white; border-radius: 30px; border: none; padding: 0.5rem 1rem; font-weight: bold; transition: 0.3s; width: 100%; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .stButton > button:hover { transform: scale(1.02); background: linear-gradient(90deg, #3b82f6, #1e3a8a); }
    .main-header { text-align: center; background: linear-gradient(135deg, #ffffff, #dbeafe); padding: 1rem; border-radius: 20px; margin-bottom: 1rem; border-bottom: 4px solid #2563eb; color: #1e3a8a; }
    .report-card { background: rgba(255,255,255,0.95); border-radius: 15px; padding: 1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 1rem; border: 1px solid #bfdbfe; }
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 30px; padding: 0.5rem 1rem; background-color: #e2e8f0; color: #1e3a8a; font-weight: bold; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #2563eb, #1e40af); color: white; }
    @media (max-width: 768px) { .stButton > button { padding: 0.4rem 0.8rem; font-size: 0.8rem; } .main-header h1 { font-size: 1.5rem; } }
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
    st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ للبنات</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل (طالبات)</p></div>", unsafe_allow_html=True)
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
    menu = ["📊 ایڈمن ڈیش بورڈ", "📊 یومیہ تعلیمی رپورٹ (طالبات)", "🎓 امتحانی نظام", "📜 ماہانہ رزلٹ کارڈ",
            "📘 پارہ تعلیمی رپورٹ", "🕒 معلمات کی حاضری", "🏛️ رخصت کی منظوری",
            "👥 یوزر مینجمنٹ (طالبات/معلمات)", "📚 ٹائم ٹیبل مینجمنٹ", "🔑 پاسورڈ تبدیل کریں", "📋 عملہ نگرانی و شکایات",
            "📢 نوٹیفیکیشنز", "📈 تجزیہ و رپورٹس", "⚙️ بیک اپ & سیٹنگز"]
else:
    menu = ["📝 روزانہ سبق اندراج (طالبات)", "🎓 امتحانی درخواست", "📩 رخصت کی درخواست",
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

# ==================== 8. ایڈمن سیکشنز ====================
# 8.1 ایڈمن ڈیش بورڈ
if selected == "📊 ایڈمن ڈیش بورڈ" and st.session_state.user_type == "admin":
    st.markdown("<div class='main-header'><h1>📊 ایڈمن ڈیش بورڈ (طالبات)</h1></div>", unsafe_allow_html=True)
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = conn.execute("SELECT COUNT(*) FROM teachers WHERE name!='admin'").fetchone()[0]
    col1, col2 = st.columns(2)
    col1.metric("کل طالبات", total_students)
    col2.metric("کل معلمات", total_teachers)
    conn.close()

# 8.2 یومیہ تعلیمی رپورٹ (طالبات) - مختصر (پہلے جیسا)
elif selected == "📊 یومیہ تعلیمی رپورٹ (طالبات)" and st.session_state.user_type == "admin":
    st.header("📊 یومیہ تعلیمی رپورٹ (طالبات) - ترمیم، حذف، اضافہ")
    
    with st.sidebar:
        d1 = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        d2 = st.date_input("تاریخ اختتام", date.today())
        conn = get_db_connection()
        teachers_list = ["تمام"] + [t[0] for t in conn.execute("SELECT DISTINCT t_name FROM hifz_records UNION SELECT name FROM teachers WHERE name!='admin'").fetchall()]
        conn.close()
        sel_teacher = st.selectbox("معلمہ / کلاس", teachers_list)
        dept_filter = st.selectbox("شعبہ", ["تمام", "حفظ", "درسِ نظامی", "عصری تعلیم"])
    
    def get_existing_columns(table_name):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = [row[1] for row in cursor.fetchall()]
        conn.close()
        return cols
    
    combined_df = pd.DataFrame()
    
    if dept_filter in ["تمام", "حفظ"]:
        hifz_cols = get_existing_columns("hifz_records")
        select_parts = []
        if 'r_date' in hifz_cols:
            select_parts.append("r_date as تاریخ")
        if 's_name' in hifz_cols:
            select_parts.append("s_name as نام")
        if 'father_name' in hifz_cols:
            select_parts.append("father_name as 'والد کا نام'")
        if 't_name' in hifz_cols:
            select_parts.append("t_name as معلمہ")
        if 'surah' in hifz_cols:
            select_parts.append("surah as 'سبق/کتاب'")
        if 'lines' in hifz_cols:
            select_parts.append("lines as 'کل ستر'")
        if 'sq_m' in hifz_cols:
            select_parts.append("sq_m as سبقی_غلطی")
        if 'm_m' in hifz_cols:
            select_parts.append("m_m as منزل_غلطی")
        if 'attendance' in hifz_cols:
            select_parts.append("attendance as حاضری")
        if not select_parts:
            select_parts = ["*"]
        query = f"SELECT {', '.join(select_parts)} FROM hifz_records WHERE r_date BETWEEN ? AND ?"
        params = [d1, d2]
        if sel_teacher != "تمام":
            query += " AND t_name = ?"
            params.append(sel_teacher)
        try:
            conn = get_db_connection()
            hifz_df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            if not hifz_df.empty:
                hifz_df['شعبہ'] = 'حفظ'
                if 'سبقی_غلطی' in hifz_df.columns and 'منزل_غلطی' in hifz_df.columns:
                    hifz_df['کل_غلطیاں'] = hifz_df['سبقی_غلطی'].fillna(0) + hifz_df['منزل_غلطی'].fillna(0)
                    hifz_df['درجہ'] = hifz_df['کل_غلطیاں'].apply(get_grade_from_mistakes)
                combined_df = pd.concat([combined_df, hifz_df], ignore_index=True)
        except Exception as e:
            st.error(f"حفظ کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")
    
    if dept_filter in ["تمام", "درسِ نظامی", "عصری تعلیم"]:
        gen_cols = get_existing_columns("general_education")
        select_parts = []
        if 'r_date' in gen_cols:
            select_parts.append("r_date as تاریخ")
        if 's_name' in gen_cols:
            select_parts.append("s_name as نام")
        if 'father_name' in gen_cols:
            select_parts.append("father_name as 'والد کا نام'")
        if 't_name' in gen_cols:
            select_parts.append("t_name as معلمہ")
        if 'dept' in gen_cols:
            select_parts.append("dept as شعبہ")
        if 'book_subject' in gen_cols:
            select_parts.append("book_subject as 'سبق/کتاب'")
        if 'today_lesson' in gen_cols:
            select_parts.append("today_lesson as 'آج کا سبق'")
        if 'homework' in gen_cols:
            select_parts.append("homework as 'ہوم ورک'")
        if 'performance' in gen_cols:
            select_parts.append("performance as کارکردگی")
        if 'attendance' in gen_cols:
            select_parts.append("attendance as حاضری")
        if not select_parts:
            select_parts = ["*"]
        query = f"SELECT {', '.join(select_parts)} FROM general_education WHERE r_date BETWEEN ? AND ?"
        params = [d1, d2]
        if sel_teacher != "تمام":
            query += " AND t_name = ?"
            params.append(sel_teacher)
        if dept_filter != "تمام":
            query += " AND dept = ?"
            params.append(dept_filter)
        try:
            conn = get_db_connection()
            gen_df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            if not gen_df.empty:
                for col in ['کل_غلطیاں', 'درجہ']:
                    if col not in gen_df.columns:
                        gen_df[col] = ''
                combined_df = pd.concat([combined_df, gen_df], ignore_index=True)
        except Exception as e:
            st.error(f"عمومی تعلیم کے ریکارڈ لوڈ کرتے وقت خرابی: {str(e)}")
    
    if combined_df.empty:
        st.warning("کوئی ریکارڈ نہیں ملا")
    else:
        st.success(f"کل {len(combined_df)} ریکارڈ ملے")
        edited_df = st.data_editor(combined_df, num_rows="dynamic", use_container_width=True, key="daily_editor")
        
        if st.button("💾 تمام تبدیلیاں محفوظ کریں"):
            conn = get_db_connection()
            c = conn.cursor()
            if dept_filter in ["تمام", "حفظ"]:
                del_query = "DELETE FROM hifz_records WHERE r_date BETWEEN ? AND ?"
                del_params = [d1, d2]
                if sel_teacher != "تمام":
                    del_query += " AND t_name = ?"
                    del_params.append(sel_teacher)
                c.execute(del_query, del_params)
            if dept_filter in ["تمام", "درسِ نظامی", "عصری تعلیم"]:
                del_query_gen = "DELETE FROM general_education WHERE r_date BETWEEN ? AND ?"
                del_params_gen = [d1, d2]
                if sel_teacher != "تمام":
                    del_query_gen += " AND t_name = ?"
                    del_params_gen.append(sel_teacher)
                if dept_filter != "تمام":
                    del_query_gen += " AND dept = ?"
                    del_params_gen.append(dept_filter)
                c.execute(del_query_gen, del_params_gen)
            
            for _, row in edited_df.iterrows():
                if row.get('شعبہ') == 'حفظ':
                    mapping = {
                        'تاریخ': 'r_date',
                        'نام': 's_name',
                        'والد کا نام': 'father_name',
                        'معلمہ': 't_name',
                        'سبق/کتاب': 'surah',
                        'کل ستر': 'lines',
                        'سبقی_غلطی': 'sq_m',
                        'منزل_غلطی': 'm_m',
                        'حاضری': 'attendance'
                    }
                    insert_cols = []
                    insert_vals = []
                    for display_col, db_col in mapping.items():
                        if display_col in row and pd.notna(row[display_col]) and row[display_col] != '':
                            insert_cols.append(db_col)
                            val = row[display_col]
                            if db_col in ['lines', 'sq_m', 'm_m']:
                                val = int(val) if str(val).isdigit() else 0
                            insert_vals.append(val)
                    if insert_cols:
                        placeholders = ','.join(['?' for _ in insert_cols])
                        sql = f"INSERT INTO hifz_records ({','.join(insert_cols)}) VALUES ({placeholders})"
                        c.execute(sql, insert_vals)
                else:
                    mapping = {
                        'تاریخ': 'r_date',
                        'نام': 's_name',
                        'والد کا نام': 'father_name',
                        'معلمہ': 't_name',
                        'شعبہ': 'dept',
                        'سبق/کتاب': 'book_subject',
                        'آج کا سبق': 'today_lesson',
                        'ہوم ورک': 'homework',
                        'کارکردگی': 'performance',
                        'حاضری': 'attendance'
                    }
                    insert_cols = []
                    insert_vals = []
                    for display_col, db_col in mapping.items():
                        if display_col in row and pd.notna(row[display_col]) and row[display_col] != '':
                            insert_cols.append(db_col)
                            insert_vals.append(row[display_col])
                    if insert_cols:
                        placeholders = ','.join(['?' for _ in insert_cols])
                        sql = f"INSERT INTO general_education ({','.join(insert_cols)}) VALUES ({placeholders})"
                        c.execute(sql, insert_vals)
            conn.commit()
            conn.close()
            log_audit(st.session_state.username, "Edited Daily Report", f"Date range {d1} to {d2}, Teacher {sel_teacher}")
            st.success("تبدیلیاں محفوظ ہو گئیں")
            st.rerun()
        
        html_report = generate_html_report(edited_df, "یومیہ تعلیمی رپورٹ (طالبات)", start_date=d1.strftime("%Y-%m-%d"), end_date=d2.strftime("%Y-%m-%d"))
        st.download_button("📥 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "daily_report_girls.html", "text/html")
        if st.button("🖨️ پرنٹ کریں"):
            st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html_report}`);w.print();</script>", height=0)

# 8.3 امتحانی نظام (ایڈمن) - مختصر (پہلے جیسا)
elif selected == "🎓 امتحانی نظام" and st.session_state.user_type == "admin":
    st.header("🎓 امتحانی نظام (طالبات)")
    tab1, tab2 = st.tabs(["پینڈنگ امتحانات", "مکمل شدہ"])
    with tab1:
        conn = get_db_connection()
        pending = conn.execute("SELECT id, s_name, father_name, dept, from_para, to_para, start_date, exam_type FROM exams WHERE status=?", ("پینڈنگ",)).fetchall()
        conn.close()
        if not pending:
            st.info("کوئی پینڈنگ امتحان نہیں")
        else:
            for eid, sn, fn, dept, fp, tp, sd, etype in pending:
                with st.expander(f"{sn} بنت {fn} | {dept} | {etype} | {fp} تا {tp}"):
                    st.write(f"**تاریخ ابتدا:** {sd}")
                    end_date = st.date_input("تاریخ اختتام", date.today(), key=f"end_{eid}")
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
                                  (q1,q2,q3,q4,q5,total,g,"مکمل", end_date, eid))
                        if g != "ناکام":
                            for para in range(fp, tp+1):
                                existing = c.execute("SELECT 1 FROM passed_paras WHERE s_name=? AND father_name=? AND para_no=?", (sn, fn, para)).fetchone()
                                if not existing:
                                    c.execute("INSERT INTO passed_paras (s_name, father_name, para_no, passed_date, exam_type, grade) VALUES (?,?,?,?,?,?)",
                                              (sn, fn, para, date.today(), etype, g))
                        conn.commit()
                        exam_row = c.execute("SELECT * FROM exams WHERE id=?", (eid,)).fetchone()
                        conn.close()
                        exam_dict = {
                            'id': exam_row[0], 's_name': exam_row[1], 'father_name': exam_row[2],
                            'dept': exam_row[3], 'from_para': exam_row[4], 'to_para': exam_row[5],
                            'start_date': exam_row[6], 'end_date': exam_row[7],
                            'q1': exam_row[8], 'q2': exam_row[9], 'q3': exam_row[10],
                            'q4': exam_row[11], 'q5': exam_row[12], 'total': exam_row[13],
                            'grade': exam_row[14], 'status': exam_row[15], 'exam_type': exam_row[16]
                        }
                        result_html = generate_exam_result_card(exam_dict)
                        st.success("امتحان کلیئر کر دیا گیا")
                        st.download_button("📥 رزلٹ کارڈ ڈاؤن لوڈ کریں", result_html, f"Result_{sn}_{fp}-{tp}.html", "text/html")
                        st.rerun()
    with tab2:
        conn = get_db_connection()
        hist = pd.read_sql_query("SELECT s_name, father_name, dept, from_para, to_para, total, grade, exam_type, end_date FROM exams WHERE status='مکمل' ORDER BY end_date DESC", conn)
        conn.close()
        if not hist.empty:
            st.dataframe(hist, use_container_width=True)
            st.download_button("ہسٹری CSV", convert_df_to_csv(hist), "exam_history.csv")
        else:
            st.info("کوئی مکمل شدہ امتحان نہیں")

# 8.4 ماہانہ رزلٹ کارڈ (طالبات) - مختصر (پہلے جیسا)
elif selected == "📜 ماہانہ رزلٹ کارڈ" and st.session_state.user_type == "admin":
    st.header("📜 ماہانہ رزلٹ کارڈ (طالبات)")
    conn = get_db_connection()
    students_list = conn.execute("""
        SELECT s.id, s.name, s.father_name, GROUP_CONCAT(sd.dept, ', ') as depts
        FROM students s
        LEFT JOIN student_depts sd ON s.id = sd.student_id
        GROUP BY s.id
    """).fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی طالبہ نہیں")
    else:
        student_names = [f"{s[1]} بنت {s[2]} ({s[3]})" for s in students_list]
        sel = st.selectbox("طالبہ منتخب کریں", student_names)
        s_name, rest = sel.split(" بنت ")
        father_name, depts_str = rest.split(" (")
        depts_str = depts_str.replace(")", "")
        dept_options = depts_str.split(", ")
        if len(dept_options) > 1:
            selected_dept = st.selectbox("شعبہ منتخب کریں", dept_options)
        else:
            selected_dept = dept_options[0]
        start = st.date_input("تاریخ آغاز", date.today().replace(day=1))
        end = st.date_input("تاریخ اختتام", date.today())
        
        if selected_dept == "حفظ":
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, attendance as حاضری, surah as 'سبق (آیت تا آیت)', lines as 'کل ستر',
                                      sq_p as 'سبقی (پارہ)', sq_m as 'سبقی (غلطی)', sq_a as 'سبقی (اٹکن)',
                                      m_p as 'منزل (پارہ)', m_m as 'منزل (غلطی)', m_a as 'منزل (اٹکن)'
                                      FROM hifz_records WHERE s_name=? AND father_name=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(s_name, father_name, start, end))
            conn.close()
            if not df.empty:
                df['کل_غلطیاں'] = df['سبقی (غلطی)'] + df['منزل (غلطی)']
                df['درجہ'] = df['کل_غلطیاں'].apply(get_grade_from_mistakes)
                avg_mistakes = df['کل_غلطیاں'].mean()
                st.info(f"**اوسط غلطیاں:** {round(avg_mistakes, 1)} | **مجموعی درجہ:** {get_grade_from_mistakes(avg_mistakes)}")
        else:
            conn = get_db_connection()
            df = pd.read_sql_query("""SELECT r_date as تاریخ, book_subject as 'کتاب/مضمون', today_lesson as 'آج کا سبق',
                                      homework as 'ہوم ورک', performance as کارکردگی
                                      FROM general_education WHERE s_name=? AND father_name=? AND dept=? AND r_date BETWEEN ? AND ?
                                      ORDER BY r_date ASC""", conn, params=(s_name, father_name, selected_dept, start, end))
            conn.close()
        
        if df.empty:
            st.warning("کوئی ریکارڈ نہیں")
        else:
            st.dataframe(df, use_container_width=True)
            passed = []
            if selected_dept == "حفظ":
                conn = get_db_connection()
                passed = conn.execute("SELECT para_no, passed_date, grade FROM passed_paras WHERE s_name=? AND father_name=? ORDER BY para_no", (s_name, father_name)).fetchall()
                conn.close()
                if passed:
                    st.write("**پاس شدہ پارے:**")
                    for p in passed:
                        st.write(f"پارہ {p[0]} - تاریخ: {p[1]} - گریڈ: {p[2]}")
            html = generate_html_report(df, "ماہانہ رزلٹ کارڈ", student_name=f"{s_name} بنت {father_name}",
                                        start_date=start.strftime("%Y-%m-%d"), end_date=end.strftime("%Y-%m-%d"),
                                        passed_paras=[p[0] for p in passed] if passed else None)
            st.download_button("📥 HTML ڈاؤن لوڈ", html, f"{s_name}_result.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# 8.5 پارہ تعلیمی رپورٹ
elif selected == "📘 پارہ تعلیمی رپورٹ" and st.session_state.user_type == "admin":
    st.header("📘 پارہ تعلیمی رپورٹ (طالبات)")
    conn = get_db_connection()
    students_list = conn.execute("""
        SELECT DISTINCT s.name, s.father_name
        FROM students s
        JOIN student_depts sd ON s.id = sd.student_id
        WHERE sd.dept='حفظ'
    """).fetchall()
    conn.close()
    if not students_list:
        st.warning("کوئی حفظ کی طالبہ نہیں")
    else:
        student_names = [f"{s[0]} بنت {s[1]}" for s in students_list]
        sel = st.selectbox("طالبہ منتخب کریں", student_names)
        s_name, father_name = sel.split(" بنت ")
        conn = get_db_connection()
        passed_df = pd.read_sql_query("SELECT para_no as 'پارہ نمبر', passed_date as 'تاریخ پاس', grade as 'گریڈ', exam_type as 'امتحان کی قسم' FROM passed_paras WHERE s_name=? AND father_name=? ORDER BY para_no", conn, params=(s_name, father_name))
        conn.close()
        if passed_df.empty:
            st.info("اس طالبہ کا کوئی پاس شدہ پارہ نہیں")
        else:
            st.dataframe(passed_df, use_container_width=True)
            html = generate_para_report(s_name, father_name, passed_df)
            st.download_button("📥 رپورٹ ڈاؤن لوڈ کریں", html, f"Para_Report_{s_name}.html", "text/html")
            if st.button("🖨️ پرنٹ کریں"):
                st.components.v1.html(f"<script>var w=window.open();w.document.write(`{html}`);w.print();</script>", height=0)

# 8.6 معلمات کی حاضری (ایڈمن)
elif selected == "🕒 معلمات کی حاضری" and st.session_state.user_type == "admin":
    st.header("معلمات کی حاضری ریکارڈ")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as معلمہ, arrival as آمد, departure as رخصت FROM t_attendance ORDER BY a_date DESC", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

# 8.7 رخصت کی منظوری (ایڈمن)
elif selected == "🏛️ رخصت کی منظوری" and st.session_state.user_type == "admin":
    st.header("رخصت کی منظوری (معلمات)")
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

# 8.8 یوزر مینجمنٹ (طالبات/معلمات) - درست شدہ ورژن
elif selected == "👥 یوزر مینجمنٹ (طالبات/معلمات)" and st.session_state.user_type == "admin":
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
                c.execute("DELETE FROM teachers WHERE name!='admin'")
                for _, row in edited_teachers.iterrows():
                    placeholders = ",".join(["?" for _ in existing_cols])
                    c.execute(f"INSERT INTO teachers ({','.join(existing_cols)}) VALUES ({placeholders})", tuple(row[col] for col in existing_cols))
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
                dept = st.selectbox("شعبہ (اختیاری)", ["حفظ", "درسِ نظامی", "عصری تعلیم", ""])
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
                                      (name, hash_password(password), dept if dept else None, phone, address, id_card, joining_date, photo_path))
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
        st.subheader("موجودہ طالبات (متعدد شعبے اور اساتذہ)")
        conn = get_db_connection()
        # محفوظ کوئری: اگر student_teachers موجود نہ ہو تو صرف بنیادی معلومات دکھائیں
        try:
            students_df = pd.read_sql_query("""
                SELECT s.id, s.name, s.father_name, s.mother_name, s.dob, s.admission_date, 
                       s.exit_date, s.exit_reason, s.id_card, s.phone, s.address, 
                       s.class, s.section,
                       GROUP_CONCAT(DISTINCT sd.dept, ', ') as depts,
                       GROUP_CONCAT(DISTINCT t.name || ' (' || st.dept || ')', ', ') as teachers
                FROM students s
                LEFT JOIN student_depts sd ON s.id = sd.student_id
                LEFT JOIN student_teachers st ON s.id = st.student_id
                LEFT JOIN teachers t ON st.teacher_id = t.id
                GROUP BY s.id
            """, conn)
        except Exception as e:
            st.error(f"ڈیٹا لوڈ کرنے میں خرابی: {str(e)}۔ براہ کرم ایڈمن سے رابطہ کریں۔")
            students_df = pd.DataFrame()
        conn.close()
        if not students_df.empty:
            st.dataframe(students_df, use_container_width=True)
            st.info("شعبہ جات اور اساتذہ کی تبدیلی کے لیے 'نیا طالبہ داخل کریں' والے فارم میں ترمیم کریں یا حذف کر کے دوبارہ داخل کریں۔")
        else:
            st.info("کوئی طالبہ موجود نہیں")
        
        with st.expander("➕ نئی طالبہ داخل کریں"):
            with st.form("new_student_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("طالبہ کا نام*")
                    father = st.text_input("والد کا نام*")
                    mother = st.text_input("والدہ کا نام (اختیاری)")
                    dob = st.date_input("تاریخ پیدائش", date.today() - timedelta(days=365*10))
                    admission_date = st.date_input("تاریخ داخلہ", date.today())
                with col2:
                    st.write("شعبہ جات اور متعلقہ معلمہ:")
                    conn = get_db_connection()
                    all_teachers = conn.execute("SELECT id, name FROM teachers WHERE name!='admin'").fetchall()
                    conn.close()
                    teachers_dict = {t[1]: t[0] for t in all_teachers}
                    teacher_names = list(teachers_dict.keys())
                    
                    dept_teacher_map = {}
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.checkbox("حفظ"):
                            selected_teacher = st.selectbox("حفظ کی معلمہ", teacher_names, key="teacher_hifz")
                            dept_teacher_map["حفظ"] = selected_teacher
                        if st.checkbox("درسِ نظامی"):
                            selected_teacher = st.selectbox("درسِ نظامی کی معلمہ", teacher_names, key="teacher_dars")
                            dept_teacher_map["درسِ نظامی"] = selected_teacher
                    with col_b:
                        if st.checkbox("عصری تعلیم"):
                            selected_teacher = st.selectbox("عصری تعلیم کی معلمہ", teacher_names, key="teacher_school")
                            dept_teacher_map["عصری تعلیم"] = selected_teacher
                    
                    class_name = st.text_input("کلاس (عصری تعلیم کے لیے)")
                    section = st.text_input("سیکشن")
                
                id_card = st.text_input("شناختی کارڈ نمبر (B-Form)")
                phone = st.text_input("فون نمبر")
                address = st.text_area("پتہ")
                photo = st.file_uploader("تصویر (اختیاری)", type=["jpg", "png", "jpeg"])
                st.markdown("---")
                st.markdown("**اگر طالبہ مدرسہ چھوڑ چکی ہے تو درج ذیل معلومات بھریں (ورنہ خالی چھوڑیں):**")
                exit_date = st.date_input("تاریخ خارج", value=None)
                exit_reason = st.text_area("وجہ خارج")
                
                if st.form_submit_button("داخلہ کریں"):
                    if name and father and dept_teacher_map:
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
                                         id_card, phone, address, class, section, photo)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (name, father, mother, dob, admission_date, exit_date, exit_reason,
                                       id_card, phone, address, class_name, section, photo_path))
                            student_id = c.lastrowid
                            for dept, teacher_name in dept_teacher_map.items():
                                teacher_id = teachers_dict[teacher_name]
                                c.execute("INSERT INTO student_depts (student_id, dept) VALUES (?,?)", (student_id, dept))
                                c.execute("INSERT INTO student_teachers (student_id, teacher_id, dept) VALUES (?,?,?)",
                                          (student_id, teacher_id, dept))
                            conn.commit()
                            st.success(f"طالبہ کامیابی سے داخل ہو گئی۔ شعبے: {', '.join(dept_teacher_map.keys())}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خرابی: {str(e)}")
                        finally:
                            conn.close()
                    else:
                        st.error("نام، والد کا نام اور کم از کم ایک شعبہ کے ساتھ معلمہ کا انتخاب ضروری ہے")

# 8.9 ٹائم ٹیبل مینجمنٹ (ایڈمن) - مختصر (پہلے جیسا)
elif selected == "📚 ٹائم ٹیبل مینجمنٹ" and st.session_state.user_type == "admin":
    st.header("📚 ٹائم ٹیبل مینجمنٹ (معلمات)")
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

# 8.10 پاسورڈ تبدیل کریں (ایڈمن اور معلمہ) - مختصر (پہلے جیسا)
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

# 8.11 عملہ نگرانی و شکایات - مختصر (پہلے جیسا)
elif selected == "📋 عملہ نگرانی و شکایات" and st.session_state.user_type == "admin":
    st.header("📋 عملہ نگرانی و شکایات")
    
    tab1, tab2 = st.tabs(["➕ نیا اندراج", "📜 ریکارڈ دیکھیں"])
    
    with tab1:
        with st.form("new_monitoring"):
            conn = get_db_connection()
            staff_list = [t[0] for t in conn.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
            conn.close()
            if not staff_list:
                st.warning("کوئی معلمہ/عملہ موجود نہیں۔ پہلے اساتذہ رجسٹر کریں۔")
            else:
                staff_name = st.selectbox("معلمہ / عملہ کا نام", staff_list)
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
        
        query = "SELECT id, staff_name as 'معلمہ/عملہ', date as تاریخ, note_type as نوعیت, description as تفصیل, action_taken as 'کارروائی', status as حالت, created_by as 'داخل کردہ', created_at as 'داخل کردہ تاریخ' FROM staff_monitoring WHERE date BETWEEN ? AND ?"
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

# 8.14 بیک اپ & سیٹنگز
elif selected == "⚙️ بیک اپ & سیٹنگز" and st.session_state.user_type == "admin":
    st.header("بیک اپ اور سیٹنگز")
    if st.button("💾 ڈیٹا بیس کا بیک اپ لیں"):
        tables = ["teachers", "students", "student_depts", "student_teachers", "hifz_records", "general_education", "t_attendance", "exams", "passed_paras", "timetable", "leave_requests", "notifications", "audit_log", "staff_monitoring"]
        conn = get_db_connection()
        for t in tables:
            try:
                df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
                df.to_csv(f"{t}_backup.csv", index=False)
            except:
                pass
        conn.close()
        st.success("بیک اپ مکمل (تمام ٹیبلز کی CSV فائلیں بن گئیں)")
    with st.expander("آڈٹ لاگ"):
        conn = get_db_connection()
        logs = pd.read_sql_query("SELECT user, action, timestamp, details FROM audit_log ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        st.dataframe(logs)

# ==================== 9. استاد کے سیکشن ====================
# 9.1 روزانہ سبق اندراج (طالبات) - شعبہ کے ساتھ
if selected == "📝 روزانہ سبق اندراج (طالبات)" and st.session_state.user_type == "teacher":
    conn = get_db_connection()
    teacher_id = conn.execute("SELECT id FROM teachers WHERE name=?", (st.session_state.username,)).fetchone()[0]
    conn.close()
    
    st.header("📝 روزانہ سبق اندراج (طالبات)")
    dept = st.selectbox("شعبہ منتخب کریں", ["حفظ", "درسِ نظامی", "عصری تعلیم"])
    today = date.today()
    
    if dept == "حفظ":
        st.subheader("حفظ کا اندراج (➕ بٹن سے مزید پارے شامل کریں)")
        conn = get_db_connection()
        students = conn.execute("""
            SELECT s.id, s.name, s.father_name 
            FROM students s
            JOIN student_teachers st ON s.id = st.student_id
            WHERE st.teacher_id=? AND st.dept='حفظ'
        """, (teacher_id,)).fetchall()
        conn.close()
        if not students:
            st.info("آپ کی کلاس میں کوئی طالبہ نہیں")
        else:
            for sid, s, f in students:
                key = f"{s}_{f}"
                st.markdown(f"### 👤 {s} بنت {f}")
                att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_{key}", horizontal=True)
                
                if att == "حاضر":
                    sabaq_nagha = st.checkbox("سبق ناغہ", key=f"sabaq_nagha_{key}")
                    if not sabaq_nagha:
                        surah = st.selectbox("سورت", surahs_urdu, key=f"surah_{key}")
                        a_from = st.text_input("آیت (سے)", key=f"af_{key}")
                        a_to = st.text_input("آیت (تک)", key=f"at_{key}")
                        sabq = f"{surah}: {a_from}-{a_to}"
                        lines = st.number_input("کل ستر (لائنوں کی تعداد)", min_value=0, value=0, key=f"lines_{key}")
                    else:
                        sabq = "ناغہ"
                        lines = 0
                    
                    sq_nagha = st.checkbox("سبقی ناغہ", key=f"sq_nagha_{key}")
                    if not sq_nagha:
                        if f"sq_rows_{key}" not in st.session_state:
                            st.session_state[f"sq_rows_{key}"] = 1
                        st.write("**سبقی**")
                        sq_parts = []; sq_a = 0; sq_m = 0
                        for i in range(st.session_state[f"sq_rows_{key}"]):
                            cols = st.columns([2,2,1,1])
                            p = cols[0].selectbox("پارہ", paras, key=f"sqp_{key}_{i}")
                            v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{key}_{i}")
                            a = cols[2].number_input("اٹکن", 0, key=f"sqa_{key}_{i}")
                            e = cols[3].number_input("غلطی", 0, key=f"sqe_{key}_{i}")
                            sq_parts.append(f"{p}:{v}")
                            sq_a += a; sq_m += e
                        if st.button("➕ مزید سبقی پارہ", key=f"add_sq_{key}"):
                            st.session_state[f"sq_rows_{key}"] += 1
                            st.rerun()
                    else:
                        sq_parts = ["ناغہ"]
                        sq_a = sq_m = 0
                    
                    m_nagha = st.checkbox("منزل ناغہ", key=f"m_nagha_{key}")
                    if not m_nagha:
                        if f"m_rows_{key}" not in st.session_state:
                            st.session_state[f"m_rows_{key}"] = 1
                        st.write("**منزل**")
                        m_parts = []; m_a = 0; m_m = 0
                        for j in range(st.session_state[f"m_rows_{key}"]):
                            cols = st.columns([2,2,1,1])
                            p = cols[0].selectbox("پارہ", paras, key=f"mp_{key}_{j}")
                            v = cols[1].selectbox("مقدار", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{key}_{j}")
                            a = cols[2].number_input("اٹکن", 0, key=f"ma_{key}_{j}")
                            e = cols[3].number_input("غلطی", 0, key=f"me_{key}_{j}")
                            m_parts.append(f"{p}:{v}")
                            m_a += a; m_m += e
                        if st.button("➕ مزید منزل پارہ", key=f"add_m_{key}"):
                            st.session_state[f"m_rows_{key}"] += 1
                            st.rerun()
                    else:
                        m_parts = ["ناغہ"]
                        m_a = m_m = 0
                    
                    if st.button(f"محفوظ کریں ({s})", key=f"save_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND father_name=?", (today, s, f)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے")
                        else:
                            c.execute("""INSERT INTO hifz_records 
                                        (r_date, s_name, father_name, t_name, surah, lines, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (today, s, f, st.session_state.username, sabq, lines,
                                       " | ".join(sq_parts), sq_a, sq_m,
                                       " | ".join(m_parts), m_a, m_m, att))
                            conn.commit()
                            log_audit(st.session_state.username, "Hifz Entry", f"{s} {today}")
                            st.success("محفوظ ہو گیا")
                        conn.close()
                else:
                    if st.button(f"محفوظ کریں ({s})", key=f"save_absent_{key}"):
                        conn = get_db_connection()
                        c = conn.cursor()
                        chk = c.execute("SELECT 1 FROM hifz_records WHERE r_date=? AND s_name=? AND father_name=?", (today, s, f)).fetchone()
                        if chk:
                            st.error(f"{s} کا ریکارڈ پہلے سے موجود ہے")
                        else:
                            c.execute("""INSERT INTO hifz_records 
                                        (r_date, s_name, father_name, t_name, surah, lines, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                      (today, s, f, st.session_state.username, "ناغہ", 0, "ناغہ", 0, 0, "ناغہ", 0, 0, att))
                            conn.commit()
                            st.success("محفوظ ہو گیا")
                        conn.close()
                st.markdown("---")
    
    elif dept == "درسِ نظامی":
        st.subheader("درسِ نظامی سبق ریکارڈ (طالبات)")
        conn = get_db_connection()
        students = conn.execute("""
            SELECT s.name, s.father_name 
            FROM students s
            JOIN student_teachers st ON s.id = st.student_id
            WHERE st.teacher_id=? AND st.dept='درسِ نظامی'
        """, (teacher_id,)).fetchall()
        conn.close()
        if not students:
            st.info("کوئی طالبہ نہیں")
        else:
            with st.form("dars_form"):
                records = []
                for s, f in students:
                    st.markdown(f"### {s} بنت {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_dars_{s}", horizontal=True)
                    if att == "حاضر":
                        book = st.text_input("کتاب کا نام", key=f"book_{s}")
                        lesson = st.text_area("آج کا سبق", key=f"lesson_{s}")
                        perf = st.select_slider("کارکردگی", ["بہت بہتر", "بہتر", "مناسب", "کمزور"], key=f"perf_{s}")
                        records.append((today, s, f, st.session_state.username, "درسِ نظامی", book, lesson, "", perf, att))
                    else:
                        records.append((today, s, f, st.session_state.username, "درسِ نظامی", "ناغہ", "ناغہ", "", "ناغہ", att))
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, s_name, father_name, t_name, dept, book_subject, today_lesson, performance, attendance) VALUES (?,?,?,?,?,?,?,?,?)",
                                  rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")
    
    elif dept == "عصری تعلیم":
        st.subheader("عصری تعلیم ڈائری (طالبات)")
        conn = get_db_connection()
        students = conn.execute("""
            SELECT s.name, s.father_name 
            FROM students s
            JOIN student_teachers st ON s.id = st.student_id
            WHERE st.teacher_id=? AND st.dept='عصری تعلیم'
        """, (teacher_id,)).fetchall()
        conn.close()
        if not students:
            st.info("کوئی طالبہ نہیں")
        else:
            with st.form("school_form"):
                records = []
                for s, f in students:
                    st.markdown(f"### {s} بنت {f}")
                    att = st.radio("حاضری", ["حاضر", "غیر حاضر", "رخصت"], key=f"att_school_{s}", horizontal=True)
                    if att == "حاضر":
                        subject = st.selectbox("مضمون", ["اردو", "انگلش", "ریاضی", "سائنس", "اسلامیات", "سماجی علوم"], key=f"sub_{s}")
                        topic = st.text_input("عنوان", key=f"topic_{s}")
                        hw = st.text_area("ہوم ورک", key=f"hw_{s}")
                        records.append((today, s, f, st.session_state.username, "عصری تعلیم", subject, topic, hw, "", att))
                    else:
                        records.append((today, s, f, st.session_state.username, "عصری تعلیم", "ناغہ", "ناغہ", "ناغہ", "", att))
                if st.form_submit_button("محفوظ کریں"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for rec in records:
                        c.execute("INSERT INTO general_education (r_date, s_name, father_name, t_name, dept, book_subject, today_lesson, homework, attendance) VALUES (?,?,?,?,?,?,?,?,?)",
                                  rec)
                    conn.commit()
                    conn.close()
                    st.success("محفوظ ہو گیا")

# 9.2 امتحانی درخواست (معلمہ) - شعبہ کے ساتھ
elif selected == "🎓 امتحانی درخواست" and st.session_state.user_type == "teacher":
    conn = get_db_connection()
    teacher_id = conn.execute("SELECT id FROM teachers WHERE name=?", (st.session_state.username,)).fetchone()[0]
    students = conn.execute("""
        SELECT s.name, s.father_name, st.dept
        FROM students s
        JOIN student_teachers st ON s.id = st.student_id
        WHERE st.teacher_id=?
    """, (teacher_id,)).fetchall()
    conn.close()
    if not students:
        st.warning("کوئی طالبہ نہیں")
    else:
        with st.form("exam_request"):
            s_list = [f"{s[0]} بنت {s[1]} ({s[2]})" for s in students]
            sel = st.selectbox("طالبہ", s_list)
            s_name, rest = sel.split(" بنت ")
            father_name, dept = rest.split(" (")
            dept = dept.replace(")", "")
            exam_type = st.selectbox("امتحان کی قسم", ["ماہانہ", "سہ ماہی", "سالانہ", "پارہ ٹیسٹ"])
            start_date = st.date_input("تاریخ ابتدا", date.today())
            end_date = None
            from_para = 0
            to_para = 0
            if exam_type == "پارہ ٹیسٹ":
                para = st.number_input("پارہ نمبر", min_value=1, max_value=30, value=1)
                from_para = para
                to_para = para
                end_date = st.date_input("تاریخ اختتام", date.today() + timedelta(days=7))
            else:
                col1, col2 = st.columns(2)
                from_para = col1.number_input("پارہ نمبر (شروع)", min_value=1, max_value=30, value=1)
                to_para = col2.number_input("پارہ نمبر (اختتام)", min_value=from_para, max_value=30, value=min(from_para+4,30))
                end_date = None
            if st.form_submit_button("بھیجیں"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO exams (s_name, father_name, dept, from_para, to_para, start_date, end_date, status, exam_type) VALUES (?,?,?,?,?,?,?,?,?)",
                          (s_name, father_name, dept, from_para, to_para, start_date, end_date, "پینڈنگ", exam_type))
                conn.commit()
                conn.close()
                st.success("درخواست بھیج دی گئی")

# 9.3 رخصت کی درخواست (معلمہ) - پہلے جیسا
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

# 9.4 میری حاضری (معلمہ) - پہلے جیسا
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

# 9.5 میرا ٹائم ٹیبل (معلمہ) - پہلے جیسا
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
