import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { AuthProvider } from "./lib/auth-provider";
import { AboutPage } from "./pages/AboutPage";
import { AccountPage } from "./pages/AccountPage";
import { AuthCallback } from "./pages/AuthCallback";
import { PricingPage } from "./pages/PricingPage";
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
  if (path === "/pricing") {
    return <PricingPage />;
  }
  if (path === "/account") {
    return <AccountPage />;
  }

  return <App />;
}

const path = window.location.pathname;

if (path === "/auth/callback") {
  createRoot(rootElement).render(<AuthCallback />);
} else {
  createRoot(rootElement).render(
    <StrictMode>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </StrictMode>,
  );
}
