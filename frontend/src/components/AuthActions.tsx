import { isAuthConfigured, useAuth } from "../lib/auth-provider";

export function AuthActions() {
  const authConfigured = isAuthConfigured();
  const { user, loading: authLoading, signIn, signOut } = useAuth();

  if (!authConfigured) {
    return null;
  }

  if (authLoading) {
    return <span>Checking session…</span>;
  }

  if (user) {
    return (
      <>
        <span className="auth-email">{user.email}</span>
        <button type="button" className="button-subtle" onClick={() => void signOut()}>
          Sign out
        </button>
      </>
    );
  }

  return (
    <button type="button" className="button-subtle" onClick={() => void signIn()}>
      Sign in
    </button>
  );
}
