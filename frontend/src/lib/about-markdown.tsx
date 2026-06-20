import { Fragment, type ReactNode } from "react";

import { CHECKYOURDRAWINGS_SITE_URL } from "./legal-urls";

function normalizeHref(href: string): string {
  if (href.startsWith("mailto:") || href.startsWith("tel:")) {
    return href;
  }

  if (href.startsWith("//")) {
    return `https:${href}`;
  }

  if (href.startsWith("http://")) {
    return `https://${href.slice("http://".length)}`;
  }

  if (href.startsWith("https://")) {
    return href;
  }

  if (href.startsWith("/")) {
    return `${CHECKYOURDRAWINGS_SITE_URL}${href}`;
  }

  return `https://${href}`;
}

const OVERLAY_LABELS = ["Blue", "Orange", "Green", "Red"] as const;
type OverlayLabel = (typeof OVERLAY_LABELS)[number];

const LEGEND_LINE = /^(Blue|Orange|Green|Red) — (.*)$/;

const SWATCH_CLASS: Record<OverlayLabel, string> = {
  Blue: "overlay-swatch overlay-swatch--blue",
  Orange: "overlay-swatch overlay-swatch--orange",
  Green: "overlay-swatch overlay-swatch--green",
  Red: "overlay-swatch overlay-swatch--red",
};

function isLegendLine(line: string): boolean {
  return LEGEND_LINE.test(line.trim());
}

function renderLegendLine(line: string, key: string): ReactNode {
  const match = line.trim().match(LEGEND_LINE);
  if (match === null) {
    return null;
  }

  const label = match[1] as OverlayLabel;
  const description = match[2];

  return (
    <div className="overlay-legend-row" key={key}>
      <span className={SWATCH_CLASS[label]} aria-hidden="true" />
      <span>
        <strong>{label}</strong>
        {" — "}
        {description}
      </span>
    </div>
  );
}

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /(\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null = pattern.exec(text);

  while (match !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[2] !== undefined) {
      parts.push(<strong key={`${match.index}-${match[2]}`}>{match[2]}</strong>);
    } else if (match[3] !== undefined && match[4] !== undefined) {
      parts.push(
        <a
          key={`${match.index}-${match[3]}`}
          href={normalizeHref(match[4])}
          className="landing-inline-link"
          target="_blank"
          rel="noreferrer"
        >
          {match[3]}
        </a>,
      );
    }

    lastIndex = pattern.lastIndex;
    match = pattern.exec(text);
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

function renderParagraph(text: string, key: number): ReactNode {
  const lines = text.split("\n").map((line) => line.trimEnd());

  if (lines.some((line) => line.length > 0) && lines.filter((line) => line.length > 0).every(isLegendLine)) {
    return (
      <div key={key} className="overlay-legend">
        {lines
          .filter((line) => line.length > 0)
          .map((line, lineIndex) => renderLegendLine(line, `${key}-${lineIndex}`))}
      </div>
    );
  }

  return (
    <p key={key}>
      {lines.map((line, lineIndex) => (
        <Fragment key={lineIndex}>
          {lineIndex > 0 && <br />}
          {line.length > 0 ? renderInline(line) : null}
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
        <a
          key={index}
          href={normalizeHref(linkMatch[2] ?? "/")}
          className="landing-cta"
          target="_blank"
          rel="noreferrer"
        >
          {linkMatch[1]}
        </a>,
      );
      return;
    }

    nodes.push(renderParagraph(trimmed, index));
  });

  return nodes;
}
