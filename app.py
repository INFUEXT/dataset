import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="INFUGEN API Extractor", layout="wide")
st.title("🧪 INFUGEN Pharma Extractor")
st.markdown("Extract clean APIs and analyze top molecules traded for human use.")

uploaded_file = st.file_uploader("Upload CSV Export Dataset", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Numeric cleanup with coercion
    numeric_cols = ["Quantity", "FOB (INR)", "Item Rate(INR)", "FOB (USD)"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # FOB USD fallback with current conversion rate
    if "FOB (USD)" not in df.columns or df["FOB (USD)"].sum() == 0:
        df["FOB (USD)"] = df["FOB (INR)"] * 0.012  # Using current INR-USD rate

    # Enhanced API extraction
    def is_invalid(token):
        dosage_pattern = re.compile(r"^\d+\s?(MG|ML|GM|G|KG)$", re.IGNORECASE)
        return bool(dosage_pattern.match(token)) or len(token) < 4

    def extract_api(name):
        name = str(name).upper()
        exclude_terms = {
            "PHARMACEUTICAL", "LIMITED", "PRIVATE", "HARMLESS", "EXPORT",
            "LAB", "LABS", "INDIA", "TABLET", "CAPSULE", "INJECTION", 
            "SYRUP", "CREAM", "OINTMENT", "DROPS", "NOS", "KGS", "KG"
        }
        
        tokens = re.split(r"[-+/(),.% ]", name)
        valid_tokens = [
            t.strip() for t in tokens
            if t.strip() and t.strip() not in exclude_terms 
            and not is_invalid(t.strip())
        ]
        
        return valid_tokens[0] if valid_tokens else "INVALID"

    df["API"] = df["Product Name"].apply(extract_api)
    valid_df = df[df["API"] != "INVALID"].copy()

    # Human-use validation
    human_indicators = r"\b(TABLET|CAPSULE|INJECTION|SYRUP|CREAM|OINTMENT|DROPS)\b"
    human_df = valid_df[valid_df["Product Name"].str.contains(human_indicators, case=False, na=False)]

    # Analysis section
    with st.sidebar:
        api_filter = st.selectbox("Filter API", ["All"] + sorted(human_df["API"].unique()))
    
    filtered_df = human_df if api_filter == "All" else human_df[human_df["API"] == api_filter]

    # Top 5 APIs analysis
    if not filtered_df.empty:
        top_apis = filtered_df.groupby("API").agg(
            Total_Quantity=("Quantity", "sum"),
            Total_FOB=("FOB (USD)", "sum")
        ).nlargest(5, "Total_Quantity").index.tolist()

        st.subheader("🔬 Top 5 Human-use APIs - Detailed Analysis")
        
        analysis_data = []
        for api in top_apis:
            api_df = filtered_df[filtered_df["API"] == api]
            
            # Strength extraction
            strengths = api_df["Product Name"].str.extractall(r"(\d+\s?MG|\d+\s?ML)")[0].unique()[:3]
            
            # Packaging analysis
            packaging = api_df["Unit"].value_counts().index.tolist()[:3]
            
            # Metric calculations
            analysis_data.append({
                "API": api,
                "Category": api_df["Product Name"].str.split().str[0].mode()[0],
                "Export Count": api_df.shape[0],
                "Total Shipments": api_df["Quantity"].sum(),
                "Common Strengths": ", ".join(strengths) if any(strengths) else "Standard",
                "Avg Qty/Export": api_df["Quantity"].sum() / max(api_df.shape[0], 1),
                "Packaging Types": ", ".join(packaging) if packaging else "Various",
                "Total Nos": api_df[api_df["Unit"].str.upper() == "NOS"]["Quantity"].sum(),
                "Total Kg": api_df[api_df["Unit"].str.upper().isin(["KG", "KGS"])]["Quantity"].sum(),
                "Avg FOB/Pack ($)": api_df["FOB (USD)"].sum() / max(api_df["Quantity"].sum(), 1),
                "Avg Price/Unit ($)": api_df["FOB (USD)"].sum() / max(api_df["Quantity"].sum(), 1)
            })

        analysis_df = pd.DataFrame(analysis_data).round(2)
        st.dataframe(analysis_df.style.format({
            "Avg Qty/Export": "{:.2f}",
            "Avg FOB/Pack ($)": "${:.2f}",
            "Avg Price/Unit ($)": "${:.2f}"
        }))

        # Export clean data
        st.download_button("💾 Download Analysis Data", 
                         data=analysis_df.to_csv(index=False),
                         file_name="api_analysis.csv",
                         mime="text/csv")
    else:
        st.warning("No valid pharmaceutical data found in uploaded file")

else:
    st.info("Please upload a CSV file to begin analysis")
