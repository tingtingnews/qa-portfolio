# Test Strategy

## Overview

This document outlines the testing strategy for the B2B Admin Dashboard — a React/Redux single-page application used by brands to manage campaigns, view analytics, and track contributor activity.

## Scope

### In Scope

| Area | What's Tested |
|------|---------------|
| Analytics Dashboard | 6 tabs (Performance, Overview, Audience, Conversion, Spend, Insights) — widget rendering, date filters, GraphQL responses, chart data |
| Media Hub | Campaign list, filters, pagination, full Create Campaign wizard (3-step form with video/image uploads) |
| Contributors | List rendering, search, filters, pagination |
| API Layer | GraphQL and REST responses captured via network interception — structure, status codes, data integrity |
| CI/CD | Automated test runs on push/PR with pytest-html and Allure reporting |

### Planned

| Area | Status |
|------|--------|
| Load Testing (k6) | Planned — smoke test and ramp-up scenarios |
| Additional CRUD flows | Planned — edit/delete campaigns, user management |

## Test Design Principles

**Integrated test layers:** Each test file validates UI rendering, API responses, and data correctness together rather than separating them into isolated layers. This mirrors how real users experience the application — a page load triggers API calls, which populate widgets, which display data.

**Session-scoped authentication:** The application requires a full interactive login to initialize its Redux store (participant data, brand lists, widget subscriptions). Restoring cookies alone doesn't bootstrap this state, so tests share a single authenticated browser session for speed.

**Stateless test isolation:** Despite sharing a session, each test resets its date range and navigates fresh to avoid state leakage.

**Selector strategy:** The app uses Ant Design, which renders some components (dropdowns, modals, date pickers) in DOM portals outside the main component tree. Tests use a mix of ID selectors, CSS class selectors, and JavaScript evaluation to handle these reliably.

## Risk Areas

- **Ant Design portals:** Dropdown options and modals render outside the parent component's DOM tree, making standard Playwright selectors unreliable. Mitigated with `page.evaluate()` for portal-rendered elements.
- **Redux state dependency:** Tests depend on the Redux store being fully initialized. Mitigated by performing a real login rather than restoring session storage.
- **Background polling:** The app has long-lived connections that prevent `networkidle` from resolving. Mitigated by waiting for specific widget content instead.

## Environment

| Setting | Value |
|---------|-------|
| Browser | Chromium (headless in CI, headed locally) |
| Viewport | 1440 x 900 |
| Test Runner | pytest with playwright plugin |
| CI | GitHub Actions (Ubuntu 22.04) |
| Reports | pytest-html, Allure |
