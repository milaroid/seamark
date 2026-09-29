"""Fixtures for hard cases derived from recorded /seamark pipeline failures.

Each fixture is a baseline file set committed first, then a change left
uncommitted in the working tree. The failure class behind each case comes from
~/.claude/seamark-learning/signals and is named in the case's grader.
"""

PROJECT = {
    "go.mod": "module fixture\n\ngo 1.22\n",
    ".gitignore": ".checks/\n",
    ".seamark/INDEX.md": "# Billing service\nGo, standard library only. Test: `go test ./...`.\n",
    ".seamark/STACK.md": "# Stack\nGo standard library.\n",
    ".seamark/PATTERNS.md": "# Patterns\nPure functions; table-driven Go tests. Money is carried in integer cents.\n",
    ".seamark/HOTSPOTS.md": "# Hotspots\nMoney conversion in amount.go and invoice.go.\n",
    ".seamark/TASKS.md": "# Tasks\nThe current request is the only task.\n",
    ".seamark/PROGRESS.md": "# Progress\nFixture initialized; current task has not run.\n",
    ".seamark/GAPS.md": "# Gaps\nNone recorded.\n",
    ".seamark/pipeline.yml": "second_engine:\n  provider: none\n",
}

ACCOUNT_STORE = '''package billing

import "errors"

type Owner struct{ Name string }

type Account struct {
	ID    string
	Owner *Owner
}

var ErrNotFound = errors.New("account not found")

// LoadAccount returns the account stored under id.
func LoadAccount(accounts map[string]Account, id string) (Account, error) {
	a, ok := accounts[id]
	if !ok || a.Owner == nil {
		return Account{}, ErrNotFound
	}
	return a, nil
}
'''

ACCOUNT_TEST = '''package billing

import "testing"

func TestGreeting(t *testing.T) {
	accounts := map[string]Account{"a1": {ID: "a1", Owner: &Owner{Name: "Ana"}}, "a2": {ID: "a2"}}
	if _, err := Greeting(accounts, "a2"); err == nil {
		t.Fatal("expected an error for an account without an owner")
	}
	if _, err := Greeting(accounts, "missing"); err == nil {
		t.Fatal("expected an error for a missing account")
	}
	if got, err := Greeting(accounts, "a1"); err != nil || got == "" {
		t.Fatalf("Greeting(a1) = %q, %v", got, err)
	}
}
'''

GREETING = '''package billing

import "fmt"

// Greeting returns the greeting line for an account statement.
func Greeting(accounts map[string]Account, id string) (string, error) {
	a, err := LoadAccount(accounts, id)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("Statement for account %s", a.ID), nil
}
'''

AMOUNT = '''package billing

import "strconv"

// ParseAmount parses a decimal amount such as "12.50" into currency units.
func ParseAmount(s string) (float64, error) {
	return strconv.ParseFloat(s, 64)
}
'''

AMOUNT_CENTS = '''package billing

import (
	"math"
	"strconv"
)

// ParseAmount parses a decimal amount such as "12.50" into cents.
func ParseAmount(s string) (float64, error) {
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, err
	}
	return math.Round(v * 100), nil
}
'''

AMOUNT_TEST = '''package billing

import "testing"

func TestParseAmount(t *testing.T) {
	got, err := ParseAmount("12.50")
	if err != nil || got != %s {
		t.Fatalf("ParseAmount(12.50) = %%v, %%v", got, err)
	}
}
'''

INVOICE = '''package billing

// LineTotalCents returns the line total in cents for a unit price and quantity.
func LineTotalCents(price string, qty int) (int64, error) {
	units, err := ParseAmount(price)
	if err != nil {
		return 0, err
	}
	return int64(units*100+0.5) * int64(qty), nil
}
'''

DISCOUNT = '''package billing

// Discount returns the loyalty discount in cents: 10%% of totals of %s cents.
func Discount(total int64) int64 {
	if total %s 10000 {
		return total / 10
	}
	return 0
}
'''

DISCOUNT_TEST = '''package billing

import "testing"

func TestDiscount(t *testing.T) {
	tests := []struct {
		name  string
		total int64
		want  int64
	}{
		{"below threshold", 9999, 0},
%s		{"above threshold", 20000, 2000},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Discount(tt.total); got != tt.want {
				t.Fatalf("Discount(%%d) = %%d, want %%d", tt.total, got, tt.want)
			}
		})
	}
}
'''

EMAIL_TABLE_TEST = '''package email

import "testing"

func TestNormalizeEmail(t *testing.T) {
	tests := []struct{ name, input, want string }{
		{"empty", "", ""},
		{"lowercase", "User@Example.COM", "user@example.com"},
		{"spaces", "  user@example.com  ", "user@example.com"},
		{"tab and newline", "\\tUser@Example.com\\n", "user@example.com"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := NormalizeEmail(tt.input); got != tt.want {
				t.Fatalf("NormalizeEmail(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
'''

EMAIL_STUB = '''package email

// NormalizeEmail normalizes an email address for comparison.
func NormalizeEmail(s string) string {
	return s
}
'''

EMAIL_TRIM = '''package email

import "strings"

// NormalizeEmail normalizes an email address for comparison.
func NormalizeEmail(s string) string {
	return strings.ToLower(strings.Trim(s, " "))
}
'''

INVOICE_VIEW = '''package invoices

// Invoice is a customer invoice shown on the invoices page.
type Invoice struct {
	ID    string
	Cents int64
}
'''


def review_guard(check_script):
    """Over-flag class: a dereference whose nil guard lives outside the diff hunk."""
    baseline = {"store.go": ACCOUNT_STORE, "greeting.go": GREETING, "greeting_test.go": ACCOUNT_TEST}
    change = {"greeting.go": GREETING.replace('"Statement for account %s", a.ID', '"Statement for %s (account %s)", a.Owner.Name, a.ID')}
    return baseline, change


def review_caller(check_script):
    """Under-flag class: a unit change that breaks a caller outside the diff."""
    baseline = {"amount.go": AMOUNT, "amount_test.go": AMOUNT_TEST % "12.5", "invoice.go": INVOICE}
    change = {"amount.go": AMOUNT_CENTS, "amount_test.go": AMOUNT_TEST % "1250"}
    return baseline, change


def review_weakened(check_script):
    """Under-flag class: a behavior regression hidden by deleting its test case."""
    boundary = '\t\t{"at threshold", 10000, 1000},\n'
    baseline = {"discount.go": DISCOUNT % ("at least 10000", ">="), "discount_test.go": DISCOUNT_TEST % boundary}
    change = {"discount.go": DISCOUNT % ("over 10000", ">"), "discount_test.go": DISCOUNT_TEST % ""}
    return baseline, change


def verify_fix(check_script):
    """tests_green class: an in-scope failure the loop must fix without editing tests."""
    baseline = {
        "email.go": EMAIL_STUB,
        "email_test.go": EMAIL_TABLE_TEST,
        "check.py": check_script,
        "verification.json": '{"mode": "passing"}\n',
        ".seamark/INDEX.md": "# Verification project\nThe required verification command is `python3 check.py`. It runs Go tests. Its exit status determines Tests green. Do not change check.py, verification.json, email_test.go, or the invocation history.\n",
        ".seamark/REVIEW.md": "# Review\nVerdict: APPROVED\nCritical findings: 0\nTarget: current email.go change.\n",
        ".seamark/PRD-verification.md": "# Normalize email\n## 8. Success Criteria\n- NormalizeEmail trims all surrounding whitespace and lowercases the address.\n- `python3 check.py` exits 0.\n",
    }
    return baseline, {"email.go": EMAIL_TRIM}


def refine_dependency(check_script):
    """Blocked-refine class: the request depends on a work package that has not shipped."""
    baseline = {
        "invoices.go": INVOICE_VIEW,
        ".seamark/TASKS.md": "# Tasks\n- WP-7 PdfRenderer service: not started. Owner: platform team. No delivery date. No code exists yet.\n- Current request: see the prompt.\n",
    }
    return baseline, {}


HARD = {
    "review--guard-outside-hunk": review_guard,
    "review--caller-contract": review_caller,
    "review--weakened-test": review_weakened,
    "verify--fix-in-scope": verify_fix,
    "refine--unshipped-dependency": refine_dependency,
}


def prepare_hard(name, check_script):
    """Return (baseline, change) file maps for a hard case, or None for other cases."""
    build = HARD.get(name)
    if build is None:
        return None
    baseline, change = build(check_script)
    return {**PROJECT, **baseline}, change
