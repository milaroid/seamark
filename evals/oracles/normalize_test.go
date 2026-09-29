package email

import "testing"

func TestEvalNormalizeEmail(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  string
	}{
		{"trim", "  user@example.com\t", "user@example.com"},
		{"lowercase", "USER@EXAMPLE.COM", "user@example.com"},
		{"empty", "", ""},
		{"combined", "\n User@Example.COM \t", "user@example.com"},
		{"whitespace", " \t\n", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := NormalizeEmail(tt.input); got != tt.want {
				t.Fatalf("NormalizeEmail(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
