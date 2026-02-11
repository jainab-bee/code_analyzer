import streamlit as st
import pandas as pd

st.title("AI Code Reviewer")

st.subheader("Understanding the Report Fields")

# Create a DataFrame explaining the fields
fields_info = pd.DataFrame([
    {
        "Field": "Type",
        "Meaning": "Kind of issue detected (rule or problem found in code).",
        "Examples": '"Missing docstring", "Poor variable name", "Unused variable", "Debug print found"'
    },
    {
        "Field": "Detail",
        "Meaning": "Specific information about the issue (function, variable, or value).",
        "Examples": "Function name missing docstring, variable name 'x', magic number 42"
    },
    {
        "Field": "Context",
        "Meaning": "Where the issue occurs, usually the function or class it belongs to. None if global.",
        "Examples": "Function: analyze_code_metrics, Class: MyClass, Global: None"
    },
    {
        "Field": "Level",
        "Meaning": "Severity of the issue.",
        "Examples": '"INFO" → minor, "WARNING" → needs attention, "CRITICAL" → serious problem'
    }
])

# Display as table
st.table(fields_info)

# Optional: Add an expander with more detailed explanation
with st.expander("Detailed explanation of each field"):
    st.markdown("""
**Type**  
- This is the kind of issue detected. Example: `"Missing docstring"`, `"Poor variable name"`.  

**Detail**  
- Provides specific info about the issue. For a missing docstring, it’s the function name. For poor variable name, it’s the variable name itself.  

**Context**  
- Shows where the issue occurs (function, class, or global scope).  

**Level**  
- `"INFO"` → Minor issue (like missing docstring)  
- `"WARNING"` → Needs attention (like magic number)  
- `"CRITICAL"` → Serious problem (like empty except block)
""")
