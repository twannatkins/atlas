import { Suspense } from "react";
import dynamic from "next/dynamic";

const ReferralView = dynamic(() => import("./referral-view"), { ssr: false });

export function generateStaticParams() {
  return [{ uri: "_placeholder" }];
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <ReferralView />
    </Suspense>
  );
}
