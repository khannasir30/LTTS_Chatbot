import streamlit as st
import pandas as pd
import re

# === PAGE LAYOUT ===
st.set_page_config(layout="wide")

# --- Title and Logo ---
col1, col2 = st.columns([8, 2])
with col1:
    st.title("Conversational Analytics Assistant")
    st.write("Welcome to AIde — an AI-powered tool for analyzing business trends using your P&L and utilization data.")
with col2:
    try:
        st.image("https://raw.githubusercontent.com/khannasir30/LTTS_Chatbot/main/SE%20logo.png", width=200)
    except FileNotFoundError:
        st.warning("Logo image not found. Please check the file path.")

# === Load Excel ===
@st.cache_data
def load_data():
    try:
        file_path = "https://raw.githubusercontent.com/khannasir30/LTTS_Chatbot/main/OPS%20MIS_BRD%203_V1.1.xlsx"
        df = pd.read_excel(file_path, sheet_name="P&L")
        df['Month'] = pd.to_datetime(df['Month'], errors='coerce')
        df['Quarter_Year'] = "Q" + df['Month'].dt.quarter.astype(str) + df['Month'].dt.year.astype(str)
        df['Group1'] = df['Group1'].str.upper()
        return df
    except FileNotFoundError:
        st.error("Data file not found. Please ensure the Excel file is at the specified path.")
        return pd.DataFrame()

df = load_data()

# --- Sample Question Buttons FIRST ---
sample_questions = [
    "Show margin less than 20",
    "List CM greater than 30 for Q1 2025",
    "Revenue more than 5000 in Q2 2025",
    "Cost under 1000 for Q2 2025",
    "Show last quarter results",
    "Show latest quarter in 2024"
]

cols = st.columns(3)
for i, sq in enumerate(sample_questions):
    if cols[i % 3].button(sq, key=f"sample_{i}"):
        st.session_state.user_question = sq
        st.rerun()

# --- Text Input ---
col_q, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("🧹 Clear Response"):
        st.session_state.user_question = ""
        st.rerun()

with col_q:
    user_question = st.text_input("👉 Ask your business question:", key="user_question")

# === Data Processing and Filtering ===
if not df.empty:
    # Revenue & Cost Calculation
    revenue_groups = ["ONSITE", "OFFSHORE", "INDIRECT REVENUE"]
    revenue_df = (
        df[df['Group1'].isin(revenue_groups)]
        .groupby(['FinalCustomerName', 'Quarter_Year'], as_index=False)['Amount in USD']
        .sum()
        .rename(columns={'FinalCustomerName': 'Client', 'Amount in USD': 'Revenue'})
    )
    revenue_dfs = (
        df[df['Group1'].isin(revenue_groups)]
        .groupby(['Segment', 'Quarter_Year'], as_index=False)['Amount in USD']
        .sum()
        .rename(columns={'Segment': 'Segment', 'Amount in USD': 'Revenue'})
    )
    cost_groups = [
        "DIRECT EXPENSE", "OWN OVERHEADS", "INDIRECT EXPENSE", "PROJECT LEVEL DEPRECIATION",
        "DIRECT EXPENSE - DU BLOCK SEATS ALLOCATION", "DIRECT EXPENSE - DU POOL ALLOCATION", "ESTABLISHMENT EXPENSES"
    ]
    cost_df = (
        df[df['Group1'].isin(cost_groups)]
        .groupby(['FinalCustomerName', 'Quarter_Year'], as_index=False)['Amount in USD']
        .sum()
        .rename(columns={'FinalCustomerName': 'Client', 'Amount in USD': 'Cost'})
    )
    cost_dfs = (
        df[df['Group1'].isin(cost_groups)]
        .groupby(['Segment', 'Quarter_Year'], as_index=False)['Amount in USD']
        .sum()
        .rename(columns={'Segment': 'Segment', 'Amount in USD': 'Cost'})
    )
    
    final_df = pd.merge(revenue_df, cost_df, on=['Client', 'Quarter_Year'], how='outer').fillna(0)
    final_df['Margin %'] = 0.0
    mask = final_df['Revenue'] != 0
    final_df.loc[mask, 'Margin %'] = ((final_df['Revenue'] - final_df['Cost']) / final_df['Revenue']) * 100

    # Filtering
    margin_aliases = ["margin", "cm %", "cm", "cm%", "margin %", "margin%"]
    filtered_df = final_df.copy()

    if user_question.strip():
        q = user_question.lower()
        replacements = {
            "less than or equal to": "<=",
            "greater than or equal to": ">=",
            "less than": "<",
            "greater than": ">",
            "more than": ">",
            "over": ">",
            "under": "<"
        }
        for k, v in replacements.items():
            q = q.replace(k, v)

        quarter_match = re.search(r"(Q[1-4]\s?20\d{2})", q, re.IGNORECASE)
        if quarter_match:
            qtr = quarter_match.group(1).replace(" ", "")
            filtered_df = filtered_df[filtered_df['Quarter_Year'].str.upper() == qtr.upper()]

        if "last quarter" in q and "latest quarter in" not in q:
            last_qtr = final_df.sort_values("Quarter_Year").Quarter_Year.unique()[-1]
            filtered_df = filtered_df[filtered_df['Quarter_Year'] == last_qtr]

        year_match = re.search(r"(latest quarter|last quarter) in (\d{4})", q)
        if year_match:
            year = int(year_match.group(2))
            year_df = final_df[final_df['Quarter_Year'].str.endswith(str(year))]
            if not year_df.empty:
                latest_qtr = year_df.sort_values("Quarter_Year").Quarter_Year.unique()[-1]
                filtered_df = filtered_df[filtered_df['Quarter_Year'] == latest_qtr]
            else:
                filtered_df = filtered_df.iloc[0:0]

        if any(alias in q for alias in margin_aliases):
            margin_match = re.search(r"(\<|\>|\<=|\>=|=)\s*(-?\d+\.?\d*)", q)
            if margin_match:
                op, val = margin_match.groups()
                val = float(val)
                filtered_df = filtered_df.query(f"`Margin %` {op} @val")

        if "revenue" in q:
            revenue_match = re.search(r"revenue\s*(\<|\>|\<=|\>=|=)\s*([\d,\.]+)", q)
            if revenue_match:
                op, val = revenue_match.groups()
                val = float(val.replace(",", ""))
                filtered_df = filtered_df.query(f"Revenue {op} @val")

        if "cost" in q:
            cost_match = re.search(r"cost\s*(\<|\>|\<=|\>=|=)\s*([\d,\.]+)", q)
            if cost_match:
                op, val = cost_match.groups()
                val = float(val.replace(",", ""))
                filtered_df = filtered_df.query(f"Cost {op} @val")

    # Tabs for Results
    tab1, tab2 ,tab3 , tab4  = st.tabs(["📋 By Client", "🚛 By Segment","🏢 By BU", " 🏭 By DU"])

    with tab1:
        if user_question.strip():
            display_df = filtered_df.copy()
            display_df['Revenue'] = display_df['Revenue'].map(lambda x: f"{x:,.1f}")
            display_df['Cost'] = display_df['Cost'].map(lambda x: f"{x:,.1f}")
            display_df['Margin %'] = display_df['Margin %'].map(lambda x: f"{x:.1f}%")
            st.dataframe(display_df[['Client', 'Quarter_Year', 'Revenue', 'Cost', 'Margin %']], use_container_width=True)
        else:
            st.info("Please enter a question or click a sample question to see results.")

    with tab2:
        st.subheader("Aggregated Revenue, Cost & Margin by Month")
        agg_df = (
            final_df.groupby("Quarter_Year", as_index=False)[["Revenue", "Cost"]]
            .sum()
        )
        agg_df['Margin %'] = 0.0
        mask = agg_df['Revenue'] != 0
        agg_df.loc[mask, 'Margin %'] = ((agg_df['Revenue'] - agg_df['Cost']) / agg_df['Revenue']) * 100

        agg_df['Revenue'] = agg_df['Revenue'].map(lambda x: f"{x:,.1f}")
        agg_df['Cost'] = agg_df['Cost'].map(lambda x: f"{x:,.1f}")
        agg_df['Margin %'] = agg_df['Margin %'].map(lambda x: f"{x:.1f}%")

        st.dataframe(agg_df, use_container_width=True)
    
    with tab3:
        if user_question.strip():
            display_df = filtered_df.copy()
            display_df['Revenue'] = display_df['Revenue'].map(lambda x: f"{x:,.1f}")
            display_df['Cost'] = display_df['Cost'].map(lambda x: f"{x:,.1f}")
            display_df['Margin %'] = display_df['Margin %'].map(lambda x: f"{x:.1f}%")
            st.dataframe(display_df[['Client', 'Quarter_Year', 'Revenue', 'Cost', 'Margin %']], use_container_width=True)
        else:
            st.info("Please enter a question or click a sample question to see results.")    
    with tab4:
        st.subheader("Aggregated Revenue, Cost & Margin by Month")
        agg_df = (
            final_df.groupby("Quarter_Year", as_index=False)[["Revenue", "Cost"]]
            .sum()
        )
        agg_df['Margin %'] = 0.0
        mask = agg_df['Revenue'] != 0
        agg_df.loc[mask, 'Margin %'] = ((agg_df['Revenue'] - agg_df['Cost']) / agg_df['Revenue']) * 100

        agg_df['Revenue'] = agg_df['Revenue'].map(lambda x: f"{x:,.1f}")
        agg_df['Cost'] = agg_df['Cost'].map(lambda x: f"{x:,.1f}")
        agg_df['Margin %'] = agg_df['Margin %'].map(lambda x: f"{x:.1f}%")

        st.dataframe(agg_df, use_container_width=True)



