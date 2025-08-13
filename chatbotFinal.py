import streamlit as st
import pandas as pd
import re
from io import BytesIO
import requests

# === PAGE LAYOUT ===
st.set_page_config(layout="wide")

# ==== GitHub File URLs ====
GITHUB_EXCEL_URL = "https://github.com/khannasir30/LTTS_Chatbot/blob/main/OPS%20MIS_BRD%203_V1.1.xlsx"
GITHUB_LOGO_URL = "https://github.com/khannasir30/LTTS_Chatbot/blob/main/SE%20logo.png"

# === Load Logo from GitHub ===
def load_logo(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            st.image(BytesIO(response.content), width=200)
        else:
            st.error("Logo not found on GitHub.")
    except Exception as e:
        st.error(f"Error loading logo: {e}")

# === Load Excel from GitHub ===
@st.cache_data
def load_data_from_github(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            df = pd.read_excel(BytesIO(response.content), sheet_name="P&L")
            df['Month'] = pd.to_datetime(df['Month'], errors='coerce')
            df['Quarter_Year'] = "Q" + df['Month'].dt.quarter.astype(str) + df['Month'].dt.year.astype(str)
            df['Group1'] = df['Group1'].str.upper()
            return df
        else:
            st.error("Excel file not found on GitHub.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return pd.DataFrame()

# --- Title and Logo ---
col1, col2 = st.columns([8, 2])
with col1:
    st.title("Conversational Analytics Assistant")
    st.write("Welcome to AIde — an AI-powered tool for analyzing business trends using your P&L and utilization data.")

with col2:
    load_logo(GITHUB_LOGO_URL)

# === Load Data ===
df = load_data_from_github(GITHUB_EXCEL_URL)

if not df.empty:
    # --- Sample Question Buttons ---
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
    revenue_groups = ["ONSITE", "OFFSHORE", "INDIRECT REVENUE"]
    revenue_df = (
        df[df['Group1'].isin(revenue_groups)]
        .groupby(['FinalCustomerName', 'Quarter_Year', 'Month'], as_index=False)['Amount in USD']
        .sum()
        .rename(columns={'FinalCustomerName': 'Client', 'Amount in USD': 'Revenue'})
    )
    cost_groups = [
        "DIRECT EXPENSE", "OWN OVERHEADS", "INDIRECT EXPENSE", "PROJECT LEVEL DEPRECIATION",
        "DIRECT EXPENSE - DU BLOCK SEATS ALLOCATION", "DIRECT EXPENSE - DU POOL ALLOCATION", "ESTABLISHMENT EXPENSES"
    ]
    cost_df = (
        df[df['Group1'].isin(cost_groups)]
        .groupby(['FinalCustomerName', 'Quarter_Year', 'Month'], as_index=False)['Amount in USD']
        .sum()
        .rename(columns={'FinalCustomerName': 'Client', 'Amount in USD': 'Cost'})
    )

    final_df = pd.merge(revenue_df, cost_df, on=['Client', 'Quarter_Year', 'Month'], how='outer').fillna(0)
    final_df['Margin %'] = 0.0
    mask = final_df['Revenue'] != 0
    final_df.loc[mask, 'Margin %'] = ((final_df['Revenue'] - final_df['Cost']) / final_df['Revenue']) * 100

    # Filtering logic (same as your code)...
    # [KEEP the rest of your original filtering + tabs code unchanged]

else:
    st.error("Data could not be loaded from GitHub.")
