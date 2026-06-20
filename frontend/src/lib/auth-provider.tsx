import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type AuthUser = {
  email: string;
  name?: string | null;
};

const AUTH_URL = (import.meta.env.VITE_KVSHVL_AUTH_URL ?? "").replace(/\/$/, "");
const TOKEN_STORAGE_KEY = "kvshvl_platform_jwt";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

let accessTokenGetter: (() => string | null) | null = null;

export function getAuthAccessToken(): string | null {
  return accessTokenGetter?.() ?? null;
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const base64Url = parts[1] ?? "";
  const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  try {
    const json = atob(base64);
    const payload = JSON.parse(json) as unknown;
    if (typeof payload === "object" && payload !== null) {
      return payload as Record<string, unknown>;
    }
  } catch {
    return null;
  }
  return null;
}

function readTokenFromStorage(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeTokenToStorage(token: string | null): void {
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // ignore
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = readTokenFromStorage();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    const payload = decodeJwtPayload(token);
    const email = payload?.email;
    const name = payload?.name;
    if (typeof email === "string" && email) {
      setUser({ email, name: typeof name === "string" ? name : null });
    } else {
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    accessTokenGetter = () => readTokenFromStorage();
    return () => {
      accessTokenGetter = null;
    };
  }, []);

  async function signIn(): Promise<void> {
    if (!AUTH_URL) {
      throw new Error("VITE_KVSHVL_AUTH_URL is not configured for this environment.");
    }
    const returnTo = `${window.location.origin}/auth/callback`;
    window.location.assign(
      `${AUTH_URL}/sign-in?return_to=${encodeURIComponent(returnTo)}`,
    );
  }

  async function signOut(): Promise<void> {
    writeTokenToStorage(null);
    setUser(null);
  }

  const value: AuthContextValue = {
    user,
    loading,
    signIn,
    signOut,
    getAccessToken: () => readTokenFromStorage(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}

export function isAuthConfigured(): boolean {
  return Boolean(AUTH_URL);
}
