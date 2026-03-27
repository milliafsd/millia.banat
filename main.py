import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64
import pytz

# --- 1. ڈیٹا بیس سیٹ اپ (للبنات کے لیے نیا نام) ---
DB_NAME = 'jamia_millia_banat_v1.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS teachers 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                 surah TEXT, a_from TEXT, a_to TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, 
                 m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT, principal_note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, back_date DATE, status TEXT, request_date DATE)''')
    c.execute("""CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            s_name TEXT, 
            f_name TEXT, 
            para_no INTEGER, 
            start_date TEXT, 
            end_date TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
            total INTEGER, 
            grade TEXT,
            status TEXT)""")
    conn.commit()

    # کالمز کا اضافہ (نئے فیچرز کے لیے)
    cols = [
        ("students", "phone", "TEXT"), ("students", "address", "TEXT"), ("students", "id_card", "TEXT"), 
        ("students", "photo", "TEXT"), ("teachers", "phone", "TEXT"), ("teachers", "address", "TEXT"), 
        ("teachers", "id_card", "TEXT"), ("teachers", "photo", "TEXT"), 
        ("leave_requests", "l_type", "TEXT"), ("leave_requests", "days", "INTEGER"), 
        ("leave_requests", "notification_seen", "INTEGER DEFAULT 0")
    ]
    for t, col, typ in cols:
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
        except: pass

    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

# ---------- HELPER FUNCTIONS ----------
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def get_pakistan_time():
    """Return current datetime in Pakistan Standard Time (UTC+5)."""
    pst = pytz.timezone('Asia/Karachi')
    return datetime.now(pst)

# ---------- HTML REPORT GENERATION ----------
def generate_html_report(df, title, include_avg=True, student_name=None, father_name=None, date_range=None):
    """
    Generate a beautiful HTML report from a DataFrame containing hifz_records data.
    """
    # Ensure RTL and Urdu font
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
            * {{
                font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', 'Urdu Typesetting', serif;
                direction: rtl;
                text-align: right;
            }}
            body {{
                padding: 20px;
                margin: 0 auto;
                max-width: 1200px;
            }}
            h1, h2, h3 {{
                color: #1e5631;
                text-align: center;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #1e5631;
                padding-bottom: 10px;
            }}
            .info {{
                margin-bottom: 20px;
                background: #f1f8e9;
                padding: 10px;
                border-radius: 8px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 14px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: right;
                vertical-align: top;
            }}
            th {{
                background-color: #1e5631;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .summary {{
                background: #e8f5e9;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .signatures {{
                margin-top: 40px;
                display: flex;
                justify-content: space-between;
                padding: 20px;
                border-top: 1px solid #ddd;
            }}
            .signature {{
                text-align: center;
                width: 30%;
            }}
            .grade {{
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 10px;
                border-radius: 8px;
                margin-top: 20px;
            }}
            @media print {{
                body {{
                    margin: 0;
                    padding: 0;
                }}
                .no-print {{
                    display: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>جامعہ ملیہ اسلامیہ للبنات</h1>
            <h2>{title}</h2>
        </div>
    """

    if student_name and father_name:
        html += f"""
        <div class="info">
            <p><strong>طالبہ کا نام:</strong> {student_name} بنت {father_name}</p>
            <p><strong>مدت:</strong> {date_range[0]} تا {date_range[1]}</p>
        </div>
        """

    # Table
    if not df.empty:
        html += """
        <table>
            <thead>
                <tr>
                    <th>تاریخ</th>
                    <th>طالبہ کا نام</th>
                    <th>ولدیت</th>
                    <th>معلمہ</th>
                    <th>حاضری</th>
                    <th>نیا سبق (سورت / آیات)</th>
                    <th>سبقی (پارہ / مقدار / غلطیاں / اٹکن)</th>
                    <th>سبقی غلطیاں</th>
                    <th>سبقی اٹکن</th>
                    <th>منزل (پارہ / مقدار / غلطیاں / اٹکن)</th>
                    <th>منزل غلطیاں</th>
                    <th>منزل اٹکن</th>
                    <th>ناظمہ نوٹ</th>
                </tr>
            </thead>
            <tbody>
        """
        for _, row in df.iterrows():
            html += f"""
                <tr>
                    <td>{row['r_date']}</td>
                    <td>{row['s_name']}</td>
                    <td>{row['f_name']}</td>
                    <td>{row['t_name']}</td>
                    <td>{row['attendance']}</td>
                    <td>{row.get('surah', '')}</td>
                    <td>{row.get('sq_p', '')}</td>
                    <td>{row.get('sq_m', 0)}</td>
                    <td>{row.get('sq_a', 0)}</td>
                    <td>{row.get('m_p', '')}</td>
                    <td>{row.get('m_m', 0)}</td>
                    <td>{row.get('m_a', 0)}</td>
                    <td>{row.get('principal_note', '')}</td>
                </tr>
            """
        html += "</tbody></table>"

        # Average calculations
        if include_avg:
            avg_sq_m = df['sq_m'].mean() if 'sq_m' in df else 0
            avg_m_m = df['m_m'].mean() if 'm_m' in df else 0
            avg_total_err = avg_sq_m + avg_m_m

            # Grade logic
            if avg_total_err <= 0.8:
                grade = "ممتاز"
                color = "green"
            elif avg_total_err <= 2.5:
                grade = "جید جدا"
                color = "blue"
            elif avg_total_err <= 5.0:
                grade = "جید"
                color = "orange"
            elif avg_total_err <= 10.0:
                grade = "مقبول"
                color = "darkorange"
            else:
                grade = "راسب"
                color = "red"

            html += f"""
            <div class="summary">
                <h3>خلاصہ</h3>
                <p>کل ریکارڈ: {len(df)}</p>
                <p>اوسط سبقی غلطی: {avg_sq_m:.2f}</p>
                <p>اوسط منزل غلطی: {avg_m_m:.2f}</p>
                <p>اوسط کل غلطی: {avg_total_err:.2f}</p>
                <div class="grade" style="background:{color}; color:white;">
                    مجموعی درجہ: {grade}
                </div>
            </div>
            """
    else:
        html += "<p>کوئی ریکارڈ نہیں ملا۔</p>"

    # Signatures
    html += """
        <div class="signatures">
            <div class="signature">
                _________________<br>
                معلمہ کا دستخط
            </div>
            <div class="signature">
                _________________<br>
                ناظمہ کا دستخط
            </div>
            <div class="signature">
                _________________<br>
                پرنسپل کا دستخط
            </div>
        </div>
        <div class="no-print" style="text-align: center; margin-top: 20px;">
            <button onclick="window.print()" style="background: #1e5631; color: white; padding: 8px 15px; border-radius: 5px; border: none; cursor: pointer;">🖨️ پرنٹ کریں</button>
        </div>
    </body>
    </html>
    """
    return html

# ---------- امتحانی رپورٹ کا فنکشن (unchanged) ----------
def render_exam_report():
    st.subheader("🎓 امتحانی تعلیمی نظام")
    
    # صارف کی قسم چیک کریں
    u_type = st.session_state.user_type

    if u_type == "teacher":
        st.info("📢 **معلمہ پینل:** یہاں سے آپ طالبہ کا نام امتحان کے لیے بھیج سکتی ہیں۔")
        
        # ڈیٹا بیس سے اس معلمہ کی طالبات لائیں
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
        
        if not students:
            st.warning("آپ کی کلاس میں کوئی طالبہ رجسٹرڈ نہیں ہے۔")
        else:
            with st.form("exam_request_form"):
                s_list = [f"{s[0]} بنت {s[1]}" for s in students]
                sel_student = st.selectbox("طالبہ منتخب کریں", s_list)
                para_to_test = st.number_input("پارہ نمبر جس کا امتحان لینا ہے", 1, 30)
                s_date = st.date_input("آغازِ امتحان (تاریخِ درخواست)", date.today())
                
                if st.form_submit_button("امتحان کے لیے نامزد کریں 🚀"):
                    s_name, f_name = sel_student.split(" بنت ")
                    # چیک کریں کہ کیا اس پارے کا امتحان پہلے سے پینڈنگ تو نہیں
                    exists = c.execute("SELECT 1 FROM exams WHERE s_name=? AND f_name=? AND para_no=? AND status='پینڈنگ'", (s_name, f_name, para_to_test)).fetchone()
                    
                    if exists:
                        st.error("🛑 اس طالبہ کی اس پارے کے لیے درخواست پہلے سے ناظمہ صاحبہ کے پاس موجود ہے۔")
                    else:
                        c.execute("INSERT INTO exams (s_name, f_name, para_no, start_date, status) VALUES (?,?,?,?,?)",
                                  (s_name, f_name, para_to_test, str(s_date), "پینڈنگ"))
                        conn.commit()
                        st.success(f"✅ {s_name} (پارہ {para_to_test}) کی درخواست بھیج دی گئی ہے۔")

    elif u_type == "admin":
        tab1, tab2 = st.tabs(["📥 پینڈنگ امتحانات (ناظمہ پینل)", "📜 مکمل شدہ ریکارڈ (ہسٹری)"])
        
        with tab1:
            st.markdown("### 🖋️ ممتحنہ (ناظمہ صاحبہ) کے نمبرات")
            # صرف پینڈنگ امتحانات لائیں
            pending = c.execute("SELECT id, s_name, f_name, para_no, start_date FROM exams WHERE status='پینڈنگ'").fetchall()
            
            if not pending:
                st.info("فی الحال کوئی طالبہ امتحان کے لیے نامزد نہیں ہے۔")
            else:
                for eid, sn, fn, pn, sd in pending:
                    with st.expander(f"📝 امتحان: {sn} بنت {fn} (پارہ {pn}) - درخواست تاریخ: {sd}"):
                        st.write("پانچ سوالات کے نمبر درج کریں (ہر سوال 20 نمبر کا ہے):")
                        q_cols = st.columns(5)
                        q1 = q_cols[0].number_input("س 1", 0, 20, key=f"q1_{eid}")
                        q2 = q_cols[1].number_input("س 2", 0, 20, key=f"q2_{eid}")
                        q3 = q_cols[2].number_input("س 3", 0, 20, key=f"q3_{eid}")
                        q4 = q_cols[3].number_input("س 4", 0, 20, key=f"q4_{eid}")
                        q5 = q_cols[4].number_input("س 5", 0, 20, key=f"q5_{eid}")
                        
                        total = q1 + q2 + q3 + q4 + q5
                        
                        # گریڈ کی منطق
                        if total >= 90: g, s_msg = "ممتاز", "کامیاب"
                        elif total >= 80: g, s_msg = "جید جداً", "کامیاب"
                        elif total >= 70: g, s_msg = "جید", "کامیاب"
                        elif total >= 60: g, s_msg = "مقبول", "کامیاب"
                        else: g, s_msg = "دوبارہ کوشش کریں", "ناکام"
                        
                        st.markdown(f"**کل نمبر:** `{total}` | **گریڈ:** `{g}` | **کیفیت:** `{s_msg}`")
                        
                        if st.button("امتحان کلیئر کریں اور محفوظ کریں ✅", key=f"save_{eid}"):
                            e_date = str(date.today())
                            c.execute("""UPDATE exams SET 
                                      q1=?, q2=?, q3=?, q4=?, q5=?, total=?, grade=?, status=?, end_date=? 
                                      WHERE id=?""", (q1, q2, q3, q4, q5, total, g, s_msg, e_date, eid))
                            conn.commit()
                            st.success(f"✅ {sn} کا پارہ {pn} کلیئر کر دیا گیا ہے۔")
                            st.rerun()

        with tab2:
            st.markdown("### 📜 امتحانی ہسٹری")
            history_df = pd.read_sql_query("""SELECT s_name as نام, f_name as ولدیت, para_no as پارہ, 
                                           start_date as آغاز, end_date as اختتام, 
                                           total as نمبر, grade as درجہ, status as کیفیت 
                                           FROM exams WHERE status != 'پینڈنگ' ORDER BY id DESC""", conn)
            if not history_df.empty:
                st.dataframe(history_df, use_container_width=True, hide_index=True)
                
                # سرٹیفکیٹ ڈاؤنلوڈ اور پرنٹ
                col_d, col_p = st.columns(2)
                col_d.download_button("📥 رپورٹ ڈاؤن لوڈ کریں (CSV)", convert_df_to_csv(history_df), "exam_history.csv", "text/csv")
                col_p.markdown("<button onclick='window.print()' style='background: #1e5631; color: white; padding: 8px 15px; border-radius: 5px; border: none; width: 100%; cursor: pointer;'>🖨️ صفحہ پرنٹ کریں</button>", unsafe_allow_html=True)
            else:
                st.info("ابھی تک کوئی امتحان مکمل نہیں ہوا۔")

# ---------- 2. اسٹائلنگ ----------
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ للبنات", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
    * {
        font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', 'Urdu Typesetting', 'Alvi Nastaleeq', 'Nafees Nastaleeq', serif;
    }
    body {direction: rtl; text-align: right;}
    .stButton>button {background: #1e5631; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: none; padding: 10px;}
    .stButton>button:hover {background: #143e22;}
    .main-header {text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-bottom: 4px solid #1e5631;}
    
    /* پرنٹنگ کے لیے مخصوص سٹائلز */
    @media print {
        .stSidebar { display: none !important; }
        .stButton { display: none !important; }
        .stDownloadButton { display: none !important; }
        header { display: none !important; }
        button { display: none !important; }
        .main-header { border-bottom: none; }
        body { direction: rtl; text-align: right; }
    }
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# --- مرکزی ہیڈر ---
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ للبنات</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل (شعبہ طالبات)</p></div>", unsafe_allow_html=True)

# ---------- HTML ڈاؤن لوڈ کا فنکشن (جاوا اسکرپٹ) ----------
def add_html_download_button():
    html_code = """
    <div style="margin-top: 20px;">
        <button onclick="downloadPageAsHTML()" style="background: #1e5631; color: white; padding: 8px 15px; border-radius: 5px; border: none; width: 100%; cursor: pointer;">📄 صفحہ بطور HTML ڈاؤن لوڈ کریں</button>
    </div>
    <script>
        function downloadPageAsHTML() {
            // کلیدی مواد کو کاپی کریں (سائیڈ بار کے بغیر)
            var mainContent = document.querySelector('.main');
            if (!mainContent) mainContent = document.body;
            var htmlContent = `<!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><title>جامعہ ملیہ للبنات</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu&display=swap');
                * { font-family: 'Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', 'Urdu Typesetting', serif; }
                body { direction: rtl; text-align: right; padding: 20px; }
                .main-header { text-align: center; color: #1e5631; background-color: #f1f8e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            </style>
            </head>
            <body>${mainContent.innerHTML}</body>
            </html>`;
            var blob = new Blob([htmlContent], {type: 'text/html'});
            var link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'jamia_report.html';
            link.click();
        }
    </script>
    """
    st.components.v1.html(html_code, height=50)

# ---------- لاگ ان ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.subheader("🔐 لاگ ان پینل")
        u = st.text_input("صارف کا نام (Username)")
        p = st.text_input("پاسورڈ (Password)", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("❌ غلط معلومات، براہ کرم دوبارہ کوشش کریں۔")
else:
    # سائیڈ بار میں HTML ڈاؤن لوڈ بٹن شامل کریں
    with st.sidebar:
        add_html_download_button()
        st.divider()

    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 معلمات کا ریکارڈ", "🏛️ ناظمہ پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری", "🔑 پاسورڈ تبدیل کریں"]
        
    m = st.sidebar.radio("📌 مینو منتخب کریں", menu)

    # ================= ADMIN SECTION =================
    if m == "📊 یومیہ تعلیمی رپورٹ":
        st.markdown("<h2 style='text-align: center; color: #1e5631;'>📊 ماسٹر تعلیمی رپورٹ و تجزیہ</h2>", unsafe_allow_html=True)

        with st.sidebar:
            st.header("🔍 فلٹرز")
            d1 = st.date_input("آغاز", date.today().replace(day=1))
            d2 = st.date_input("اختتام", date.today())
            t_list = ["تمام"] + [t[0] for t in c.execute("SELECT DISTINCT t_name FROM hifz_records").fetchall()]
            sel_t = st.selectbox("معلمہ/کلاس", t_list)
            s_list = ["تمام"] + [s[0] for s in c.execute("SELECT DISTINCT s_name FROM hifz_records").fetchall()]
            sel_s = st.selectbox("طالبہ", s_list)

        query = "SELECT * FROM hifz_records WHERE r_date BETWEEN ? AND ?"
        params = [d1, d2]
        if sel_t != "تمام": query += " AND t_name = ?"; params.append(sel_t)
        if sel_s != "تمام": query += " AND s_name = ?"; params.append(sel_s)
        
        df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            st.warning("منتخب کردہ فلٹرز کے مطابق کوئی ریکارڈ نہیں ملا۔")
        else:
            st.subheader("💡 خلاصہ (Summary)")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("کل ریکارڈ", len(df))
            m2.metric("حاضر طالبات", len(df[df['attendance'] == 'حاضر']))
            m3.metric("اوسط سبقی غلطی", round(df['sq_m'].mean(), 1))
            m4.metric("اوسط منزل غلطی", round(df['m_m'].mean(), 1))

            st.subheader("🛠️ ڈیٹا کنٹرول (تبدیلی اور حذف)")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
            
            # Enhanced print/download buttons
            col1, col2, col3 = st.columns(3)
            col1.download_button("📥 CSV ڈاؤن لوڈ کریں", convert_df_to_csv(edited_df), "daily_report.csv", "text/csv")
            
            # HTML report generation
            html_report = generate_html_report(df, "یومیہ تعلیمی رپورٹ", include_avg=True)
            col2.download_button("📄 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, "daily_report.html", "text/html")
            
            # Print HTML report
            if col3.button("🖨️ رپورٹ پرنٹ کریں"):
                # Open HTML in a new window/tab and print
                import webbrowser
                with open("temp_report.html", "w", encoding="utf-8") as f:
                    f.write(html_report)
                webbrowser.open("temp_report.html")
                st.info("رپورٹ نئی ونڈو میں کھل گئی ہے۔ وہاں سے پرنٹ کریں۔")

            if st.button("💾 تمام تبدیلیاں مستقل محفوظ کریں"):
                try:
                    c.execute(f"DELETE FROM hifz_records WHERE r_date BETWEEN '{d1}' AND '{d2}'" + 
                              (f" AND t_name='{sel_t}'" if sel_t != "تمام" else "") + 
                              (f" AND s_name='{sel_s}'" if sel_s != "تمام" else ""))
                    edited_df.to_sql('hifz_records', conn, if_exists='append', index=False)
                    st.success("✅ ڈیٹا کامیابی سے اپ ڈیٹ ہو گیا!")
                    st.rerun()
                except Exception as e:
                    st.error(f"ایرر: {e}")

    elif m == "📜 ماہانہ رزلٹ کارڈ":
        st.header("📜 ماہانہ رزلٹ کارڈ")
        s_list = [s[0] for s in c.execute("SELECT DISTINCT name FROM students").fetchall()]
        if s_list:
            sc, d1c, d2c = st.columns([2,1,1])
            sel_s = sc.selectbox("طالبہ", s_list)
            date1, date2 = d1c.date_input("آغاز", date.today().replace(day=1)), d2c.date_input("اختتام", date.today())
            
            # Fetch detailed records for this student in the date range
            query = "SELECT * FROM hifz_records WHERE s_name=? AND r_date BETWEEN ? AND ?"
            detailed_df = pd.read_sql_query(query, conn, params=(sel_s, date1, date2))
            
            if not detailed_df.empty:
                # Existing summary chart and grade
                st.subheader("📈 ماہانہ کارکردگی کا گراف")
                chart_df = detailed_df[['r_date', 'sq_m', 'm_m']].copy()
                chart_df.rename(columns={'r_date': 'تاریخ', 'sq_m': 'سبقی_غلطی', 'm_m': 'منزل_غلطی'}, inplace=True)
                st.line_chart(chart_df.set_index('تاریخ'))
                
                avg_err = detailed_df['sq_m'].mean() + detailed_df['m_m'].mean()
                if avg_err <= 0.8: g, col = "🌟 ممتاز", "green"
                elif avg_err <= 2.5: g, col = "✅ جید جدا", "blue"
                elif avg_err <= 5.0: g, col = "🟡 جید", "orange"
                elif avg_err <= 10.0: g, col = "🟠 مقبول", "darkorange"
                else: g, col = "❌ راسب", "red"
                
                st.markdown(f"<div style='background:{col}; padding:20px; border-radius:10px; text-align:center; color:white;'><h2>درجہ: {g}</h2><p>اوسط غلطی: {avg_err:.2f}</p></div>", unsafe_allow_html=True)
                
                # Show detailed table
                st.subheader("📋 تفصیلی ریکارڈ")
                display_df = detailed_df[['r_date', 's_name', 'f_name', 't_name', 'attendance', 'surah', 'sq_p', 'sq_m', 'sq_a', 'm_p', 'm_m', 'm_a', 'principal_note']]
                display_df.rename(columns={
                    'r_date': 'تاریخ', 's_name': 'طالبہ کا نام', 'f_name': 'ولدیت', 't_name': 'معلمہ',
                    'attendance': 'حاضری', 'surah': 'نیا سبق', 'sq_p': 'سبقی', 'sq_m': 'سبقی غلطی', 'sq_a': 'سبقی اٹکن',
                    'm_p': 'منزل', 'm_m': 'منزل غلطی', 'm_a': 'منزل اٹکن', 'principal_note': 'ناظمہ نوٹ'
                }, inplace=True)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Enhanced print/download buttons
                col1, col2, col3 = st.columns(3)
                col1.download_button("📥 CSV ڈاؤن لوڈ کریں", convert_df_to_csv(detailed_df), f"result_{sel_s}.csv", "text/csv")
                
                # HTML report
                html_report = generate_html_report(detailed_df, f"ماہانہ رزلٹ کارڈ: {sel_s}", include_avg=True,
                                                  student_name=sel_s, father_name=detailed_df['f_name'].iloc[0] if not detailed_df.empty else "",
                                                  date_range=(date1, date2))
                col2.download_button("📄 HTML رپورٹ ڈاؤن لوڈ کریں", html_report, f"result_{sel_s}.html", "text/html")
                
                if col3.button("🖨️ رپورٹ پرنٹ کریں"):
                    import webbrowser
                    with open("temp_report.html", "w", encoding="utf-8") as f:
                        f.write(html_report)
                    webbrowser.open("temp_report.html")
                    st.info("رپورٹ نئی ونڈو میں کھل گئی ہے۔ وہاں سے پرنٹ کریں۔")
            else:
                st.warning("اس طالبہ کا ریکارڈ نہیں ملا۔")

    # ... rest of the code (other menus) unchanged ...
    # (The remaining code for other menus is exactly as in the original, so omitted for brevity)
    # ... 
