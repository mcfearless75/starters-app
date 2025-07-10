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
    st.error("❌ OpenAI API key not found. Please set it as OPENAI_API_KEY in your environment.")
    st.stop()
client = OpenAI(api_key=openai_key)

def ai_query_system(prompt: str, df: pd.DataFrame) -> str:
    data_json = df.to_json(orient="records")
    messages = [
        {"role": "system", "content": "You are a savvy HR data analyst."},
        {"role": "user", "content": f"{prompt}\n\nHere is the starters data:\n{data_json}"}
    ]
    resp = client.chat.completions.create(
        model="gpt-4", messages=messages, temperature=0.2, max_tokens=500
    )
    return resp.choices[0].message.content.strip()

# ─── PAGE CONFIG & CUSTOM THEME ─────────────────────────────────
st.set_page_config(page_title="New Starter Details", layout="centered")
st.markdown("""
<style>
/* ─── NARROWER PAGE ────────────────────────────────────────── */
div.block-container {
    max-width: 1200px !important;
    padding: 3rem !important;
}

/* ─── CARDS ─────────────────────────────────────────────────── */
.section-card {
    background: #fff;
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
}
.section-card h2 {
    margin-top: 0;
    color: #005f8c;
    font-size: 1.4rem;
}

/* ─── FORM FIELDS ───────────────────────────────────────────── */
.css-1r6slb0.e1fqkh3o2,
.css-1urxts9.e1fqkh3o2 {
    margin-bottom: 1.25rem;
}

/* ─── SEPARATORS ───────────────────────────────────────────── */
hr {
    border: none;
    border-top: 2px dashed #555 !important;
    margin: 2rem 0 !important;
}

/* ─── DATA EDITOR ──────────────────────────────────────────── */
div[data-testid="stDataEditor"] .ag-root-wrapper {
    font-size: 24px!important;
    line-height: 1.6!important;
}
div[data-testid="stDataEditor"] .ag-header-cell-text {
    font-size: 26px!important;
    font-weight: 700!important;
}
div[data-testid="stDataEditor"] .ag-cell {
    padding: 20px!important;
}
div[data-testid="stDataEditor"] .ag-row {
    min-height: 60px!important;
}
</style>
""", unsafe_allow_html=True)

# ─── DATABASE SETUP ─────────────────────────────────────────────
conn = sqlite3.connect("starters.db", check_same_thread=False)
c    = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS starters (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier_name     TEXT,
  supplier_contact  TEXT,
  supplier_address  TEXT,
  employee_name     TEXT,
  address           TEXT,
  ni_number         TEXT,
  role_position     TEXT,
  department        TEXT,
  start_date        TEXT,
  office_location   TEXT,
  salary_details    TEXT,
  probation_length  TEXT,
  emergency_contact TEXT,
  additional_info   TEXT,
  generated_date    TEXT
)
""")
conn.commit()

# ─── DUPLICATE CLEANUP ─────────────────────────────────────────
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

# ─── LOGO ENCODING ───────────────────────────────────────────────
with open("logo.png", "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

def generate_pdf_bytes(fields):
    env    = Environment(loader=FileSystemLoader("."))
    tpl    = env.get_template("template.html")
    html   = tpl.render(**fields)
    wkpath = shutil.which("wkhtmltopdf")
    if not wkpath:
        raise RuntimeError("wkhtmltopdf not found on PATH.")
    cfg = pdfkit.configuration(wkhtmltopdf=wkpath)
    return pdfkit.from_string(html, False,
                              configuration=cfg,
                              options={"enable-local-file-access": None})

# ─── NAVIGATION ──────────────────────────────────────────────────
st.sidebar.title("🔀 Navigation")
page = st.sidebar.radio(
    "Navigation",
    ["New Starter", "Starter List", "🤖 AI Assistant"],
    label_visibility="collapsed"
)

# ─── NEW STARTER FORM ────────────────────────────────────────────
if page == "New Starter":
    st.title("🆕 New Starter Details")

    with st.form("new_starter_form"):
        # Supplier Information
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("## 🏢 Supplier Information")
        left, right = st.columns([1, 1])
        with left:
            supplier_name    = st.text_input("Supplier Name", "PRL Site Solutions")
            supplier_contact = st.text_input("Supplier Contact", "Office")
        with right:
            supplier_address = st.text_area(
                "Supplier Address",
                "259 Wallasey village\nWallasey\nCH45 3LR",
                height=120
            )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

        # Client Information
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("## 🏢 Client Information")
        cleft, cright = st.columns([1, 1])
        with cleft:
            client_name    = st.text_input("Client Name")
            client_contact = st.text_input("Client Contact")
        with cright:
            client_address = st.text_area("Client Address", height=120)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)

        # Candidate Information
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

        # Emergency & Additional Information
        with st.expander("📝 Emergency & Additional Information", expanded=False):
            e1, e2 = st.columns(2)
            with e1:
                emergency_contact = st.text_area("Emergency Contact Info", height=120)
            with e2:
                additional_info   = st.text_area("Additional Information", height=120)

        # Submit button (inside the form)
        submitted = st.form_submit_button("📄 Generate PDF")

    if submitted:
        # Blank out removed fields
        ni_number, probation_length = "", ""

        # Prepare all fields for the PDF template
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
            "ni_number":         ni_number,
            "role_position":     role_position,
            "department":        department,
            "start_date":        start_date.strftime("%d %B %Y"),
            "office_location":   office_location,
            "salary_details":    salary_details,
            "probation_length":  probation_length,
            "emergency_contact": emergency_contact.replace("\n","<br/>"),
            "additional_info":   additional_info.replace("\n","<br/>"),
            "generated_date":    datetime.today().strftime("%d %B %Y"),
        }

        # Insert into DB (exclude logo & client info)
        db_cols = [
            "supplier_name","supplier_contact","supplier_address",
            "employee_name","address","ni_number",
            "role_position","department","start_date",
            "office_location","salary_details","probation_length",
            "emergency_contact","additional_info","generated_date"
        ]
        placeholders = ",".join("?" for _ in db_cols)
        sql = f"INSERT INTO starters ({','.join(db_cols)}) VALUES ({placeholders})"
        c.execute(sql, tuple(html_fields[col] for col in db_cols))
        conn.commit()

        # Generate & download PDF
        try:
            pdfb = generate_pdf_bytes(html_fields)
            st.success("✅ PDF created!")
            st.download_button(
                "⬇️ Download PDF",
                pdfb,
                file_name=f"new_starter_{employee_name.replace(' ','_')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

# ─── STARTER LIST VIEW & CRUD ───────────────────────────────────
elif page == "Starter List":
    st.title("📋 Starter List")
    df = pd.read_sql("SELECT * FROM starters", conn)

    if df.empty:
        st.info("No starters recorded yet.")
    else:
        df_orig = df.copy()
        if hasattr(st, "data_editor"):
            edited = st.data_editor(df, use_container_width=True, height=800, num_rows="dynamic")
        else:
            edited = st.experimental_data_editor(df, use_container_width=True, height=800, num_rows="dynamic")

        if edited is not None and st.button("💾 Save changes"):
            # DELETE removed rows
            to_delete = set(df_orig["id"]) - set(edited["id"])
            if to_delete:
                c.executemany("DELETE FROM starters WHERE id = ?", [(i,) for i in to_delete])
                st.write(f"🗑️ Deleted {len(to_delete)} starter(s)")
            # UPDATE remaining rows
            for _, row in edited.iterrows():
                c.execute("""
                  UPDATE starters SET
                    supplier_name=?,supplier_contact=?,supplier_address=?,
                    employee_name=?,address=?,ni_number=?,
                    role_position=?,department=?,start_date=?,
                    office_location=?,salary_details=?,probation_length=?,
                    emergency_contact=?,additional_info=?,generated_date=?
                  WHERE id=?
                """, tuple(row[col] for col in [
                        "supplier_name","supplier_contact","supplier_address",
                        "employee_name","address","ni_number",
                        "role_position","department","start_date",
                        "office_location","salary_details","probation_length",
                        "emergency_contact","additional_info","generated_date"
                    ]) + (row["id"],))
            conn.commit()
            st.success("✅ All changes saved!")

        st.markdown("---")
        st.subheader("🔄 Re-generate PDF for an Existing Starter")
        options = {r["id"]: f"{r['employee_name']} (ID {r['id']})" for _, r in df.iterrows()}
        sel = st.selectbox("Select Starter", list(options), format_func=lambda i: options[i])
        if st.button("📄 Generate PDF for Selected"):
            rec = df[df["id"] == sel].iloc[0]
            # client fields blank on regen
            html_fields = {
                "logo_b64":          logo_b64,
                "supplier_name":     rec["supplier_name"],
                "supplier_contact":  rec["supplier_contact"],
                "supplier_address":  rec["supplier_address"].replace("\n","<br/>"),
                "client_name":       "",
                "client_contact":    "",
                "client_address":    "",
                "employee_name":     rec["employee_name"],
                "address":           rec["address"].replace("\n","<br/>"),
                "ni_number":         rec["ni_number"],
                "role_position":     rec["role_position"],
                "department":        rec["department"],
                "start_date":        rec["start_date"],
                "office_location":   rec["office_location"],
                "salary_details":    rec["salary_details"],
                "probation_length":  rec["probation_length"],
                "emergency_contact": rec["emergency_contact"].replace("\n","<br/>"),
                "additional_info":   rec["additional_info"].replace("\n","<br/>"),
                "generated_date":    rec["generated_date"],
            }
            try:
                pdfb = generate_pdf_bytes(html_fields)
                st.success(f"✅ PDF for {rec['employee_name']} ready!")
                st.download_button(
                    "⬇️ Download PDF",
                    pdfb,
                    file_name=f"starter_{rec['employee_name'].replace(' ','_')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Failed to generate PDF: {e}")

        st.markdown("---")
        st.subheader("📄 Download Full Starters Report")
        if st.button("Generate All Starters PDF"):
            df_all = df.drop(columns=["supplier_name","supplier_contact","supplier_address"])
            html = "<!DOCTYPE html><html><head><meta charset='utf-8'/><title>All Starters</title>" \
                   "<style>@page{size:A4 landscape;margin:20mm;}body{font-family:Arial;font-size:12px;}" \
                   "table{width:100%;border-collapse:collapse;}th,td{border:1px solid#333;padding:6px;}" \
                   "th{background:#005f8c;color:#fff;}</style></head><body><h1>All Starters Report</h1><table><thead><tr>"
            for col in df_all.columns:
                html += f"<th>{col.replace('_',' ').title()}</th>"
            html += "</tr></thead><tbody>"
            for _, row in df_all.iterrows():
                html += "<tr>" + "".join(f"<td>{row[c]}</td>" for c in df_all.columns) + "</tr>"
            html += "</tbody></table></body></html>"
            wk = shutil.which("wkhtmltopdf")
            if not wk:
                st.error("wkhtmltopdf not found.")
            else:
                cfg = pdfkit.configuration(wkhtmltopdf=wk)
                opts = {"enable-local-file-access": None, "page-size":"A4", "orientation":"Landscape"}
                try:
                    pdfb = pdfkit.from_string(html, False, configuration=cfg, options=opts)
                    st.download_button("⬇️ Download All Starters PDF", pdfb,
                                       file_name="all_starters_report.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

# ─── AI ASSISTANT TAB ─────────────────────────────────────────────
else:
    st.title("🤖 AI Assistant")
    df = pd.read_sql("SELECT * FROM starters", conn)
    st.dataframe(df, use_container_width=True, height=250)
    user_prompt = st.text_area("Your question or request for GPT-4", height=120)
    if st.button("Ask AI"):
        if not user_prompt.strip():
            st.error("Please enter a question or request.")
        else:
            with st.spinner("Thinking…"):
                try:
                    answer = ai_query_system(user_prompt, df)
                    st.markdown("### 🤖 GPT-4 says:")
                    st.write(answer)
                except Exception as e:
                    st.error(f"OpenAI request failed: {e}")
