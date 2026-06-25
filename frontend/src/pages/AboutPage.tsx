import aboutMarkdown from "../../../index.md?raw";

import { AppLayout } from "../components/AppLayout";
import { renderAboutMarkdown } from "../lib/about-markdown";

export function AboutPage() {
  return (
    <AppLayout
      title="Drawing revisions hide their changes."
      subtitle="You align sheets and compare by eye."
      shellClassName="landing-shell"
    >
      {renderAboutMarkdown(aboutMarkdown)}
    </AppLayout>
  );
}
