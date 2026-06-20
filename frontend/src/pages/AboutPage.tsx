import aboutMarkdown from "../../../index.md?raw";

import { renderAboutMarkdown } from "../lib/about-markdown";

export function AboutPage() {
  return (
    <div className="page-body">
      <main className="landing-shell">{renderAboutMarkdown(aboutMarkdown)}</main>
    </div>
  );
}
