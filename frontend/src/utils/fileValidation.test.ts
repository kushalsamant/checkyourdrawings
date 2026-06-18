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
  it("accepts PDF files", () => {
    const file = new File(["content"], "drawing.pdf", { type: "application/pdf" });
    expect(validateFile(file)).toBeNull();
  });

  it("rejects unsupported extensions", () => {
    const file = new File(["content"], "drawing.png", { type: "image/png" });
    expect(validateFile(file)).toMatch(/Unsupported file type/);
  });

  it("rejects DWG files", () => {
    const file = new File(["content"], "drawing.dwg", { type: "application/octet-stream" });
    expect(validateFile(file)).toMatch(/Unsupported file type/);
  });

  it("rejects files over the size limit", () => {
    const file = new File([new Uint8Array(MAX_FILE_SIZE_BYTES + 1)], "drawing.pdf", {
      type: "application/pdf",
    });
    expect(validateFile(file)).toMatch(/100 MB/);
  });

  it("allows empty mime type when extension is valid", () => {
    const file = new File(["content"], "drawing.pdf", { type: "" });
    expect(validateFile(file)).toBeNull();
  });
});
