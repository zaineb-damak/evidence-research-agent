// Catch-all route: the app's own 404, outside the authenticated shell.

import { Link } from "react-router-dom";

import { ROUTE_HOME } from "../routes";

const TITLE = "Page not found";
const BODY = "That link doesn't point anywhere in this app.";
const HOME_LINK_LABEL = "Start a new research run";

export function NotFoundPage() {
  return (
    <div className="not-found">
      <h1 className="not-found__title">{TITLE}</h1>
      <p className="not-found__body">{BODY}</p>
      <Link to={ROUTE_HOME}>{HOME_LINK_LABEL}</Link>
    </div>
  );
}
