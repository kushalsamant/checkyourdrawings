import { describe, expect, it } from "vitest";

import { buildImageUrl, parseCompareResponse } from "./api";


describe("buildImageUrl", () => {
  it("builds a relative API image path for dev proxy", () => {
    expect(buildImageUrl("/outputs/comparison-abc.png")).toBe(
      "/outputs/comparison-abc.png",
    );
  });

  it("rejects absolute URLs from other origins when API base is unset", () => {
    expect(() => buildImageUrl("https://evil.example/outputs/x.png")).not.toThrow();
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
          drawing_a_bbox: { x: 0, y: 0, width: 100, height: 100 },
          drawing_b_bbox: { x: 0, y: 0, width: 100, height: 100 },
          overlap_bbox: { x: 10, y: 10, width: 80, height: 80 },
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
