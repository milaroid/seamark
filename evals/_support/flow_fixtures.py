"""Fixtures for decision provenance and review reconciliation."""


def prepare_review(name, write):
    if not name.startswith("review-fanout--judge-"):
        return False
    write(".seamark/INDEX.md", "# Report service\nProduction requests enter gateway.dispatch before routes.py. The blind lens reports need reconciliation against source. Do not edit source or lens reports.\n")
    write(".seamark/pipeline.yml", "second_engine:\n  provider: none\n")
    write(".seamark/PROGRESS.md", "# Progress\nBlind reviews complete; judge pending.\n")
    write(".seamark/GAPS.md", "# Gaps\nNone recorded.\n")
    write("routes.py", 'def export_report(request):\n    return {"rows": ["internal report"]}\n\nROUTES = {"/api/export": export_report}\n')
    write(".seamark/lens-reports.md", """# Completed blind lens reports
## Security
Critical: routes.py:1-2 returns an internal report without an authentication check.
Evidence: `return {"rows": ["internal report"]}`. Its route is registered at routes.py:4.
Trace the production entry point before accepting or discarding this finding.
## Architecture
The production entry point is gateway.dispatch. The gateway is believed to validate
X-API-Key before every route, including /api/export. If that guard covers the route,
the security finding is a false positive. Verify gateway.py; this belief is not proof.
""")
    if name.endswith("resolved") and not name.endswith("unresolved"):
        write("gateway.py", '''import hmac
import os
from routes import ROUTES

def dispatch(path, headers):
    expected = os.environ.get("REPORT_API_KEY")
    supplied = headers.get("X-API-Key", "")
    if not expected:
        return 503, {}
    if not supplied or not hmac.compare_digest(supplied, expected):
        return 401, {}
    handler = ROUTES.get(path)
    if handler is None:
        return 404, {}
    return 200, handler(headers)
''')
    return True


def prepare_decisions(name, write):
    if name == "plan--provisional":
        write(".seamark/PRD-limiter.md", """# PROVISIONAL — pending Q1
Goal: rate-limit authenticated requests to the HTTP gateway.
Q1: what quota and accounting window should the product enforce?
The user has not answered. The following is an assistant-authored draft, not an approved specification.
Assumption for illustration: 100 requests per minute per API key, fixed window.
## 8. Success Criteria
- Requests exceeding the eventual agreed quota receive 429.
""")
    if name == "implement--provisional":
        write(".seamark/PLAN.md", """# PROVISIONAL — not approved
Draft task: change NormalizeEmail in email.go to strings.ToLower(strings.TrimSpace(s)),
add TestNormalizeEmail in normalize_test.go, then run go test ./....
Unresolved Q1: should normalization lowercase addresses or preserve their case?
Lowercasing is an assistant assumption only. The user has not selected or delegated this choice.
""")
