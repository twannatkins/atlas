import { Suspense } from "react";
import dynamic from "next/dynamic";

const ClientView = dynamic(() => import("./client-view"), { ssr: false });

export function generateStaticParams() {
  return [{ uri: "_placeholder" }];
}

export default function Page() {
  return (
    <Suspense fallback={null}>
      <ClientView />
    </Suspense>
  );
}
