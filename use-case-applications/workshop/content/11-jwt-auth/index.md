---
title: "Module 11 — JWT Authorization"
weight: 110
---

# Module 11 — JWT Authorization

## Learning Objectives

- Explain why IAM-based auth (Phase 1) breaks when two UIs serve different personas
  from the same registry endpoint
- Trace how a Cognito-issued JWT carries `custom:persona` as a signed claim,
  making the persona claim unmodifiable by UI code
- Implement `registry_resolve_from_jwt()` and confirm that different persona claims
  in the token produce different capability sets — and that a token without a
  persona claim returns empty capabilities
- Compare IAM vs JWT authorization across five dimensions: auth method, persona
  source, trust model, per-user cost, and forgery risk

## Time Estimate

20–25 minutes.

## Prerequisites

- [Module 10 — Wealth UI](../10-wealth-ui/) complete
- Both UI fragments and capability palettes verified

## What You Will Build

A local simulation of JWT-based registry filtering: `create_sample_jwt_payload()`
produces token payloads with `custom:persona`, and `registry_resolve_from_jwt()`
filters the agent registry by that claim. The notebook does not call Cognito or
verify signatures — it demonstrates the contract that production JWT validation
enforces.

The notebook is `notebooks/phase-2-advisor/04_jwt_auth.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1 (`cell-01-terms`).
The Key Terms table defines "IAM-based auth," "JWT-based auth," "persona claim,"
"Cognito," and "fine-grained authorization."

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-2-advisor/04_jwt_auth.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains:
- Why IAM authorizes the service, not the user — and why that fails with two UIs
- How JWT moves the persona claim from a request body parameter (trusted by
  convention) into a Cognito-signed token (trusted by cryptographic verification)
- Why supporting N personas with JWT requires only N claim values in Cognito,
  not N IAM roles and N trust policies

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load agent descriptors.

Expected output:

```
Agents loaded: N
Setup complete.
```

### Step 4 — Inspect JWT token structure (cell 4)

Run cell 4 (`cell-04-jwt-structure`) to see what a Cognito-issued JWT payload
looks like. The `custom:persona` claim is the key field — in production this
value is set by Cognito based on the user's group membership and cannot be
changed by the UI code.

Expected output:

```
Consumer Banker JWT payload:
{
  "sub": "user-12345",
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_AtlasPool",
  "aud": "atlas-app-client-id",
  "exp": ...,
  "iat": ...,
  "custom:persona": "atlas-consumer-banker",
  "custom:team_id": "wealth-team-east",
  "token_use": "id"
}

...

Key difference: custom:persona claim identifies the user's role.
The registry reads this claim to filter capabilities.
```

![JWT payload comparison](/static/images/11-step-04-jwt-payload.png)

### Step 5 — Filter the registry by JWT claim (cell 5)

Run cell 5 (`cell-05-registry-filter`) to see `registry_resolve_from_jwt()` in
action. In production, AppSync extracts the claim from the `Authorization` header
and passes it to the resolver; the resolver logic is what cell 5 simulates.

Expected output:

```
Registry result for Consumer Banker JWT:
  Persona: atlas-consumer-banker
  Capabilities: [...]

Registry result for Wealth Advisor JWT:
  Persona: atlas-wealth-advisor
  Capabilities: [...]

Registry result for token without persona claim:
  {'error': 'No persona claim in token', 'capabilities': []}
```

### Step 6 — Compare IAM vs JWT (cell 6)

Run cell 6 (`cell-06-iam-vs-jwt`) to print the side-by-side comparison.

Expected output:

```
IAM vs JWT authorization comparison:
============================================================

Phase 1 (IAM):
  auth_method          IAM role assumption
  persona_source       Request body parameter
  trust_model          Trust the calling service
  per_user_cost        One IAM role per persona
  forgery_risk         UI code can claim any persona

Phase 2 (JWT):
  auth_method          Cognito JWT token
  persona_source       Signed token claim
  trust_model          Trust the identity provider
  per_user_cost        One token claim value
  forgery_risk         Claim is cryptographically signed
```

### Step 7 — Verify JWT claim structure (cell 8)

Run cell 8 (`cell-08-verify-jwt-claim`) to assert that both persona tokens
contain the correct `custom:persona` value.

Expected output:

```
Verifying JWT persona claim structure...

  [PASS] atlas-consumer-banker: custom:persona = atlas-consumer-banker
  [PASS] atlas-wealth-advisor: custom:persona = atlas-wealth-advisor

[PASS] All JWT tokens contain the correct persona claim.
```

### Step 8 — Verify registry JWT-based filtering (cell 9)

Run cell 9 (`cell-09-verify-filtering`) to assert that different persona claims
return different capability sets, and that a token without a persona claim returns
empty capabilities.

Expected output:

```
Verifying registry JWT-based filtering...

Consumer Banker capabilities: [...]
Wealth Advisor capabilities:  [...]

No-persona token capabilities: []

[PASS] Registry correctly filters by JWT persona claim.
Per-request authorization works without IAM role assumption per user.
```

## Expected Outputs

- JWT payloads for Consumer Banker and Wealth Advisor printed with `custom:persona` claims
- IAM vs JWT comparison table printed
- Registry returns different (non-empty) capability sets for different persona tokens
- Registry returns empty capabilities for a token without a persona claim
- Both verify cells print `[PASS]`

## Troubleshooting

**Cell 8 fails: custom:persona claim missing from token**

The `create_sample_jwt_payload()` function must include `"custom:persona": persona`
in the returned dict. If the key name differs (e.g., `"persona"` without the
`"custom:"` prefix), both the verify cell and the production Cognito attribute
name will not match. In Cognito, custom attributes are always prefixed with
`custom:`.

**Cell 9 fails: Consumer Banker and Wealth Advisor get identical capabilities**

`registry_resolve_from_jwt()` reads `jwt_payload.get("custom:persona")` and filters
on `discoverable_by`. If both personas return the same list, the descriptor
`discoverable_by` arrays are not correctly differentiated — return to
[Module 10 — Wealth UI](../10-wealth-ui/) and fix the descriptor files first.

**Cell 9 fails: no-persona token returns non-empty capabilities**

The function must return an error dict (or empty list) when `custom:persona` is
absent from the payload. The guard condition `if not persona: return {...}` must
execute before the filter loop. Check the function implementation in cell 5.

**Cell 4 prints "exp" as a large integer that changes each run**

The `exp` claim is `int(time.time()) + 3600` — a Unix timestamp set at run time.
The landmark shows `...` for this field. This is expected; the exact value is
irrelevant for the concept the cell teaches.

## What's Next

JWT auth ensures the persona claim travels as a cryptographically verified token.
[Module 12 — End-to-End Walkthrough](../12-end-to-end/) assembles all Phase 2
components — signal detection, rationale drafting, routing, JWT-verified advisor
notification, and conversational follow-up — into a single six-step flow that
produces a cross-UI audit trail spanning both personas.
