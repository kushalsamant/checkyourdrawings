import { describe, expect, it } from "vitest";

import {
  MAX_FILE_SIZE_BYTES,
  getFileExtension,
  validateFile,
} from "../utils/fileValidation";


describe("getFileExtension", () => {
  it("returns the lowercase extension", () => {
    expect(getFileExtension("drawing.PDF")).toBe(".pdf");
  });

  it("returns an empty string for extensionless filenames", () => {
    expect(getFileExtension("drawing")).toBe("");
  });
});

describe("validateFile", () => {
  it.each([
    [".pdf", "application/pdf"],
    [".png", "image/png"],
    [".jpg", "image/jpeg"],
    [".jpeg", "image/jpeg"],
    [".dwg", "application/octet-stream"],
  ])("accepts %s with %s", (extension, mimeType) => {
    const file = new File(["content"], `drawing${extension}`, { type: mimeType });
    expect(validateFile(file)).toBeNull();
  });

  it("rejects unsupported extensions", () => {
    const file = new File(["content"], "drawing.gif", { type: "image/gif" });
    expect(validateFile(file)).toMatch(/Unsupported file type/);
  });

  it("rejects files over the size limit", () => {
    const file = new File([new Uint8Array(MAX_FILE_SIZE_BYTES + 1)], "drawing.png", {
      type: "image/png",
    });
    expect(validateFile(file)).toMatch(/100 MB/);
  });

  it("allows empty mime type when extension is valid", () => {
    const file = new File(["content"], "drawing.png", { type: "" });
    expect(validateFile(file)).toBeNull();
  });
});
