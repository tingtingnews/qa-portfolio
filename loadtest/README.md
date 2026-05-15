# Load Tests

Performance testing using k6 (planned).

## Planned Scenarios

- **Smoke test:** 1 virtual user, 30 seconds — baseline sanity check
- **Load test:** Ramp 0 to 50 virtual users — thresholds: p95 < 500ms, error rate < 1%
- **API stress test:** High-frequency calls to analytics endpoints under concurrent load

## Tools

- [k6](https://k6.io/) — open-source load testing tool
- Results will be integrated into the CI/CD pipeline
