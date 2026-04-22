"""
Telegram Bot Wrapper for Edgebet.
Ejecutar standalone: python python/telegram_bot.py
"""
import os
import asyncio
from telegram import Bot
from api.db import connect

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "mock-token")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "mock-id")

async def send_vip_alert(pick_match: str, prediction: str, odds: float, confidence: int):
    bot = Bot(token=TOKEN)
    message = (
        f"👑 *ALERTA VIP EDGEBET* 👑\n\n"
        f"⚽ {pick_match}\n"
        f"📊 Pick: *{prediction}*\n"
        f"📈 Cuota: {odds}\n"
        f"🔥 Confianza: {confidence}%\n\n"
        f"Ingresa a edgebet.app para ver el análisis Claude detallado y la distribución de stake recomendada."
    )
    
    # En producción buscar usuarios VIP activos con telegram vinculado
    with connect() as cur:
        # mock retrieval
        pass
        
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=message, parse_mode='Markdown')
        print(f"[telegram] Alerta VIP enviada para {pick_match}")
    except Exception as e:
        print(f"[telegram] Error enviando alerta: {e}")

if __name__ == "__main__":
    print("Edgebet Telegram Bot service started...")
    # asyncio.run(send_vip_alert("Arsenal vs Chelsea", "Arsenal Gana", 2.10, 85))
