import { describe, expect, it, vi } from "vitest";

import { buildImageUrl, getErrorMessage, parseCompareResponse } from "./api";


describe("getErrorMessage", () => {
  it("returns API detail for auth misconfiguration instead of compare-busy fallback", async () => {
    const response = new Response(
      JSON.stringify({ detail: "Authentication database is not configured." }),
      { status: 503, headers: { "Content-Type": "application/json" } },
    );

    await expect(getErrorMessage(response)).resolves.toBe(
      "Authentication database is not configured.",
    );
  });

  it("returns compare-busy message when 503 has no parseable detail", async () => {
    const response = new Response("", { status: 503 });

    await expect(getErrorMessage(response)).resolves.toBe(
      "Another comparison is in progress. Try again in a moment.",
    );
  });
});

describe("buildImageUrl", () => {
  it("builds a relative API image path for dev proxy", () => {
    expect(buildImageUrl("/outputs/comparison-abc.png")).toBe(
      "/outputs/comparison-abc.png",
    );
  });

  it("rejects absolute URLs from disallowed origins when API base is unset", () => {
    expect(() => buildImageUrl("https://evil.example/outputs/x.png")).toThrow();
  });

  it("allows absolute URLs from the configured API base", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.com");

    expect(
      buildImageUrl("https://api.example.com/outputs/comparison-abc.png"),
    ).toBe("https://api.example.com/outputs/comparison-abc.png");

    vi.unstubAllEnvs();
  });
});

describe("parseCompareResponse", () => {
  it("accepts a valid comparison payload", () => {
    const payload = {
      image_path: "/outputs/comparison-abc.png",
      pdf_path: "/outputs/comparison-abc.pdf",
      metadata: {
        alignment: { inlier_matches: 10, inlier_ratio: 0.9 },
        alignment_confidence: { status: "high", message: null },
        content: {
          drawing_a_bbox: { x: 0, y: 0, width: 100, height: 100 },
          drawing_b_bbox: { x: 0, y: 0, width: 100, height: 100 },
          overlap_bbox: { x: 10, y: 10, width: 80, height: 80 },
          comparison_bbox: { x: 0, y: 0, width: 100, height: 100 },
        },
        overlay: {
          orange_pixels: 1,
          blue_pixels: 2,
          green_pixels: 3,
          red_pixels: 0,
        },
        differences: {
          width: 100,
          height: 100,
          changed_pixel_count: 3,
          changed_pixel_ratio: 0.5,
        },
        output_page: {
          mode: "source_a",
          width_pt: 842,
          height_pt: 595,
          raster_dpi: 150,
        },
      },
    };

    const parsed = parseCompareResponse(payload);
    expect(parsed.image_path).toBe("/outputs/comparison-abc.png");
    expect(parsed.pdf_path).toBe("/outputs/comparison-abc.pdf");
  });

  it("rejects missing alignment confidence", () => {
    expect(() =>
      parseCompareResponse({
        image_path: "/outputs/x.png",
        pdf_path: "/outputs/x.pdf",
        metadata: {
          alignment: { inlier_ratio: 0.9 },
          content: {
            drawing_a_bbox: { x: 0, y: 0, width: 1, height: 1 },
            drawing_b_bbox: { x: 0, y: 0, width: 1, height: 1 },
            overlap_bbox: { x: 0, y: 0, width: 1, height: 1 },
          },
          overlay: {
            orange_pixels: 0,
            blue_pixels: 0,
            green_pixels: 0,
            red_pixels: 0,
          },
          differences: {
            width: 1,
            height: 1,
            changed_pixel_count: 0,
            changed_pixel_ratio: 0,
          },
        },
      }),
    ).toThrow("alignment confidence");
  });

  it("rejects missing difference counts", () => {
    expect(() =>
      parseCompareResponse({
        image_path: "/outputs/x.png",
        pdf_path: "/outputs/x.pdf",
        metadata: {
          alignment: {},
          alignment_confidence: { status: "high", message: null },
          content: {
            drawing_a_bbox: { x: 0, y: 0, width: 1, height: 1 },
            drawing_b_bbox: { x: 0, y: 0, width: 1, height: 1 },
            overlap_bbox: { x: 0, y: 0, width: 1, height: 1 },
          },
          overlay: {
            orange_pixels: 0,
            blue_pixels: 0,
            green_pixels: 0,
            red_pixels: 0,
          },
          differences: { width: 1, height: 1 },
        },
      }),
    ).toThrow("difference counts");
  });
});
