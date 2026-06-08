/**
 * Root layout for the Wholesale UI.
 *
 * Wraps the app in Apollo Provider and auth context.
 * The persona claim flows from here through every component.
 */

import React from "react";
import "./globals.css"; // @tailwind base/components/utilities — generates the utility classes
import "../../../shared/ui/tokens.css"; // the --color-* design-token vars
import "../../../shared/ui/atlas-ui.css"; // the warm-paper "true-UI" design system (loaded last → wins)
import { Providers } from "./providers";

export const metadata = {
  title: "ATLAS Wholesale UI — Consumer Banker",
  description: "Consumer-to-Wealth referral workflow powered by the ATLAS agentic semantic layer",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // theme-wholesale sets the info-blue accent for the Consumer-Banker lens; the
  // `atlas` class turns on the warm-paper ground from atlas-ui.css.
  return (
    <html lang="en">
      <body className="atlas theme-wholesale">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
