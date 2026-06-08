/**
 * Referral Detail page.
 *
 * Shows the signals that triggered a referral, the drafted rationale
 * (editable if pending), the routing decision, and the audit trail.
 * This is where the human-in-the-loop pattern is most visible — the
 * rationale is drafted by an agent and gated by the banker's approval.
 */

"use client";

import React, { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation } from "@apollo/client";
import { REFERRAL_DETAIL_QUERY } from "../../../graphql/queries";
import { ROUTE_REFERRAL_MUTATION, DRAFT_RATIONALE_MUTATION } from "../../../graphql/mutations";
import { useAuth } from "../../../../../shared/auth/use-auth";
import { AppShell } from "../../../../../shared/ui/chrome";
import { SignalCard } from "../../../components/signal-card";
import { ComplianceBanner } from "../../../components/compliance-banner";
import { HouseholdStrip } from "../../../components/household-strip";
import { RationaleEditor } from "../../../components/rationale-editor";
import { CapabilityPalette } from "../../../components/capability-palette";

const NAV = [{ href: "/", label: "My book" }];

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
    return (
      <AppShell brandSuffix="Wholesale" navLinks={NAV}>
        <p className="loading-line">Loading referral…</p>
      </AppShell>
    );
  }

  const household = data?.household;
  const signals = data?.wealthSignals ?? [];
  const referrals = data?.referrals ?? [];
  const memberNodes =
    household?.members?.map((m: any) => ({
      uri: m.uri,
      type: "atlas:Customer",
      label: m.label,
      relationship: "atlas:memberOf",
    })) ?? [];

  return (
    <AppShell brandSuffix="Wholesale" navLinks={NAV}>
      <div className="shell">
        <div className="shell-main">
          {/* Compliance banner — illustrative (marked "Example"): the non-tipping-off copy
              pattern is shown, but no per-entity compliance state exists to drive it
              (hasComplianceHold is undefined + never persisted; see ComplianceBanner's
              illustrative prop doc + 04a). Do NOT wire to a fabricated field. */}
          <ComplianceBanner hasComplianceReview={true} personaClaim={personaClaim} illustrative={true} />

          {/* Household header + route action */}
          <div className="card">
            <div className="head">
              <div className="av">RK</div>
              <div className="grow">
                <div className="title-row">
                  <span className="name">{household?.label || householdUri}</span>
                  <span className="chip">fibo:Household</span>
                </div>
                <p className="sub">
                  Referred from Consumer Banking · {signals.length} wealth-readiness signal
                  {signals.length === 1 ? "" : "s"} derived
                </p>
              </div>
            </div>

            {memberNodes.length > 0 && (
              <div className="relstrip">
                <div className="rel-lab">Household relationship · members &amp; accounts (real graph)</div>
                <HouseholdStrip nodes={memberNodes} />
              </div>
            )}
          </div>

          {/* Signals + capability cards */}
          <div className="card">
            <div className="card-h">
              <span className="t">Wealth-readiness signals</span>
              <span className="meta">
                <span className="lab-live">live</span> derived · SHACL
              </span>
            </div>
            {signals.length > 0 ? (
              <>
                {signals.map((sig: any) => (
                  <SignalCard
                    key={sig.uri}
                    signalType={sig.signalType}
                    signalDate={sig.signalDate}
                    provenance={sig.provenance}
                  />
                ))}
                <p className="card-note">
                  Signals are derived from confirmed enterprise data. Signal strength is not
                  shown — it is not a derived value, so it is not rendered.
                </p>
              </>
            ) : (
              <p className="empty">No signals derived for this household yet.</p>
            )}
          </div>

          {/* Rationale editor — the human-in-the-loop control */}
          <div className="card">
            <div className="card-h">
              <span className="t">Referral rationale</span>
              <span className="meta">
                <span className="lab-live">live</span> referral-rationale-drafter
              </span>
            </div>
            {draftError && (
              <p className="card-note" role="alert" style={{ color: "var(--rust-ink)" }}>
                {draftError}
              </p>
            )}
            <RationaleEditor
              initialDraft={draftText}
              isGenerating={isGenerating}
              onGenerateDraft={handleGenerateDraft}
              onApprove={handleApprove}
            />
          </div>

          {/* Existing referrals (if any) */}
          {referrals.length > 0 && (
            <div className="card">
              <div className="card-h">
                <span className="t">Previous referrals</span>
                <span className="meta">PROV-O · routing &amp; review events</span>
              </div>
              <div className="audit">
                {referrals.map((ref: any) => (
                  <div key={ref.uri}>
                    <span className="ts">{new Date(ref.referralDate).toLocaleDateString()}</span>{" "}
                    routed · outcome ·{" "}
                    <span className="id">
                      {ref.routingDecision?.humanReview?.reviewOutcome || "pending"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Roadmap — explicitly NOT live */}
          <div className="future-band">
            <div className="future-h">
              <svg className="i" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--future)" strokeWidth="1.7">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
              <span className="lab">Possible next</span>
              <span className="note">roadmap — not shown as live</span>
            </div>
            <p className="future-body">
              <b>Real per-entity compliance state</b> (drive the banner from a persisted
              compliance-review field — needs compliance data) · <b>click-to-invoke palette</b>{" "}
              (the action side beyond the wired draft/route/ask — deferred-buildable).
            </p>
          </div>
        </div>

        <CapabilityPalette
          personaClaim={personaClaim}
          onInvoke={(name) => console.log("Invoke:", name)}
        />
      </div>
    </AppShell>
  );
}
