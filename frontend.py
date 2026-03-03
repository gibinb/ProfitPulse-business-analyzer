import streamlit as st
import pandas as pd
import plotly.express as px
from prophet import Prophet
from prophet.plot import plot_plotly
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error

from backend import (
    register_user, get_user, get_profile, get_user_role,
    create_business, get_user_businesses,
    save_sales, save_expense,
    get_transactions, delete_transaction, update_transaction,
    add_inventory, get_inventory, get_low_stock, get_inventory_movements, compute_cogs,
    calculate_profit, get_sales_trend,
    process_csv_profit,
    get_expense_by_category,
    check_password, create_token, verify_token,
    generate_pdf_report, generate_excel_report,
    get_all_users, get_all_businesses, update_user_role,
    generate_ai_insights, send_report_email,
)

st.set_page_config(page_title="📈 Business Profit Analyzer", layout="wide")

PERIOD_MAP = {
    "Today":      "today",
    "This Week":  "week",
    "This Month": "month",
    "All Time":   "all",
}
ROLES = ["Owner", "Accountant", "Staff", "Admin"]


# ══════════════════════════════════════════════════════════════
#  HELPER
# ══════════════════════════════════════════════════════════════

def _pages_for_role(role):
    if role == "Admin":
        return ["Admin", "Profile"]
    if role == "Staff":
        return ["Dashboard", "Transactions", "Profile"]
    if role == "Accountant":
        return ["Dashboard", "Transactions", "Business Intelligence", "Profile"]
    return ["Dashboard", "Transactions", "Inventory", "Business Intelligence", "Profile"]


# ══════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════

def run_app():

    if "token" not in st.session_state:
        st.session_state.token = None

    # ──────────────────── LOGIN / REGISTER ────────────────────
    if not st.session_state.token:
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown("<h1 style='text-align:center;'>📊 Business Profit Analyzer</h1>",
                        unsafe_allow_html=True)

            tab_login, tab_reg = st.tabs(["🔐 Login", "📝 Register"])

            with tab_login:
                username = st.text_input("Username", key="l_u")
                password = st.text_input("Password", type="password", key="l_p")
                if st.button("Login"):
                    user = get_user(username)
                    if user and check_password(password, user[1]):
                        st.session_state.token = create_token(username)
                        st.rerun()
                    else:
                        st.error("Invalid username or password")

            with tab_reg:
                new_user  = st.text_input("Username",                  key="r_u")
                new_email = st.text_input("Email",                     key="r_e")
                new_pass  = st.text_input("Password", type="password", key="r_p")

                is_admin = st.checkbox("Register as Admin")
                adm_code = ""
                if is_admin:
                    adm_code = st.text_input("Admin Code", type="password", key="r_a")

                if st.button("Create Account"):
                    if register_user(new_user, new_email, new_pass, adm_code):
                        st.success("Account created! Please login. 🎉")
                    else:
                        st.warning("Username already exists or invalid input.")
        return

    # ──────────────────── AUTHENTICATED ───────────────────────
    username = verify_token(st.session_state.token)
    if not username:
        st.session_state.token = None
        st.rerun()

    role = get_user_role(username)
    businesses = get_user_businesses(username)

    if not businesses and role != "Admin":
        st.title("🏢 Create Your First Business")
        bname = st.text_input("Business Name")
        if st.button("Create Business"):
            if bname:
                create_business(username, bname)
                st.rerun()
            else:
                st.warning("Please enter a business name.")
        return

    # ── Sidebar ────────────────────────────────────────────────
    st.sidebar.markdown(f"### 👋 {username}  `{role}`")

    if businesses:
        biz_dict     = {name: bid for bid, name in businesses}
        selected_biz = st.sidebar.selectbox("🏢 Business", list(biz_dict.keys()))
        business_id  = biz_dict[selected_biz]
    else:
        selected_biz = None
        business_id  = None

    if role != "Admin":
        if "add_biz" not in st.session_state:
            st.session_state.add_biz = False
        if st.sidebar.button("➕ Add New Business"):
            st.session_state.add_biz = True
        if st.session_state.add_biz:
            nb = st.sidebar.text_input("New Business Name")
            if st.sidebar.button("Confirm"):
                if nb:
                    create_business(username, nb)
                    st.session_state.add_biz = False
                    st.rerun()

    pages = _pages_for_role(role)
    page  = st.sidebar.radio("Navigation", pages)

    if st.sidebar.button("🚪 Logout"):
        st.session_state.token = None
        st.rerun()


    # ══════════════════════════════════════════════════════════
    #  DASHBOARD
    # ══════════════════════════════════════════════════════════
    if page == "Dashboard":
        st.title("📊 Dashboard")

        period_label = st.selectbox("Period", list(PERIOD_MAP.keys()), index=2)
        period       = PERIOD_MAP[period_label]

        sales, expense, cogs, profit = calculate_profit(business_id, period)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Sales",   f"₹{sales:,.0f}")
        c2.metric("🧾 Expense", f"₹{expense:,.0f}")
        c3.metric("📦 COGS",    f"₹{cogs:,.0f}")
        c4.metric("📈 Profit",  f"₹{profit:,.0f}",
                  delta=f"{'▲' if profit >= 0 else '▼'} {abs(profit):,.0f}")

        trend_rows = get_sales_trend(business_id, period)
        if trend_rows:
            trend_df = pd.DataFrame(trend_rows, columns=["Date", "Revenue", "COGS"])
            trend_df["Profit"] = trend_df["Revenue"] - trend_df["COGS"]
            st.subheader("📉 Sales Trend")
            fig = px.line(trend_df, x="Date", y=["Revenue", "COGS", "Profit"], markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales data for this period yet.")

        st.subheader("⚠️ Low Stock Alerts")
        low = get_low_stock(business_id)
        if low:
            for item in low:
                st.error(f"**{item[0]}** — only {item[1]} units remaining!")
        else:
            st.success("All items are well stocked ✅")


    # ══════════════════════════════════════════════════════════
    #  TRANSACTIONS
    # ══════════════════════════════════════════════════════════
    elif page == "Transactions":
        st.title("💳 Transactions")

        tab_add, tab_manage = st.tabs(["➕ Add Transaction", "🗂️ Manage Transactions"])

        with tab_add:
            txn_type = st.selectbox("Type", ["Sales", "Expense"])

            if txn_type == "Sales":
                product = st.text_input("Product Name")
                qty     = st.number_input("Quantity Sold",      min_value=1)
                amount  = st.number_input("Total Sales Amount", min_value=0.0)
                date    = st.date_input("Sale Date")
                notes   = st.text_area("Notes (optional)", height=68)
                if st.button("Save Sale ✅"):
                    if product:
                        save_sales(username, business_id, product, qty, amount, date, notes)
                        st.success("Sale saved & inventory updated!")
                    else:
                        st.warning("Please enter a product name.")
            else:
                if role == "Staff":
                    st.warning("Staff cannot add expenses.")
                else:
                    cat    = st.selectbox("Category",
                                          ["Rent","Utilities","Supplies","Salary","Marketing","Other"])
                    amount = st.number_input("Expense Amount", min_value=0.0)
                    date   = st.date_input("Expense Date")
                    notes  = st.text_area("Notes (optional)", height=68)
                    if st.button("Save Expense ✅"):
                        save_expense(username, business_id, amount, cat, date, notes)
                        st.success("Expense saved!")

        with tab_manage:
            if role == "Staff":
                st.info("Staff can view but not edit transactions.")

            rows = get_transactions(business_id, limit=100)
            if rows:
                df = pd.DataFrame(rows,
                    columns=["ID","Type","Amount","Category","Product","Qty","Date","Notes"])
                st.dataframe(df, hide_index=True, use_container_width=True)

                if role != "Staff":
                    st.markdown("---")
                    col_del, col_edit = st.columns(2)

                    with col_del:
                        st.subheader("🗑️ Delete")
                        del_id = st.number_input("Transaction ID", min_value=1, step=1, key="del_id")
                        if st.button("Delete", type="primary"):
                            delete_transaction(int(del_id), business_id)
                            st.success("Transaction deleted.")
                            st.rerun()

                    with col_edit:
                        st.subheader("✏️ Edit")
                        edit_id  = st.number_input("Transaction ID", min_value=1, step=1, key="edit_id")
                        new_amt  = st.number_input("New Amount",  min_value=0.0, key="edit_amt")
                        new_note = st.text_input("Notes", key="edit_note")
                        if st.button("Update", type="primary"):
                            update_transaction(int(edit_id), business_id, new_amt, new_note)
                            st.success("Transaction updated.")
                            st.rerun()
            else:
                st.info("No transactions found.")


    # ══════════════════════════════════════════════════════════
    #  INVENTORY
    # ══════════════════════════════════════════════════════════
    elif page == "Inventory":
        st.title("📦 Inventory Management")

        tab_add, tab_view, tab_moves = st.tabs(
            ["➕ Add Stock", "📋 Current Stock", "🔄 Movement History"]
        )

        with tab_add:
            product   = st.text_input("Product Name")
            qty       = st.number_input("Quantity",            min_value=1)
            cost      = st.number_input("Unit Cost (₹)",       min_value=0.0)
            threshold = st.number_input("Low Stock Threshold", min_value=1, value=5)
            date      = st.date_input("Purchase Date")
            if st.button("Add Inventory ✅"):
                if product:
                    add_inventory(username, business_id, product, qty, cost, date, threshold)
                    st.success("Inventory added!")
                else:
                    st.warning("Please enter a product name.")
            st.metric("Total COGS", f"₹{compute_cogs(business_id):,.2f}")

        with tab_view:
            items = get_inventory(business_id)
            if items:
                inv_df = pd.DataFrame(items,
                    columns=["Product","Quantity","Unit Cost","Low Stock Threshold","Purchase Date"])
                st.dataframe(inv_df, hide_index=True, use_container_width=True)
            else:
                st.info("No inventory records yet.")

        with tab_moves:
            moves = get_inventory_movements(business_id)
            if moves:
                mov_df = pd.DataFrame(moves,
                    columns=["Product","Change Qty","Movement Type","Date"])
                mov_df["Movement Type"] = mov_df["Movement Type"].map(
                    {"IN": "🟢 IN", "OUT": "🔴 OUT"}
                )
                st.dataframe(mov_df, hide_index=True, use_container_width=True)
            else:
                st.info("No movement history yet.")


    # ══════════════════════════════════════════════════════════
    #  BUSINESS INTELLIGENCE
    # ══════════════════════════════════════════════════════════
    elif page == "Business Intelligence":
        st.title("📈 Business Intelligence")

        # ── AI Business Insights ──────────────────────────────
        st.subheader("🤖 AI Business Insights & Recommendations")
        if st.button("Generate Insights 🔍"):
            with st.spinner("Analyzing your business data..."):
                insights, recommendations = generate_ai_insights(business_id, selected_biz)

            st.markdown("#### 📊 Insights")
            for item in insights:
                st.markdown(item)

            if recommendations:
                st.markdown("#### 💡 Recommendations")
                for rec in recommendations:
                    st.markdown(rec)
            else:
                st.success("Your business looks healthy — no major recommendations at this time! ✅")

        st.markdown("---")

        # ── Expense breakdown ──
        st.subheader("💸 Expense Category Breakdown")
        cat_data = get_expense_by_category(business_id)
        if cat_data:
            cat_df = pd.DataFrame(cat_data, columns=["Category","Amount"])
            fig    = px.pie(cat_df, names="Category", values="Amount", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expense data available.")

        st.markdown("---")

        # ── Report downloads ──
        st.subheader("📄 Download Reports")
        rep_period_label = st.selectbox("Report Period", list(PERIOD_MAP.keys()), index=2,
                                         key="rep_period")
        rep_period = PERIOD_MAP[rep_period_label]

        col_pdf, col_xls = st.columns(2)
        with col_pdf:
            if st.button("Generate PDF Report"):
                try:
                    pdf_bytes = generate_pdf_report(selected_biz, business_id, rep_period)
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"{selected_biz}_report.pdf",
                        mime="application/pdf",
                    )
                except ImportError:
                    st.error("Install fpdf2: pip install fpdf2")

        with col_xls:
            if st.button("Generate Excel Report"):
                try:
                    xl_bytes = generate_excel_report(selected_biz, business_id, rep_period)
                    st.download_button(
                        "⬇️ Download Excel",
                        data=xl_bytes,
                        file_name=f"{selected_biz}_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except ImportError:
                    st.error("Install openpyxl: pip install openpyxl")

        st.markdown("---")

        # ── Email Report ──────────────────────────────────────
        st.subheader("📧 Email Report")

        with st.expander("⚙️ How to set up Gmail for sending emails"):
            st.markdown("""
            1. Go to your **Google Account → Security**
            2. Enable **2-Step Verification**
            3. Go to **App Passwords** and generate one for "Mail"
            4. Set these two environment variables before running the app:
```
            set SMTP_EMAIL=youremail@gmail.com
            set SMTP_PASSWORD=your_16_digit_app_password
```
            """)

        email_to     = st.text_input("Recipient Email Address", key="email_to")
        email_period = st.selectbox("Report Period", list(PERIOD_MAP.keys()),
                                     index=2, key="email_period")
        email_type   = st.selectbox("Report Format", ["pdf", "excel"], key="email_type")

        if st.button("📨 Send Report via Email"):
            if email_to:
                with st.spinner("Sending email..."):
                    result = send_report_email(
                        email_to, selected_biz, business_id,
                        PERIOD_MAP[email_period], email_type
                    )
                if result is True:
                    st.success(f"Report sent successfully to {email_to} ✅")
                else:
                    st.error(f"Failed to send: {result}")
            else:
                st.warning("Please enter a recipient email address.")

        st.markdown("---")

        # ── CSV Analytics & Forecasting ───────────────────────
        st.subheader("📊 CSV Analytics & Forecasting")
        file = st.file_uploader("Upload Sales CSV", type=["csv"])

        if file:
            df = pd.read_csv(file)
            st.subheader("Data Preview")
            st.dataframe(df.head())

            result, error = process_csv_profit(df)
            if error:
                st.error(error)
                return

            df, daily = result
            total_sales  = df["Revenue"].sum()
            total_profit = df["Profit"].sum()
            total_cogs   = df["COGS"].sum()
            margin       = (total_profit / total_sales * 100) if total_sales > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Revenue", f"₹{total_sales:,.0f}")
            c2.metric("Total COGS",    f"₹{total_cogs:,.0f}")
            c3.metric("Total Profit",  f"₹{total_profit:,.0f}")
            c4.metric("Profit Margin", f"{margin:.2f}%")

            fig_trend = px.line(daily, x="Date", y=["Revenue","COGS","Profit"], markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)

            st.subheader("🏷️ Product-wise Profit")
            prod_profit = df.groupby("Product")[["Profit"]].sum().reset_index()
            st.plotly_chart(
                px.bar(prod_profit, x="Product", y="Profit", color="Profit", text_auto=True),
                use_container_width=True,
            )

            forecast_df = daily.rename(columns={"Date":"ds","Revenue":"y"})
            model = Prophet(yearly_seasonality=False)
            model.fit(forecast_df)
            future   = model.make_future_dataframe(periods=7)
            forecast = model.predict(future)

            st.subheader("🔮 7-Day Revenue Forecast")
            st.plotly_chart(plot_plotly(model, forecast), use_container_width=True)

            st.subheader("🧠 Profit Prediction (Regression)")
            X = df[["Revenue","COGS"]]
            y = df["Profit"]
            if len(X) >= 5:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
                reg    = LinearRegression().fit(X_train, y_train)
                y_pred = reg.predict(X_test)
                st.write(f"**R² Score:** {r2_score(y_test, y_pred):.3f}")
                st.write(f"**MAE:** ₹{mean_absolute_error(y_test, y_pred):,.2f}")

                st.markdown("#### 🔢 Predict Custom Profit")
                p_rev  = st.number_input("Revenue (₹)", min_value=0.0, key="pred_rev")
                p_cogs = st.number_input("COGS (₹)",    min_value=0.0, key="pred_cogs")
                if st.button("Predict"):
                    pred = reg.predict([[p_rev, p_cogs]])[0]
                    st.success(f"Predicted Profit: ₹{pred:,.2f}")
            else:
                st.info("Upload at least 5 rows for regression analysis.")

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Processed CSV", csv,
                               "profit_report.csv", "text/csv")
        else:
            st.info("Upload a CSV with columns: Date, Product, Quantity, Selling_Price, Cost_Price")


    # ══════════════════════════════════════════════════════════
    #  ADMIN
    # ══════════════════════════════════════════════════════════
    elif page == "Admin":
        if role != "Admin":
            st.error("Access denied.")
            return

        st.title("🔧 Admin Dashboard")
        tab_users, tab_biz = st.tabs(["👥 Users", "🏢 Businesses"])

        with tab_users:
            users = get_all_users()
            if users:
                u_df = pd.DataFrame(users, columns=["Username","Email","Role"])
                st.dataframe(u_df, hide_index=True, use_container_width=True)

                st.markdown("#### Change User Role")
                target   = st.selectbox("Select User", [u[0] for u in users])
                new_role = st.selectbox("New Role", ROLES)
                if st.button("Update Role"):
                    update_user_role(target, new_role)
                    st.success(f"Role updated to {new_role}.")
                    st.rerun()
            else:
                st.info("No users found.")

        with tab_biz:
            all_biz = get_all_businesses()
            if all_biz:
                b_df = pd.DataFrame(all_biz,
                    columns=["ID","Business Name","Owner","Created At"])
                st.dataframe(b_df, hide_index=True, use_container_width=True)
                st.metric("Total Businesses", len(all_biz))
            else:
                st.info("No businesses found.")


    # ══════════════════════════════════════════════════════════
    #  PROFILE
    # ══════════════════════════════════════════════════════════
    elif page == "Profile":
        st.title("👤 Profile")
        user = get_profile(username)
        if user:
            st.markdown(f"**Username:** {user[0]}")
            st.markdown(f"**Email:** {user[1]}")
            st.markdown(f"**Role:** `{user[2]}`")
            st.markdown(f"**Businesses:** {len(businesses)}")