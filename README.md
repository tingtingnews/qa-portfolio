# QA Engineering Portfolio

![CI](https://github.com/tingtingnews/qa-portfolio/actions/workflows/test.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Playwright](https://img.shields.io/badge/Playwright-1.52-green)

QA automation suite for a B2B Admin Dashboard — a React/Redux SPA used by brands to manage campaigns, track analytics, and monitor audience engagement. Tests combine UI validation, API response verification, and data integrity checks within each test file to reflect real-world QA workflows.

---

## Tech Stack

| Layer       | Tools                                    |
|-------------|------------------------------------------|
| UI / E2E    | Playwright + Python                      |
| API         | Playwright network interception, requests|
| Database    | psycopg2 (PostgreSQL validation)         |
| CI/CD       | GitHub Actions (automated on push/PR)    |
| Reporting   | pytest-html, Allure                      |
| Load Test   | k6 (planned)                             |

---

## Project Structure

```
qa-portfolio/
├── tests/
│   ├── analytics/           # Dashboard analytics (6 tabs)
│   │   ├── test_performance.py
│   │   ├── test_overview.py
│   │   ├── test_audience.py
│   │   ├── test_conversion.py
│   │   ├── test_spend.py
│   │   └── test_insights.py
│   ├── media_hub/           # Campaign management
│   │   ├── test_campaigns.py
│   │   └── test_create_campaign.py
│   └── contributors/        # Contributor list and filters
│       └── test_contributors.py
├── loadtest/                # Performance tests (planned)
├── specs/                   # Test strategy documentation
├── conftest.py              # Shared fixtures: login, navigation, session
├── pytest.ini               # Pytest configuration and markers
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
└── .github/workflows/
    └── test.yml             # CI/CD pipeline
```

---

## What Each Test File Covers

Each test file combines **UI checks**, **API response validation**, and **data integrity assertions** — not just clicking buttons.

**Analytics (6 modules):** Widget rendering, date range filters, GraphQL response structure, chart data population, metric calculations, and cross-tab consistency.

**Media Hub — Campaigns:** Campaign list table rendering, pagination, status filters, search functionality, and API payload verification.

**Media Hub — Create Campaign:** Full campaign creation wizard (3 steps), form validation with Ant Design components, file upload for video/image ads, budget input, date pickers, navigation between steps, and API request interception to verify submitted payloads.

**Contributors:** Contributor list rendering, search and filter interactions, pagination, and result count verification.

---

## Run Locally

```bash
# Clone and install
git clone https://github.com/tingtingnews/qa-portfolio.git
cd qa-portfolio
pip install -r requirements.txt
playwright install chromium

# Set credentials
cp .env.example .env
# Edit .env with your credentials

# Run all tests
pytest tests/ -v

# Run by feature
pytest tests/analytics/ -v
pytest tests/media_hub/ -v
pytest tests/contributors/ -v

# Run with HTML report
pytest tests/ -v --html=reports/report.html --self-contained-html

# Run with Allure report
pytest tests/ -v --alluredir=reports/allure-results
allure serve reports/allure-results
```

---

## CI/CD Pipeline

Tests run automatically on every push and pull request to `main` via GitHub Actions. The pipeline installs dependencies, runs all Playwright tests in headless mode, and uploads both pytest-html and Allure reports as downloadable artifacts.

---

## Test Approach

- **Session-scoped login:** One browser login shared across all tests for speed — the React/Redux app requires a real login to bootstrap its state (storage_state alone doesn't restore the Redux store).
- **Network interception:** Tests capture GraphQL and REST API responses in-flight to validate data without needing direct DB access.
- **Ant Design aware selectors:** Custom selector strategies for Ant Design components (Select dropdowns rendered in portals, DatePicker calendars, Switch toggles, Upload widgets).
- **Date range isolation:** Each test fixture resets the date range to avoid state leakage between tests.

---

## About Me

QA Engineer building expertise in full-stack test automation and AI-assisted testing.

[LinkedIn](https://linkedin.com/in/ting28/) | [GitHub](https://github.com/tingtingnews)
