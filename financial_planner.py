import streamlit as st
import pandas as pd
from datetime import datetime
import shutil
from pathlib import Path

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Finance OS", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
FILE = BASE_DIR / "finance_data.xlsx"
BACKUP_FILE = BASE_DIR / "finance_backup.xlsx"

CATEGORIES = [
    "Rent", "Groceries", "Eating Out", "Transport",
    "Subscriptions", "Entertainment", "Savings", "Misc"
]

# ---------------- LOAD / SAVE ----------------
def load():
    if FILE.exists():
        df = pd.read_excel(FILE)

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        df = df.dropna(subset=["Date"])
        return df

    return pd.DataFrame(columns=[
        "Date", "Type", "Category", "Description", "Amount"
    ])


def save(df):
    df.to_excel(FILE, index=False)


def backup():
    if FILE.exists():
        shutil.copy(FILE, BACKUP_FILE)


# ---------------- SESSION STATE ----------------
if "df" not in st.session_state:
    st.session_state.df = load()

df = st.session_state.df


# ---------------- SIDEBAR ----------------
st.sidebar.title("💰 Finance OS")

page = st.sidebar.radio("Navigate", [
    "Dashboard",
    "Add Transaction",
    "Edit/Delete",
    "Budgets",
    "Goals",
    "Insights"
])


# ================= DASHBOARD =================
if page == "Dashboard":
    st.title("📊 Dashboard")

    if df.empty:
        st.info("No data yet.")
        st.stop()

    income = df[df["Type"] == "Income"]["Amount"].sum()
    expenses = df[df["Type"] == "Expense"]["Amount"].sum()
    balance = income - expenses

    c1, c2, c3 = st.columns(3)
    c1.metric("Income", f"${income:,.2f}")
    c2.metric("Expenses", f"${expenses:,.2f}")
    c3.metric("Balance", f"${balance:,.2f}")

    st.divider()

    st.subheader("Spending by Category")
    cat = df[df["Type"] == "Expense"].groupby("Category")["Amount"].sum()
    st.bar_chart(cat)

    st.subheader("Timeline")
    timeline = df.groupby(df["Date"].dt.date)["Amount"].sum()
    st.line_chart(timeline)


# ================= ADD =================
elif page == "Add Transaction":
    st.title("➕ Add Transaction")

    with st.form("form"):
        ttype = st.selectbox("Type", ["Expense", "Income"])
        date = st.date_input("Date", datetime.today())
        category = st.selectbox(
            "Category",
            CATEGORIES if ttype == "Expense" else ["Income"]
        )
        desc = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0)

        submit = st.form_submit_button("Save")

        if submit:
            new = pd.DataFrame([{
                "Date": date,
                "Type": ttype,
                "Category": category,
                "Description": desc,
                "Amount": amount
            }])

            st.session_state.df = pd.concat([df, new], ignore_index=True)

            save(st.session_state.df)
            backup()

            st.success("Saved!")


# ================= EDIT / DELETE =================
elif page == "Edit/Delete":
    st.title("🗑 Edit / Delete Transactions")

    if df.empty:
        st.info("No data.")
        st.stop()

    df_display = df.copy()
    df_display["Index"] = df_display.index

    st.dataframe(df_display)

    idx = st.number_input("Row index to delete", min_value=0, step=1)

    if st.button("Delete Row"):
        df = df.drop(index=idx).reset_index(drop=True)

        st.session_state.df = df
        save(df)
        backup()

        st.success("Deleted!")


# ================= BUDGETS =================
elif page == "Budgets":
    st.title("📦 Budgets")

    if df.empty:
        st.stop()

    current_month = datetime.now().month
    exp = df[
        (df["Type"] == "Expense") &
        (df["Date"].dt.month == current_month)
    ]

    budgets = {}

    for cat in CATEGORIES:
        budgets[cat] = st.number_input(cat, value=0.0)

    st.divider()

    for cat in CATEGORIES:
        spent = exp[exp["Category"] == cat]["Amount"].sum()
        budget = budgets[cat]

        if budget > 0:
            st.write(f"{cat}: ${spent:.2f} / ${budget:.2f}")
            st.progress(min(spent / budget, 1.0))


# ================= GOALS =================
elif page == "Goals":
    st.title("🎯 Goals")

    if "goals" not in st.session_state:
        st.session_state.goals = []

    with st.form("goal"):
        name = st.text_input("Goal")
        target = st.number_input("Target", min_value=0.0)
        current = st.number_input("Saved", min_value=0.0)

        submit = st.form_submit_button("Add")

        if submit:
            st.session_state.goals.append({
                "name": name,
                "target": target,
                "current": current
            })

    for g in st.session_state.goals:
        progress = g["current"] / g["target"] if g["target"] else 0

        st.write(g["name"])
        st.progress(min(progress, 1))
        st.write(f"${g['current']} / ${g['target']}")


# ================= INSIGHTS =================
elif page == "Insights":
    st.title("🧠 Smart Insights")

    if df.empty:
        st.stop()

    exp = df[df["Type"] == "Expense"]

    st.subheader("Spending Insights")

    if not exp.empty:
        top = exp.groupby("Category")["Amount"].sum().sort_values(ascending=False).head(1)
        st.write(f"💡 Highest spending category: **{top.index[0]}** (${top.values[0]:.2f})")

        avg = exp["Amount"].mean()
        st.write(f"📊 Average expense: ${avg:.2f}")

    income = df[df["Type"] == "Income"]["Amount"].sum()
    savings = income - exp["Amount"].sum()

    st.write(f"💰 Estimated savings: ${savings:.2f}")

    if savings < 0:
        st.error("⚠️ You are overspending")
    else:
        st.success("✔️ You are within budget")