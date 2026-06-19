import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { Session, User } from "@supabase/supabase-js";

import { getSupabaseClient, isSupabaseConfigured } from "./supabase";

interface AuthContextValue {
  user: User | null;
  session: Session | null;
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  const supabase = getSupabaseClient();

  useEffect(() => {
    if (supabase === null) {
      setLoading(false);
      return;
    }

    let isMounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!isMounted) {
        return;
      }
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setUser(nextSession?.user ?? null);
      setLoading(false);
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, [supabase]);

  useEffect(() => {
    accessTokenGetter = () => session?.access_token ?? null;
    return () => {
      accessTokenGetter = null;
    };
  }, [session]);

  async function signIn(): Promise<void> {
    if (supabase === null) {
      throw new Error("Supabase is not configured for this environment.");
    }

    const redirectTo = `${window.location.origin}/auth/callback`;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo },
    });
    if (error) {
      throw error;
    }
  }

  async function signOut(): Promise<void> {
    if (supabase === null) {
      setSession(null);
      setUser(null);
      return;
    }

    await supabase.auth.signOut();
    setSession(null);
    setUser(null);
  }

  const value: AuthContextValue = {
    user,
    session,
    loading,
    signIn,
    signOut,
    getAccessToken: () => session?.access_token ?? null,
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
  return isSupabaseConfigured();
}
