import aboutMarkdown from "../../../index.md?raw";

import { renderAboutMarkdown } from "../lib/about-markdown";
import { CHECKYOURDRAWINGS_SITE_URL } from "../lib/legal-urls";

export function AboutPage() {
  return (
    <div className="page-body">
      <main className="landing-shell">
        {renderAboutMarkdown(aboutMarkdown)}

        <footer className="app-footer">
          <p>
            <a href={`${CHECKYOURDRAWINGS_SITE_URL}/`}>Back to app</a>
          </p>
          <p>&copy; {new Date().getFullYear()} Check Your Drawings</p>
        </footer>
      </main>
    </div>
  );
}
