import aboutMarkdown from "../../../index.md?raw";

import { AppLayout } from "../components/AppLayout";
import { renderAboutMarkdown } from "../lib/about-markdown";

export function AboutPage() {
  return (
    <AppLayout
      title="Revision compare is repetitive work"
      subtitle="Check Your Drawings helps you review two drawing PDFs without manually aligning sheets in CAD."
      shellClassName="landing-shell"
    >
      {renderAboutMarkdown(aboutMarkdown)}
    </AppLayout>
  );
}
