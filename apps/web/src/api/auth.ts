// JWT auth: obtain a token via POST /auth/token and keep it for the session.
// The token lives in memory and mirrors to sessionStorage so a refresh keeps
// the user signed in for the tab.

import { AUTH_TOKEN_PATH, AUTH_TOKEN_STORAGE_KEY } from "../constants";
import type { TokenResponse } from "./types";

const CONTENT_TYPE_HEADER = "Content-Type";
const JSON_CONTENT_TYPE = "application/json";

let accessToken: string | null = readStoredToken();

function readStoredToken(): string | null {
  try {
    return sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return accessToken;
}

export function isAuthenticated(): boolean {
  return accessToken !== null;
}

function storeToken(token: string): void {
  accessToken = token;
  try {
    sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } catch {
    // Session storage may be unavailable (private mode); in-memory token still works.
  }
}

export function clearToken(): void {
  accessToken = null;
  try {
    sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage errors on clear.
  }
}

export async function login(email: string, password: string): Promise<void> {
  const response = await fetch(AUTH_TOKEN_PATH, {
    method: "POST",
    headers: { [CONTENT_TYPE_HEADER]: JSON_CONTENT_TYPE },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error("Invalid email or password");
  }
  const data = (await response.json()) as TokenResponse;
  storeToken(data.access_token);
}
