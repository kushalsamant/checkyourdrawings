import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { AuthProvider } from "./lib/auth-provider";
import { AuthCallback } from "./pages/AuthCallback";
import "./styles.css";

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("Root element was not found.");
}

const isAuthCallback = window.location.pathname === "/auth/callback";

createRoot(rootElement).render(
  <StrictMode>
    <AuthProvider>
      {isAuthCallback ? <AuthCallback /> : <App />}
    </AuthProvider>
  </StrictMode>,
);
