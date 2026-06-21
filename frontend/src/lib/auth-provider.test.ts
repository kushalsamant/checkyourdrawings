import { describe, expect, it } from "vitest";

import { isJwtExpired } from "./auth-provider";

const NOW_MS = 1_000_000_000_000;

function makeToken(payload: Record<string, unknown>): string {
  const body = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `header.${body}.signature`;
}

describe("isJwtExpired", () => {
  it("treats a token expiring in the future as valid", () => {
    const token = makeToken({ exp: Math.floor(NOW_MS / 1000) + 3600 });
    expect(isJwtExpired(token, NOW_MS)).toBe(false);
  });

  it("treats an expired token as expired", () => {
    const token = makeToken({ exp: Math.floor(NOW_MS / 1000) - 60 });
    expect(isJwtExpired(token, NOW_MS)).toBe(true);
  });

  it("treats a token without exp as expired", () => {
    const token = makeToken({ sub: "user-1", email: "a@b.com" });
    expect(isJwtExpired(token, NOW_MS)).toBe(true);
  });

  it("treats a malformed token as expired", () => {
    expect(isJwtExpired("not-a-jwt", NOW_MS)).toBe(true);
  });
});
