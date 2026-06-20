import { readOAuthError, tryCompleteAuthCallback } from "../lib/auth-callback";

interface AuthCallbackProps {
  initialError: string;
}

export function AuthCallback({ initialError }: AuthCallbackProps) {
  return (
    <div className="page-body">
      <main className="app-shell auth-callback">
        <p role="alert">{initialError}</p>
        <p>
          <a href="/">Back to app</a>
        </p>
      </main>
    </div>
  );
}

export function getAuthCallbackInitialError(): string | null {
  return readOAuthError();
}

export function resolveAuthCallbackError(): string | null {
  const oauthError = getAuthCallbackInitialError();
  if (oauthError) {
    return oauthError;
  }

  return tryCompleteAuthCallback();
}
