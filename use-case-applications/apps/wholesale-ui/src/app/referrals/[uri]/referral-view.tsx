/**
 * Referral Detail page.
 *
 * Shows the signals that triggered a referral, the drafted rationale
 * (editable if pending), the routing decision, and the audit trail.
 * This is where the human-in-the-loop pattern is most visible.
 */

"use client";

import React, { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation } from "@apollo/client";
import { REFERRAL_DETAIL_QUERY } from "../../../graphql/queries";
import { ROUTE_REFERRAL_MUTATION, DRAFT_RATIONALE_MUTATION } from "../../../graphql/mutations";
import { useAuth } from "../../../../../shared/auth/use-auth";
import { SignalCard } from "../../../components/signal-card";
import { ComplianceBanner } from "../../../components/compliance-banner";
import { HouseholdStrip } from "../../../components/household-strip";
import { RationaleEditor } from "../../../components/rationale-editor";
import { CapabilityPalette } from "../../../components/capability-palette";

export default function ReferralDetailPage() {
  const params = useParams();
  const householdUri = decodeURIComponent(params.uri as string);
  const { personaClaim, userId } = useAuth();

  const { data, loading } = useQuery(REFERRAL_DETAIL_QUERY, {
    variables: { householdUri },
  });

  const [routeReferral] = useMutation(ROUTE_REFERRAL_MUTATION);
  const [draftRationale] = useMutation(DRAFT_RATIONALE_MUTATION);
  const [draftText, setDraftText] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [draftError, setDraftError] = useState("");

  const handleGenerateDraft = useCallback(async () => {
    setIsGenerating(true);
    setDraftError("");
    // Invoke referral-rationale-drafter (Bedrock) for real, grounded in THIS household's
    // actual signals (signalUris from the live query) — not a canned string. The draft is
    // probabilistic + requires review (badges in RationaleEditor); the human gates routing.
    const signalUris = (data?.wealthSignals ?? []).map((s: any) => s.uri);
    try {
      const { data: res } = await draftRationale({
        variables: { householdUri, signalUris },
      });
      const draft = res?.draftRationale;
      if (draft?.status === "success" && draft.draftNarrative) {
        setDraftText(draft.draftNarrative);
      } else {
        setDraftError(
          "The drafter couldn't generate a rationale just now. You can write one directly below.",
        );
      }
    } catch (err) {
      console.error("Draft generation failed:", err);
      setDraftError(
        "The drafter couldn't generate a rationale just now. You can write one directly below.",
      );
    } finally {
      setIsGenerating(false);
    }
  }, [data, householdUri, draftRationale]);

  const handleApprove = useCallback(
    async (approvedText: string) => {
      const signalUris = (data?.wealthSignals ?? []).map((s: any) => s.uri);
      try {
        await routeReferral({
          variables: {
            householdUri,
            signalUris,
            approvedRationale: approvedText,
            originatingBankerId: userId,
          },
        });
        alert("Referral routed successfully.");
      } catch (err) {
        console.error("Routing failed:", err);
      }
    },
    [data, householdUri, userId, routeReferral],
  );

  if (loading) {
    return <div className="p-6 text-neutral-400">Loading referral...</div>;
  }

  const household = data?.household;
  const signals = data?.wealthSignals ?? [];
  const referrals = data?.referrals ?? [];

  return (
    <div className="flex min-h-screen">
      <main className="flex-1 space-y-6 p-6">
        <header>
          <h1 className="text-2xl font-semibold">
            Referral — {household?.label || householdUri}
          </h1>
        </header>

        {/* Compliance banner — illustrative (marked "Example"): the non-tipping-off copy
            pattern is shown, but no per-entity compliance state exists to drive it
            (hasComplianceHold is undefined + never persisted; see ComplianceBanner's
            illustrative prop doc + 04a). Do NOT wire to a fabricated field. */}
        <ComplianceBanner
          hasComplianceReview={true}
          personaClaim={personaClaim}
          illustrative={true}
        />

        {/* Household context */}
        {household && (
          <section>
            <h2 className="text-lg font-semibold mb-2">Household</h2>
            <HouseholdStrip
              nodes={
                household.members?.map((m: any) => ({
                  uri: m.uri,
                  type: "atlas:Customer",
                  label: m.label,
                  relationship: "atlas:memberOf",
                })) ?? []
              }
            />
          </section>
        )}

        {/* Signals that justify the referral */}
        <section>
          <h2 className="text-lg font-semibold mb-2">Signals</h2>
          <div className="space-y-3">
            {signals.map((sig: any) => (
              <SignalCard
                key={sig.uri}
                signalType={sig.signalType}
                strength={sig.strength}
                signalDate={sig.signalDate}
                provenance={sig.provenance}
              />
            ))}
          </div>
        </section>

        {/* Rationale editor — the human-in-the-loop control */}
        <section>
          <h2 className="text-lg font-semibold mb-2">Rationale</h2>
          {draftError && (
            <p className="mb-2 text-sm text-amber-700" role="alert">{draftError}</p>
          )}
          <RationaleEditor
            initialDraft={draftText}
            isGenerating={isGenerating}
            onGenerateDraft={handleGenerateDraft}
            onApprove={handleApprove}
          />
        </section>

        {/* Existing referrals (if any) */}
        {referrals.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-2">Previous referrals</h2>
            {referrals.map((ref: any) => (
              <div
                key={ref.uri}
                className="rounded-md border border-neutral-200 p-3 text-sm"
              >
                <p>
                  <strong>Routed:</strong>{" "}
                  {new Date(ref.referralDate).toLocaleDateString()}
                </p>
                <p>
                  <strong>Outcome:</strong>{" "}
                  {ref.routingDecision?.humanReview?.reviewOutcome || "Pending"}
                </p>
              </div>
            ))}
          </section>
        )}
      </main>

      <aside className="w-72 border-l border-neutral-200 bg-neutral-50">
        <CapabilityPalette
          personaClaim={personaClaim}
          onInvoke={(name) => console.log("Invoke:", name)}
        />
      </aside>
    </div>
  );
}
