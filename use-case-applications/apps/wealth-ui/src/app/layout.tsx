/**
 * Root layout for the Wealth UI.
 *
 * Same shared design tokens as the Wholesale UI — Thesis 2 in action:
 * same backbone, different lens.
 */

import React from "react";
import "./globals.css"; // @tailwind base/components/utilities — generates the utility classes
import "../../../shared/ui/tokens.css"; // the --color-* design-token vars
import "../../../shared/ui/atlas-ui.css"; // the warm-paper "true-UI" design system (loaded last → wins)
import { Providers } from "./providers";

export const metadata = {
  title: "ATLAS Wealth UI — Advisor Workbench",
  description: "Wealth Advisor client coverage and conversational surface powered by the ATLAS agentic semantic layer",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // theme-wealth sets the indigo accent for the Wealth-Advisor lens; same backbone
  // as Wholesale, different lens (Thesis 2). `atlas` turns on the warm-paper ground.
  return (
    <html lang="en">
      <body className="atlas theme-wealth">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
