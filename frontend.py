import streamlit as st
import pandas as pd
import plotly.express as px
from prophet import Prophet
from prophet.plot import plot_plotly
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error
import os

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
    log_report, get_report_logs,
    get_system_settings, update_system_setting,
    get_accessible_businesses, grant_business_access,
    revoke_business_access, get_user_access_list,
    get_team_members, owner_create_team_member,
    delete_user, change_user_password,
    log_login, log_logout, get_login_logs,
)

st.set_page_config(page_title="📈 ProfitPulse", layout="wide")

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
        return ["Dashboard", "Transactions", "Business Intelligence", "Reports", "Profile"]
    # Owner — Team commented out for now
    return ["Dashboard", "Transactions", "Inventory",
            "Business Intelligence", "Reports",
            # "Team",  # TODO: uncomment when Team feature is ready
            "Profile"]


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
            st.markdown(
                "<h1 style='text-align:center;'>📊 ProfitPulse</h1>"
                "<p style='text-align:center;color:gray;'>Small Business Sales & Profit Analyzer</p>",
                unsafe_allow_html=True,
            )

            tab_login, tab_reg = st.tabs(["🔐 Login", "📝 Register"])

            with tab_login:
                username = st.text_input("Username", key="l_u")
                password = st.text_input("Password", type="password", key="l_p")
                if st.button("Login"):
                    user = get_user(username)
                    if user and check_password(password, user[1]):
                        st.session_state.token = create_token(username)
                        log_login(username)
                        st.rerun()
                    else:
                        st.error("Invalid username or password")

            with tab_reg:
                new_user  = st.text_input("Username",                  key="r_u")
                new_email = st.text_input("Email",                     key="r_e")
                new_pass  = st.text_input("Password", type="password", key="r_p")
                if st.button("Create Account"):
                    if register_user(new_user, new_email, new_pass):
                        st.success("Account created! Please login. 🎉")
                    else:
                        st.warning("Username already exists or invalid input.")
        return

    # ──────────────────── AUTHENTICATED ───────────────────────
    username = verify_token(st.session_state.token)
    if not username:
        st.session_state.token = None
        st.rerun()

    role       = get_user_role(username)
    businesses = get_accessible_businesses(username, role)

    # ── No business handling by role ──────────────────────────
    if role == "Owner" and not businesses:
        st.title("🏢 Create Your First Business")
        st.info("Welcome to ProfitPulse! Start by creating your business.")
        bname = st.text_input("Business Name")
        if st.button("Create Business ✅"):
            if bname:
                create_business(username, bname)
                st.rerun()
            else:
                st.warning("Please enter a business name.")
        if st.button("🚪 Logout", key="logout_nobiz"):
            log_logout(username)
            st.session_state.token = None
            st.rerun()
        return

    if role in ("Accountant", "Staff") and not businesses:
        st.title("⏳ Waiting for Business Access")
        st.info("""
        👋 Welcome to ProfitPulse! Your account is ready but you haven't
        been assigned to any business yet.

        Please ask your **Owner** to add you from their **Team** page.
        """)
        if st.button("🚪 Logout", key="logout_wait"):
            log_logout(username)
            st.session_state.token = None
            st.rerun()
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

    if role == "Owner":
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
        log_logout(username)
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
            trend_df           = pd.DataFrame(trend_rows, columns=["Date", "Revenue", "COGS"])
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

        # AI Insights tab commented out for now
        # tab_forecast, tab_insights, tab_expense = st.tabs([
        #     "🔮 Forecasting", "🤖 AI Insights", "💸 Expense Analysis"
        # ])
        tab_forecast, tab_expense = st.tabs([
            "🔮 Forecasting", "💸 Expense Analysis",
            # "🤖 AI Insights",  # TODO: uncomment when AI Insights is ready
        ])

        with tab_forecast:
            st.subheader("📊 CSV Analytics & Forecasting")
            st.caption("Upload a CSV file with historical sales data to generate forecasts and predictions.")

            file = st.file_uploader("Upload Sales CSV", type=["csv"])

            if file:
                df = pd.read_csv(file)
                st.subheader("Data Preview")
                st.dataframe(df.head())

                result, error = process_csv_profit(df)
                if error:
                    st.error(error)
                else:
                    df, daily    = result
                    total_sales  = df["Revenue"].sum()
                    total_profit = df["Profit"].sum()
                    total_cogs   = df["COGS"].sum()
                    margin       = (total_profit / total_sales * 100) if total_sales > 0 else 0

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Revenue", f"₹{total_sales:,.0f}")
                    c2.metric("Total COGS",    f"₹{total_cogs:,.0f}")
                    c3.metric("Total Profit",  f"₹{total_profit:,.0f}")
                    c4.metric("Profit Margin", f"{margin:.2f}%")

                    fig_trend = px.line(daily, x="Date",
                                        y=["Revenue","COGS","Profit"], markers=True,
                                        title="Revenue, COGS & Profit Trend")
                    st.plotly_chart(fig_trend, use_container_width=True)

                    st.subheader("🏷️ Product-wise Profit")
                    prod_profit = df.groupby("Product")[["Profit"]].sum().reset_index()
                    st.plotly_chart(
                        px.bar(prod_profit, x="Product", y="Profit",
                               color="Profit", text_auto=True),
                        use_container_width=True,
                    )

                    st.subheader("🔮 7-Day Revenue Forecast")
                    forecast_df = daily.rename(columns={"Date":"ds","Revenue":"y"})
                    model       = Prophet(yearly_seasonality=False)
                    model.fit(forecast_df)
                    future   = model.make_future_dataframe(periods=7)
                    forecast = model.predict(future)
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

        # ── AI Insights (commented out) ──────────────────────
        # with tab_insights:
        #     st.subheader("🤖 AI Business Insights & Recommendations")
        #     st.caption("Analyzes your real business data and generates actionable insights.")
        #     if st.button("Generate Insights 🔍"):
        #         with st.spinner("Analyzing your business data..."):
        #             insights, recommendations = generate_ai_insights(business_id, selected_biz)
        #         st.markdown("#### 📊 Insights")
        #         for item in insights:
        #             st.markdown(item)
        #         if recommendations:
        #             st.markdown("#### 💡 Recommendations")
        #             for rec in recommendations:
        #                 st.markdown(rec)
        #         else:
        #             st.success("Your business looks healthy - no major recommendations! ✅")

        with tab_expense:
            st.subheader("💸 Expense Category Breakdown")
            cat_data = get_expense_by_category(business_id)
            if cat_data:
                cat_df = pd.DataFrame(cat_data, columns=["Category", "Amount"])

                col_chart, col_table = st.columns([2, 1])
                with col_chart:
                    fig = px.pie(cat_df, names="Category", values="Amount",
                                 hole=0.4, title="Expense Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                with col_table:
                    st.markdown("#### Breakdown")
                    total_exp = cat_df["Amount"].sum()
                    for _, row in cat_df.iterrows():
                        pct = (row["Amount"] / total_exp * 100) if total_exp > 0 else 0
                        st.markdown(f"**{row['Category']}** — ₹{row['Amount']:,.0f} `{pct:.1f}%`")
            else:
                st.info("No expense data available. Add some expenses first.")


    # ══════════════════════════════════════════════════════════
    #  REPORTS
    # ══════════════════════════════════════════════════════════
    elif page == "Reports":
        st.title("📄 Reports")

        # Email Report tab commented out for now
        # tab_download, tab_email = st.tabs(["⬇️ Download Reports", "📧 Email Report"])
        (tab_download,) = st.tabs(["⬇️ Download Reports"])
        # "📧 Email Report",  # TODO: uncomment when Email Report is ready

        with tab_download:
            st.subheader("⬇️ Download Reports")
            st.caption("Generate and download PDF or Excel reports for your business.")

            rep_period_label = st.selectbox("Report Period", list(PERIOD_MAP.keys()),
                                             index=2, key="rep_period")
            rep_period = PERIOD_MAP[rep_period_label]

            sales, expense, cogs, profit = calculate_profit(business_id, rep_period)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Sales",   f"₹{sales:,.0f}")
            m2.metric("🧾 Expense", f"₹{expense:,.0f}")
            m3.metric("📦 COGS",    f"₹{cogs:,.0f}")
            m4.metric("📈 Profit",  f"₹{profit:,.0f}")

            st.markdown("---")
            col_pdf, col_xls = st.columns(2)

            with col_pdf:
                st.markdown("#### 📄 PDF Report")
                st.caption("Financial summary with formatted table.")
                if st.button("Generate PDF Report"):
                    try:
                        pdf_bytes = generate_pdf_report(selected_biz, business_id, rep_period)
                        st.download_button(
                            "⬇️ Download PDF",
                            data=pdf_bytes,
                            file_name=f"{selected_biz}_report.pdf",
                            mime="application/pdf",
                        )
                        st.success("PDF ready! Click above to download.")
                    except ImportError:
                        st.error("Install fpdf2: pip install fpdf2")

            with col_xls:
                st.markdown("#### 📊 Excel Report")
                st.caption("3 sheets: Summary, Transactions, Inventory.")
                if st.button("Generate Excel Report"):
                    try:
                        xl_bytes = generate_excel_report(selected_biz, business_id, rep_period)
                        st.download_button(
                            "⬇️ Download Excel",
                            data=xl_bytes,
                            file_name=f"{selected_biz}_report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                        st.success("Excel ready! Click above to download.")
                    except ImportError:
                        st.error("Install openpyxl: pip install openpyxl")

            st.markdown("---")
            st.subheader("🕓 Your Report History")
            my_logs = get_report_logs(business_id)
            if my_logs:
                log_df = pd.DataFrame(my_logs,
                    columns=["ID","Business","Report Type","Location","Generated At"])
                st.dataframe(log_df[["Report Type","Generated At"]],
                             hide_index=True, use_container_width=True)
            else:
                st.info("No reports generated yet for this business.")

        # ── Email Report (commented out) ─────────────────────
        # with tab_email:
        #     st.subheader("📧 Send Report via Email")
        #     email_to     = st.text_input("Recipient Email Address", key="email_to")
        #     email_period = st.selectbox("Report Period", list(PERIOD_MAP.keys()), index=2, key="email_period")
        #     email_type   = st.selectbox("Report Format", ["pdf", "excel"], key="email_type")
        #     if st.button("📨 Send Report via Email"):
        #         if email_to:
        #             with st.spinner("Generating and sending report..."):
        #                 result = send_report_email(email_to, selected_biz, business_id, PERIOD_MAP[email_period], email_type)
        #             if result is True:
        #                 st.success(f"Report sent successfully to **{email_to}** ✅")
        #             else:
        #                 st.error(f"Failed to send: {result}")
        #         else:
        #             st.warning("Please enter a recipient email address.")


    # ══════════════════════════════════════════════════════════
    #  TEAM (commented out — uncomment when ready)
    # ══════════════════════════════════════════════════════════
    # elif page == "Team":
    #     st.title("👥 Team Management")
    #     st.caption(f"Managing team for **{selected_biz}**")
    #     tab_create, tab_view = st.tabs(["➕ Add Team Member", "👥 My Team"])
    #     with tab_create:
    #         col1, col2 = st.columns(2)
    #         with col1:
    #             tm_username = st.text_input("Username", key="tm_user")
    #             tm_email    = st.text_input("Email",    key="tm_email")
    #         with col2:
    #             tm_password = st.text_input("Password", type="password", key="tm_pass")
    #             tm_role     = st.selectbox("Role", ["Accountant", "Staff"], key="tm_role")
    #         if st.button("➕ Create Team Member", type="primary"):
    #             if tm_username and tm_email and tm_password:
    #                 success, msg = owner_create_team_member(tm_username, tm_email, tm_password, tm_role, business_id, username)
    #                 if success:
    #                     st.success(f"✅ {msg}")
    #                     st.rerun()
    #                 else:
    #                     st.error(f"❌ {msg}")
    #             else:
    #                 st.warning("Please fill in all fields.")
    #     with tab_view:
    #         members = get_team_members(business_id)
    #         if members:
    #             team_df = pd.DataFrame(members, columns=["Username", "Email", "Role", "Added On"])
    #             st.dataframe(team_df, hide_index=True, use_container_width=True)
    #             member_names = [m[0] for m in members]
    #             remove_user  = st.selectbox("Select Member to Remove", member_names, key="remove_member")
    #             if st.button("❌ Revoke Access", type="primary"):
    #                 revoke_business_access(remove_user, business_id)
    #                 st.success(f"Access revoked for {remove_user}.")
    #                 st.rerun()
    #         else:
    #             st.info("No team members yet.")


    # ══════════════════════════════════════════════════════════
    #  ADMIN
    # ══════════════════════════════════════════════════════════
    elif page == "Admin":
        if role != "Admin":
            st.error("Access denied.")
            return

        st.title("🔧 Admin Dashboard - ProfitPulse")

        tab_users, tab_biz, tab_reports, tab_logs, tab_settings = st.tabs([
            "👥 Users", "🏢 Businesses", "📄 Report Logs", "🕐 Login History", "⚙️ System Settings"
        ])

        # ── Users Tab ─────────────────────────────────────────
        with tab_users:
            users = get_all_users()
            if users:
                u_df = pd.DataFrame(users, columns=["Username", "Email", "Role"])
                st.dataframe(u_df, hide_index=True, use_container_width=True)
                st.metric("Total Users", len(users))

                st.markdown("---")
                col_left, col_right = st.columns(2)

                with col_left:
                    st.markdown("#### 🔄 Change User Role")
                    target   = st.selectbox("Select User", [u[0] for u in users], key="role_target")
                    new_role = st.selectbox("New Role", ROLES, key="role_new")
                    if st.button("Update Role", key="btn_role"):
                        update_user_role(target, new_role)
                        st.success(f"Role updated to {new_role} for **{target}**.")
                        st.rerun()

                with col_right:
                    st.markdown("#### 🔑 Change User Password")
                    pwd_target  = st.selectbox("Select User", [u[0] for u in users], key="pwd_target")
                    new_pwd     = st.text_input("New Password",     type="password", key="new_pwd")
                    confirm_pwd = st.text_input("Confirm Password", type="password", key="confirm_pwd")
                    if st.button("Change Password", key="btn_pwd"):
                        if not new_pwd:
                            st.warning("Please enter a new password.")
                        elif new_pwd != confirm_pwd:
                            st.error("Passwords do not match.")
                        else:
                            change_user_password(pwd_target, new_pwd)
                            st.success(f"Password changed successfully for **{pwd_target}**.")

                st.markdown("---")
                st.markdown("#### 🗑️ Delete User")
                st.caption("⚠️ Permanently deletes the user account. Their business data will remain.")

                deletable_users = [u for u in users if u[0] != username]
                if deletable_users:
                    del_target = st.selectbox(
                        "Select User to Delete",
                        [u[0] for u in deletable_users],
                        key="del_target"
                    )
                    del_info = next((u for u in users if u[0] == del_target), None)
                    if del_info:
                        st.warning(f"Deleting **{del_info[0]}** ({del_info[2]}) — {del_info[1]}")

                    confirm_del = st.checkbox(f"I confirm deletion of {del_target}", key="confirm_del")
                    if st.button("🗑️ Delete User", type="primary", key="btn_del"):
                        if confirm_del:
                            delete_user(del_target)
                            st.success(f"User **{del_target}** has been deleted.")
                            st.rerun()
                        else:
                            st.error("Please check the confirmation checkbox first.")
                else:
                    st.info("No other users to delete.")
            else:
                st.info("No users found.")

        # ── Businesses Tab ────────────────────────────────────
        with tab_biz:
            all_biz = get_all_businesses()
            if all_biz:
                b_df = pd.DataFrame(all_biz,
                    columns=["ID","Business Name","Owner","Created At"])
                st.dataframe(b_df, hide_index=True, use_container_width=True)
                st.metric("Total Businesses", len(all_biz))
            else:
                st.info("No businesses found.")

        # ── Report Logs Tab ───────────────────────────────────
        with tab_reports:
            st.subheader("📄 All Report Generation Logs")
            logs = get_report_logs()
            if logs:
                log_df = pd.DataFrame(logs,
                    columns=["ID","Business","Report Type","Location","Generated At"])
                st.dataframe(log_df, hide_index=True, use_container_width=True)
                st.metric("Total Reports Generated", len(logs))

                col1, col2 = st.columns(2)
                pdf_count   = sum(1 for l in logs if l[2] == "PDF")
                excel_count = sum(1 for l in logs if l[2] == "Excel")
                col1.metric("📄 PDF Reports",   pdf_count)
                col2.metric("📊 Excel Reports", excel_count)
            else:
                st.info("No reports have been generated yet.")

        # ── Login History Tab ─────────────────────────────────
        with tab_logs:
            st.subheader("🕐 User Login / Logout History")
            st.caption("Tracks every login and logout across all users.")

            col_filter, col_limit = st.columns([2, 1])
            with col_filter:
                all_usernames   = ["All Users"] + [u[0] for u in get_all_users()]
                filter_username = st.selectbox("Filter by User", all_usernames, key="log_filter")
            with col_limit:
                log_limit = st.number_input("Show last N records", min_value=10,
                                             max_value=500, value=50, step=10, key="log_limit")

            if filter_username == "All Users":
                login_data = get_login_logs(limit=log_limit)
            else:
                login_data = get_login_logs(username=filter_username, limit=log_limit)

            if login_data:
                log_df = pd.DataFrame(login_data, columns=["Username", "Login Time", "Logout Time"])
                log_df["Logout Time"] = log_df["Logout Time"].fillna("Active / not logged out")

                def calc_duration(row):
                    if row["Logout Time"] == "Active / not logged out":
                        return "🟢 Active"
                    try:
                        diff = pd.to_datetime(row["Logout Time"]) - pd.to_datetime(row["Login Time"])
                        mins = int(diff.total_seconds() / 60)
                        return f"{mins} min" if mins < 60 else f"{mins//60}h {mins%60}m"
                    except Exception:
                        return "-"

                log_df["Duration"] = log_df.apply(calc_duration, axis=1)
                st.dataframe(log_df, hide_index=True, use_container_width=True)

                c1, c2 = st.columns(2)
                c1.metric("Total Sessions", len(login_data))
                c2.metric("Currently Active", sum(1 for r in login_data if r[2] is None))
            else:
                st.info("No login history found.")

        # ── System Settings Tab ───────────────────────────────
        with tab_settings:
            st.subheader("⚙️ System Settings")
            settings = get_system_settings()

            st.markdown("#### 🏷️ Application")
            app_name = st.text_input(
                "Application Name",
                value=settings.get("app_name", "ProfitPulse"),
            )
            max_biz = st.number_input(
                "Max Businesses per User",
                min_value=1, max_value=20,
                value=int(settings.get("max_businesses", "5")),
            )

            st.markdown("#### 📊 Data Quality Monitor")
            m1, m2, m3 = st.columns(3)
            m1.metric("👥 Total Users",       len(get_all_users()))
            m2.metric("🏢 Total Businesses",  len(get_all_businesses()))
            m3.metric("📄 Reports Generated", len(get_report_logs()))

            st.markdown("#### 📧 Email Configuration")
            smtp_configured = bool(os.getenv("SMTP_EMAIL") and os.getenv("SMTP_PASSWORD"))
            if smtp_configured:
                st.success("✅ SMTP Email is configured and ready.")
            else:
                st.warning("⚠️ SMTP not configured. Set SMTP_EMAIL and SMTP_PASSWORD.")

            if st.button("💾 Save Settings"):
                update_system_setting("app_name",       app_name)
                update_system_setting("max_businesses", str(max_biz))
                st.success("Settings saved successfully ✅")


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

            st.markdown("---")
            st.subheader("🕐 My Login History")
            my_logs = get_login_logs(username=username, limit=10)
            if my_logs:
                my_log_df = pd.DataFrame(my_logs, columns=["Username", "Login Time", "Logout Time"])
                my_log_df["Logout Time"] = my_log_df["Logout Time"].fillna("Current session")
                st.dataframe(my_log_df[["Login Time", "Logout Time"]],
                             hide_index=True, use_container_width=True)
            else:
                st.info("No login history yet.")