const STORAGE_KEY = "kvshvl_anon_session_id";
const LEGACY_STORAGE_KEY = "cyd_anon_session_id";

function generateUuidV4(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID().toLowerCase();
  }

  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function readStoredSessionId(): string | null {
  try {
    const current = localStorage.getItem(STORAGE_KEY);
    if (current) {
      return current;
    }

    const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (legacy) {
      localStorage.setItem(STORAGE_KEY, legacy);
      localStorage.removeItem(LEGACY_STORAGE_KEY);
      return legacy;
    }

    return null;
  } catch {
    return null;
  }
}

function writeStoredSessionId(sessionId: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, sessionId);
  } catch {
    // ignore
  }
}

const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function getAnonSessionId(): string {
  const existing = readStoredSessionId();
  if (existing && UUID_V4_PATTERN.test(existing)) {
    return existing.toLowerCase();
  }

  const sessionId = generateUuidV4();
  writeStoredSessionId(sessionId);
  return sessionId;
}

export const ANON_SESSION_HEADER = "X-Anon-Session";
