/**
 * Root layout for the Wholesale UI.
 *
 * Wraps the app in Apollo Provider and auth context.
 * The persona claim flows from here through every component.
 */

import React from "react";
import "./globals.css"; // @tailwind base/components/utilities — generates the utility classes
import "../../../shared/ui/tokens.css"; // the --color-* design-token vars the Tailwind theme references
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
  return (
    <html lang="en">
      <body className="font-sans antialiased bg-neutral-50 text-neutral-900">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
