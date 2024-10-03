import asyncio
import difflib
import os
import logging
from asyncio import create_task
import httpx
import validators
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, filters, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, the bot is started!", parse_mode=ParseMode.HTML)


async def foo(update, value, time, string):
    await update.message.reply_text(f"task{value}: " + string)


async def create_new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, you are in new command!", parse_mode=ParseMode.HTML)
    create_task(foo(update, 1, 6, "Hello World!"))


async def validate_url(update, url):
    if len(url) <= 0:
        await update.message.reply_text("Sorry, url is empty!")
    else:
        if validators.url(url):
            await update.message.reply_text("Done, url added correctly!")
        else:
            await update.message.reply_text("Sorry, url is invalid!")


async def routine(update, url) -> None:
    prev_content = None
    while True:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            curr_content = response.text
            if prev_content is not None:
                if prev_content != curr_content:
                    print("Content has changed!")
                    await update.message.reply_text("Hi, some content has changed!")
                else:
                    print("Content not changed!")
            prev_content = curr_content
        # Wait for the specified interval before the next check
        await asyncio.sleep(60)


async def add(update, context) -> None:
    url = update.message.text.replace("/add", "").replace(" ", "")
    await validate_url(update, url)
    create_task(routine(update, url))


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
    app.add_handler(CommandHandler("add", add, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("new", create_new_task, filters=filters.User(ALLOWED_IDS)))
    app.run_polling()


if __name__ == "__main__":
    main()
