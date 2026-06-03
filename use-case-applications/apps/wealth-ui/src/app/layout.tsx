/**
 * Root layout for the Wealth UI.
 *
 * Same shared design tokens as the Wholesale UI — Thesis 2 in action:
 * same backbone, different lens.
 */

import React from "react";
import "../../../shared/ui/tokens.css";
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
  return (
    <html lang="en">
      <body className="font-sans antialiased bg-neutral-50 text-neutral-900">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
