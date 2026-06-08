/**
 * Shared app chrome for both ATLAS UIs.
 *
 * One backbone, two lenses (Thesis 2): the Wholesale and Wealth apps render
 * the SAME shell — warm-paper ground, app bar with brand + breadcrumb + who,
 * and the "live now / possible next" legend — and only differ by the accent
 * theme class set on <body> and the nav links passed in. The legend is not
 * decoration: it tells a novice, on every screen, how to read a roadmap
 * (dashed) panel apart from a live one. Nothing here invents data; the chrome
 * only frames what the pages render.
 */

"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "../auth/use-auth";

interface NavLink {
  href: string;
  label: string;
}

interface AppShellProps {
  /** Short brand suffix shown after "ATLAS ·" (e.g. "Wholesale", "Wealth"). */
  brandSuffix: string;
  /** Top-bar nav links for this app. */
  navLinks: NavLink[];
  children: React.ReactNode;
}

/** First two initials of a display name, for the avatar circle. */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "—";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Human label for a persona claim (the cognito:group). */
function personaLabel(claim: string): string {
  const map: Record<string, string> = {
    "atlas-consumer-banker": "Consumer Banker",
    "atlas-wealth-advisor": "Wealth Advisor",
    "atlas-bsa-analyst": "BSA Analyst",
    "atlas-ontology-steward": "Ontology Steward",
    "atlas-auditor": "Auditor",
  };
  return map[claim] || claim || "";
}

export function AppShell({ brandSuffix, navLinks, children }: AppShellProps) {
  const { displayName, personaClaim, isAuthenticated, signOut } = useAuth();
  const pathname = usePathname();

  return (
    <div className="atlas-wrap">
      {/* live / roadmap legend — honest reading key, on every screen (matches the
          "true-UI preview" header in the design templates) */}
      <div className="preview-tag">
        <span className="dot" />
        <b>ATLAS · {brandSuffix}</b> built on the agentic semantic layer — live graph data
        <span className="legend">
          <span>
            <span className="swatch live" /> live now
          </span>
          <span>
            <span className="swatch future" /> possible next
          </span>
        </span>
      </div>

      {/* The outer paper shell — matches the templates: appbar + all cards live inside a
          single --panel-2 container. */}
      <div className="shell">
        <div className="appbar">
          <a className="brand" href="/">
            <span className="mk">A</span> ATLAS · {brandSuffix}
          </a>
          <span className="crumb">{pathname}</span>
          {isAuthenticated && (
            <nav className="navlinks" aria-label="Sections">
              {navLinks.map((l) => (
                <a key={l.href} href={l.href}>
                  {l.label}
                </a>
              ))}
            </nav>
          )}
          {isAuthenticated && (
            <div className="who">
              <span className="av">{initials(displayName || personaClaim)}</span>
              <span>
                {displayName || "—"} · {personaLabel(personaClaim)}
              </span>
              <button className="signout" onClick={signOut}>
                Sign out
              </button>
            </div>
          )}
        </div>

        {children}
      </div>
    </div>
  );
}

interface SignInGateProps {
  /** e.g. "Sign in as Consumer Banker". */
  label: string;
  /** One-line description of what this app is. */
  blurb: string;
  signIn: () => void;
}

/** The unauthenticated landing — themed sign-in card. */
export function SignInGate({ label, blurb, signIn }: SignInGateProps) {
  return (
    <div className="signin-wrap">
      <div className="signin-card">
        <div className="mk">A</div>
        <h1>{label.replace(/^Sign in as /, "")}</h1>
        <p>{blurb}</p>
        <button className="btn accent" onClick={signIn}>
          {label}
        </button>
      </div>
    </div>
  );
}
