import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="INNOVEXA | Hazard Monitoring",
    page_icon="🛡️",
    layout="wide"
)

if "reports" not in st.session_state:
    st.session_state.reports = []

st.sidebar.title("🛡️ TEAM-INNOVEXA")
st.sidebar.write("AI Hazard & Facilities Monitoring")

role = st.sidebar.selectbox(
    "Select your role",
    ["Student", "Staff", "Admin"]
)

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Report a Problem", "All Reports"]
)

st.title("AI-Based Hazard & Facilities Monitoring")
st.caption("Developed by Team-INNOVEXA")

reports = st.session_state.reports

if page == "Dashboard":
    st.subheader(f"Welcome to the {role} Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Reports", len(reports))
    col2.metric(
        "Pending Reports",
        sum(r["Status"] == "Pending" for r in reports)
    )
    col3.metric(
        "Resolved Reports",
        sum(r["Status"] == "Resolved" for r in reports)
    )

    st.subheader("Recent Reports")
    if reports:
        st.dataframe(
            pd.DataFrame(reports),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No reports yet. Submit a report to get started.")

elif page == "Report a Problem":
    st.subheader("Report a Facility Problem")

    with st.form("report_form", clear_on_submit=True):
        name = st.text_input("Your name")
        facility = st.selectbox(
            "Facility",
            [
                "Computer",
                "Air Conditioner",
                "Electrical Equipment",
                "Furniture",
                "Other"
            ]
        )
        location = st.text_input("Building / Room")
        priority = st.selectbox(
            "Priority", ["Low", "Medium", "High"]
        )
        description = st.text_area("Describe the problem")
        photo = st.file_uploader(
            "Upload a photo",
            type=["png", "jpg", "jpeg"]
        )

        submitted = st.form_submit_button("Submit Report")

        if submitted:
            if not name.strip() or not location.strip() or not description.strip():
                st.error("Please complete your name, location and description.")
            else:
                st.session_state.reports.append({
                    "Reporter": name.strip(),
                    "Facility": facility,
                    "Location": location.strip(),
                    "Priority": priority,
                    "Description": description.strip(),
                    "Photo": photo.name if photo else "No photo",
                    "Status": "Pending",
                    "Created": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.success("Your report was submitted successfully!")

                if photo:
                    st.image(photo, caption="Uploaded problem photo", width=300)

elif page == "All Reports":
    st.subheader("All Facility Reports")

    if not reports:
        st.info("No reports have been submitted.")
    else:
        for i, report in enumerate(reports):
            with st.expander(
                f"{report['Facility']} — {report['Status']}"
            ):
                st.write("**Reporter:**", report["Reporter"])
                st.write("**Location:**", report["Location"])
                st.write("**Priority:**", report["Priority"])
                st.write("**Description:**", report["Description"])
                st.write("**Created:**", report["Created"])

                if role in ["Staff", "Admin"]:
                    status = st.selectbox(
                        "Update status",
                        ["Pending", "In Progress", "Resolved"],
                        index=[
                            "Pending", "In Progress", "Resolved"
                        ].index(report["Status"]),
                        key=f"status_{i}"
                    )

                    if st.button("Save Status", key=f"save_{i}"):
                        st.session_state.reports[i]["Status"] = status
                        st.rerun()

st.divider()
st.caption("Frontend/UI Development — ZEHAD AMZAD BIN AMIR")