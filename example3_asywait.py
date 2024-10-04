import asyncio
import os
import logging
from asyncio import create_task
from dotenv import load_dotenv
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, filters, ContextTypes
from telegram import Update

async def foo(update, value, time, string):
    await asyncio.sleep(time)
    await update.message.reply_text(f"task{value}: " + string)

async def routine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi {update.message.from_user.username}, you are in <b>routine()!</b>!", parse_mode=ParseMode.HTML)
    task1 = create_task(foo(update, 1, 10, "Ciao Mondo!"))
    task2 = create_task(foo(update, 2, 3,"Hello World!"))
    await task1
    await task2


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi {update.message.from_user.username}, the bot is <b>started()</b>!", parse_mode=ParseMode.HTML)


async def fetch_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def routine2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    urls = ["https://example.com", "https://python.org", "https://google.com"]
    tasks = [fetch_url(url) for url in urls]
    results = await asyncio.gather(*tasks)
    for url, content in zip(urls, results):
        print(f"Fetched {len(content)} bytes from {url}")
        await update.message.reply_text(f"Hi {update.message.from_user.username}, fetched <b>{len(content)}</b> bytes from {url}!", parse_mode=ParseMode.HTML)



def main() -> None:
    # Per loggare in console informazioni e status dell'applicazione
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

    # Load .env (environment) and override system's variables
    load_dotenv(override=True)

    # Recupero environment-variables from .env
    TOKEN_API = os.getenv("TOKEN_API")
    ALLOWED_IDS = [int(user_id) for user_id in os.getenv("ALLOWED_IDS").replace(" ", "").split(",")]

    app = Application.builder().token(TOKEN_API).build()
    app.add_handler(CommandHandler("start", start, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("routine", routine, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("routine2", routine2, filters=filters.User(ALLOWED_IDS)))
    app.run_polling()


if __name__ == "__main__":
    main()
