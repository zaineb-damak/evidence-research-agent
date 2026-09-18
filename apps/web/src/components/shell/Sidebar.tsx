// Sidebar: brand row, the actions block (start a new run, search history),
// the grouped run history, and the account footer.

import { ChevronsLeft, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { BRAND_NAME, HISTORY_SEARCH_PLACEHOLDER, ICON_STROKE_WIDTH } from "../../constants";
import { useSidebar } from "../../hooks/useSidebar";
import { ROUTE_HOME } from "../../routes";
import { AccountFooter } from "./AccountFooter";
import { SessionList } from "./SessionList";

const NEW_RESEARCH_LABEL = "New research";
const CLOSE_SIDEBAR_LABEL = "Close sidebar";
const NEW_RESEARCH_ICON_SIZE = 15;
const SEARCH_ICON_SIZE = 14;
const COLLAPSE_ICON_SIZE = 15;

export function Sidebar() {
  const [searchQuery, setSearchQuery] = useState("");
  const { isOpen, close } = useSidebar();

  return (
    <>
      {isOpen && (
        <button
          type="button"
          className="sidebar__scrim"
          aria-label={CLOSE_SIDEBAR_LABEL}
          onClick={close}
        />
      )}
      <aside className={`sidebar${isOpen ? " sidebar--open" : ""}`}>
        <div className="sidebar__brand-row">
          <div className="brand sidebar__brand">
            <span className="brand__mark" aria-hidden="true" />
            <span className="brand__name">{BRAND_NAME}</span>
          </div>
          <button
            type="button"
            className="sidebar__collapse"
            aria-label={CLOSE_SIDEBAR_LABEL}
            onClick={close}
          >
            <ChevronsLeft size={COLLAPSE_ICON_SIZE} strokeWidth={ICON_STROKE_WIDTH} />
          </button>
        </div>

        <div className="sidebar__actions">
          <Link className="sidebar__new-research" to={ROUTE_HOME}>
            <Plus
              className="sidebar__new-research-icon"
              size={NEW_RESEARCH_ICON_SIZE}
              strokeWidth={ICON_STROKE_WIDTH}
              aria-hidden="true"
            />
            {NEW_RESEARCH_LABEL}
          </Link>
          <div className="sidebar__search">
            <Search size={SEARCH_ICON_SIZE} strokeWidth={ICON_STROKE_WIDTH} aria-hidden="true" />
            <input
              className="sidebar__search-input"
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={HISTORY_SEARCH_PLACEHOLDER}
              aria-label={HISTORY_SEARCH_PLACEHOLDER}
            />
          </div>
        </div>

        <div className="sidebar__history">
          <SessionList searchQuery={searchQuery} />
        </div>

        <AccountFooter />
      </aside>
    </>
  );
}
