// The main column's header: the current view's title, a status pill, and the
// Share/Export actions. Rendered by each page (the title and pill are page
// state) inside the AppShell's main column.
//
// Share and Export are disabled: the handoff leaves both flows undesigned and
// there is no backend for either yet.

import { Menu } from "lucide-react";

import { ICON_STROKE_WIDTH } from "../../constants";
import { useSidebar } from "../../hooks/useSidebar";

const SHARE_LABEL = "Share";
const EXPORT_LABEL = "Export";
const UNAVAILABLE_ACTION_TITLE = "Not available yet";
const OPEN_SIDEBAR_LABEL = "Open sidebar";
const MENU_ICON_SIZE = 16;

export type HeaderBadgeTone = "running" | "neutral";

interface MainHeaderProps {
  title: string;
  badgeLabel: string;
  badgeTone?: HeaderBadgeTone;
}

export function MainHeader({ title, badgeLabel, badgeTone = "neutral" }: MainHeaderProps) {
  const { open } = useSidebar();

  return (
    <header className="main-header">
      <div className="main-header__title-group">
        <button
          type="button"
          className="main-header__drawer-toggle"
          aria-label={OPEN_SIDEBAR_LABEL}
          onClick={open}
        >
          <Menu size={MENU_ICON_SIZE} strokeWidth={ICON_STROKE_WIDTH} />
        </button>
        <span className="main-header__title">{title}</span>
        <span
          className={`main-header__badge${
            badgeTone === "running" ? " main-header__badge--running" : ""
          }`}
        >
          {badgeLabel}
        </span>
      </div>
      <div className="main-header__actions">
        <button
          type="button"
          className="main-header__action"
          disabled
          title={UNAVAILABLE_ACTION_TITLE}
        >
          {SHARE_LABEL}
        </button>
        <button
          type="button"
          className="main-header__action main-header__action--subtle"
          disabled
          title={UNAVAILABLE_ACTION_TITLE}
        >
          {EXPORT_LABEL}
        </button>
      </div>
    </header>
  );
}
