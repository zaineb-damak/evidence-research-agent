// Reactive auth state for the app. Wraps the token-storage functions already
// in api/auth.ts (login/signup/clearToken/isAuthenticated) instead of
// reimplementing token persistence — this context only adds the piece that
// was missing: a React-reactive "am I signed in" value plus a cached display
// email (there is no backend /me endpoint; see CLAUDE.md known v1 gaps).

import { createContext, useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  clearToken,
  isAuthenticated as hasStoredToken,
  login,
  signup,
} from "../api/auth";
import { AUTH_EMAIL_STORAGE_KEY } from "../constants";

export interface AuthContextValue {
  isAuthenticated: boolean;
  email: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredEmail(): string | null {
  try {
    return sessionStorage.getItem(AUTH_EMAIL_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeEmail(email: string): void {
  try {
    sessionStorage.setItem(AUTH_EMAIL_STORAGE_KEY, email);
  } catch {
    // Session storage may be unavailable (private mode); in-memory state still works.
  }
}

function clearStoredEmail(): void {
  try {
    sessionStorage.removeItem(AUTH_EMAIL_STORAGE_KEY);
  } catch {
    // Ignore storage errors on clear.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(hasStoredToken());
  const [email, setEmail] = useState<string | null>(readStoredEmail());

  const signIn = useCallback(async (emailInput: string, password: string) => {
    await login(emailInput, password);
    storeEmail(emailInput);
    setEmail(emailInput);
    setAuthenticated(true);
  }, []);

  const signUp = useCallback(async (emailInput: string, password: string) => {
    await signup(emailInput, password);
    storeEmail(emailInput);
    setEmail(emailInput);
    setAuthenticated(true);
  }, []);

  const signOut = useCallback(() => {
    clearToken();
    clearStoredEmail();
    setEmail(null);
    setAuthenticated(false);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ isAuthenticated: authenticated, email, signIn, signUp, signOut }),
    [authenticated, email, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
