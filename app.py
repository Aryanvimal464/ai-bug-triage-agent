"""Streamlit UI. Run: streamlit run app.py"""
import os

import pandas as pd
import streamlit as st

from agent import BUGS_FILE, TICKETS_FILE, triage

BASE_DATA = BUGS_FILE.parent
st.set_page_config(page_title="AI Bug Triage Agent", page_icon="🐞", layout="wide")
st.title("🐞 AI Bug Triage Agent")
st.caption("Bug report likho (English / Hindi / Hinglish) - agent severity, priority, module aur duplicates nikalega.")

if not os.getenv("GEMINI_API_KEY"):
    from dotenv import load_dotenv
    load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    st.error("GEMINI_API_KEY nahi mila. `.env` file mein Gemini API key add karo.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["Triage", "Existing bugs", "Tickets", "Accuracy report"])

with tab1:
    examples = {
        "Duplicate example": "Valid email aur password dalne ke baad bhi login nahi ho raha, invalid credentials aa raha hai",
        "New bug example": "Wishlist page par images load nahi ho rahi, grey box dikhta hai aur page slow hai",
    }
    choice = st.selectbox("Example chuno (optional)", ["-"] + list(examples))
    report = st.text_area("Bug report", value=examples.get(choice, ""), height=140)
    save = st.checkbox("Naya bug ho to ticket save karo (tickets.csv)", value=True)

    if st.button("Triage karo", type="primary", disabled=not report.strip()):
        with st.spinner("Agent soch raha hai..."):
            try:
                out = triage(report, create_tickets=save)
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()
        d = out["decision"]
        if not d:
            st.error(out["error"])
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Severity", d["severity"])
            c2.metric("Priority", d["priority"])
            c3.metric("Module", d["module"])
            c4.metric("Duplicate?", f"Yes (#{d.get('duplicate_of_id', '')})" if d["is_duplicate"] else "No")
            st.subheader(d["clean_title"])
            st.write(d["reasoning"])
            if d.get("steps_to_reproduce"):
                st.markdown("**Steps to reproduce**\n\n" + d["steps_to_reproduce"])
                col_a, col_b = st.columns(2)
                col_a.markdown("**Expected**\n\n" + d.get("expected", "-"))
                col_b.markdown("**Actual**\n\n" + d.get("actual", "-"))
        with st.expander("Agent ne kaunse tools use kiye"):
            for step in out["log"]:
                st.markdown(f"`{step['tool']}`")
                st.json({"input": step["input"], "output": step["output"]})

with tab2:
    st.dataframe(pd.read_csv(BUGS_FILE), use_container_width=True, hide_index=True)

with tab3:
    if TICKETS_FILE.exists():
        st.dataframe(pd.read_csv(TICKETS_FILE), use_container_width=True, hide_index=True)
    else:
        st.info("Abhi koi ticket nahi bana.")

with tab4:
    report_md = BASE_DATA / "eval_report.md"
    if report_md.exists():
        st.markdown(report_md.read_text(encoding="utf-8"))
        st.dataframe(pd.read_csv(BASE_DATA / "eval_results.csv"), use_container_width=True, hide_index=True)
    else:
        st.info("Pehle terminal mein `python evaluate.py` chalao.")
