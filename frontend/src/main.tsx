import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { AuthProvider } from "./lib/auth-provider";
import { AboutPage } from "./pages/AboutPage";
import { AuthCallback } from "./pages/AuthCallback";
import "./styles.css";

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("Root element was not found.");
}

function RootPage() {
  const path = window.location.pathname;

  if (path === "/auth/callback") {
    return <AuthCallback />;
  }

  if (path === "/about") {
    return <AboutPage />;
  }

  return <App />;
}

createRoot(rootElement).render(
  <StrictMode>
    <AuthProvider>
      <RootPage />
    </AuthProvider>
  </StrictMode>,
);
