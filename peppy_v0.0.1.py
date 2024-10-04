from telegram.ext import Application, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode
from asyncio import create_task
from dotenv import load_dotenv
from telegram import Update
import validators
import logging
import asyncio
import httpx
import os


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, the bot is started!", parse_mode=ParseMode.HTML)


async def foo(update, value, time, string):
    await update.message.reply_text(f"task{value}: " + string)


async def foo_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, you are in /new command!", parse_mode=ParseMode.HTML)
    create_task(foo(update, 1, 6, "Hello World!"))


async def validate_url(update: Update, url):
    if len(url) <= 0:
        await update.message.reply_text("Sorry, url is empty!")
        return False
    else:
        if validators.url(url):
            await update.message.reply_text("Done, url added correctly!")
            return True
        else:
            await update.message.reply_text("Sorry, url is invalid!")
            return False


async def trak_routine(update, url) -> None:
    client = httpx.AsyncClient()
    try:
        prev_content = None
        while True:
            response = await client.get(url)
            curr_content = response.text
            if prev_content is not None:
                if prev_content != curr_content:
                    logging.info(f"Content has changed for {url}")
                    await update.message.reply_text(f"Hi, some content has changed for {url}")
                else:
                    logging.info(f"Content not changed for {url}")
            prev_content = curr_content
            # Wait for the specified interval before the next check
            await asyncio.sleep(60)
    except Exception as exc:
        logging.warning("An exception occurred:", exc)
    finally:
        await client.aclose()


async def add(update, context) -> None:
    url = update.message.text.replace("/add", "").replace(" ", "")
    is_valid = await validate_url(update, url)
    if is_valid:
        create_task(trak_routine(update, url))


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
    app.add_handler(CommandHandler("new", foo_task, filters=filters.User(ALLOWED_IDS)))
    app.run_polling()


if __name__ == "__main__":
    main()
