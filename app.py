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
except:
    openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    st.error("❌ OpenAI API key not found. Set OPENAI_API_KEY in your environment.")
    st.stop()
client = OpenAI(api_key=openai_key)

def ai_query_system(prompt: str, df: pd.DataFrame) -> str:
    data_json = df.to_json(orient="records")
    messages = [
        {"role":"system","content":"You are a savvy HR data analyst."},
        {"role":"user",  "content":f"{prompt}\n\nHere is the data:\n{data_json}"}
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

# ─── DATABASE SETUP & MIGRATION ────────────────────────────────
conn = sqlite3.connect("starters.db", check_same_thread=False)
c    = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS starters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier_name TEXT,
  supplier_contact TEXT,
  supplier_address TEXT,
  client_name TEXT,
  client_contact TEXT,
  client_address TEXT,
  employee_name TEXT,
  address TEXT,
  ni_number TEXT,
  role_position TEXT,
  department TEXT,
  start_date TEXT,
  office_location TEXT,
  salary_details TEXT,
  probation_length TEXT,
  emergency_contact TEXT,
  additional_info TEXT,
  generated_date TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE,
  contact TEXT,
  address TEXT
)
""")
conn.commit()
# Deduplicate starters
c.execute("""
DELETE FROM starters
WHERE id NOT IN (
  SELECT MIN(id) FROM starters
  GROUP BY
    supplier_name, supplier_contact, supplier_address,
    client_name, client_contact, client_address,
    employee_name, address, ni_number,
    role_position, department, start_date,
    office_location, salary_details, probation_length,
    emergency_contact, additional_info, generated_date
)
""")
conn.commit()

# ─── LOGO ENCODING ───────────────────────────────────────────────
with open("logo.png","rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

def generate_pdf_bytes(fields):
    tpl  = Environment(loader=FileSystemLoader(".")).get_template("template.html")
    html = tpl.render(**fields)
    wk   = shutil.which("wkhtmltopdf")
    if not wk:
        raise RuntimeError("wkhtmltopdf not found on PATH.")
    cfg = pdfkit.configuration(wkhtmltopdf=wk)
    return pdfkit.from_string(html, False, configuration=cfg,
                              options={"enable-local-file-access":None})

# ─── NAVIGATION ──────────────────────────────────────────────────
st.sidebar.title("🔀 Navigation")
page = st.sidebar.radio(
    "Navigation",
    ["New Starter", "Add Client", "Starter List", "🤖 AI Assistant"],
    label_visibility="collapsed"
)

# ─── NEW STARTER FORM ────────────────────────────────────────────
if page == "New Starter":
    st.title("🆕 New Starter Details")

    # Load clients for dropdown
    clients_df     = pd.read_sql("SELECT * FROM clients ORDER BY name", conn)
    client_options = ["<New Client>"] + clients_df["name"].tolist()

    # Pre-initialize session state
    st.session_state.setdefault("client_select", "<New Client>")
    st.session_state.setdefault("client_name_input", "")
    st.session_state.setdefault("client_contact_input", "")
    st.session_state.setdefault("client_address_input", "")

    with st.form("new_starter_form"):
        # ─── SUPPLIER CARD ──────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("## 🏢 Supplier Information")
        s1, s2 = st.columns(2)
        with s1:
            supplier_name    = st.text_input("Supplier Name", "PRL Site Solutions")
            supplier_contact = st.text_input("Supplier Contact", "Office")
        with s2:
            supplier_address = st.text_area(
                "Supplier Address",
                "259 Wallasey village\nWallasey\nCH45 3LR",
                height=120
            )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

        # ─── CLIENT CARD (dropdown now here) ────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("## 🏢 Client Information")
        # **moved** dropdown into the card
        sel = st.selectbox("Choose a client:", client_options, key="client_select")
        if sel != "<New Client>":
            row = clients_df[clients_df["name"] == sel].iloc[0]
            st.session_state.client_name_input    = row["name"]
            st.session_state.client_contact_input = row["contact"]
            st.session_state.client_address_input = row["address"]
        else:
            st.session_state.client_name_input = ""
            st.session_state.client_contact_input = ""
            st.session_state.client_address_input = ""
        client_name    = st.text_input("Client Name", key="client_name_input")
        client_contact = st.text_input("Client Contact", key="client_contact_input")
        client_address = st.text_area("Client Address", key="client_address_input", height=120)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

        # ─── CANDIDATE CARD ────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("## 👤 Candidate Information")
        c1, c2 = st.columns(2)
        with c1:
            employee_name = st.text_input("Employee Name")
            address       = st.text_area("Address", height=100)
        with c2:
            role_position  = st.text_input("Role / Position")
            department     = st.text_input("Department")
            start_date     = st.date_input("Start Date")
            office_location= st.text_input("Office Location")
            salary_details = st.text_area("Salary Details", height=80)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

        # ─── EMERGENCY & ADDITIONAL ────────────────────────────
        with st.expander("📝 Emergency & Additional Information"):
            e1, e2 = st.columns(2)
            with e1:
                emergency_contact = st.text_area("Emergency Contact Info", height=120)
            with e2:
                additional_info   = st.text_area("Additional Information", height=120)

        submitted = st.form_submit_button("📄 Generate PDF")

    if submitted:
        # If creating a brand‐new client, save & halt
        if sel == "<New Client>" and client_name.strip():
            c.execute(
                "INSERT OR IGNORE INTO clients(name,contact,address) VALUES (?,?,?)",
                (client_name.strip(), client_contact.strip(), client_address.strip())
            )
            conn.commit()
            st.success("✅ New client saved — please refresh to use it.")
            st.stop()

        # Build PDF context
        html_fields = {
            "logo_b64":          logo_b64,
            "supplier_name":     supplier_name,
            "supplier_contact":  supplier_contact,
            "supplier_address":  supplier_address.replace("\n","<br/>"),
            "client_name":       client_name,
            "client_contact":    client_contact,
            "client_address":    client_address.replace("\n","<br/>"),
            "employee_name":     employee_name,
            "address":           address.replace("\n","<br/>"),
            "ni_number":         "",
            "role_position":     role_position,
            "department":        department,
            "start_date":        start_date.strftime("%d %B %Y"),
            "office_location":   office_location,
            "salary_details":    salary_details,
            "probation_length":  "",
            "emergency_contact": emergency_contact.replace("\n","<br/>"),
            "additional_info":   additional_info.replace("\n","<br/>"),
            "generated_date":    datetime.today().strftime("%d %B %Y"),
        }

        # Persist starter record
        db_cols = [
          "supplier_name","supplier_contact","supplier_address",
          "client_name","client_contact","client_address",
          "employee_name","address","ni_number",
          "role_position","department","start_date",
          "office_location","salary_details","probation_length",
          "emergency_contact","additional_info","generated_date"
        ]
        ph = ",".join("?" for _ in db_cols)
        sql = f"INSERT INTO starters ({','.join(db_cols)}) VALUES ({ph})"
        c.execute(sql, tuple(html_fields[c] for c in db_cols))
        conn.commit()

        # Render & Download PDF
        try:
            pdfb = generate_pdf_bytes(html_fields)
            st.success("✅ PDF created!")
            st.download_button("⬇️ Download PDF", pdfb,
                file_name=f"new_starter_{employee_name.replace(' ','_')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

# ─── ADD CLIENT PAGE ─────────────────────────────────────────────
elif page == "Add Client":
    st.title("➕ Add Client")
    with st.form("add_client_form"):
        cn = st.text_input("Client Name")
        cc = st.text_input("Contact")
        ca = st.text_area("Address", height=120)
        sub = st.form_submit_button("💾 Save Client")
    if sub:
        if not cn.strip():
            st.error("Please enter a client name.")
        else:
            c.execute(
                "INSERT OR IGNORE INTO clients(name,contact,address) VALUES (?,?,?)",
                (cn.strip(), cc.strip(), ca.strip())
            )
            conn.commit()
            st.success(f"✅ Client “{cn}” added! Refresh to use it.")

# ─── STARTER LIST ────────────────────────────────────────────────
elif page == "Starter List":
    st.title("📋 Starter List")
    df = pd.read_sql("SELECT * FROM starters", conn)
    if df.empty:
        st.info("No starters recorded yet.")
    else:
        if hasattr(st, "data_editor"):
            edited = st.data_editor(df, use_container_width=True, height=600)
        elif hasattr(st, "experimental_data_editor"):
            edited = st.experimental_data_editor(df, use_container_width=True, height=600, num_rows="dynamic")
        else:
            st.warning("Interactive editing requires Streamlit ≥1.24.0.")
            st.dataframe(df, use_container_width=True)
            edited = None

        if edited is not None and st.button("💾 Save changes"):
            orig = pd.read_sql("SELECT * FROM starters", conn)
            to_del = set(orig["id"]) - set(edited["id"])
            if to_del:
                c.executemany("DELETE FROM starters WHERE id=?", [(i,) for i in to_del])
            for _, row in edited.iterrows():
                c.execute("""
                  UPDATE starters SET
                    supplier_name=?,supplier_contact=?,supplier_address=?,
                    client_name=?,client_contact=?,client_address=?,
                    employee_name=?,address=?,ni_number=?,
                    role_position=?,department=?,start_date=?,
                    office_location=?,salary_details=?,probation_length=?,
                    emergency_contact=?,additional_info=?,generated_date=?
                  WHERE id=?
                """, tuple(row[col] for col in db_cols) + (row["id"],))
            conn.commit()
            st.success("✅ All changes saved!")

# ─── AI ASSISTANT ────────────────────────────────────────────────
else:
    st.title("🤖 AI Assistant")
    df = pd.read_sql("SELECT * FROM starters", conn)
    st.dataframe(df, use_container_width=True, height=250)
    prompt = st.text_area("Your question for GPT-4", height=120)
    if st.button("Ask AI"):
        if not prompt.strip():
            st.error("Enter a question.")
        else:
            st.markdown("### 🤖 GPT-4 says:")
            st.write(ai_query_system(prompt, df))
