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

# username : set("url1",...,"urlN")
user_list_dict = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, nice to meet you, I'm @PeppyWebMonitorBot. \n"
                                    f"\nMy job is to follow and monitor the websites you want. "
                                    f"I will notify you whenever one of your websites has undergone a change in content.\n\n"
                                    f"For the list of commands use /help", parse_mode=ParseMode.HTML)


async def foo(update, value, time, string):
    await update.message.reply_text(f"task{value}: " + string)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "\nHere\'s the list of my commands:\n" \
           "/start - strat the bot\n" \
           "/follow {url} - follow url\n" \
           "/list - see followed url\n" \
           "/help - see list of commands \n"
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, you are in /help command!\n"
                                    f"{text}", parse_mode=ParseMode.HTML)


async def shower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    curr_list_url = user_list_dict.get(update.message.from_user.username)
    if curr_list_url is not None and len(curr_list_url) > 0:
        text = ""
        for i, item in enumerate(curr_list_url):
            text += f"{i + 1}. {item}\n"
        await update.message.reply_text(text, disable_web_page_preview=True)
    else:
        await update.message.reply_text("You don't follow any url!")


async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, you are in /list command!", parse_mode=ParseMode.HTML)
    create_task(shower(update, context))


async def validate_url(update: Update, url):
    if len(url) <= 0:
        await update.message.reply_text("Sorry, url is empty!")
    else:
        if validators.url(url):
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
                    logging.debug(f"Content has changed for {url}")
                    await update.message.reply_text(f"Hi, some content has changed for {url}")
                else:
                    logging.debug(f"Content not changed for {url}")
            prev_content = curr_content
            # Wait for the specified interval before the next check
            await asyncio.sleep(60 * 60) #? 1 hour
    except Exception as exc:
        logging.warning("An exception occurred:", exc)
    finally:
        await client.aclose()


async def follow(update, context) -> None:
    url = update.message.text.replace("/follow", "").replace(" ", "")
    is_valid = await validate_url(update, url)

    if is_valid:
        curr_user_set = user_list_dict.get(update.message.from_user.username)
        if curr_user_set is None:
            curr_user_set = set()

        if url not in curr_user_set:
            curr_user_set.add(url)
            await update.message.reply_text("Done, url added correctly!")

            user_list_dict[update.message.from_user.username] = curr_user_set
            logging.debug(print(user_list_dict))

            create_task(trak_routine(update, url))
        else:
            await update.message.reply_text("Sorry, url already added!")


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
    app.add_handler(CommandHandler("follow", follow, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("list", show_list, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("help", show_help, filters=filters.User(ALLOWED_IDS)))
    app.run_polling()


if __name__ == "__main__":
    main()
