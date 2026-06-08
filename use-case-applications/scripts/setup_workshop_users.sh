#!/usr/bin/env bash
# Set up the two named workshop protagonists in the Cognito user pool, and remove any
# other users. These are the identities a workshop attendee logs in as. This pool uses
# EMAIL as the username (UsernameAttributes:[email]), so the login id is an email; the
# human display name is carried by the `name` attribute.
#
#   dana.brooks@atlas.demo   — Dana Brooks   — atlas-consumer-banker (Wholesale UI)
#   marcus.webb@atlas.demo   — Marcus Webb   — atlas-wealth-advisor  (Wealth UI)
#
# STAFF names are deliberately DISTINCT from CUSTOMER names. "Rachel Kim" is a CUSTOMER in
# the graph (the referral-subject, customer-c6b6e4ad…) — so the consumer banker is NOT
# Rachel; she is Dana Brooks. Marcus Webb is the wealth advisor a routed referral lands
# with. No staff/customer name collisions.
#
# Both use the workshop password "password123". The `name` attribute carries the human
# display name that flows to the app bar (the ID token's OIDC `name` claim). The persona
# comes from group membership (cognito:groups), which the AppSync resolver reads for
# Lake Formation scoping.
#
# Idempotent: re-running resets passwords/attributes and re-asserts group membership.
#
# Usage:  POOL_ID=us-east-1_xxxx ./setup_workshop_users.sh
set -euo pipefail

POOL_ID="${POOL_ID:-us-east-1_ByfAyZSdj}"
PASSWORD="${WORKSHOP_PASSWORD:-password123}"

# Tracks the ACTUAL usernames Cognito assigns. In an email-as-username pool the stored
# Username is an opaque sub UUID (the email is only the sign-in alias), so we must keep
# the real Username — not the email — when pruning, or we delete what we just created.
KEEP_USERNAMES=""

create_user () {
  local email="$1" name="$2" group="$3"
  echo "── $email ($name, $group)"
  aws cognito-idp admin-create-user \
    --user-pool-id "$POOL_ID" --username "$email" \
    --user-attributes Name=name,Value="$name" Name=email,Value="$email" \
                      Name=email_verified,Value=true "Name=custom:persona,Value=$group" \
    --message-action SUPPRESS >/dev/null 2>&1 || echo "   (exists — updating)"
  # Ensure attributes are current even if the user already existed.
  aws cognito-idp admin-update-user-attributes \
    --user-pool-id "$POOL_ID" --username "$email" \
    --user-attributes Name=name,Value="$name" Name=email,Value="$email" \
                      Name=email_verified,Value=true "Name=custom:persona,Value=$group" >/dev/null
  # Permanent password (no force-change prompt).
  aws cognito-idp admin-set-user-password \
    --user-pool-id "$POOL_ID" --username "$email" --password "$PASSWORD" --permanent >/dev/null
  # Group membership (the persona the resolver scopes on).
  aws cognito-idp admin-add-user-to-group \
    --user-pool-id "$POOL_ID" --username "$email" --group-name "$group" >/dev/null
  # Resolve and record the actual stored Username (the sub) for the keep-list.
  local sub
  sub="$(aws cognito-idp admin-get-user --user-pool-id "$POOL_ID" --username "$email" \
         --query "Username" --output text)"
  KEEP_USERNAMES="$KEEP_USERNAMES $sub"
  echo "   ready (username=$sub)"
}

BANKER="dana.brooks@atlas.demo"
ADVISOR="marcus.webb@atlas.demo"

echo "Pool: $POOL_ID"
create_user "$BANKER"  "Dana Brooks"  "atlas-consumer-banker"
create_user "$ADVISOR" "Marcus Webb"  "atlas-wealth-advisor"

echo ""
echo "── removing any OTHER users (keeping only Dana + Marcus)"
for u in $(aws cognito-idp list-users --user-pool-id "$POOL_ID" --query "Users[].Username" --output text); do
  case " $KEEP_USERNAMES " in
    *" $u "*) : ;;  # keep — one of the two we just created
    *) echo "   deleting $u"; aws cognito-idp admin-delete-user --user-pool-id "$POOL_ID" --username "$u" >/dev/null ;;
  esac
done

echo ""
echo "Done. Workshop logins (password: $PASSWORD):"
echo "  Wholesale UI → $BANKER   (Dana Brooks · Consumer Banker)"
echo "  Wealth UI    → $ADVISOR   (Marcus Webb · Wealth Advisor)"
