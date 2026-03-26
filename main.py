import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3

# --- 1. ڈیٹا بیس سیٹ اپ ---
DB_NAME = 'jamia_millia_v1.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, father_name TEXT, teacher_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hifz_records 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, r_date DATE, s_name TEXT, f_name TEXT, t_name TEXT, 
                  surah TEXT, a_from TEXT, a_to TEXT, sq_p TEXT, sq_a INTEGER, sq_m INTEGER, 
                  m_p TEXT, m_a INTEGER, m_m INTEGER, attendance TEXT, principal_note TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS t_attendance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, a_date DATE, arrival TEXT, departure TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leave_requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, t_name TEXT, reason TEXT, start_date DATE, back_date DATE, status TEXT, request_date DATE)''')
    c.execute("INSERT OR IGNORE INTO teachers (name, password) VALUES (?,?)", ("admin", "jamia123"))
    conn.commit()

init_db()

def get_grade(avg_errors):
    if avg_errors <= 0.5: return "ممتاز (A+)"
    elif avg_errors <= 1.5: return "جید جداً (A)"
    elif avg_errors <= 3: return "جید (B)"
    elif avg_errors <= 5: return "مقبول (C)"
    else: return "راسب (Fail)"

surahs_urdu = ["الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس", "التكوير", "الإنفطار", "المطففين", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر", "الهمزة", "الفيل", "قریش", "الماعون", "الکوثر", "الكافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"]
paras = [f"پارہ {i}" for i in range(1, 31)]

st.set_page_config(page_title="جامعہ ملیہ اسلامیہ فیصل آباد", layout="wide")
st.markdown("<style>body{direction:rtl; text-align:right;} .stButton>button{background:#1e5631; color:white; border-radius:10px; font-weight:bold; width:100%;}</style>", unsafe_allow_html=True)

# مین ٹائٹل
st.markdown("<h1 style='text-align: center; color: #1e5631;'>🕌 جامعہ ملیہ اسلامیہ فیصل آباد</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.subheader("لاگ ان پینل")
        u = st.text_input("صارف کا نام"); p = st.text_input("پاسورڈ", type="password")
        if st.button("داخل ہوں"):
            res = c.execute("SELECT * FROM teachers WHERE name=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.user_type = "admin" if u == "admin" else "teacher"
                st.rerun()
            else: st.error("غلط معلومات")
else:
    if st.session_state.user_type == "admin":
        menu = ["📊 تعلیمی رپورٹ", "📜 ماہانہ رزلٹ کارڈ", "🕒 اساتذہ کا ریکارڈ", "⚙️ انتظامی کنٹرول"]
    else:
        menu = ["📝 تعلیمی اندراج", "📩 رخصت کی درخواست", "🕒 میری حاضری"]

    m = st.sidebar.radio("مینو", menu)

    # --- ایڈمن: اساتذہ کا ریکارڈ (ترمیم اور حذف کے اختیارات کے ساتھ) ---
    if m == "🕒 اساتذہ کا ریکارڈ":
        st.header("اساتذہ کی حاضری و رخصت کا انتظام")
        t1, t2 = st.tabs(["حاضری درست کریں / حذف کریں", "رخصت کی منظوری"])

        with t1:
            att_df = pd.read_sql_query("SELECT id as 'ID', t_name as 'استاد', a_date as 'تاریخ', arrival as 'آمد', departure as 'رخصت' FROM t_attendance ORDER BY a_date DESC", conn)
            st.dataframe(att_df, use_container_width=True)

            st.divider()
            st.subheader("حاضری میں ترمیم کریں")
            edit_id = st.number_input("حاضری ID لکھیں جس میں تبدیلی کرنی ہے", min_value=1, step=1)

            col_e1, col_e2, col_e3 = st.columns(3)
            new_date = col_e1.date_input("نئی تاریخ")
            new_arr = col_e2.text_input("آمد کا وقت (مثلاً 08:00 AM)")
            new_dep = col_e3.text_input("رخصت کا وقت (مثلاً 02:00 PM)")

            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.button("💾 تبدیلی محفوظ کریں"):
                c.execute("UPDATE t_attendance SET a_date=?, arrival=?, departure=? WHERE id=?", (new_date, new_arr, new_dep, edit_id))
                conn.commit(); st.success("حاضری اپ ڈیٹ کر دی گئی!"); st.rerun()

            if btn_col2.button("🗑️ یہ حاضری حذف کریں"):
                c.execute("DELETE FROM t_attendance WHERE id=?", (edit_id,))
                conn.commit(); st.warning("ریکارڈ حذف کر دیا گیا!"); st.rerun()

        with t2:
            df_l = pd.read_sql_query("SELECT id, t_name, start_date, back_date, status FROM leave_requests ORDER BY id DESC", conn)
            st.dataframe(df_l, use_container_width=True)
            lid = st.number_input("درخواست ID (رخصت)", min_value=1, step=1)
            lc1, lc2 = st.columns(2)
            if lc1.button("✅ منظور کریں"): c.execute("UPDATE leave_requests SET status='منظور' WHERE id=?", (lid,)); conn.commit(); st.rerun()
            if lc2.button("❌ نامنظور کریں"): c.execute("UPDATE leave_requests SET status='نامنظور' WHERE id=?", (lid,)); conn.commit(); st.rerun()

    # --- استاد: میری حاضری (تاریخ کے ساتھ) ---
    elif m == "🕒 میری حاضری":
        st.header("روزانہ حاضری کا اندراج")
        h_date = st.date_input("تاریخ منتخب کریں", date.today())
        ti = st.time_input("آمد کا وقت")
        to = st.time_input("رخصت کا وقت")
        if st.button("حاضری لگائیں"):
            c.execute("INSERT INTO t_attendance (t_name, a_date, arrival, departure) VALUES (?,?,?,?)", 
                      (st.session_state.username, h_date, ti.strftime("%I:%M %p"), to.strftime("%I:%M %p")))
            conn.commit(); st.success(f"{h_date} کی حاضری لگ گئی!")

    # --- باقی تمام پیجز (تعلیمی اندراج، رزلٹ کارڈ وغیرہ پہلے جیسے ہی رکھے گئے ہیں) ---
    elif m == "📝 تعلیمی اندراج":
        st.header("📖 سبق، سبقی اور منزل کا اندراج")
        students = c.execute("SELECT name, father_name FROM students WHERE teacher_name=?", (st.session_state.username,)).fetchall()
        for s, f in students:
            with st.expander(f"👤 طالب علم: {s} ولد {f}"):
                c_d, c_a = st.columns(2)
                r_date = c_d.date_input("تاریخ", date.today(), key=f"d_{s}")
                att = c_a.radio("حاضری", ["حاضر", "غیر حاضر"], key=f"at_{s}")
                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("### **سبق**")
                    su = st.selectbox("سورت", surahs_urdu, key=f"su_{s}")
                    af = st.text_input("آیت (سے)", "1", key=f"af_{s}")
                    at_v = st.text_input("آیت (تک)", "10", key=f"at_v_{s}")
                with col2:
                    st.markdown("### **سبقی**")
                    sp = st.selectbox("سبقی پارہ", paras, key=f"sp_{s}")
                    sa = st.number_input("اٹکن", 0, key=f"sa_{s}")
                    sm = st.number_input("غلطی", 0, key=f"sm_{s}")
                with col3:
                    st.markdown("### **منزل**")
                    mp = st.selectbox("منزل پارہ", paras, key=f"mp_{s}")
                    ma = st.number_input("منزل اٹکن", 0, key=f"ma_{s}")
                    mm = st.number_input("منزل غلطی", 0, key=f"mm_{s}")
                if st.button(f"محفوظ کریں: {s}", key=f"btn_{s}"):
                    c.execute('''INSERT INTO hifz_records (r_date, s_name, f_name, t_name, surah, a_from, a_to, sq_p, sq_a, sq_m, m_p, m_a, m_m, attendance, principal_note) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (r_date, s, f, st.session_state.username, su, af, at_v, sp, sa, sm, mp, ma, mm, att, "انتظارِ رائے"))
                    conn.commit(); st.success("ریکارڈ محفوظ!")

    elif m == "📊 تعلیمی رپورٹ":
        st.header("تعلیمی رپورٹ")
        df = pd.read_sql_query("SELECT * FROM hifz_records", conn)
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ڈاؤن لوڈ رپورٹ", data=csv, file_name="Report.csv")

    elif m == "📜 ماہانہ رزلٹ کارڈ":
        st.header("ماہانہ رزلٹ کارڈ")
        sts = [r[0] for r in c.execute("SELECT name FROM students").fetchall()]
        if sts:
            sel_st = st.selectbox("طالب علم", sts)
            sel_m = st.selectbox("مہینہ", list(range(1, 13)), index=datetime.now().month-1)
            if st.button("رزلٹ دیکھیں"):
                res_df = pd.read_sql_query(f"SELECT * FROM hifz_records WHERE s_name='{sel_st}' AND strftime('%m', r_date)='{sel_m:02d}'", conn)
                if not res_df.empty:
                    avg_m = res_df['m_m'].mean()
                    c1, c2, c3 = st.columns(3)
                    c1.metric("حاضری", len(res_df[res_df['attendance']=='حاضر']))
                    c2.metric("اوسط غلطی", f"{avg_m:.1f}")
                    c3.metric("گریڈ", get_grade(avg_m))
                    st.dataframe(res_df, use_container_width=True)

    elif m == "📩 رخصت کی درخواست":
        st.header("رخصت کی درخواست")
        sd = st.date_input("آغاز"); ed = st.date_input("واپسی"); rsn = st.text_area("وجہ")
        if st.button("ارسال کریں"):
            c.execute("INSERT INTO leave_requests (t_name, reason, start_date, back_date, status, request_date) VALUES (?,?,?,?,?,?)", (st.session_state.username, rsn, sd, ed, "پینڈنگ", date.today()))
            conn.commit(); st.success("ارسال ہوگئی")
        st.table(pd.read_sql_query(f"SELECT start_date, back_date, status FROM leave_requests WHERE t_name='{st.session_state.username}'", conn))

    elif m == "⚙️ انتظامی کنٹرول":
        tab1, tab2 = st.tabs(["اساتذہ", "طلباء"])
        with tab1:
            st.dataframe(pd.read_sql_query("SELECT id, name FROM teachers WHERE name!='admin'", conn))
            tid = st.number_input("حذف کریں استاد ID", min_value=1, step=1)
            if st.button("حذف استاد"): c.execute("DELETE FROM teachers WHERE id=?", (tid,)); conn.commit(); st.rerun()
            nt = st.text_input("نام"); np = st.text_input("پاسورڈ")
            if st.button("رجسٹر کریں"): c.execute("INSERT INTO teachers (name, password) VALUES (?,?)", (nt, np)); conn.commit(); st.success("کامیاب")
        with tab2:
            st.dataframe(pd.read_sql_query("SELECT id, name, father_name, teacher_name FROM students", conn))
            sid = st.number_input("حذف طالب علم ID", min_value=1, step=1)
            if st.button("حذف طالب علم"): c.execute("DELETE FROM students WHERE id=?", (sid,)); conn.commit(); st.rerun()
            sn = st.text_input("نام طالب علم"); sf = st.text_input("ولدیت")
            t_list = [r[0] for r in c.execute("SELECT name FROM teachers WHERE name!='admin'").fetchall()]
            if t_list:
                stch = st.selectbox("استاد", t_list)
                if st.button("شامل کریں"): c.execute("INSERT INTO students (name, father_name, teacher_name) VALUES (?,?,?)", (sn, sf, stch)); conn.commit(); st.success("کامیاب")

    if st.sidebar.button("🚪 لاگ آؤٹ"):
        st.session_state.logged_in = False; st.rerun()