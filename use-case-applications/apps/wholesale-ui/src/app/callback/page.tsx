import { Suspense } from "react";
import dynamic from "next/dynamic";

// OAuth redirect target. Cognito sends the user here with ?code=... after login.
// ssr:false because the exchange runs in the browser (PKCE verifier in
// sessionStorage, tokens in localStorage).
const CallbackView = dynamic(() => import("./callback-view"), { ssr: false });

export default function Page() {
  return (
    <Suspense fallback={null}>
      <CallbackView />
    </Suspense>
  );
}
