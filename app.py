import os
import base64
import sqlite3
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import pdfkit
import pandas as pd
import streamlit as st
import shutil
from openai import OpenAI

# ─── OPENAI KEY LOADING ─────────────────────────────────────────
try:
    openai_key = st.secrets["openai"]["key"]
except Exception:
    openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    st.error("❌ OpenAI API key not found. Set OPENAI_API_KEY in your environment.")
    st.stop()

client = OpenAI(api_key=openai_key)

def ai_query_system(prompt: str, df: pd.DataFrame) -> str:
    data_json = df.to_json(orient="records")
    messages = [
        {"role":"system", "content":"You are a savvy HR data analyst."},
        {"role":"user",   "content":f"{prompt}\n\nHere is the starters data:\n{data_json}"}
    ]
    resp = client.chat.completions.create(
        model="gpt-4", messages=messages, temperature=0.2, max_tokens=500
    )
    return resp.choices[0].message.content.strip()

# ─── PAGE CONFIG & THEME ────────────────────────────────────────
st.set_page_config(page_title="New Starter Details", layout="centered")
st.markdown("""
<style>
div.block-container { max-width:1200px!important; padding:3rem!important; }
.section-card { background:#fff; border-radius:8px; padding:24px; margin-bottom:24px; box-shadow:0 2px 12px rgba(0,0,0,0.15); }
.section-card h2 { margin-top:0; color:#005f8c; font-size:1.4rem; }
.css-1r6slb0.e1fqkh3o2, .css-1urxts9.e1fqkh3o2 { margin-bottom:1.25rem; }
hr { border:none; border-top:2px dashed #555!important; margin:2rem 0!important; }
</style>
""", unsafe_allow_html=True)

# ─── DB SETUP ────────────────────────────────────────────────────
conn = sqlite3.connect("starters.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS starters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier_name TEXT, supplier_contact TEXT, supplier_address TEXT,
  employee_name TEXT, address TEXT, ni_number TEXT,
  role_position TEXT, department TEXT, start_date TEXT,
  office_location TEXT, salary_details TEXT, probation_length TEXT,
  emergency_contact TEXT, additional_info TEXT, generated_date TEXT
)""")
c.execute("""CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE, contact TEXT, address TEXT
)""")
conn.commit()

# ─── DEDUPE ──────────────────────────────────────────────────────
c.execute("""
DELETE FROM starters
WHERE id NOT IN (
  SELECT MIN(id)
  FROM starters
  GROUP BY
    supplier_name, supplier_contact, supplier_address,
    employee_name, address, ni_number,
    role_position, department, start_date,
    office_location, salary_details, probation_length,
    emergency_contact, additional_info, generated_date
)
""")
conn.commit()

# ─── LOGO ────────────────────────────────────────────────────────
with open("logo.png","rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

def generate_pdf_bytes(fields):
    env  = Environment(loader=FileSystemLoader("."))
    tpl  = env.get_template("template.html")
    html = tpl.render(**fields)
    wk   = shutil.which("wkhtmltopdf")
    if not wk:
        raise RuntimeError("wkhtmltopdf not found")
    cfg = pdfkit.configuration(wkhtmltopdf=wk)
    return pdfkit.from_string(html, False, configuration=cfg,
                              options={"enable-local-file-access":None})

# ─── NAVIGATION ──────────────────────────────────────────────────
st.sidebar.title("🔀 Navigation")
page = st.sidebar.radio("Navigation",
    ["New Starter","Starter List","🤖 AI Assistant"],
    label_visibility="collapsed"
)

# ─── NEW STARTER ─────────────────────────────────────────────────
if page=="New Starter":
    st.title("🆕 New Starter Details")

    # load clients
    clients_df     = pd.read_sql("SELECT * FROM clients ORDER BY name", conn)
    client_options = ["<New Client>"] + clients_df["name"].tolist()

    with st.form("new_starter_form"):
        # Supplier
        st.markdown('<div class="section-card">',unsafe_allow_html=True)
        st.markdown("## 🏢 Supplier Information")
        l,r = st.columns([1,1])
        with l:
            supplier_name    = st.text_input("Supplier Name","PRL Site Solutions")
            supplier_contact = st.text_input("Supplier Contact","Office")
        with r:
            supplier_address = st.text_area("Supplier Address","259 Wallasey village\nWallasey\nCH45 3LR",height=120)
        st.markdown("</div>",unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)

        # Client
        st.markdown('<div class="section-card">',unsafe_allow_html=True)
        st.markdown("## 🏢 Client Information")
        sel = st.selectbox("Choose a client:", client_options)
        if sel!="<New Client>":
            row = clients_df[clients_df["name"]==sel].iloc[0]
            client_name,client_contact,client_address = sel,row["contact"],row["address"]
        else:
            client_name=client_contact=client_address=""
        cl,cr = st.columns([1,1])
        with cl:
            client_name    = st.text_input("Client Name",client_name)
            client_contact = st.text_input("Client Contact",client_contact)
        with cr:
            client_address = st.text_area("Client Address",client_address,height=120)
        st.markdown("</div>",unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)

        # Candidate
        st.markdown('<div class="section-card">',unsafe_allow_html=True)
        st.markdown("## 👤 Candidate Information")
        c1,c2 = st.columns(2)
        with c1:
            employee_name = st.text_input("Employee Name")
            address       = st.text_area("Address",height=100)
        with c2:
            role_position  = st.text_input("Role / Position")
            department     = st.text_input("Department")
            start_date     = st.date_input("Start Date")
            office_location= st.text_input("Office Location")
            salary_details = st.text_area("Salary Details",height=80)
        st.markdown("</div>",unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)

        # Emergency & Additional
        with st.expander("📝 Emergency & Additional Info",expanded=False):
            e1,e2 = st.columns(2)
            with e1: emergency_contact = st.text_area("Emergency Contact Info",height=120)
            with e2: additional_info   = st.text_area("Additional Information",height=120)

        submitted = st.form_submit_button("📄 Generate PDF")

    if submitted:
        # save new client & rerun
        if sel=="<New Client>" and client_name.strip():
            c.execute(
              "INSERT OR IGNORE INTO clients(name,contact,address) VALUES(?,?,?)",
              (client_name,client_contact,client_address)
            )
            conn.commit()
            st.success("✅ New client saved — please refresh to update list.")
            st.stop()

        # prepare PDF fields
        ni_no=prob_len=""
        html_fields = {
            "logo_b64":logo_b64,
            "supplier_name":supplier_name,
            "supplier_contact":supplier_contact,
            "supplier_address":supplier_address.replace("\n","<br/>"),
            "client_name":client_name,
            "client_contact":client_contact,
            "client_address":client_address.replace("\n","<br/>"),
            "employee_name":employee_name,
            "address":address.replace("\n","<br/>"),
            "ni_number":ni_no,
            "role_position":role_position,
            "department":department,
            "start_date":start_date.strftime("%d %B %Y"),
            "office_location":office_location,
            "salary_details":salary_details,
            "probation_length":prob_len,
            "emergency_contact":emergency_contact.replace("\n","<br/>"),
            "additional_info":additional_info.replace("\n","<br/>"),
            "generated_date":datetime.today().strftime("%d %B %Y")
        }

        # insert starter
        cols = [
          "supplier_name","supplier_contact","supplier_address",
          "employee_name","address","ni_number",
          "role_position","department","start_date",
          "office_location","salary_details","probation_length",
          "emergency_contact","additional_info","generated_date"
        ]
        ph = ",".join("?" for _ in cols)
        sql= f"INSERT INTO starters({','.join(cols)}) VALUES({ph})"
        c.execute(sql,tuple(html_fields[c] for c in cols))
        conn.commit()

        # generate PDF
        try:
            pdfb=generate_pdf_bytes(html_fields)
            st.success("✅ PDF created!")
            st.download_button("⬇️ Download PDF",pdfb,
              file_name=f"new_starter_{employee_name.replace(' ','_')}.pdf",
              mime="application/pdf")
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

# ─── LIST & AI TABS UNCHANGED ───────────────────────────────────

