import pandas as pd
import sqlite3
import streamlit as st
import os
import sys
import plotly.express as px
from datetime import datetime
import re  # ใช้งาน Regular Expression

# --- 1. กำหนดตำแหน่งและชื่อไฟล์ Database ---
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'officers_database.db')

# --- 2. เปลี่ยนฟังก์ชันตรวจสอบ Database ---
def is_using_supabase():
    return False

# --- 3. เปลี่ยนฟังก์ชันอ่านข้อมูลประกาศ (Announcements) ---
def get_all_announcements():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(columns=['announcement_no', 'start_date', 'minister_name', 'term_years'])
    
    with sqlite3.connect(DB_PATH) as conn:
        try:
            df = pd.read_sql("SELECT * FROM announcements", conn)
            return df
        except Exception:
            return pd.DataFrame(columns=['announcement_no', 'start_date', 'minister_name', 'term_years'])

def get_announcement_dict():
    df = get_all_announcements()
    if df.empty:
        return {}
    df = df.set_index('announcement_no')
    return df.to_dict('index')

# --- 4. เปลี่ยนฟังก์ชันเพิ่ม/แก้ไข ประกาศ ---
def add_or_update_announcement(announcement_no, start_date, minister_name=None, term_years=4.0):
    df_new = pd.DataFrame([{
        'announcement_no': int(announcement_no),
        'start_date': start_date,
        'minister_name': minister_name,
        'term_years': float(term_years)
    }])
    
    df_existing = get_all_announcements()
    
    if not df_existing.empty:
        df_existing = df_existing[df_existing['announcement_no'] != int(announcement_no)]
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
        
    with sqlite3.connect(DB_PATH) as conn:
        df_combined.to_sql('announcements', conn, if_exists='replace', index=False)

# --- 5. เปลี่ยนฟังก์ชันลบประกาศ ---
def delete_announcement(announcement_no):
    df_existing = get_all_announcements()
    if not df_existing.empty:
        df_remaining = df_existing[df_existing['announcement_no'] != int(announcement_no)]
        with sqlite3.connect(DB_PATH) as conn:
            df_remaining.to_sql('announcements', conn, if_exists='replace', index=False)

# --- 6. เปลี่ยนฟังก์ชันโหลดข้อมูลพนักงาน (History) ---
def load_officers_history():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
        
    with sqlite3.connect(DB_PATH) as conn:
        try:
            df = pd.read_sql("SELECT * FROM officers_history", conn)
            return df
        except Exception:
            return pd.DataFrame()

# --- 7. เปลี่ยนฟังก์ชันเพิ่มข้อมูลพนักงาน (Append) ---
def append_officers_history(df_new):
    if df_new.empty:
        return 0
        
    with sqlite3.connect(DB_PATH) as conn:
        df_new.to_sql('officers_history', conn, if_exists='append', index=False)
        
    return len(df_new)

# --- 8. เปลี่ยนฟังก์ชันล้างฐานข้อมูลพนักงาน ---
def delete_all_officers_history():
    if os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS officers_history")
            conn.commit()

# --- 9. ฟังก์ชันจัดการหน่วยงานและจังหวัด (Agency Registry) ---
def get_agency_registry():
    """อ่านหน่วยงานทั้งหมดจาก agency_registry"""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(columns=['agency_name', 'province', 'region', 'updated_at'])
    with sqlite3.connect(DB_PATH) as conn:
        try:
            return pd.read_sql("SELECT * FROM agency_registry ORDER BY agency_name", conn)
        except Exception:
            return pd.DataFrame(columns=['agency_name', 'province', 'region', 'updated_at'])

# พจนานุกรมจับคู่จังหวัด -> ภาค
PROVINCE_TO_REGION = {
    'เชียงใหม่': 'ภาคเหนือ', 'ลำพูน': 'ภาคเหนือ', 'ลำปาง': 'ภาคเหนือ', 'อุตรดิตถ์': 'ภาคเหนือ', 
    'แพร่': 'ภาคเหนือ', 'น่าน': 'ภาคเหนือ', 'พะเยา': 'ภาคเหนือ', 'เชียงราย': 'ภาคเหนือ', 'แม่ฮ่องสอน': 'ภาคเหนือ',
    'นครราชสีมา': 'ภาคตะวันออกเฉียงเหนือ', 'บุรีรัมย์': 'ภาคตะวันออกเฉียงเหนือ', 'สุรินทร์': 'ภาคตะวันออกเฉียงเหนือ', 
    'ศรีสะเกษ': 'ภาคตะวันออกเฉียงเหนือ', 'อุบลราชธานี': 'ภาคตะวันออกเฉียงเหนือ', 'ยโสธร': 'ภาคตะวันออกเฉียงเหนือ', 
    'ชัยภูมิ': 'ภาคตะวันออกเฉียงเหนือ', 'อำนาจเจริญ': 'ภาคตะวันออกเฉียงเหนือ', 'บึงกาฬ': 'ภาคตะวันออกเฉียงเหนือ', 
    'หนองบัวลำภู': 'ภาคตะวันออกเฉียงเหนือ', 'ขอนแก่น': 'ภาคตะวันออกเฉียงเหนือ', 'อุดรธานี': 'ภาคตะวันออกเฉียงเหนือ', 
    'เลย': 'ภาคตะวันออกเฉียงเหนือ', 'หนองคาย': 'ภาคตะวันออกเฉียงเหนือ', 'มหาสารคาม': 'ภาคตะวันออกเฉียงเหนือ', 
    'ร้อยเอ็ด': 'ภาคตะวันออกเฉียงเหนือ', 'กาฬสินธุ์': 'ภาคตะวันออกเฉียงเหนือ', 'สกลนคร': 'ภาคตะวันออกเฉียงเหนือ', 
    'นครพนม': 'ภาคตะวันออกเฉียงเหนือ', 'มุกดาหาร': 'ภาคตะวันออกเฉียงเหนือ',
    'กรุงเทพมหานคร': 'ภาคกลาง', 'สมุทรปราการ': 'ภาคกลาง', 'นนทบุรี': 'ภาคกลาง', 'ปทุมธานี': 'ภาคกลาง', 
    'พระนครศรีอยุธยา': 'ภาคกลาง', 'อ่างทอง': 'ภาคกลาง', 'ลพบุรี': 'ภาคกลาง', 'สิงห์บุรี': 'ภาคกลาง', 
    'ชัยนาท': 'ภาคกลาง', 'สระบุรี': 'ภาคกลาง', 'นครนายก': 'ภาคกลาง', 'นครสวรรค์': 'ภาคกลาง', 
    'อุทัยธานี': 'ภาคกลาง', 'กำแพงเพชร': 'ภาคกลาง', 'ตาก': 'ภาคกลาง', 'สุโขทัย': 'ภาคกลาง', 
    'พิษณุโลก': 'ภาคกลาง', 'พิจิตร': 'ภาคกลาง', 'เพชรบูรณ์': 'ภาคกลาง', 'สุพรรณบุรี': 'ภาคกลาง',
    'นครปฐม': 'ภาคกลาง', 'สมุทรสาคร': 'ภาคกลาง', 'สมุทรสงคราม': 'ภาคกลาง',
    'ชลบุรี': 'ภาคตะวันออก', 'ระยอง': 'ภาคตะวันออก', 'จันทบุรี': 'ภาคตะวันออก', 'ตราด': 'ภาคตะวันออก', 
    'ฉะเชิงเทรา': 'ภาคตะวันออก', 'ปราจีนบุรี': 'ภาคตะวันออก', 'สระแก้ว': 'ภาคตะวันออก',
    'ราชบุรี': 'ภาคตะวันตก', 'กาญจนบุรี': 'ภาคตะวันตก', 'เพชรบุรี': 'ภาคตะวันตก', 'ประจวบคีรีขันธ์': 'ภาคตะวันตก',
    'นครศรีธรรมราช': 'ภาคใต้', 'กระบี่': 'ภาคใต้', 'พังงา': 'ภาคใต้', 'ภูเก็ต': 'ภาคใต้', 'สุราษฎร์ธานี': 'ภาคใต้', 
    'ระนอง': 'ภาคใต้', 'ชุมพร': 'ภาคใต้', 'สงขลา': 'ภาคใต้', 'สตูล': 'ภาคใต้', 'ตรัง': 'ภาคใต้', 
    'พัทลุง': 'ภาคใต้', 'ปัตตานี': 'ภาคใต้', 'ยะลา': 'ภาคใต้', 'นราธิวาส': 'ภาคใต้'
}

def get_agency_mapping():
    """ดึง dict การจับคู่หน่วยงาน -> (จังหวัด, ภาค) จาก agency_registry"""
    if not os.path.exists(DB_PATH):
        return {}
    with sqlite3.connect(DB_PATH) as conn:
        try:
            df_reg = pd.read_sql("SELECT agency_name, province, region FROM agency_registry", conn)
            mapping = {}
            for _, r in df_reg.iterrows():
                ag = str(r['agency_name']).strip()
                prov = str(r['province']).strip() if pd.notna(r['province']) else ""
                reg = str(r['region']).strip() if pd.notna(r['region']) and str(r['region']).strip() else PROVINCE_TO_REGION.get(prov, "")
                if ag and prov:
                    mapping[ag] = (prov, reg)
            return mapping
        except Exception:
            return {}

def save_agency(agency_name, province, region=""):
    """บันทึก/อัปเดตหน่วยงาน (upsert) พร้อมอัปเดตข้อมูลพนักงานในระบบทันที"""
    ag_clean = agency_name.strip()
    prov_clean = province.strip()
    reg_clean = region.strip() if region and region.strip() else PROVINCE_TO_REGION.get(prov_clean, "")
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agency_registry (
                agency_name TEXT PRIMARY KEY,
                province TEXT,
                region TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            INSERT OR REPLACE INTO agency_registry (agency_name, province, region, updated_at)
            VALUES (?, ?, ?, ?)
        """, (ag_clean, prov_clean, reg_clean, datetime.now().strftime('%d/%m/%Y %H:%M')))
        
        # ซิงค์อัปเดตข้อมูลพนักงานใน officers_history ทันที
        try:
            conn.execute("""
                UPDATE officers_history 
                SET จังหวัด = ?, ภาค = ? 
                WHERE TRIM(หน่วยงาน) = ?
            """, (prov_clean, reg_clean, ag_clean))
        except Exception:
            pass
        conn.commit()

    # ซิงค์อัปเดตไฟล์ CSV หลัก (ถ้ามี)
    if os.path.exists(DATA_PATH):
        try:
            df_csv = pd.read_csv(DATA_PATH)
            if 'หน่วยงาน' in df_csv.columns:
                mask = df_csv['หน่วยงาน'].fillna('').astype(str).str.strip() == ag_clean
                if mask.any():
                    df_csv.loc[mask, 'จังหวัด'] = prov_clean
                    if reg_clean:
                        df_csv.loc[mask, 'ภาค'] = reg_clean
                    df_csv.to_csv(DATA_PATH, index=False, encoding='utf-8-sig')
        except Exception:
            pass

def delete_agency(agency_name):
    """ลบหน่วยงานออกจาก agency_registry"""
    if not os.path.exists(DB_PATH):
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM agency_registry WHERE agency_name = ?", (agency_name,))
        conn.commit()

def search_agency(keyword):
    """ค้นหาหน่วยงานจากทั้ง agency_registry และ officers_history"""
    results = []
    kw = f"%{keyword.strip()}%"
    
    if os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            # 1. ค้นจาก agency_registry
            try:
                df_reg = pd.read_sql(
                    "SELECT agency_name AS หน่วยงาน, province AS จังหวัด, region AS ภาค, updated_at AS อัปเดตล่าสุด FROM agency_registry WHERE agency_name LIKE ?",
                    conn, params=(kw,)
                )
                if not df_reg.empty:
                    df_reg['แหล่งข้อมูล'] = '🟢 บันทึกไว้ในระบบ'
                    results.append(df_reg)
            except Exception:
                pass
            
            # 2. ค้นจาก officers_history
            try:
                df_hist = pd.read_sql(
                    'SELECT DISTINCT "หน่วยงาน", "จังหวัด", "ภาค" FROM officers_history WHERE "หน่วยงาน" LIKE ?',
                    conn, params=(kw,)
                )
                if not df_hist.empty:
                    df_hist['อัปเดตล่าสุด'] = '-'
                    df_hist['แหล่งข้อมูล'] = '🔵 ประวัตินำเข้าข้อมูล'
                    results.append(df_hist)
            except Exception:
                pass
    
    # 3. ถ้าใน DB ไม่มี officers_history แต่มีไฟล์ CSV
    if not results and os.path.exists(DATA_PATH):
        try:
            df_csv = pd.read_csv(DATA_PATH)
            if 'หน่วยงาน' in df_csv.columns and 'จังหวัด' in df_csv.columns:
                m = df_csv['หน่วยงาน'].fillna('').astype(str).str.contains(keyword.strip(), case=False, regex=False)
                sub = df_csv[m][['หน่วยงาน', 'จังหวัด', 'ภาค']].drop_duplicates()
                if not sub.empty:
                    sub['อัปเดตล่าสุด'] = '-'
                    sub['แหล่งข้อมูล'] = '🔵 ประวัตินำเข้าข้อมูล (CSV)'
                    results.append(sub)
        except Exception:
            pass

    if results:
        res_df = pd.concat(results, ignore_index=True)
        return res_df.drop_duplicates(subset=['หน่วยงาน', 'จังหวัด', 'ภาค', 'แหล่งข้อมูล'])
    return pd.DataFrame()

# ==========================================
# Custom CSS (สไตล์ทางการ / ราชการ)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
    
    [data-testid="stMainBlockContainer"], .block-container {
        max-width: 100% !important;
        padding-left: 2rem !important;  
        padding-right: 2rem !important;  /* เพิ่มระยะขอบขวาให้กว้างขึ้นเพื่อหลบปุ่ม Deploy */
        padding-top: 3.5rem !important;  /* ดันเนื้อหาลงมาจากขอบบนให้สวยงาม */
    }

    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif !important;
    }

    h1 { 
        font-size: 1.6rem !important; 
        font-weight: 600 !important; 
        color: #0f4c81 !important; 
        margin-bottom: 0px !important;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4b5563;
        margin-bottom: 20px;
    }
    
    h4, .stTabs [data-baseweb="tab"] { 
        font-size: 1.1rem !important; 
        font-weight: 600 !important; 
        color: #1f2937 !important; 
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1f2937;
        border-left: 4px solid #0f4c81;
        padding-left: 10px;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    hr { margin: 1.5rem 0; border: 0; border-top: 1px solid #d1d5db; }

    [data-testid="metric-container"] {
        background-color: #ffffff; 
        border: 1px solid #e5e7eb; 
        border-top: 3px solid #0f4c81; 
        padding: 15px; 
        border-radius: 2px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# COMMON HELPERS
# ============================================================
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SUM_พนักงานเจ้าหน้าที่แยกตามระดับ_Cleaned.csv")

def format_ymd(days):
    if pd.isna(days): return ""
    days = abs(int(days))
    years = days // 365
    remaining_days = days % 365
    months = remaining_days // 30
    d = remaining_days % 30
    parts = []
    if years > 0: parts.append(f"{years} ปี")
    if months > 0: parts.append(f"{months} เดือน")
    if d > 0 or len(parts) == 0: parts.append(f"{d} วัน")
    return " ".join(parts)

def get_status_display(days):
    if pd.isna(days): return "-"
    days = int(days)
    if days < 0: return "สิ้นสุดวาระ"
    elif days <= 90: return f"ใกล้สิ้นสุดวาระ (เหลือ {format_ymd(days)})"
    else: return f"อยู่ในวาระปกติ (เหลือ {format_ymd(days)})"

def get_status_type(days):
    if pd.isna(days): return 'UNKNOWN'
    if days < 0: return 'EXPIRED'
    elif days <= 90: return 'WARNING'
    else: return 'ACTIVE'

def highlight_row_status(row):
    val = row.get('ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ')
    if pd.isna(val): style = ''
    elif val < 0: style = 'background-color: #fee2e2; color: #b91c1c; font-weight: 500;'
    elif val <= 90: style = 'background-color: #fef3c7; color: #b45309; font-weight: 500;'
    else: style = 'background-color: #dcfce7; color: #15803d; font-weight: 500;'
    return [style] * len(row)

# ==========================================
# Sidebar Navigation
# ==========================================
with st.sidebar:
    st.markdown("<div style='text-align:center; padding: 10px 0;'><span style='font-size:2rem;'>🛡️</span></div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; font-weight:700; color:#0f4c81; font-size:1rem; margin-bottom:1rem;'>ระบบสารสนเทศพนักงานเจ้าหน้าที่</div>", unsafe_allow_html=True)
    st.divider()
    menu = st.radio(
        "เลือกเมนู:",
        ["📅 จัดการประกาศราชกิจจาฯ", "🏢 จัดการหน่วยงาน", "📁 อัปโหลดและประมวลผลข้อมูล", "📊 แดชบอร์ดสรุปผล"],
        label_visibility="collapsed"
    )
    st.divider()
    if is_using_supabase():
        st.success("☁️ ฐานข้อมูล: Supabase (Online)")
    else:
        st.caption(f"📅 วันที่ปัจจุบัน: {datetime.now().strftime('%d/%m/%Y')}")
    st.caption(f"⏰ เวลา: {datetime.now().strftime('%H:%M น.')}")

# ==============================================================================
# 1. แดชบอร์ดสรุปผล
# ==============================================================================
if menu == "📊 แดชบอร์ดสรุปผล":
    st.markdown("<h1>ระบบสารสนเทศเพื่อการติดตามและวิเคราะห์ข้อมูลพนักงานเจ้าหน้าที่</h1>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>ตามพระราชบัญญัติว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์</div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin-top: 0;'>", unsafe_allow_html=True)
    
    def kpi_card(title, value, subtext, border_color, value_color):
        return f"""
        <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-top: 3px solid {border_color}; padding: 15px; border-radius: 2px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); height: 100%;">
            <div style="font-size: 0.95rem; font-weight: 600; color: #4b5563; margin-bottom: 0.2rem;">{title}</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: {value_color}; line-height: 1.2;">{value}</div>
            <div style="font-size: 0.85rem; color: #6b7280; margin-top: 0.2rem;">{subtext}</div>
        </div>
        """
    
    def load_data_realtime():
        try:
            df_sql = load_officers_history()
            if not df_sql.empty:
                df = df_sql
            elif os.path.exists(DATA_PATH):
                df = pd.read_csv(DATA_PATH)
            else:
                return None
        except Exception:
            if os.path.exists(DATA_PATH):
                df = pd.read_csv(DATA_PATH)
            else:
                return None

        # --- ดึงข้อมูลประกาศล่าสุดแบบ Real-time ---
        announcements_db = get_announcement_dict()
        
        expiry_dates_be = []
        remaining_days_list = []
        exp_date_dt_list = []
        updated_start_dates = [] # เพิ่มลิสต์เก็บวันที่เริ่มใหม่
        updated_ministers = []   # เพิ่มลิสต์เก็บชื่อรัฐมนตรีใหม่
        
        today = pd.Timestamp.now().normalize()

        for i, row in df.iterrows():
            ann_no = row.get('ประกาศฉบับที่')
            start_date_str = None
            minister_name = row.get('รัฐมนตรี (minister)')
            term_yrs = 4.0

            # 1. พยายามดึงข้อมูลใหม่จาก Database ประกาศล่าสุด
            try:
                ann_no_int = int(float(str(ann_no))) if not pd.isna(ann_no) and str(ann_no).strip() != '' else None
                if ann_no_int in announcements_db:
                    start_date_str = announcements_db[ann_no_int].get('start_date')
                    minister_name = announcements_db[ann_no_int].get('minister_name')
                    term_yrs = announcements_db[ann_no_int].get('term_years', 4.0) or 4.0
            except:
                pass

            # เก็บค่าอัปเดตไว้โชว์บนจอ
            updated_start_dates.append(start_date_str)
            updated_ministers.append(minister_name)

            if pd.isna(start_date_str) or not start_date_str:
                expiry_dates_be.append(None)
                remaining_days_list.append(None)
                exp_date_dt_list.append(pd.NaT)
                continue

            try:
                from datetime import datetime, timedelta
                from dateutil.relativedelta import relativedelta
                import re

                date_str_clean = str(start_date_str).strip()
                match = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', date_str_clean)
                if match:
                    d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    if y > 2400: y -= 543
                    
                    start_date_obj = datetime(year=y, month=m, day=d)
                    expiry_date_obj = start_date_obj + relativedelta(years=int(term_yrs)) - timedelta(days=1)
                    
                    exp_date_dt_list.append(pd.Timestamp(expiry_date_obj))
                    thai_exp_year = expiry_date_obj.year + 543
                    expiry_dates_be.append(f"{expiry_date_obj.day:02d}/{expiry_date_obj.month:02d}/{thai_exp_year}")
                    
                    delta = expiry_date_obj - today
                    remaining_days_list.append(delta.days)
                else:
                    expiry_dates_be.append(None)
                    remaining_days_list.append(None)
                    exp_date_dt_list.append(pd.NaT)
            except:
                expiry_dates_be.append(None)
                remaining_days_list.append(None)
                exp_date_dt_list.append(pd.NaT)

        # 2. เขียนทับคอลัมน์บนหน้าจอด้วยข้อมูลที่อัปเดตใหม่ล่าสุด
        df['วันที่เริ่ม (announcement_date)'] = updated_start_dates
        df['รัฐมนตรี (minister)'] = updated_ministers
        df['วันหมดอายุบัตร'] = expiry_dates_be
        df['exp_date_dt'] = exp_date_dt_list
        df['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ'] = remaining_days_list

        # 3. จัดรูปแบบให้วันที่เริ่มโชว์เป็น พ.ศ. เสมอ
        if 'วันที่เริ่ม (announcement_date)' in df.columns:
            def convert_announce_to_be(val):
                if pd.isna(val): return "-"
                val_str = str(val).strip()
                import re
                match = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', val_str)
                if match:
                    d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    if 0 < y < 2400: y += 543
                    return f"{d:02d}/{m:02d}/{y}"
                return val_str
                
            df['วันที่เริ่ม (announcement_date)'] = df['วันที่เริ่ม (announcement_date)'].apply(convert_announce_to_be)
            
        # 4. ตัดทศนิยมคอลัมน์ประกาศฉบับที่ (ป้องกันเลข 17.000000)
        if 'ประกาศฉบับที่' in df.columns:
            df['ประกาศฉบับที่'] = pd.to_numeric(df['ประกาศฉบับที่'], errors='coerce').astype('Int64').astype(str).replace('<NA>', '-')

        # 5. ซิงค์จังหวัดและภาคตาม Agency Registry ล่าสุดแบบ Real-time
        if 'หน่วยงาน' in df.columns:
            ag_map = get_agency_mapping()
            if ag_map:
                for ag_name, (prov_val, reg_val) in ag_map.items():
                    mask = df['หน่วยงาน'].fillna('').astype(str).str.strip() == ag_name
                    if mask.any():
                        df.loc[mask, 'จังหวัด'] = prov_val
                        if reg_val:
                            df.loc[mask, 'ภาค'] = reg_val

        return df
    
    df_raw = load_data_realtime()
    
    
    if df_raw is None:
        st.error("ไม่พบไฟล์ข้อมูล กรุณาอัปโหลดข้อมูลก่อน")
        st.info("ไปที่เมนู 📁 อัปโหลดและประมวลผลข้อมูล เพื่ออัปโหลดและประมวลผลไฟล์ข้อมูล")
        st.stop()
    
    df = df_raw.copy()
    # --- เริ่มส่วนที่เพิ่ม: ตัดทศนิยมคอลัมน์ประกาศฉบับที่ ---
    if 'ประกาศฉบับที่' in df.columns:
        # แปลงเป็นตัวเลขจำนวนเต็ม (Int64) เพื่อตัดทศนิยมทิ้ง แล้วแปลงเป็นข้อความ
        df['ประกาศฉบับที่'] = pd.to_numeric(df['ประกาศฉบับที่'], errors='coerce').astype('Int64').astype(str).replace('<NA>', '-')
    df['clean_full_name'] = df['ชื่อ'].fillna('').astype(str).str.strip() + " " + df['นามสกุล'].fillna('').astype(str).str.strip()
    
    if 'ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ' in df.columns:
        df['status_type'] = df['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ'].apply(get_status_type)
        df['สถานะปัจจุบัน'] = df['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ'].apply(get_status_display)
    
    name_counts = df['clean_full_name'].value_counts()
    df['is_duplicate'] = df['clean_full_name'].map(lambda x: name_counts.get(x, 0) > 1)
    
    # --- ดึงปีที่แต่งตั้ง (พ.ศ.) จากวันที่เริ่มประกาศ ---
    def extract_thai_year(val):
        if pd.isna(val) or not str(val).strip():
            return None
        val_str = str(val).strip()
        m = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', val_str)
        if m:
            y = int(m.group(3))
            if y < 2400:
                y += 543
            return str(y)
        return None

    if 'วันที่เริ่ม (announcement_date)' in df.columns:
        df['ปีที่แต่งตั้ง (พ.ศ.)'] = df['วันที่เริ่ม (announcement_date)'].apply(extract_thai_year)
    else:
        df['ปีที่แต่งตั้ง (พ.ศ.)'] = None
    
    st.sidebar.markdown("<div class='section-title'>การกรองข้อมูล (Filters)</div>", unsafe_allow_html=True)
    
    def reset_filters():
        st.session_state.search_input = ""
        st.session_state.status_select = "ทั้งหมด"
        st.session_state.gender_select = "ทุกเพศ"
        st.session_state.ann_select = "ทุกฉบับประกาศ"
        st.session_state.year_select = "ทุกปี"
        st.session_state.minister_select = "ทุกรัฐมนตรี"
        st.session_state.region_select = "ทุกภูมิภาค"
        st.session_state.prov_select = "ทุกจังหวัด"
        st.session_state.agency_select = "ทุกหน่วยงาน"
    
    if 'search_input' not in st.session_state: st.session_state.search_input = ""
    if 'status_select' not in st.session_state: st.session_state.status_select = "ทั้งหมด"
    if 'gender_select' not in st.session_state: st.session_state.gender_select = "ทุกเพศ"
    if 'ann_select' not in st.session_state: st.session_state.ann_select = "ทุกฉบับประกาศ"
    if 'year_select' not in st.session_state: st.session_state.year_select = "ทุกปี"
    if 'minister_select' not in st.session_state: st.session_state.minister_select = "ทุกรัฐมนตรี"
    if 'region_select' not in st.session_state: st.session_state.region_select = "ทุกภูมิภาค"
    if 'prov_select' not in st.session_state: st.session_state.prov_select = "ทุกจังหวัด"
    if 'agency_select' not in st.session_state: st.session_state.agency_select = "ทุกหน่วยงาน"
    
    search_term = st.sidebar.text_input("ระบุคำค้นหา (ชื่อ / ตำแหน่ง / หน่วยงาน):", key="search_input")
    
    status_options = {
        "ทั้งหมด": "ALL",
        "หมดอายุแล้ว": "EXPIRED",
        "ใกล้หมดอายุ (ภายใน 90 วัน)": "WARNING",
        "ยังไม่หมดอายุ (ปกติ)": "ACTIVE",
        "เฉพาะผู้ได้รับการแต่งตั้งซ้ำ/ต่ออายุ": "DUPLICATE"
    }
    selected_status_label = st.sidebar.selectbox("สถานะการดำรงตำแหน่ง (ภาพรวม):", list(status_options.keys()), key="status_select")
    selected_status = status_options[selected_status_label]
    
    gender_list = ["ทุกเพศ", "ชาย", "หญิง", "ไม่ระบุ"]
    selected_gender = st.sidebar.selectbox("เพศ:", gender_list, key="gender_select")
    
    announcement_list = ["ทุกฉบับประกาศ"] + sorted([str(x) for x in df['ประกาศฉบับที่'].dropna().unique() if str(x) != 'nan'])
    selected_ann = st.sidebar.selectbox("ประกาศฉบับที่:", announcement_list, key="ann_select")
    
    # ตัวเลือกฟิลเตอร์ปีที่แต่งตั้ง (พ.ศ.)
    unique_years = [str(x) for x in df['ปีที่แต่งตั้ง (พ.ศ.)'].dropna().unique() if str(x) not in ('nan', 'None', '')]
    unique_years = sorted(unique_years, reverse=True)
    year_list = ["ทุกปี"] + unique_years
    selected_year = st.sidebar.selectbox("ปีที่แต่งตั้ง (พ.ศ.):", year_list, key="year_select")
    
    # ตัวเลือกฟิลเตอร์รัฐมนตรีผู้ลงนาม — ดึงจากข้อมูลจริง รองรับรัฐมนตรีใหม่ในอนาคตอัตโนมัติ
    minister_col = 'รัฐมนตรี (minister)'
    if minister_col in df.columns:
        minister_vals = df[minister_col].dropna().astype(str)
        minister_vals = minister_vals[minister_vals.str.strip() != '']
        unique_ministers = sorted(minister_vals.unique().tolist())
    else:
        unique_ministers = []
    minister_list = ["ทุกรัฐมนตรี"] + unique_ministers
    selected_minister = st.sidebar.selectbox("รัฐมนตรีผู้ลงนาม:", minister_list, key="minister_select")

    region_list = ["ทุกภูมิภาค"] + sorted([str(x) for x in df['ภาค'].dropna().unique()]) if 'ภาค' in df.columns else ["ทุกภูมิภาค"]
    selected_region = st.sidebar.selectbox("ภูมิภาค:", region_list, key="region_select")
    
    province_list = ["ทุกจังหวัด"] + sorted([str(x) for x in df['จังหวัด'].dropna().unique()]) if 'จังหวัด' in df.columns else ["ทุกจังหวัด"]
    selected_province = st.sidebar.selectbox("จังหวัด:", province_list, key="prov_select")
    
    agency_list = ["ทุกหน่วยงาน"] + sorted([str(x) for x in df['หน่วยงาน'].dropna().unique()]) if 'หน่วยงาน' in df.columns else ["ทุกหน่วยงาน"]
    selected_agency = st.sidebar.selectbox("สังกัดหน่วยงาน:", agency_list, key="agency_select")
    
    st.sidebar.markdown("<hr style='margin: 15px 0 10px 0;'>", unsafe_allow_html=True)
    st.sidebar.button("ล้างตัวกรอง", on_click=reset_filters)
    
    filtered_df = df.copy()
    
    if search_term:
        term = search_term.lower()
        filtered_df = filtered_df[
            filtered_df['ชื่อ-นามสกุล'].fillna('').str.lower().str.contains(term) |
            filtered_df['หน่วยงาน'].fillna('').str.lower().str.contains(term)
        ]
    
    if selected_status == "EXPIRED":
        filtered_df = filtered_df[filtered_df['status_type'] == 'EXPIRED']
    elif selected_status == "WARNING":
        filtered_df = filtered_df[filtered_df['status_type'] == 'WARNING']
    elif selected_status == "ACTIVE":
        filtered_df = filtered_df[filtered_df['status_type'] == 'ACTIVE']
    elif selected_status == "DUPLICATE":
        filtered_df = filtered_df[filtered_df['is_duplicate'] == True]
    
    if selected_gender != "ทุกเพศ" and 'เพศ' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['เพศ'] == selected_gender]
    
    if selected_ann != "ทุกฉบับประกาศ":
        filtered_df = filtered_df[filtered_df['ประกาศฉบับที่'].astype(str) == selected_ann]
    
    if selected_year != "ทุกปี" and 'ปีที่แต่งตั้ง (พ.ศ.)' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['ปีที่แต่งตั้ง (พ.ศ.)'].astype(str) == selected_year]

    if selected_minister != "ทุกรัฐมนตรี" and minister_col in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[minister_col].astype(str) == selected_minister]
    
    if selected_region != "ทุกภูมิภาค" and 'ภาค' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['ภาค'] == selected_region]
    
    if selected_province != "ทุกจังหวัด" and 'จังหวัด' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['จังหวัด'] == selected_province]
    
    if selected_agency != "ทุกหน่วยงาน" and 'หน่วยงาน' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['หน่วยงาน'] == selected_agency]
    
    total_count = len(filtered_df)
    unique_count = filtered_df['clean_full_name'].nunique()
    expired_count = (filtered_df['status_type'] == 'EXPIRED').sum()
    warning_count = (filtered_df['status_type'] == 'WARNING').sum()
    active_count = (filtered_df['status_type'] == 'ACTIVE').sum()
    duplicate_persons_count = filtered_df[filtered_df['is_duplicate'] == True]['clean_full_name'].nunique()
    percent_expired = (expired_count / total_count * 100) if total_count > 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.markdown(kpi_card("จำนวนรายการทั้งหมด", f"{total_count:,}", f"({unique_count:,} บุคคล)", "#0f4c81", "#111827"), unsafe_allow_html=True)
    with col2: st.markdown(kpi_card("สถานะ: หมดอายุแล้ว", f"{expired_count:,}", f"สัดส่วน {percent_expired:.1f}%", "#b91c1c", "#b91c1c"), unsafe_allow_html=True)
    with col3: st.markdown(kpi_card("สถานะ: ใกล้หมดอายุ", f"{warning_count:,}", "ภายใน 90 วัน", "#b45309", "#b45309"), unsafe_allow_html=True)
    with col4: st.markdown(kpi_card("สถานะ: ยังไม่หมดอายุ", f"{active_count:,}", "อยู่ในวาระปกติ", "#15803d", "#15803d"), unsafe_allow_html=True)
    with col5: st.markdown(kpi_card("การแต่งตั้งซ้ำ", f"{duplicate_persons_count:,}", "บุคคล", "#0f4c81", "#111827"), unsafe_allow_html=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "สรุปภาพรวมและสถิติ",
        "วิเคราะห์สถานะหมดอายุ",
        "ข้อมูลการแต่งตั้งซ้ำ",
        "ฐานข้อมูลฉบับเต็ม"
    ])
    
    with tab1:
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("<div class='section-title'>สัดส่วนสถานะบัตรพนักงานเจ้าหน้าที่</div>", unsafe_allow_html=True)
            status_df = pd.DataFrame({
                "สถานะ": ["ยังไม่หมดอายุ", "ใกล้หมดอายุ", "หมดอายุแล้ว"],
                "จำนวน": [active_count, warning_count, expired_count]
            })
            fig_status = px.pie(
                status_df, names="สถานะ", values="จำนวน", color="สถานะ", hole=0.45,
                color_discrete_map={"ยังไม่หมดอายุ": "#15803d", "ใกล้หมดอายุ": "#b45309", "หมดอายุแล้ว": "#b91c1c"}
            )
            fig_status.update_traces(textposition='auto', textinfo='label+percent', textfont_size=14, marker=dict(line=dict(color='#ffffff', width=2)))
            fig_status.update_layout(showlegend=False, height=320, margin=dict(l=20, r=20, t=20, b=20), font=dict(family="Sarabun", size=14, color="#374151"))
            st.plotly_chart(fig_status, use_container_width=True)
    
        with col_chart2:
            st.markdown("<div class='section-title'>การกระจายตัวของพนักงานเจ้าหน้าที่ (ภูมิภาค)</div>", unsafe_allow_html=True)
            if 'ภาค' in filtered_df.columns:
                region_counts = filtered_df['ภาค'].value_counts().reset_index()
                region_counts.columns = ['ภาค', 'จำนวน']
                fig_region = px.bar(region_counts, x='จำนวน', y='ภาค', orientation='h', color_discrete_sequence=['#0f4c81'], text='จำนวน')
                fig_region.update_layout(yaxis={'categoryorder': 'total ascending'}, height=320, margin=dict(l=10, r=10, t=10, b=10), font=dict(family="Sarabun", size=14))
                st.plotly_chart(fig_region, use_container_width=True)
    
        col_chart3, col_chart4 = st.columns(2)
        with col_chart3:
            st.markdown("<div class='section-title'>สัดส่วนการแต่งตั้งจำแนกตามผู้ลงนาม</div>", unsafe_allow_html=True)
            if 'รัฐมนตรี (minister)' in filtered_df.columns:
                minister_counts = filtered_df['รัฐมนตรี (minister)'].value_counts().reset_index()
                minister_counts.columns = ['รัฐมนตรี', 'จำนวน']
                fig_min = px.bar(minister_counts, x='จำนวน', y='รัฐมนตรี', orientation='h', color_discrete_sequence=['#0f4c81'], text='จำนวน')
                fig_min.update_layout(yaxis={'categoryorder': 'total ascending'}, height=320, margin=dict(l=10, r=10, t=10, b=10), font=dict(family="Sarabun", size=14))
                st.plotly_chart(fig_min, use_container_width=True)
    
        with col_chart4:
            st.markdown("<div class='section-title'>10 อันดับหน่วยงานที่มีพนักงานเจ้าหน้าที่สูงสุด</div>", unsafe_allow_html=True)
            if 'หน่วยงาน' in filtered_df.columns:
                agency_counts = filtered_df['หน่วยงาน'].value_counts().head(10).reset_index()
                agency_counts.columns = ['หน่วยงาน', 'จำนวน']
                fig_agency = px.bar(agency_counts, x='จำนวน', y='หน่วยงาน', orientation='h', color_discrete_sequence=['#0f4c81'], text='จำนวน')
                fig_agency.update_layout(yaxis={'categoryorder': 'total ascending'}, height=320, margin=dict(l=10, r=10, t=10, b=10), font=dict(family="Sarabun", size=14))
                st.plotly_chart(fig_agency, use_container_width=True)
    
        col_chart5, col_chart6 = st.columns(2)
        with col_chart5:
            st.markdown("<div class='section-title'>10 อันดับจังหวัดที่มีพนักงานเจ้าหน้าที่สูงสุด</div>", unsafe_allow_html=True)
            if 'จังหวัด' in filtered_df.columns:
                prov_counts = filtered_df['จังหวัด'].value_counts().head(10).reset_index()
                prov_counts.columns = ['จังหวัด', 'จำนวน']
                fig_prov = px.bar(
                    prov_counts, x='จำนวน', y='จังหวัด', orientation='h', color_discrete_sequence=['#0f4c81'], text='จำนวน'
                )
                fig_prov.update_layout(yaxis={'categoryorder': 'total ascending'}, height=320, margin=dict(l=10, r=10, t=10, b=10), font=dict(family="Sarabun", size=14, color="#374151"))
                st.plotly_chart(fig_prov, use_container_width=True)
    
        with col_chart6:
            st.markdown("<div class='section-title'>สัดส่วนความกระจุกตัวของพนักงานเจ้าหน้าที่ตามจังหวัด</div>", unsafe_allow_html=True)
            if 'จังหวัด' in filtered_df.columns:
                prov_tree = filtered_df.groupby('จังหวัด').size().reset_index(name='จำนวน')
                if not prov_tree.empty:
                    fig_tree = px.treemap(
                        prov_tree, path=[px.Constant("ประเทศไทย"), 'จังหวัด'], values='จำนวน', color='จำนวน',
                        color_continuous_scale=px.colors.sequential.Blues, hover_name='จังหวัด'
                    )
                    fig_tree.update_traces(textinfo="label+value", textfont_size=13, marker=dict(line=dict(color='white', width=1)))
                    fig_tree.update_layout(margin=dict(l=10, r=10, t=10, b=10), font=dict(family="Sarabun"))
                    st.plotly_chart(fig_tree, use_container_width=True)
    
    with tab2:
        st.markdown("<div class='section-title'>ตารางวิเคราะห์ระยะเวลาการดำรงตำแหน่ง</div>", unsafe_allow_html=True)
        st.markdown("""<div style="background-color: #f0f9ff; padding: 12px 16px; border-radius: 4px; border: 1px solid #bae6fd; color: #0c4a6e; margin-bottom: 15px;">
            <strong>หมายเหตุการแสดงสี:</strong> <span style="color: #b91c1c; font-weight: 600;">สีแดง = สิ้นสุดวาระแล้ว</span> | 
            <span style="color: #b45309; font-weight: 600;">สีส้ม = ใกล้สิ้นสุดวาระ (ไม่เกิน 90 วัน)</span> | 
            <span style="color: #15803d; font-weight: 600;">สีเขียว = อยู่ในวาระปกติ</span></div>""", unsafe_allow_html=True)
    
        col_tab2_filter, col_tab2_export = st.columns([3, 1])
        with col_tab2_filter:
            local_status_filter = st.radio(
                "กรองแสดงผลเฉพาะในตารางนี้:",
                [
                    "ทั้งหมด",
                    ":red[🔴 สิ้นสุดวาระแล้ว]",
                    ":orange[🟡 ใกล้สิ้นสุดวาระ (<= 90 วัน)]",
                    ":green[🟢 อยู่ในวาระปกติ]"
                ],
                horizontal=True
            )
    
        tab2_df = filtered_df.copy()
        if local_status_filter == ":red[🔴 สิ้นสุดวาระแล้ว]":
            tab2_df = tab2_df[tab2_df['status_type'] == 'EXPIRED']
        elif local_status_filter == ":orange[🟡 ใกล้สิ้นสุดวาระ (<= 90 วัน)]":
            tab2_df = tab2_df[tab2_df['status_type'] == 'WARNING']
        elif local_status_filter == ":green[🟢 อยู่ในวาระปกติ]":
            tab2_df = tab2_df[tab2_df['status_type'] == 'ACTIVE']
    
        tab2_df = tab2_df.sort_values(by='ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ', ascending=True)
        
        columns_to_show = [
            'ชื่อ-นามสกุล', 'หน่วยงาน', 'จังหวัด', 'ภาค', 'ประกาศฉบับที่',
            'วันที่เริ่ม (announcement_date)', 'วันหมดอายุบัตร', 'สถานะปัจจุบัน', 'รัฐมนตรี (minister)'
        ]
        actual_columns = [col for col in columns_to_show if col in tab2_df.columns]
        tab2_display_df = tab2_df[actual_columns]
    
        with col_tab2_export:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            csv_tab2 = tab2_display_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="ส่งออกข้อมูลนี้ (CSV)",
                data=csv_tab2,
                file_name="Expiration_Analysis_Report.csv",
                mime="text/csv",
                use_container_width=True
            )
    
        exp_styled = tab2_display_df.style.apply(
            lambda row: [highlight_row_status(tab2_df.loc[row.name])[0]] * len(row), axis=1
        )
        st.dataframe(exp_styled, use_container_width=True, height=500)
    
    with tab3:
        st.markdown("<div class='section-title'>รายงานบุคคลที่ได้รับการแต่งตั้งมากกว่า 1 วาระ </div>", unsafe_allow_html=True)
        dup_names = df[df['is_duplicate']]['clean_full_name'].unique()
    
        if len(dup_names) == 0:
            st.success("ไม่พบข้อมูลผู้ได้รับการแต่งตั้งซ้ำหรือต่ออายุในระบบ")
        else:
            for name in dup_names:
                person_records = df[df['clean_full_name'] == name].sort_values(by='ประกาศฉบับที่')
                with st.expander(f"ประวัติการแต่งตั้ง: {name} (จำนวน {len(person_records)} วาระ)", expanded=False):
                    cols = st.columns(len(person_records))
                    for idx, (_, rec) in enumerate(person_records.iterrows()):
                        with cols[idx]:
                            days = rec['ระยะวันที่หมดอายุไปแล้วหรือเหลืออีกกี่วันจะหมดอายุ']
                            if pd.isna(days):
                                status_str, bg_color = "-", "#ffffff"
                            elif days < 0:
                                status_str, bg_color = f"<span style='color:#b91c1c; font-weight:600;'>สิ้นสุดวาระ</span>", "#fee2e2"
                            elif days <= 90:
                                status_str, bg_color = f"<span style='color:#b45309; font-weight:600;'>ใกล้สิ้นสุดวาระ (เหลือ {format_ymd(days)})</span>", "#fef3c7"
                            else:
                                status_str, bg_color = f"<span style='color:#15803d; font-weight:600;'>อยู่ในวาระปกติ (เหลือ {format_ymd(days)})</span>", "#dcfce7"
    
                            st.markdown(f"""
                            <div style="background-color: {bg_color}; padding: 15px; border: 1px solid #e5e7eb; border-radius: 4px;">
                                <strong style="color: #0f4c81;">ประกาศฉบับที่ {rec.get('ประกาศฉบับที่', '-')}</strong><br><br>
                                <b>หน่วยงานสังกัด:</b> {rec.get('หน่วยงาน', '-')}<br>
                                <b>จังหวัดปฏิบัติงาน:</b> {rec.get('จังหวัด', '-')}<br>
                                <b>วันที่ประกาศ:</b> {rec.get('วันที่เริ่ม (announcement_date)', '-')}<br>
                                <b>วันหมดอายุ:</b> {rec.get('วันหมดอายุบัตร', '-')}<br>
                                <b>ผู้ลงนาม:</b> {rec.get('รัฐมนตรี (minister)', '-')}<br><br>
                                <b>สถานะปัจจุบัน:</b> {status_str}
                            </div>
                            """, unsafe_allow_html=True)
    
    with tab4:
        st.markdown("<div class='section-title'>ฐานข้อมูลพนักงานเจ้าหน้าที่ฉบับสมบูรณ์</div>", unsafe_allow_html=True)
        st.markdown("""<div style="background-color: #f0f9ff; padding: 12px 16px; border-radius: 4px; border: 1px solid #bae6fd; color: #0c4a6e; margin-bottom: 15px;">
            <strong>หมายเหตุการแสดงสี:</strong> <span style="color: #b91c1c; font-weight: 600;">สีแดง = สิ้นสุดวาระแล้ว</span> | 
            <span style="color: #b45309; font-weight: 600;">สีส้ม = ใกล้สิ้นสุดวาระ (ไม่เกิน 90 วัน)</span> | 
            <span style="color: #15803d; font-weight: 600;">สีเขียว = อยู่ในวาระปกติ</span></div>""", unsafe_allow_html=True)
    
        # --- 1. กำหนดคอลัมน์ที่ต้องการโชว์ในตาราง ---
        columns_to_show_tab4 = [
          'ประกาศฉบับที่','ชื่อ-นามสกุล', 'เพศ', 'หน่วยงาน', 'จังหวัด', 'ภาค','รัฐมนตรี (minister)', 'สถานะปัจจุบัน', 'is_duplicate',
        ]
        
        # กรองเอาเฉพาะคอลัมน์ที่มีอยู่จริงป้องกัน Error
        actual_columns_tab4 = [col for col in columns_to_show_tab4 if col in filtered_df.columns]
        tab4_display_df = filtered_df[actual_columns_tab4]
    
        # --- 2. ใส่สีแถว โดยให้อ้างอิงเงื่อนไขจาก filtered_df ตัวเต็มเบื้องหลัง ---
        main_styled = tab4_display_df.style.apply(
            lambda row: [highlight_row_status(filtered_df.loc[row.name])[0]] * len(row), axis=1
        )
        
        st.dataframe(main_styled, use_container_width=True, height=500)
    
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- 3. ปุ่มดาวน์โหลด (ยังคงให้ดาวน์โหลดข้อมูล "ครบทุกคอลัมน์" เผื่อนำไปใช้งานต่อ) ---
        csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="ส่งออกข้อมูลนี้ (CSV)", 
            data=csv_data, 
            file_name="officers_export.csv", 
            mime="text/csv"
        )


# ==============================================================================
# 2. จัดการประกาศราชกิจจาฯ
# ==============================================================================
elif menu == '📅 จัดการประกาศราชกิจจาฯ':
    st.markdown("<div class='section-title'>จัดการข้อมูลประกาศราชกิจจานุเบกษา</div>", unsafe_allow_html=True)

    st.subheader("ตารางประกาศทั้งหมดในระบบ")
    df_ann = get_all_announcements()
    if df_ann.empty:
        st.info("ยังไม่มีข้อมูลประกาศในระบบ กรุณาเพิ่มประกาศด้านล่าง")
    else:
        st.dataframe(df_ann, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    st.subheader("เพิ่ม / แก้ไขประกาศ")
    st.caption("หากกรอกประกาศฉบับที่ซ้ำ ระบบจะอัปเดตข้อมูลเดิมโดยอัตโนมัติ")

    with st.form("form_add_announcement", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            ann_no_input = st.number_input("ประกาศฉบับที่ *", min_value=1, step=1, value=1)
            start_date_input = st.text_input("วันที่เริ่ม (กรอกเฉพาะตัวเลขและ /) *", placeholder="เช่น 31/12/2568")
        with col_f2:
            minister_input = st.text_input("ชื่อรัฐมนตรีผู้ลงนาม", placeholder="เช่น นายประเสริฐ จันทรรวงทอง")

        submitted = st.form_submit_button("💾 บันทึกข้อมูลประกาศ", use_container_width=True)
        if submitted:
            date_val = start_date_input.strip()
            
            if not date_val:
                st.error("กรุณากรอกวันที่เริ่ม")
            elif not re.fullmatch(r'[0-9/]+', date_val):
                st.error("❌ กรอกข้อมูลไม่ถูกต้อง: กรุณาพิมพ์เฉพาะ 'ตัวเลข' และ 'เครื่องหมาย /' เท่านั้น (ตัวอย่าง 31/12/2568)")
            else:
                try:
                    add_or_update_announcement(
                        announcement_no=int(ann_no_input),
                        start_date=date_val,
                        minister_name=minister_input.strip() if minister_input.strip() else None,
                        term_years=4.0
                    )
                    st.success(f"✅ บันทึกประกาศฉบับที่ {ann_no_input} สำเร็จแล้ว!")
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
    st.markdown("<hr>", unsafe_allow_html=True)

    st.subheader("ลบประกาศออกจากระบบ")
    df_ann_del = get_all_announcements()
    if not df_ann_del.empty:
        ann_no_list = df_ann_del['announcement_no'].tolist()
        ann_to_delete = st.selectbox("เลือกประกาศฉบับที่ต้องการลบ:", ann_no_list)
        col_del1, col_del2 = st.columns([1, 4])
        with col_del1:
            if st.button("🗑️ ลบประกาศนี้", type="primary"):
                try:
                    delete_announcement(int(ann_to_delete))
                    st.success(f"ลบประกาศฉบับที่ {ann_to_delete} สำเร็จแล้ว")
                    st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
    else:
        st.info("ไม่มีประกาศในระบบ")


# ==============================================================================
# 3. อัปโหลดและประมวลผลข้อมูล
# ==============================================================================
# ==============================================================================
# 2. จัดการหน่วยงาน
# ==============================================================================
elif menu == '🏢 จัดการหน่วยงาน':
    st.markdown("<div class='section-title'>🏢 จัดการข้อมูลหน่วยงานและจังหวัด</div>", unsafe_allow_html=True)
    st.caption("บันทึกข้อมูลหน่วยงาน ตรวจสอบจังหวัดที่เคยระบุไว้ และค้นหาประวัติหน่วยงานในระบบ")

    tab_add, tab_search, tab_list = st.tabs([
        "➕ บันทึก / อัปเดตหน่วยงาน",
        "🔍 ค้นหาจังหวัดของหน่วยงาน",
        "📋 รายการหน่วยงานทั้งหมด"
    ])

    with tab_add:
        st.subheader("บันทึก / อัปเดต ข้อมูลหน่วยงาน")
        st.caption("หากกรอกชื่อหน่วยงานที่มีอยู่แล้วในระบบ ข้อมูลจะถูกอัปเดตโดยอัตโนมัติ")

        # ตรวจสอบแจ้งเตือนสถานะการบันทึกสำเร็จ
        if 'agency_save_success' in st.session_state and st.session_state.agency_save_success:
            st.success(st.session_state.agency_save_success)
            st.toast(st.session_state.agency_save_success, icon="✅")
            del st.session_state.agency_save_success

        with st.form("form_add_agency", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                input_agency_name = st.text_input("ชื่อหน่วยงาน *", placeholder="เช่น กรมการปกครอง, สภ.เมืองเชียงใหม่")
                input_province = st.text_input("จังหวัด *", placeholder="เช่น กรุงเทพมหานคร, เชียงใหม่")
            with col_a2:
                input_region = st.text_input("ภาค / พื้นที่ (ไม่บังคับ)", placeholder="เช่น ภาคกลาง, ภาคเหนือ")
            
            submit_agency = st.form_submit_button("💾 บันทึกหน่วยงาน", use_container_width=True)
            if submit_agency:
                if not input_agency_name.strip() or not input_province.strip():
                    st.error("❌ กรุณากรอก 'ชื่อหน่วยงาน' และ 'จังหวัด' ให้ครบถ้วน")
                else:
                    try:
                        save_agency(input_agency_name, input_province, input_region)
                        st.session_state.agency_save_success = f"✅ บันทึกข้อมูลหน่วยงาน '{input_agency_name.strip()}' (จังหวัด: {input_province.strip()}) สำเร็จเรียบร้อยแล้ว!"
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")

    with tab_search:
        st.subheader("🔍 ตรวจสอบว่าหน่วยงานเคยระบุจังหวัดไว้หรือไม่")
        st.caption("ระบบจะค้นหาทั้งจากหน่วยงานที่บันทึกไว้ในระบบ และจากประวัติการนำเข้าไฟล์ประกาศ")

        col_s1, col_s2 = st.columns([4, 1])
        with col_s1:
            search_agency_kw = st.text_input("พิมพ์ชื่อหน่วยงาน (หรือบางส่วนของชื่อ):", placeholder="เช่น ตำรวจ, ตรวจคนเข้าเมือง, ศาล")
        with col_s2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_search = st.button("🔍 ค้นหา", use_container_width=True)

        if search_agency_kw.strip():
            df_search_res = search_agency(search_agency_kw.strip())
            if not df_search_res.empty:
                st.success(f"พบข้อมูลที่เกี่ยวข้องทั้งหมด {len(df_search_res):,} รายการ")
                st.dataframe(df_search_res, use_container_width=True, hide_index=True)
            else:
                st.warning(f"⚠️ ไม่พบข้อมูลหน่วยงานที่มีคำว่า '{search_agency_kw.strip()}' ในระบบ (ยังไม่เคยระบุจังหวัด)")

    with tab_list:
        st.subheader("📋 หน่วยงานที่บันทึกไว้ในระบบ (Agency Registry)")
        df_all_agencies = get_agency_registry()
        if df_all_agencies.empty:
            st.info("ยังไม่มีหน่วยงานที่บันทึกไว้ในระบบ คุณสามารถเพิ่มได้ที่แท็บ '➕ บันทึก / อัปเดตหน่วยงาน'")
        else:
            st.caption(f"ทั้งหมด {len(df_all_agencies):,} หน่วยงาน")
            df_display = df_all_agencies.rename(columns={
                'agency_name': 'ชื่อหน่วยงาน',
                'province': 'จังหวัด',
                'region': 'ภาค',
                'updated_at': 'อัปเดตล่าสุด'
            })
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            st.markdown("<hr>", unsafe_allow_html=True)
            st.subheader("🗑️ ลบข้อมูลหน่วยงาน")
            col_del_a, col_del_b = st.columns([3, 1])
            with col_del_a:
                agency_to_delete = st.selectbox("เลือกหน่วยงานที่ต้องการลบ:", df_all_agencies['agency_name'].tolist())
            with col_del_b:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ ลบหน่วยงานนี้", type="primary", use_container_width=True):
                    try:
                        delete_agency(agency_to_delete)
                        st.success(f"ลบหน่วยงาน '{agency_to_delete}' สำเร็จแล้ว")
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")


elif menu == '📁 อัปโหลดและประมวลผลข้อมูล':
    st.markdown("<div class='section-title'>อัปโหลดและประมวลผลข้อมูลดิบ</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "เลือกไฟล์ข้อมูลดิบ (Excel หรือ CSV)",
        type=["xlsx", "csv"],
        help="รองรับไฟล์ .xlsx และ .csv"
    )

    if uploaded_file is not None:
        st.subheader("ตัวอย่างข้อมูลดิบ (ก่อนประมวลผล)")
        try:
            if uploaded_file.name.endswith('.csv'):
                df_preview = pd.read_csv(uploaded_file)
            else:
                df_preview = pd.read_excel(uploaded_file)

            st.info(f"พบข้อมูล {len(df_preview):,} แถว × {len(df_preview.columns)} คอลัมน์")
            st.dataframe(df_preview.head(10), use_container_width=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            if st.button("🚀 คลีนข้อมูลและบันทึกลง Database (Append)", type="primary", use_container_width=True):
                with st.spinner("กำลังประมวลผลข้อมูล..."):
                    try:
                        from data_pipeline import process_raw_dataframe
                        upload_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        df_processed = process_raw_dataframe(
                            df_preview, 
                            source_filename=uploaded_file.name,
                            upload_time=upload_timestamp
                        )

                        rows_appended = append_officers_history(df_processed)

                        all_data = load_officers_history()
                        all_data.to_csv(DATA_PATH, index=False, encoding='utf-8-sig')

                        st.success(f"✅ บันทึกข้อมูลสะสมสำเร็จ! เพิ่มข้อมูลใหม่จำนวน {rows_appended:,} แถว (ยอดสะสมรวมใน DB: {len(all_data):,} แถว)")

                        st.subheader("ตัวอย่างข้อมูลรอบล่าสุดหลังประมวลผล")
                        st.info(f"ผลลัพธ์รอบนี้: {len(df_processed):,} แถว × {len(df_processed.columns)} คอลัมน์ | ไฟล์ต้นทาง: `{uploaded_file.name}` | เวลา: `{upload_timestamp}`")
                        st.dataframe(df_processed.head(10), use_container_width=True)

                        st.markdown("<hr>", unsafe_allow_html=True)
                        st.subheader("สถิติสรุปภาพรวมทั้งหมดในฐานข้อมูล (Cumulative Summary)")
                        if 'status_type' in all_data.columns:
                            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                            with col_s1:
                                st.metric("ยอดสะสมทั้งหมด", f"{len(all_data):,} คน")
                            with col_s2:
                                st.metric("สิ้นสุดวาระ (EXPIRED)", f"{(all_data['status_type'] == 'EXPIRED').sum():,} คน")
                            with col_s3:
                                st.metric("ใกล้หมดอายุ (WARNING)", f"{(all_data['status_type'] == 'WARNING').sum():,} คน")
                            with col_s4:
                                st.metric("อยู่ในวาระปกติ (ACTIVE)", f"{(all_data['status_type'] == 'ACTIVE').sum():,} คน")

                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาดระหว่างประมวลผล: {e}")
                        st.exception(e)

        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ได้: {e}")

    else:
        st.info("กรุณาเลือกไฟล์เพื่อเริ่มต้นอัปโหลด")
        
        df_history = load_officers_history()
        db_type_name = "Supabase Database (Online)" if is_using_supabase() else "SQLite Database (Local)"
        if not df_history.empty:
            st.success(f"✅ ฐานข้อมูลสะสม : มีข้อมูลทั้งหมด {len(df_history):,} รายการ")
            
            if 'source_file' in df_history.columns and 'upload_time' in df_history.columns:
                st.markdown("#### 📁 ประวัติการนำเข้าไฟล์สะสม (Upload History)")
                history_summary = (
                    df_history.groupby(['source_file', 'upload_time'])
                    .size()
                    .reset_index(name='จำนวนแถวที่นำเข้า')
                    .sort_values(by='upload_time', ascending=False)
                )
                st.dataframe(history_summary, use_container_width=True)
            
            if 'status_type' in df_history.columns:
                st.markdown("#### ยอดรวมแยกตามสถานะ ")
                st.dataframe(df_history['status_type'].value_counts().reset_index().rename(columns={'index': 'สถานะ', 'count': 'จำนวน'}), use_container_width=True)

            with st.expander("การจัดการฐานข้อมูลสะสม"):
                st.markdown("#### เลือกลบเฉพาะบางไฟล์")
                if 'source_file' in df_history.columns:
                    unique_files = df_history['source_file'].dropna().unique().tolist()
                    if unique_files:
                        col_del1, col_del2 = st.columns([3, 1])
                        with col_del1:
                            file_to_delete = st.selectbox("เลือกไฟล์ที่ต้องการลบข้อมูลออก:", unique_files)
                        with col_del2:
                            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                            if st.button("🗑️ ลบเฉพาะไฟล์นี้"):
                                try:
                                    # --- ลบข้อมูลของไฟล์นี้ออกจาก SQLite Database จริงๆ ---
                                    with sqlite3.connect(DB_PATH) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("DELETE FROM officers_history WHERE source_file = ?", (file_to_delete,))
                                        conn.commit()
                                        
                                    # --- อัปเดตไฟล์ CSV สำรองให้ตรงกับ Database ล่าสุด ---
                                    updated_data = load_officers_history()
                                    if not updated_data.empty:
                                        updated_data.to_csv(DATA_PATH, index=False, encoding='utf-8-sig')
                                    elif os.path.exists(DATA_PATH):
                                        os.remove(DATA_PATH)
                                        
                                    st.success(f"ลบข้อมูลจากไฟล์ '{file_to_delete}' ออกจากระบบแล้ว")
                                    st.rerun() 
                                except Exception as e:
                                    st.error(f"เกิดข้อผิดพลาดในการลบไฟล์: {e}")
                else:
                    st.info("ไม่พบประวัติชื่อไฟล์ในระบบ")

                st.markdown("<hr>", unsafe_allow_html=True)
                
                st.markdown("#### ล้างข้อมูลทั้งหมด")
                st.caption("การดำเนินการนี้จะลบประวัติการอัปโหลดทั้งหมดเพื่อเริ่มต้นใหม่")
                if st.button("🚨 ล้างฐานข้อมูลสะสมทั้งหมด (Clear History)", type="primary"):
                    delete_all_officers_history()
                    if os.path.exists(DATA_PATH):
                        os.remove(DATA_PATH)
                    st.success("ล้างข้อมูลสะสมเรียบร้อยแล้ว ระบบกำลังรีเฟรช...")
                    st.rerun()
        else:
            st.warning("⚠️ ยังไม่มีข้อมูลสะสมในฐานข้อมูล กรุณาอัปโหลดไฟล์เพื่อเริ่มต้นใช้งาน")