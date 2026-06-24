import aboutMarkdown from "../../../index.md?raw";

import { AppLayout } from "../components/AppLayout";
import { renderAboutMarkdown } from "../lib/about-markdown";

export function AboutPage() {
  return (
    <AppLayout
      title="Finding drawing changes manually is repetitive work"
      subtitle="Scale, align, overlay, scan — on every consultant return and reissue."
      shellClassName="landing-shell"
    >
      {renderAboutMarkdown(aboutMarkdown)}
    </AppLayout>
  );
}
