import aboutMarkdown from "../../about.md?raw";

import { renderAboutMarkdown } from "../lib/about-markdown";

export function AboutPage() {
  return (
    <div className="page-body">
      <main className="landing-shell">
        {renderAboutMarkdown(aboutMarkdown)}

        <footer className="app-footer">
          <p>
            <a href="/">Back to app</a>
            {" · "}
            &copy; {new Date().getFullYear()} Check Your Drawings
          </p>
        </footer>
      </main>
    </div>
  );
}
