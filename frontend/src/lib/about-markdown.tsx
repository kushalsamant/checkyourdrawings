import { Fragment, type ReactNode } from "react";

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /\*\*([^*]+)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null = pattern.exec(text);

  while (match !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    parts.push(<strong key={`${match.index}-${match[1]}`}>{match[1]}</strong>);
    lastIndex = pattern.lastIndex;
    match = pattern.exec(text);
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

function renderParagraph(text: string, key: number): ReactNode {
  const lines = text.split("\n");

  return (
    <p key={key}>
      {lines.map((line, lineIndex) => (
        <Fragment key={lineIndex}>
          {lineIndex > 0 && <br />}
          {renderInline(line.trimEnd())}
        </Fragment>
      ))}
    </p>
  );
}

export function renderAboutMarkdown(markdown: string): ReactNode[] {
  const blocks = markdown.trim().split(/\n\n+/);
  const nodes: ReactNode[] = [];

  blocks.forEach((block, index) => {
    const trimmed = block.trim();

    if (trimmed === "---") {
      nodes.push(<hr key={index} className="landing-divider" />);
      return;
    }

    if (trimmed.startsWith("# ")) {
      nodes.push(<h1 key={index}>{trimmed.slice(2)}</h1>);
      return;
    }

    if (trimmed.startsWith("## ")) {
      nodes.push(<h2 key={index}>{trimmed.slice(3)}</h2>);
      return;
    }

    if (trimmed.startsWith("- ")) {
      const items = trimmed.split("\n").filter((line) => line.startsWith("- "));

      nodes.push(
        <ul key={index}>
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item.slice(2))}</li>
          ))}
        </ul>,
      );
      return;
    }

    const linkMatch = trimmed.match(/^\[([^\]]+)\](?:\(([^)]+)\))?$/);
    if (linkMatch) {
      nodes.push(
        <a key={index} href={linkMatch[2] ?? "/"} className="landing-cta">
          {linkMatch[1]}
        </a>,
      );
      return;
    }

    nodes.push(renderParagraph(trimmed, index));
  });

  return nodes;
}
