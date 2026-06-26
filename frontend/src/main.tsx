import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { AuthProvider } from "./lib/auth-provider";
import { AboutPage } from "./pages/AboutPage";
import { AccountPage } from "./pages/AccountPage";
import { AuthCallback } from "./pages/AuthCallback";
import { PricingPage } from "./pages/PricingPage";
import "@kvshvl/platform-design-system/tokens.css";
import "@kvshvl/platform-design-system/base.css";
import "@kvshvl/platform-design-system/pages.css";
import "./compare.css";

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("Root element was not found.");
}

function AppRoutes() {
  const path = window.location.pathname;

  if (path === "/auth/callback") {
    return <AuthCallback />;
  }
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

createRoot(rootElement).render(
  <StrictMode>
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  </StrictMode>,
);
