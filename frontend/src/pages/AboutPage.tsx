import aboutMarkdown from "../../../index.md?raw";

import { PlatformAppLayout } from "../components/PlatformAppLayout";
import { renderAboutMarkdown } from "../lib/about-markdown";

export function AboutPage() {
  return (
    <PlatformAppLayout
      title="About"
      subtitle="Visual comparison for two drawing PDFs."
      shellVariant="content"
    >
      <div className="landing-content">{renderAboutMarkdown(aboutMarkdown)}</div>
    </PlatformAppLayout>
  );
}
