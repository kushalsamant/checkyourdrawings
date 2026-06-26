import {
  AppLayout,
  type AppLayoutProps,
} from "@kvshvl/platform-design-system";

import { navLinks } from "../lib/site-chrome";
import { AuthActions } from "./AuthActions";

const DEFAULT_TITLE = "Check Your Drawings";
const DEFAULT_SUBTITLE = "Upload Drawing A and Drawing B. Get an aligned overlay.";

export type PlatformAppLayoutProps = Omit<AppLayoutProps, "navLinks" | "authSlot">;

export function PlatformAppLayout({
  title = DEFAULT_TITLE,
  subtitle = DEFAULT_SUBTITLE,
  ...props
}: PlatformAppLayoutProps) {
  return (
    <AppLayout
      title={title}
      subtitle={subtitle}
      navLinks={navLinks}
      authSlot={<AuthActions />}
      {...props}
    />
  );
}
