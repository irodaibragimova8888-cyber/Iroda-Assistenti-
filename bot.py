import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from openai import AsyncOpenAI
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
AI_API_KEY = os.environ["AI_API_KEY"]
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.groq.com/openai/v1")
AI_MODEL = os.environ.get("AI_MODEL", "llama-3.3-70b-versatile")
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "Sen foydali yordamchisan. Foydalanuvchi qaysi tilda yozsa, shu tilda javob ber.",
)
MAX_HISTORY = 10

client = AsyncOpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti")

    def log_message(self, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Savolingizni yozing.\nSuhbatni tozalash uchun: /reset"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    await update.message.reply_text("Suhbat tozalandi.")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    history = context.user_data.setdefault("history", [])
    history.append({"role": "user", "content": user_text})
    history[:] = history[-MAX_HISTORY:]

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
        )
        answer = response.choices[0].message.content or "Javob bo'sh keldi."
    except Exception as e:
        logger.error("AI xatosi: %s", e)
        await update.message.reply_text("Xatolik yuz berdi. Keyinroq qayta urinib ko'ring.")
        history.pop()
        return

    history.append({"role": "assistant", "content": answer})

    for i in range(0, len(answer), 4000):
        await update.message.reply_text(answer[i : i + 4000])


def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("Bot ishga tushdi")
    app.run_polling()


if __name__ == "__main__":
    main()
