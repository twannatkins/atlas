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

/**
 * A clean breadcrumb label for the current path. NEVER renders the raw URL-encoded entity
 * URI (e.g. /clients/https%3A%2F%2F…%23customer-…) — that long string overflowed the appbar
 * and crushed the nav. Maps each known route to a readable label; for a dynamic detail
 * route it shows the page label plus the entity's short id (decoded from the last URI
 * segment), e.g. "Client 360 · c6b6e4ad".
 */
function crumbLabel(pathname: string): string {
  if (!pathname || pathname === "/") return "My book";
  const seg = pathname.replace(/^\/+|\/+$/g, "").split("/");
  const root = seg[0];
  const labels: Record<string, string> = {
    customers: "Customer 360",
    clients: "Client 360",
    referrals: "Referral",
    conversations: "Ask the graph",
    themes: "Themes",
    callback: "Signing in…",
  };
  const base = labels[root];
  if (!base) return "My book";
  // For a dynamic detail route, append a short, decoded entity id (never the encoded URI).
  if (seg.length > 1 && seg[1] && seg[1] !== "_placeholder") {
    let decoded = seg[1];
    try { decoded = decodeURIComponent(seg[1]); } catch { /* keep raw */ }
    // last URI fragment, e.g. "customer-c6b6e4ad-…-resolved" → "c6b6e4ad"
    const tail = decoded.split(/[#/]/).pop() || decoded;
    const m = tail.match(/(?:customer|household|advisor|signal)-([0-9a-f]{8})/i);
    const shortId = m ? m[1] : tail.slice(0, 12);
    return `${base} · ${shortId}`;
  }
  return base;
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
          <span className="crumb">{crumbLabel(pathname)}</span>
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
