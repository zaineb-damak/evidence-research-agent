import { useContext } from "react";

import { SidebarContext } from "../context/SidebarContext";
import type { SidebarContextValue } from "../context/SidebarContext";

export function useSidebar(): SidebarContextValue {
  const context = useContext(SidebarContext);
  if (context === null) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
}
