import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import base64

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

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# --- امتحانی رپورٹ کا فنکشن ---
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

# --- 2. اسٹائلنگ ---
st.set_page_config(page_title="جامعہ ملیہ اسلامیہ للبنات", layout="wide")
st.markdown("""
<style>
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
    }
</style>
""", unsafe_allow_html=True)

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحریم", "الملک", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القیامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التکویر", "الإنفطار", "المطففین", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشیة", "الفجر", "البلد", "الشمس", "اللیل", "الضحى", "الشرح", "التین", "العلق", "القدر", "البینة", "الزلزلة", "العادیات", "القارعة", "التکاثر", "العصر", "الهمزة", "الفیل", "قریش", "الماعون", "الکوثر", "الکافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

# --- مرکزی ہیڈر ---
st.markdown("<div class='main-header'><h1>🕌 جامعہ ملیہ اسلامیہ للبنات</h1><p>اسمارٹ تعلیمی و انتظامی پورٹل (شعبہ طالبات)</p></div>", unsafe_allow_html=True)

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
    if st.session_state.user_type == "admin":
        menu = ["📊 یومیہ تعلیمی رپورٹ", "🎓 امتحانی تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 معلمات کا ریکارڈ", "🏛️ ناظمہ پینل (رخصت)", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "🎓 امتحانی تعلیمی رپورٹ", "📩 درخواستِ رخصت", "🕒 میری حاضری"]
        
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
            
            # پرنٹ اور ڈاؤنلوڈ بٹن
            cd1, cd2 = st.columns(2)
            cd1.download_button("📥 ڈیٹا ڈاؤن لوڈ کریں (CSV)", convert_df_to_csv(edited_df), "daily_report.csv", "text/csv")
            cd2.markdown("<button onclick='window.print()' style='background: #1e5631; color: white; padding: 8px 15px; border-radius: 5px; border: none; width: 100%; cursor: pointer;'>🖨️ رپورٹ پرنٹ کریں</button>", unsafe_allow_html=True)

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
            res_df = pd.read_sql_query(f"SELECT r_date as تاریخ, surah as سورت, sq_m as سبقی_غلطی, m_m as منزل_غلطی, principal_note as رائے FROM hifz_records WHERE s_name='{sel_s}' AND r_date BETWEEN '{date1}' AND '{date2}'", conn)

            if not res_df.empty:
                st.line_chart(res_df.set_index('تاریخ')[['سبقی_غلطی', 'منزل_غلطی']])
                avg_err = res_df['سبقی_غلطی'].mean() + res_df['منزل_غلطی'].mean()
                if avg_err <= 0.8: g, col = "🌟 ممتاز", "green"
                elif avg_err <= 2.5: g, col = "✅ جید جدا", "blue"
                elif avg_err <= 5.0: g, col = "🟡 جید", "orange"
                elif avg_err <= 10.0: g, col = "🟠 مقبول", "darkorange"
                else: g, col = "❌ راسب", "red"
                
                st.markdown(f"<div style='background:{col}; padding:20px; border-radius:10px; text-align:center; color:white;'><h2>درجہ: {g}</h2><p>اوسط غلطی: {avg_err:.2f}</p></div>", unsafe_allow_html=True)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                
                cd1, cd2 = st.columns(2)
                cd1.download_button("📥 رزلٹ کارڈ ڈاؤن لوڈ کریں", convert_df_to_csv(res_df), f"result_{sel_s}.csv", "text/csv")
                cd2.markdown("<button onclick='window.print()' style='background: #1e5631; color: white; padding: 8px 15px; border-radius: 5px; border: none; width: 100%; cursor: pointer;'>🖨️ رزلٹ کارڈ پرنٹ کریں</button>", unsafe_allow_html=True)

            else: st.warning("اس طالبہ کا ریکارڈ نہیں ملا۔")

    elif m == "🏛️ ناظمہ پینل (رخصت)":
        st.header("🏛️ مہتممہ/ناظمہ پینل (رخصت کی منظوری)")
        pending = c.execute("SELECT id, t_name, l_type, reason, start_date, days FROM leave_requests WHERE status LIKE '%پینڈنگ%'").fetchall()
        if not pending: st.info("کوئی نئی درخواست نہیں ہے۔")
        else:
            for l_id, t_n, l_t, reas, s_d, dys in pending:
                with st.expander(f"📌 معلمہ: {t_n} | دن: {dys} | نوعیت: {l_t}"):
                    st.write(f"**وجہ:** {reas}")
                    c_a, c_r = st.columns(2)
                    if c_a.button("✅ منظور", key=f"app_{l_id}"):
                        c.execute("UPDATE leave_requests SET status='منظور شدہ ✅', notification_seen=0 WHERE id=?", (l_id,))
                        conn.commit(); st.rerun()
                    if c_r.button("❌ مسترد", key=f"rej_{l_id}"):
                        c.execute("UPDATE leave_requests SET status='مسترد شدہ ❌', notification_seen=0 WHERE id=?", (l_id,))
                        conn.commit(); st.rerun()

    elif m == "⚙️ انتظامی کنٹرول":
        st.header("⚙️ رجسٹریشن اور انتظامی کنٹرول")
        t1, t2 = st.tabs(["👩‍🏫 معلمات مینجمنٹ", "👩‍🎓 طالبات مینجمنٹ"])
        with t1:
            with st.form("t_reg_form"):
                tn = st.text_input("معلمہ کا نام")
                tp = st.text_input("پاسورڈ")
                if st.form_submit_button("رجسٹر کریں"):
                    if tn and tp:
                        try:
                            c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", (tn, tp))
                            conn.commit(); st.success("کامیاب!")
                        except sqlite3.IntegrityError: st.error("نام پہلے سے موجود ہے!")
        with t2:
            with st.form("s_reg_form"):
                sn, sf = st.columns(2)
                s_name = sn.text_input("طالبہ کا نام")
                s_father = sf.text_input("ولدیت")
                t_list = [t[0] for t in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
                if t_list:
                    s_teacher = st.selectbox("معلمہ", t_list)
                    if st.form_submit_button("داخل کریں"):
                        if s_name and s_father:
                            c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (s_name, s_father, s_teacher))
                            conn.commit(); st.success("داخلہ کامیاب!")

    elif m == "🕒 معلمات کا ریکارڈ":
        st.header("🕒 حاضری ریکارڈ")
        att_df = pd.read_sql_query("SELECT a_date as تاریخ, t_name as معلمہ, arrival as آمد, departure as رخصت FROM t_attendance", conn)
        if not att_df.empty: 
            st.dataframe(att_df, use_container_width=True)
            cd1, cd2 = st.columns(2)
            cd1.download_button("📥 ریکارڈ ڈاؤن لوڈ کریں", convert_df_to_csv(att_df), "teachers_attendance.csv", "text/csv")
            cd2.markdown("<button onclick='window.print()' style='background: #1e5631; color: white; padding: 8px 15px; border-radius: 5px; border: none; width: 100%; cursor: pointer;'>🖨️ پرنٹ کریں</button>", unsafe_allow_html=True)


    # ================= TEACHER SECTION =================
    elif m == "📝 تعلیمی اندراج":
        st.header("🚀 اسمارٹ تعلیمی ڈیش بورڈ")
        sel_date = st.date_input("تاریخ منتخب کریں", date.today())
        
        # ڈیٹا بیس سے طالبات کی لسٹ لینا
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()

        if not students:
            st.info("آپ کی کلاس میں کوئی طالبہ رجسٹرڈ نہیں ہے۔")
        else:
            # طالبات کی فہرست پر لوپ
            for s, f in students:
                with st.expander(f"👤 {s} بنت {f}"):
                    # حاضری کے تین بنیادی آپشنز
                    att = st.radio(f"حاضری {s}", ["حاضر", "غیر حاضر (ناغہ)", "رخصت"], key=f"att_{s}", horizontal=True)
                    
                    if att == "حاضر":
                        # --- 1. نیا سبق ---
                        st.subheader("📖 نیا سبق")
                        s_nagha = st.checkbox("سبق کا ناغہ", key=f"sn_nagha_{s}")
                        
                        if not s_nagha:
                            col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
                            surah_sel = col_s1.selectbox("سورت", surahs_urdu, key=f"surah_{s}")
                            a_from = col_s2.text_input("آیت (سے)", key=f"af_{s}")
                            a_to = col_s3.text_input("آیت (تک)", key=f"at_{s}")
                            sabq_final = f"{surah_sel}: {a_from}-{a_to}"
                        else:
                            sabq_final = "ناغہ"

                        # --- 2. سبقی ---
                        st.subheader("🔄 سبقی")
                        sq_total_nagha = st.checkbox("سبقی کا مکمل ناغہ", key=f"sq_tn_{s}")
                        sq_list, f_sq_m, f_sq_a = [], 0, 0
                        
                        if not sq_total_nagha:
                            if f"sq_count_{s}" not in st.session_state: st.session_state[f"sq_count_{s}"] = 1
                            for i in range(st.session_state[f"sq_count_{s}"]):
                                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                                p = c1.selectbox(f"پارہ {i+1}", paras, key=f"sqp_{s}_{i}")
                                v = c2.selectbox(f"مقدار {i+1}", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"sqv_{s}_{i}")
                                a = c3.number_input(f"اٹکن {i+1}", 0, key=f"sqa_{s}_{i}")
                                e = c4.number_input(f"غلطی {i+1}", 0, key=f"sqe_{s}_{i}")
                                ind_n = c5.checkbox("ناغہ", key=f"sq_n_{s}_{i}")
                                
                                if ind_n:
                                    sq_list.append(f"{p}:ناغہ")
                                else:
                                    sq_list.append(f"{p}:{v}(غ:{e},ا:{a})")
                                    f_sq_m += e; f_sq_a += a
                            
                            if st.button(f"➕ مزید سبقی {s}", key=f"btn_sq_{s}"):
                                st.session_state[f"sq_count_{s}"] += 1
                                st.rerun()
                        else:
                            sq_list = ["ناغہ"]

                        # --- 3. منزل ---
                        st.subheader("🏠 منزل")
                        m_total_nagha = st.checkbox("منزل کا مکمل ناغہ", key=f"m_tn_{s}")
                        m_list, f_m_m, f_m_a = [], 0, 0
                        
                        if not m_total_nagha:
                            if f"m_count_{s}" not in st.session_state: st.session_state[f"m_count_{s}"] = 1
                            for j in range(st.session_state[f"m_count_{s}"]):
                                mc1, mc2, mc3, mc4, mc5 = st.columns([2, 2, 1, 1, 1])
                                mp = mc1.selectbox(f"پارہ {j+1}", paras, key=f"mp_{s}_{j}")
                                mv = mc2.selectbox(f"مقدار {j+1}", ["مکمل", "آدھا", "پون", "پاؤ"], key=f"mv_{s}_{j}")
                                ma = mc3.number_input(f"اٹکن {j+1}", 0, key=f"ma_{s}_{j}")
                                me = mc4.number_input(f"غلطی {j+1}", 0, key=f"me_{s}_{j}")
                                m_ind_n = mc5.checkbox("ناغہ", key=f"m_n_{s}_{j}")
                                
                                if m_ind_n:
                                    m_list.append(f"{mp}:ناغہ")
                                else:
                                    m_list.append(f"{mp}:{mv}(غ:{me},ا:{ma})")
                                    f_m_m += me; f_m_a += ma
                            
                            if st.button(f"➕ مزید منزل {s}", key=f"btn_m_{s}"):
                                st.session_state[f"m_count_{s}"] += 1
                                st.rerun()
                        else:
                            m_list = ["ناغہ"]

                        # --- ڈیٹا محفوظ کرنا ---
                        if st.button(f"محفوظ کریں: {s}", key=f"save_{s}"):
                            check = c.execute("SELECT 1 FROM hifz_records WHERE r_date = ? AND s_name = ? AND f_name = ?", (sel_date, s, f)).fetchone()
                            if check:
                                st.error(f"🛑 ریکارڈ پہلے سے موجود ہے!")
                            else:
                                c.execute("""INSERT INTO hifz_records 
                                          (r_date, s_name, f_name, t_name, surah, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance) 
                                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", 
                                          (sel_date, s, f, st.session_state.username, sabq_final, 
                                           " | ".join(sq_list), f_sq_a, f_sq_m, " | ".join(m_list), f_m_a, f_m_m, att))
                                conn.commit()
                                st.success(f"✅ {s} کا ریکارڈ محفوظ ہو گیا۔")

                    # غیر حاضر یا رخصت کی صورت میں
                    else:
                        if st.button(f"حاضری لگائیں: {s}", key=f"save_absent_{s}"):
                            check = c.execute("SELECT 1 FROM hifz_records WHERE r_date = ? AND s_name = ? AND f_name = ?", (sel_date, s, f)).fetchone()
                            if check:
                                st.error(f"🛑 ریکارڈ پہلے سے موجود ہے!")
                            else:
                                c.execute("""INSERT INTO hifz_records (r_date, s_name, f_name, t_name, attendance, surah, sq_p, m_p) 
                                          VALUES (?,?,?,?,?,?,?,?)""", (sel_date, s, f, st.session_state.username, att, "ناغہ", "ناغہ", "ناغہ"))
                                conn.commit()
                                st.success(f"✅ {s} کی حاضری ({att}) لگ گئی ہے۔")

    elif m == "📩 درخواستِ رخصت":
        st.header("📩 اسمارٹ رخصت و نوٹیفیکیشن")
        
        tab_apply, tab_status = st.tabs(["✍️ نئی درخواست", "📜 میری رخصتوں کی تاریخ"])

        with tab_apply:
            with st.form("teacher_leave_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                l_type = col1.selectbox("رخصت کی نوعیت", ["ضروری کام", "بیماری", "ہنگامی رخصت", "دیگر"])
                s_date = col1.date_input("تاریخ آغاز", date.today())
                days = col2.number_input("کتنے دن؟", 1, 15)
                e_date = s_date + timedelta(days=days-1)
                col2.write(f"واپسی کی تاریخ: **{e_date}**")

                reason = st.text_area("تفصیلی وجہ درج کریں")

                if st.form_submit_button("درخواست ارسال کریں 🚀"):
                    if reason:
                        c.execute("""INSERT INTO leave_requests (t_name, l_type, start_date, days, reason, status, notification_seen) 
                                  VALUES (?,?,?,?,?,?,?)""", 
                                  (st.session_state.username, l_type, s_date, days, reason, "پینڈنگ (زیرِ غور)", 0))
                        conn.commit()
                        st.info("✅ درخواست ناظمہ صاحبہ کو بھیج دی گئی ہے۔")
                    else: st.warning("براہ کرم وجہ ضرور لکھیں۔")

        with tab_status:
            st.subheader("📊 میری رخصتوں کا ریکارڈ")
            my_leaves = pd.read_sql_query(f"SELECT start_date as تاریخ, l_type as نوعیت, days as دن, status as حالت FROM leave_requests WHERE t_name='{st.session_state.username}' ORDER BY start_date DESC", conn)
            if not my_leaves.empty:
                st.dataframe(my_leaves, use_container_width=True, hide_index=True)
            else: st.info("کوئی ریکارڈ نہیں ملا۔")

    elif m == "🕒 میری حاضری":
        st.header("🕒 آمد و رخصت")
        if st.button("✅ آمد"):
            c.execute("INSERT INTO t_attendance (t_name, a_date, arrival) VALUES (?,?,?)", (st.session_state.username, date.today(), datetime.now().strftime("%I:%M %p")))
            conn.commit(); st.success("ریکارڈ ہو گیا!")

    # 🎓 امتحانی رپورٹ
    elif m == "🎓 امتحانی تعلیمی رپورٹ":
        render_exam_report()

    # ================= LOGOUT =================
    st.sidebar.divider()
    if st.sidebar.button("🚪 لاگ آؤٹ کریں"):
        st.session_state.logged_in = False
        st.rerun()
