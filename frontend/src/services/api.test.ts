import { describe, expect, it } from "vitest";

import { buildImageUrl, parseCompareResponse } from "./api";


describe("buildImageUrl", () => {
  it("builds a relative API image path", () => {
    expect(buildImageUrl("/outputs/comparison-abc.png")).toBe(
      "http://127.0.0.1:8000/outputs/comparison-abc.png",
    );
  });

  it("allows absolute URLs from the API origin", () => {
    expect(buildImageUrl("http://127.0.0.1:8000/outputs/comparison-abc.png")).toBe(
      "http://127.0.0.1:8000/outputs/comparison-abc.png",
    );
  });

  it("rejects absolute URLs from other origins", () => {
    expect(() => buildImageUrl("https://evil.example/outputs/x.png")).toThrow(
      "not from the API origin",
    );
  });
});

describe("parseCompareResponse", () => {
  it("accepts a valid comparison payload", () => {
    const payload = {
      image_path: "/outputs/comparison-abc.png",
      metadata: {
        alignment: { inlier_matches: 10, inlier_ratio: 0.9 },
        alignment_confidence: { status: "high", message: null },
        content: {
          reference_bbox: { x: 0, y: 0, width: 100, height: 100 },
          revision_bbox: { x: 0, y: 0, width: 100, height: 100 },
          overlap_bbox: { x: 10, y: 10, width: 80, height: 80 },
        },
        overlay: {
          red_pixels: 1,
          blue_pixels: 2,
          green_pixels: 3,
          magenta_pixels: 0,
          background_mode: "light",
        },
        differences: { regions: [] },
      },
    };

    expect(parseCompareResponse(payload).image_path).toBe("/outputs/comparison-abc.png");
  });

  it("rejects missing alignment confidence", () => {
    expect(() =>
      parseCompareResponse({
        image_path: "/outputs/x.png",
        metadata: {
          alignment: { inlier_ratio: 0.9 },
          content: {
            reference_bbox: { x: 0, y: 0, width: 1, height: 1 },
            revision_bbox: { x: 0, y: 0, width: 1, height: 1 },
            overlap_bbox: { x: 0, y: 0, width: 1, height: 1 },
          },
          overlay: {
            red_pixels: 0,
            blue_pixels: 0,
            green_pixels: 0,
            magenta_pixels: 0,
            background_mode: "light",
          },
          differences: { regions: [] },
        },
      }),
    ).toThrow("alignment confidence");
  });

  it("rejects missing metadata regions", () => {
    expect(() =>
      parseCompareResponse({
        image_path: "/outputs/x.png",
        metadata: {
          alignment: {},
          alignment_confidence: { status: "high", message: null },
          content: {
            reference_bbox: { x: 0, y: 0, width: 1, height: 1 },
            revision_bbox: { x: 0, y: 0, width: 1, height: 1 },
            overlap_bbox: { x: 0, y: 0, width: 1, height: 1 },
          },
          overlay: {
            red_pixels: 0,
            blue_pixels: 0,
            green_pixels: 0,
            magenta_pixels: 0,
            background_mode: "light",
          },
          differences: {},
        },
      }),
    ).toThrow("difference regions");
  });
});
