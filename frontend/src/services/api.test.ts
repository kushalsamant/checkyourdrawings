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
        alignment: { inlier_matches: 10 },
        differences: { regions: [] },
      },
    };

    expect(parseCompareResponse(payload).image_path).toBe("/outputs/comparison-abc.png");
  });

  it("rejects missing metadata regions", () => {
    expect(() =>
      parseCompareResponse({
        image_path: "/outputs/x.png",
        metadata: {
          alignment: {},
          differences: {},
        },
      }),
    ).toThrow("difference regions");
  });
});
