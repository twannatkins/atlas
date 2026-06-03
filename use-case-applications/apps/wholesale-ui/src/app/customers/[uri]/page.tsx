import { Suspense } from "react";
import dynamic from "next/dynamic";

const CustomerView = dynamic(() => import("./customer-view"), { ssr: false });

export function generateStaticParams() {
  return [{ uri: "_placeholder" }];
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <CustomerView />
    </Suspense>
  );
}
