"""
Edgebet — Stripe Billing integration.

Handles:
  - checkout.session.completed → upgrade user tier
  - customer.subscription.updated → tier change (up/downgrade)
  - customer.subscription.deleted → downgrade to free
  - invoice.payment_failed → flag for retry
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header

from api.db import connect

logger = logging.getLogger("edgebet.stripe")

# Lazy import stripe to avoid crash if not installed
try:
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    HAS_STRIPE = bool(stripe.api_key and stripe.api_key != "sk_test_...")
except ImportError:
    stripe = None  # type: ignore
    HAS_STRIPE = False

ENDPOINT_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Map Stripe Price IDs → Edgebet tiers
PRICE_TIER_MAP: dict[str, str] = {
    os.getenv("STRIPE_PRICE_PRO", "price_pro"): "premium",
    os.getenv("STRIPE_PRICE_VIP", "price_vip"): "vip",
}

router = APIRouter(prefix="/stripe", tags=["stripe"])


def _resolve_tier(session_or_sub: dict) -> str:
    """Extract tier from Stripe object line items or metadata."""
    # Check metadata first (set during checkout creation)
    meta = session_or_sub.get("metadata", {}) or {}
    if meta.get("tier"):
        return meta["tier"]

    # Check line items for price ID
    items = session_or_sub.get("items", {}).get("data", [])
    if not items:
        items = session_or_sub.get("line_items", {}).get("data", [])
    for item in items:
        price_id = item.get("price", {}).get("id", "")
        if price_id in PRICE_TIER_MAP:
            return PRICE_TIER_MAP[price_id]

    return "premium"  # default if can't resolve


def _get_customer_email(customer_id: str) -> str | None:
    """Fetch email from Stripe customer object."""
    if not stripe or not HAS_STRIPE:
        return None
    try:
        customer = stripe.Customer.retrieve(customer_id)
        return customer.get("email")
    except Exception as exc:
        logger.warning("[stripe] could not fetch customer %s: %s", customer_id, exc)
        return None


def _update_user_tier(email: str, tier: str) -> bool:
    """Update user tier in database. Returns True if a row was updated."""
    try:
        with connect() as cur:
            cur.execute(
                "UPDATE users SET tier = %s WHERE email = %s",
                (tier, email.lower()),
            )
            updated = cur.rowcount > 0
            if updated:
                logger.info("[stripe] %s -> tier=%s", email, tier)
            else:
                logger.warning("[stripe] email %s not found in users table", email)
            return updated
    except Exception as exc:
        logger.error("[stripe] DB error updating tier: %s", exc)
        return False


@router.get("/status")
def stripe_status() -> dict:
    """Check if Stripe is configured."""
    return {
        "configured": HAS_STRIPE,
        "webhook_secret_set": bool(ENDPOINT_SECRET),
        "price_map": {v: k[:12] + "..." for k, v in PRICE_TIER_MAP.items()},
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    if not stripe:
        raise HTTPException(status_code=503, detail="Stripe not installed")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, ENDPOINT_SECRET,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    data_obj = event.get("data", {}).get("object", {})
    logger.info("[stripe] event: %s", event_type)

    if event_type == "checkout.session.completed":
        email = (data_obj.get("customer_details") or {}).get("email")
        if not email:
            email = _get_customer_email(data_obj.get("customer", ""))
        tier = _resolve_tier(data_obj)
        if email:
            _update_user_tier(email, tier)

    elif event_type == "customer.subscription.updated":
        # Tier change (upgrade or downgrade mid-cycle)
        customer_id = data_obj.get("customer", "")
        email = _get_customer_email(customer_id)
        tier = _resolve_tier(data_obj)
        if email:
            _update_user_tier(email, tier)

    elif event_type == "customer.subscription.deleted":
        # Cancellation → downgrade to free
        customer_id = data_obj.get("customer", "")
        email = _get_customer_email(customer_id)
        if email:
            _update_user_tier(email, "free")

    elif event_type == "invoice.payment_failed":
        customer_id = data_obj.get("customer", "")
        email = _get_customer_email(customer_id)
        logger.warning("[stripe] payment failed for %s (%s)", email, customer_id)
        # Don't downgrade immediately — Stripe retries. Only downgrade on subscription.deleted.

    return {"status": "received", "type": event_type}

