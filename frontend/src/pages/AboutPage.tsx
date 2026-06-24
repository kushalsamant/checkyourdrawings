import aboutMarkdown from "../../../index.md?raw";

import { AppLayout } from "../components/AppLayout";
import { renderAboutMarkdown } from "../lib/about-markdown";

export function AboutPage() {
  return (
    <AppLayout
      title="About"
      subtitle="Spot revision changes before site — auto-aligned coordination overlays."
      shellClassName="landing-shell"
    >
      {renderAboutMarkdown(aboutMarkdown)}
    </AppLayout>
  );
}
