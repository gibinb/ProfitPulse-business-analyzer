---
title: ProfitPulse
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.40.0
app_file: main.py
pinned: false
---

# 📊 ProfitPulse — Small Business Sales & Profit Analyzer

A web app that helps small shop owners track sales, expenses and inventory, see their
profit automatically, and forecast the next week's revenue. Built during the
**Infosys Springboard Virtual Internship 6.0**.

> **Problem:** small and micro-business owners usually track money in notebooks or
> spreadsheets, so they rarely know their real profit. Enterprise tools (SAP, Tally)
> are too costly and complex for them. ProfitPulse is a simple, open-source alternative.

**Profit = Sales − Expenses − COGS** (COGS = cost of goods sold, taken from inventory unit cost)

## ✨ Features

| Area | What it does |
|---|---|
| **Accounts & security** | Register / log in with **username or email**; bcrypt password hashing; JWT sessions (8 h); account lockout after 5 wrong passwords (5 min); admin secret-code gate; login/logout audit trail |
| **Roles (RBAC)** | Owner, Accountant, Staff, Admin — each role sees only its own pages |
| **Transactions** | Add / edit / delete sales and expenses, with notes and an optional **receipt/invoice image** |
| **Inventory** | Stock with unit cost, low-stock alerts, full IN/OUT movement history; a sale reduces stock automatically |
| **Dashboard** | Sales, Expense, COGS, Profit with Today / Week / Month / All-Time filters, trend chart, **weekly and monthly summaries** |
| **Business Intelligence** | CSV upload → revenue/COGS/profit trends, product-wise profit, **7-day Prophet forecast**, Scikit-learn regression (R², MAE), expense-category donut chart |
| **Reports** | Branded PDF report and 3-sheet Excel report (Summary, Transactions, Inventory) |
| **Admin dashboard** | Manage users (role, password, delete), unlock locked accounts, businesses, report logs, login history, system settings |
| **Mobile friendly** | Responsive CSS for phones |

_Coded but disabled (marked `TODO` in `frontend.py`): Team management, e-mail reports, AI insights, custom profit predictor._

## 🧱 Architecture

```
main.py        → loads .env, creates tables, starts the app
frontend.py    → Presentation layer  (Streamlit pages, forms, charts)
backend.py     → Application layer   (auth, profit logic, reports, lockout, uploads)
database.py    → Data layer          (PostgreSQL connection, 9 tables, safe migrations)
```

**Tech stack:** Python 3.13 · Streamlit · PostgreSQL (Supabase) · psycopg2 · bcrypt · PyJWT ·
Pandas · Plotly · Prophet · Scikit-learn · fpdf2 · openpyxl · Docker · Railway · Hugging Face Spaces

**Database (9 tables):** `users`, `business`, `transactions`, `inventory`,
`inventory_movements`, `reports`, `business_access`, `login_logs`, `system_settings`

## 👥 Roles

| Page | Owner | Accountant | Staff | Admin |
|---|:-:|:-:|:-:|:-:|
| Dashboard / Transactions | ✅ | ✅ | ✅ | ❌ |
| Inventory | ✅ | ❌ | ❌ | ❌ |
| Business Intelligence / Reports | ✅ | ✅ | ❌ | ❌ |
| Profile | ✅ | ✅ | ✅ | ✅ |
| Admin dashboard | ❌ | ❌ | ❌ | ✅ |

## 🚀 Run locally

```bash
git clone https://github.com/gibinb/ProfitPulse-business-analyzer.git
cd ProfitPulse-business-analyzer
python -m venv venv
venv\Scripts\activate            # Windows (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Windows (Linux/Mac: cp .env.example .env), then fill in your own values
streamlit run main.py
```

### Environment variables

Secrets are read **only** from environment variables (never hardcoded).

| Variable | Required | Purpose |
|---|:-:|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (Supabase pooler URL) |
| `JWT_SECRET` | ✅ | Signs login tokens. The app refuses to start without it |
| `ADMIN_SECRET` | ✅ for admin | Secret code on the admin verification page |
| `ADMIN_CODE` | optional | Code that creates an Admin account at registration |
| `SUPABASE_URL`, `SUPABASE_KEY` | optional | Receipt uploads (Supabase Storage bucket `receipts`, service-role key) |
| `SMTP_EMAIL`, `SMTP_PASSWORD` | optional | Only for the disabled e-mail report feature |

## 🐳 Docker

```bash
docker build -t profitpulse .
docker run -p 8501:8501 --env-file .env profitpulse
```

## ☁️ Deployment

GitHub → **Railway** (auto-builds the Dockerfile on every push) and **Hugging Face Spaces**.
Both connect to the same Supabase PostgreSQL database.

## 🔒 Security notes

- Passwords are stored only as bcrypt hashes; all SQL is parameterised.
- Accounts lock for 5 minutes after 5 wrong passwords (an admin can unlock them).
- Never commit `.env`; rotate any credential that was ever pushed.

## 📄 License

MIT — see [LICENSE](LICENSE). © 2026 Gibin Binoi
