// Signed-in account menu: shows the cached email (there is no backend /me
// endpoint — see CLAUDE.md known v1 gaps) with a sign-out action.

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { ROUTE_LOGIN } from "../../routes";

const DROPDOWN_CONTENT_SIDE_OFFSET = 8;
const UNKNOWN_ACCOUNT_LABEL = "Account";

export function AccountMenu() {
  const { email, signOut } = useAuth();
  const navigate = useNavigate();

  function handleSignOut(): void {
    signOut();
    navigate(ROUTE_LOGIN);
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button type="button" className="account-menu__trigger">
          {email ?? UNKNOWN_ACCOUNT_LABEL}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="account-menu__content"
          align="end"
          sideOffset={DROPDOWN_CONTENT_SIDE_OFFSET}
        >
          <DropdownMenu.Item className="account-menu__item" onSelect={handleSignOut}>
            Sign out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
