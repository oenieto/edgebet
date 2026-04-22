"""
Webhooks para integrarse con Stripe Billing y subir de Tier (free -> premium -> vip)
"""
import os
import stripe
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional

from api.db import connect

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_mock")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_mock")

router = APIRouter(prefix="/stripe", tags=["stripe"])

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None)):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
        
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event.type == 'checkout.session.completed':
        session = event.data.object
        customer_email = session.customer_details.email
        # Obtener el producto o plan para mapearlo a tier 'premium' o 'vip'
        tier = "premium" # Por defecto, en prod se extrae del item comprado
        
        if customer_email:
            with connect() as cur:
                cur.execute(
                    "UPDATE users SET tier = %s WHERE email = %s",
                    (tier, customer_email.lower())
                )
                print(f"[stripe] Usuario {customer_email} actualizado a tier {tier}")
                
    elif event.type == 'customer.subscription.deleted':
        session = event.data.object
        # Logic to extract email from customer and downgrade tier
        # we omit complete logic for brevity
        pass

    return {"status": "success"}

