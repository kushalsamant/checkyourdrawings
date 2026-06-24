import aboutMarkdown from "../../../index.md?raw";

import { AppLayout } from "../components/AppLayout";
import { renderAboutMarkdown } from "../lib/about-markdown";

export function AboutPage() {
  return (
    <AppLayout
      title="About"
      subtitle="Auto-aligned drawing comparison for coordination."
      shellClassName="landing-shell"
    >
      {renderAboutMarkdown(aboutMarkdown)}
    </AppLayout>
  );
}
