import streamlit as st
import os
import tempfile
import pandas as pd
from code_analyzer import analyze_project, auto_fix_code, generate_diff, get_python_files, read_file, create_git_hook

st.set_page_config(
    page_title="🧠 AI Code Quality Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧠 AI Code Quality Analyzer")

if "session_path" not in st.session_state:
    st.session_state.session_path = tempfile.mkdtemp()

PROJECT_PATH = st.session_state.session_path

def clear_project_folder():
    for file in os.listdir(PROJECT_PATH):
        file_path = os.path.join(PROJECT_PATH, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

st.subheader("📥 Upload Python File(s) or Paste Code")

uploaded_files = st.file_uploader(
    "Upload Python file(s)", type=["py"], accept_multiple_files=True
)

code_input = st.text_area("Or paste Python code here", height=300)

if uploaded_files:
    clear_project_folder()
    for uploaded_file in uploaded_files:
        file_path = os.path.join(PROJECT_PATH, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
    st.success(f"{len(uploaded_files)} file(s) ready for analysis")

elif code_input.strip():
    clear_project_folder()
    file_path = os.path.join(PROJECT_PATH, "input_code.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code_input)
    st.success("Code ready for analysis")

if st.button("🔍 Analyze Code Quality"):

    if len(os.listdir(PROJECT_PATH)) == 0:
        st.warning("Please upload or paste Python code first.")
        st.stop()

    with st.spinner("🤖 Analyzing code with AI... This may take a moment."):
        df, project_score, msg = analyze_project(PROJECT_PATH)

    if df is None:
        st.error(msg)
        st.stop()

    st.success(msg)

    st.subheader("📊 Project Overview")

    m1, m2, m3 = st.columns(3)
    m1.metric("Project Score", project_score)
    m2.metric("Files Analyzed", len(df))

    total_issues = sum(len(x) if isinstance(x, list) else 0 for x in df["issues"])
    m3.metric("Total Issues", total_issues)


    st.subheader("📄 File Analysis")

    for index, row in df.iterrows():
        with st.expander(f"📁 {os.path.basename(row['file'])}"):

            st.markdown("### 📊 Code Structure")
            st.markdown(
                f"""
- **Functions:** {row['functions']}
- **Classes:** {row['classes']}
- **Loops:** {row['loops']}
- **Conditionals:** {row['conditionals']}
"""
            )

            st.markdown("### ⚙ Complexity Metrics")
            st.markdown(
                f"""
- **AST Complexity:** {row.get('ast_complexity', 0)}
- **Average Complexity:** {row.get('avg_complexity',0)}
- **Maintainability Index:** {row.get('maintainability',0)}
"""
            )

            st.markdown("### 🧾 Quality Score")
            st.markdown(
                f"""
- **Score:** {row.get('score','')}
- **Grade:** {row.get('grade','')}
"""
            )

            st.markdown(f"**Warnings:** {row.get('warnings','None')}")

            issues = row.get("issues", [])
            st.markdown("### 🚨 Detected Issues")

            if issues:
                for issue in issues:
                    if isinstance(issue, dict):
                        st.markdown(
                            f"- **{issue['type']}** | Detail: `{issue['detail']}` | Context: `{issue['context']}` | Level: `{issue['level']}`"
                        )
                    else:
                        st.markdown(f"- {issue}")
            else:
                st.markdown("- No issues detected")

            st.markdown("### 🤖 AI Suggestions")
            if row.get("ai_feedback"):
                for tip in str(row["ai_feedback"]).split(";"):
                    st.markdown(f"- {tip.strip()}")
            else:
                st.markdown("- No suggestions")

    st.divider()

    st.subheader("📥 Download Reports")
    col1, col2 = st.columns(2)

    csv_path = os.path.join(PROJECT_PATH, "report.csv")
    html_path = os.path.join(PROJECT_PATH, "report.html")

    if os.path.exists(csv_path):
        with col1:
            with open(csv_path, "rb") as f:
                st.download_button(
                    "Download CSV Report",
                    f,
                    file_name="report.csv",
                    use_container_width=True
                )

    if os.path.exists(html_path):
        with col2:
            with open(html_path, "rb") as f:
                st.download_button(
                    "Download HTML Report",
                    f,
                    file_name="report.html",
                    use_container_width=True
                )

with st.expander("Detailed explanation of each field"):
    st.markdown("""
**Type**
- Category of detected issue.
Example: `Missing docstring`, `Poor variable name`

**Detail**
- Specific element causing issue (function name / variable)

**Context**
- Location of issue (function/class/global)

**Level**
- INFO → Minor
- WARNING → Needs attention
- CRITICAL → Serious problem

**AST Complexity** → Logical branching level
**Avg Complexity** → Average function complexity
**Maintainability Index** → Code readability & maintainability
**Score** → Overall quality score
**Grade** → Final rating
""")
