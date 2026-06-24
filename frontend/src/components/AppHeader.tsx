import { isAuthConfigured, useAuth } from "../lib/auth-provider";

interface AppHeaderProps {
  title?: string;
  subtitle?: string;
}

export function AppHeader({
  title = "Check Your Drawings",
  subtitle = "Upload two PDF drawings for an auto-aligned coordination overlay.",
}: AppHeaderProps) {
  const authConfigured = isAuthConfigured();
  const { user, loading: authLoading, signIn, signOut } = useAuth();

  return (
    <header className="app-header">
      <div className="app-header-row">
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>

        <div className="auth-actions">
          <a href="/" className="header-link">
            Compare
          </a>
          <a href="/pricing" className="header-link">
            Pricing
          </a>
          <a href="/account" className="header-link">
            Account
          </a>
          <a href="/about" className="header-link">
            About
          </a>
          {authConfigured &&
            (authLoading ? (
              <span>Checking session…</span>
            ) : user ? (
              <>
                <span className="auth-email">{user.email}</span>
                <button type="button" className="button-subtle" onClick={() => void signOut()}>
                  Sign out
                </button>
              </>
            ) : (
              <button type="button" className="button-subtle" onClick={() => void signIn()}>
                Sign in
              </button>
            ))}
        </div>
      </div>
    </header>
  );
}
