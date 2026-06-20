import aboutMarkdown from "../../../index.md?raw";

import { renderAboutMarkdown } from "../lib/about-markdown";
import { KVSHVL_PRIVACY_URL, KVSHVL_TERMS_URL } from "../lib/legal-urls";

export function AboutPage() {
  return (
    <div className="page-body">
      <main className="landing-shell">
        {renderAboutMarkdown(aboutMarkdown)}

        <footer className="app-footer">
          <p>
            <a href="/">Back to app</a>
            {" · "}
            <a href={KVSHVL_PRIVACY_URL} target="_blank" rel="noreferrer">
              Privacy Policy
            </a>
            {" · "}
            <a href={KVSHVL_TERMS_URL} target="_blank" rel="noreferrer">
              Terms of Service
            </a>
          </p>
          <p>&copy; {new Date().getFullYear()} Check Your Drawings</p>
        </footer>
      </main>
    </div>
  );
}
