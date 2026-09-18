// Drawer state for the sidebar. Below the drawer breakpoint (styles/shell.css)
// the sidebar is an overlay opened from the main header, which is rendered by
// each page rather than by AppShell — hence a context rather than props.

import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";

export interface SidebarContextValue {
  isOpen: boolean;
  open: () => void;
  close: () => void;
}

export const SidebarContext = createContext<SidebarContextValue | null>(null);

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  // Navigating (picking a run from history, starting a new one) closes the
  // drawer, so the reader lands on the content they just asked for.
  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  const value = useMemo<SidebarContextValue>(
    () => ({ isOpen, open, close }),
    [isOpen, open, close],
  );

  return <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>;
}
