package email

import "testing"

func TestEvalNormalizeWhitespace(t *testing.T) {
	tests := []struct{ name, input, want string }{
		{"carriage return", "\r\nUser@Example.com\r\n", "user@example.com"},
		{"vertical tab", "\vUSER@EXAMPLE.COM\f", "user@example.com"},
		{"inner space kept", " a b@example.com ", "a b@example.com"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := NormalizeEmail(tt.input); got != tt.want {
				t.Fatalf("NormalizeEmail(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
