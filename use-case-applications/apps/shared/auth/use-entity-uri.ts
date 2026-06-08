/**
 * Read the entity URI from the real browser path for a dynamic detail route.
 *
 * The apps are statically exported (output:"export"), so a dynamic route like
 * /customers/[uri] ships ONLY a single _placeholder document. CloudFront serves that
 * document for every /customers/* path (see cloudfront.ts SpaRewriteFn), so Next's
 * useParams() can return the build-time placeholder value ("_placeholder") rather than
 * the real segment. The authoritative source of the entity URI is therefore the actual
 * URL path — window.location.pathname — which carries the url-encoded entity URI that the
 * dashboard link wrote. We parse it out of the known prefix and decode it.
 *
 * Example path: /customers/https%3A%2F%2F…%23customer-c6b6e4ad…-resolved/
 *   -> "https://…#customer-c6b6e4ad…-resolved"
 */

import { useEffect, useState } from "react";

/** prefix e.g. "/customers/" or "/clients/" or "/referrals/". */
export function useEntityUri(prefix: string): string {
  const [uri, setUri] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const path = window.location.pathname;
    const idx = path.indexOf(prefix);
    if (idx === -1) return;
    // The segment after the prefix, up to the next "/" (trailingSlash adds a trailing one).
    let seg = path.slice(idx + prefix.length);
    seg = seg.replace(/\/+$/, ""); // strip trailing slash(es)
    if (!seg || seg === "_placeholder") return;
    try {
      setUri(decodeURIComponent(seg));
    } catch {
      setUri(seg);
    }
  }, [prefix]);

  return uri;
}
