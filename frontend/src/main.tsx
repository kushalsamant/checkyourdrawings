import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { AuthProvider } from "./lib/auth-provider";
import { AboutPage } from "./pages/AboutPage";
import { AuthCallback, resolveAuthCallbackError } from "./pages/AuthCallback";
import "./styles.css";

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("Root element was not found.");
}

function AppRoutes() {
  const path = window.location.pathname;

  if (path === "/about") {
    return <AboutPage />;
  }

  return <App />;
}

const path = window.location.pathname;

if (path === "/auth/callback") {
  const callbackError = resolveAuthCallbackError();
  if (callbackError !== null) {
    createRoot(rootElement).render(<AuthCallback initialError={callbackError} />);
  }
} else {
  createRoot(rootElement).render(
    <StrictMode>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </StrictMode>,
  );
}
