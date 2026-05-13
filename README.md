# QA Engineering Portfolio

![CI](https://github.com/YOUR_USERNAME/qa-portfolio/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Playwright](https://img.shields.io/badge/Playwright-1.44-green)
![k6](https://img.shields.io/badge/k6-performance-purple)
![OWASP ZAP](https://img.shields.io/badge/OWASP_ZAP-security-red)

Senior QA engineer with 6+ years of experience. This portfolio demonstrates
end-to-end test automation across UI, API, performance, and security layers
with full CI/CD pipeline integration.

---

## Tech Stack

| Layer       | Tools                                    |
|-------------|------------------------------------------|
| UI / E2E    | Playwright + Python + Page Object Model  |
| API         | requests, pytest, Postman / Newman       |
| Performance | k6 (smoke + load tests)                  |
| Security    | OWASP ZAP (DAST baseline scan)           |
| Database    | SQLite + psycopg2                        |
| CI/CD       | GitHub Actions                           |
| Reporting   | pytest-html, Allure                      |

---

## Project Structure

```
qa-portfolio/
├── tests/
│   ├── ui/          # Playwright E2E tests + Page Object Models
│   ├── api/         # API tests with requests + pytest
│   ├── db/          # Database validation tests
│   └── performance/ # k6 load + smoke tests
├── security/        # OWASP ZAP config
├── .github/workflows/tests.yml  # Full CI pipeline
└── reports/         # Auto-generated test reports
```

---

## Run Locally

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/qa-portfolio.git
cd qa-portfolio
pip install -r requirements.txt
playwright install chromium

# Copy env file
cp .env.example .env

# Run all tests
pytest tests/ -v

# Run by layer
pytest tests/ui  -v -m ui
pytest tests/api -v -m api
pytest tests/db  -v -m db

# Run performance tests (requires k6 installed)
k6 run tests/performance/smoke_test.js
k6 run tests/performance/load_test.js
```

---

## Test Coverage

### UI Tests (Playwright + POM)
- Login: valid login, locked user, empty fields, wrong password
- Cart: add item, badge count, empty cart state
- Checkout: full happy path, missing required fields

### API Tests (requests + pytest)
- Users: GET list, GET single, POST create, PUT update, DELETE
- Auth: login success, login missing fields, register flow
- Edge cases: 404 not found, 400 bad request, parametrized pagination

### Database Tests
- API → DB consistency: created user exists in DB
- Delete flow: removed user no longer in DB

### Performance Tests (k6)
- Smoke test: 1 VU / 30s — baseline sanity check
- Load test: ramp 0→50 VUs — thresholds: p95 < 500ms, errors < 1%

### Security Scan (OWASP ZAP)
- DAST baseline scan against target application
- Report uploaded as CI artifact on every run

---

## AI-Assisted Testing
- GitHub Copilot used to accelerate test script writing
- Claude API integrated for automated test case generation from user stories

---

## About Me
6+ years QA experience | CompTIA Security+ | Python | Playwright | Postman
Currently building toward Senior QA / IAM QA hybrid roles in the US market.

[LinkedIn](https://linkedin.com/in/ting28/) | [GitHub](https://github.com/tingtingnews)
