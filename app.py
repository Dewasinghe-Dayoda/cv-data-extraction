import streamlit as st
import os
import tempfile
from datetime import datetime, timezone, timedelta

from config import UPLOADS_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, GEMINI_API_KEY, GROQ_API_KEY, AI_PROVIDER
from database import (
    init_db, insert_candidate, get_all_candidates, create_batch,
    get_batches, get_candidates_by_batch, get_latest_batch,
    get_candidate_by_id, update_candidate, delete_candidate, get_stats
)
from extractor import process_cv, RateLimitError
from excel_export import export_to_excel

st.set_page_config(
    page_title="CV Data Extraction Tool",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

init_db()

st.sidebar.title("CV Extraction Tool")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["Upload & Extract", "Candidate History", "Export to Excel"],
    index=0
)

stats = get_stats()
st.sidebar.markdown("---")
st.sidebar.subheader("Database Stats")
col1, col2, col3 = st.sidebar.columns(3)
col1.metric("Total", stats["total"])
col2.metric("New", stats["extracted"])
col3.metric("Done", stats["reviewed"])

st.sidebar.markdown("---")
has_api_key = GROQ_API_KEY or GEMINI_API_KEY
if not has_api_key:
    st.sidebar.error("No API key configured")
    st.sidebar.info("Get free Groq key: console.groq.com")


def validate_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


if page == "Upload & Extract":
    st.markdown("### Upload & Extract CV Data")
    st.markdown("Upload PDF CVs and automatically extract candidate information using AI.")

    if not has_api_key:
        st.error("Please configure an AI API key first.")
        st.code("AI_PROVIDER=groq\nGROQ_API_KEY=your_key_here", language="bash")
        st.stop()

    uploaded_files = st.file_uploader(
        "Drag & drop CVs here (PDF, DOCX, PNG, JPG)",
        type=["pdf", "docx", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help=f"Maximum {MAX_FILE_SIZE_MB}MB per file"
    )

    if uploaded_files:
        valid_files = [f for f in uploaded_files if validate_file(f.name)]
        skipped = [f for f in uploaded_files if not validate_file(f.name)]

        if skipped:
            for f in skipped:
                st.warning(f"Skipped {f.name} — unsupported file type")

        if valid_files:
            st.markdown(f"**{len(valid_files)}** CV(s) ready to process")

            if st.button("Extract Data from All CVs", type="primary"):
                batch_label = f"Batch — {datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime('%b %d, %Y %I:%M %p')}"
                batch_id = create_batch(batch_label)

                errors_list = []
                success_count = 0

                progress_bar = st.progress(0, text="Starting extraction...")

                for idx, uploaded_file in enumerate(valid_files):
                    progress = (idx + 1) / len(valid_files)
                    progress_bar.progress(progress, text=f"Processing {idx + 1}/{len(valid_files)}: {uploaded_file.name}")

                    tmp_path = None
                    try:
                        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_path = tmp_file.name

                        extracted_data, cv_text = process_cv(tmp_path)

                        saved_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                        save_path = UPLOADS_DIR / saved_filename
                        with open(save_path, "wb") as f:
                            f.write(open(tmp_path, "rb").read())

                        candidate_id = insert_candidate(
                            data=extracted_data,
                            filename=uploaded_file.name,
                            cv_text=cv_text,
                            batch_id=batch_id,
                            batch_label=batch_label
                        )

                        success_count += 1

                        with st.expander(f"  {uploaded_file.name}", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.text_input("Name", extracted_data.get("candidate_name", "") or "", key=f"name_{candidate_id}", disabled=True)
                                st.text_input("Email", extracted_data.get("email", "") or "", key=f"email_{candidate_id}", disabled=True)
                                st.text_input("Phone", extracted_data.get("contact_number", "") or "", key=f"phone_{candidate_id}", disabled=True)
                            with col2:
                                st.text_input("Job Title", extracted_data.get("current_job_title", "") or "", key=f"title_{candidate_id}", disabled=True)
                                st.text_input("Experience", extracted_data.get("total_experience_years", "") or "", key=f"exp_{candidate_id}", disabled=True)
                                st.text_area("Skills", extracted_data.get("key_skills", "") or "", key=f"skills_{candidate_id}", disabled=True, height=68)

                    except RateLimitError as e:
                        errors_list.append(f"{uploaded_file.name}: {str(e)}")
                        if e.is_daily_limit:
                            minutes = e.retry_after // 60 if e.retry_after > 60 else 0
                            seconds = e.retry_after % 60 if e.retry_after > 60 else e.retry_after
                            if minutes > 0:
                                wait_msg = f"Try again in {minutes}m {seconds}s, or tomorrow after midnight UTC."
                            else:
                                wait_msg = f"Try again in {seconds} seconds."
                            st.error(f"⏳ Daily limit reached. {wait_msg}")
                        else:
                            st.error(f"Rate limit: {e}. Try again shortly.")
                    except Exception as e:
                        errors_list.append(f"{uploaded_file.name}: {str(e)}")
                        st.error(f"Error processing {uploaded_file.name}")

                    finally:
                        if tmp_path and os.path.exists(tmp_path):
                            try: os.unlink(tmp_path)
                            except: pass

                progress_bar.progress(1.0, text="Complete!")

                if success_count > 0:
                    st.success(f"Extracted **{success_count}** CV(s) — {batch_label}")
                if errors_list:
                    with st.expander(f"  {len(errors_list)} error(s) occurred"):
                        for err in errors_list:
                            st.error(err)

elif page == "Candidate History":
    st.markdown("### Candidate History")

    col1, col2 = st.columns([4, 1])
    with col1:
        search_query = st.text_input("Search", placeholder="Search by name, email, skills, job title...", label_visibility="collapsed")
    with col2:
        status_filter = st.selectbox("Status", ["All", "extracted", "reviewed"], label_visibility="collapsed")
        status_val = None if status_filter == "All" else status_filter

    candidates = get_all_candidates(search=search_query if search_query else None, status=status_val)

    if not candidates:
        st.info("No candidates found. Upload some CVs first!")
    else:
        col_info, col_export = st.columns([4, 2])
        with col_info:
            st.markdown(f"**{len(candidates)}** candidate(s) found")
        with col_export:
            if not search_query and status_val is None:
                batches = get_batches()
                latest_non_empty = next((b for b in batches if b["candidate_count"] > 0), None)
                if latest_non_empty:
                    batch_candidates = get_candidates_by_batch(latest_non_empty["id"])
                    if st.button(f"Export Latest ({len(batch_candidates)} CVs)", type="primary"):
                        filepath = export_to_excel(batch_candidates)
                        with open(filepath, "rb") as f:
                            st.download_button(
                                label="Download Excel",
                                data=f.read(),
                                file_name=os.path.basename(filepath),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="history_export_download"
                            )

        for candidate in candidates:
            expander_label = f"{candidate['candidate_name'] or 'Unknown'} — {candidate['current_job_title'] or 'No Title'}"

            with st.expander(expander_label, expanded=False):
                col1, col2, col3 = st.columns([5, 5, 1])

                with col1:
                    name = st.text_input("Candidate Name", candidate["candidate_name"] or "", key=f"h_name_{candidate['id']}")
                    email = st.text_input("Email", candidate["email"] or "", key=f"h_email_{candidate['id']}")
                    phone = st.text_input("Contact Number", candidate["contact_number"] or "", key=f"h_phone_{candidate['id']}")
                    gender = st.text_input("Gender", candidate["gender"] or "", key=f"h_gender_{candidate['id']}")

                with col2:
                    age = st.text_input("Age", candidate["age"] or "", key=f"h_age_{candidate['id']}")
                    experience = st.text_input("Total Experience", candidate["total_experience_years"] or "", key=f"h_exp_{candidate['id']}")
                    employer = st.text_input("Last Employer", candidate["last_employer"] or "", key=f"h_employer_{candidate['id']}")
                    title = st.text_input("Current/Last Job Title", candidate["current_job_title"] or "", key=f"h_title_{candidate['id']}")

                with col3:
                    st.write("")
                    st.write("")
                    new_status = st.selectbox(
                        "Status",
                        ["extracted", "reviewed"],
                        index=0 if candidate["status"] == "extracted" else 1,
                        key=f"h_status_{candidate['id']}"
                    )

                skills = st.text_area("Key Skills / Expertise", candidate["key_skills"] or "", key=f"h_skills_{candidate['id']}", height=68)

                if candidate.get("cv_text"):
                    show_cv = st.checkbox("Show Original CV Text", key=f"h_cv_chk_{candidate['id']}")
                    if show_cv:
                        st.text_area("CV Content", candidate["cv_text"], key=f"h_cv_{candidate['id']}", height=200, disabled=True)

                col_save, col_delete = st.columns([1, 1])
                with col_save:
                    if st.button("Save Changes", key=f"save_{candidate['id']}", type="primary"):
                        updated_data = {
                            "candidate_name": name,
                            "contact_number": phone,
                            "email": email,
                            "gender": gender,
                            "age": age,
                            "total_experience_years": experience,
                            "last_employer": employer,
                            "key_skills": skills,
                            "current_job_title": title,
                            "status": new_status
                        }
                        update_candidate(candidate["id"], updated_data)
                        st.success("Changes saved!")
                        st.rerun()

                with col_delete:
                    if st.button("Delete", key=f"del_{candidate['id']}", type="secondary"):
                        st.session_state[f"confirm_delete_{candidate['id']}"] = True

                    if st.session_state.get(f"confirm_delete_{candidate['id']}", False):
                        st.warning("Are you sure you want to delete this candidate?")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Yes, Delete", key=f"confirm_yes_{candidate['id']}"):
                                delete_candidate(candidate["id"])
                                st.session_state[f"confirm_delete_{candidate['id']}"] = False
                                st.success("Candidate deleted!")
                                st.rerun()
                        with c2:
                            if st.button("Cancel", key=f"confirm_no_{candidate['id']}"):
                                st.session_state[f"confirm_delete_{candidate['id']}"] = False
                                st.rerun()

elif page == "Export to Excel":
    st.markdown("### Export to Excel")

    batches = get_batches()

    if not batches:
        st.info("No candidates to export. Upload some CVs first!")
        st.stop()

    latest_batch = get_latest_batch()
    candidates = get_candidates_by_batch(latest_batch["id"])

    st.markdown(f"#### {latest_batch['label']}")
    st.markdown(f"**{len(candidates)}** candidate(s) ready for export")

    preview_df = []
    for c in candidates:
        preview_df.append({
            "Name": c["candidate_name"] or "",
            "Email": c["email"] or "",
            "Phone": c["contact_number"] or "",
            "Job Title": c["current_job_title"] or "",
            "Experience": c["total_experience_years"] or "",
            "Skills": (c["key_skills"] or "")[:50] + "..." if c["key_skills"] and len(c["key_skills"]) > 50 else c["key_skills"] or ""
        })

    st.dataframe(preview_df, use_container_width=True, hide_index=True)

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Download Excel File", type="primary"):
            try:
                filepath = export_to_excel(candidates)
                with open(filepath, "rb") as f:
                    st.download_button(
                        label="Click to Download",
                        data=f.read(),
                        file_name=os.path.basename(filepath),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                st.success(f"Generated: {os.path.basename(filepath)}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

    if len(batches) > 1:
        with st.expander("Export a different batch"):
            batch_options = {b["label"]: b["id"] for b in batches}
            batch_labels = list(batch_options.keys())
            selected_label = st.selectbox("Select batch", batch_labels, key="old_batch_select")
            selected_batch_id = batch_options[selected_label]
            old_candidates = get_candidates_by_batch(selected_batch_id)
            if old_candidates:
                st.info(f"{len(old_candidates)} candidate(s)")
                if st.button("Download this batch"):
                    try:
                        filepath = export_to_excel(old_candidates)
                        with open(filepath, "rb") as f:
                            st.download_button(
                                label="Click to Download",
                                data=f.read(),
                                file_name=os.path.basename(filepath),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="old_batch_download"
                            )
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
