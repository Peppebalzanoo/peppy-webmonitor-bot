from telegram.ext import Application, CommandHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from asyncio import create_task, CancelledError
from urllib.parse import urlparse, urljoin
from telegram.constants import ParseMode
from dotenv import load_dotenv
import validators
import logging
import asyncio
import httpx
import os

# Per loggare in console informazioni e status dell'applicazione
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# key: username, value: set("url1",...,"urlN")
user_url_dict = {}
# key: (username, url), value: task_id
task_dict = {}

# Load .env (environment) and override system's variables
load_dotenv(override=True)
# Recupero environment-variables from .env
TOKEN_API = os.getenv("TOKEN_API")
STATE_REQUEST_URL = int(os.getenv("STATE_REQUEST_URL"))
ALLOWED_IDS = [int(user_id) for user_id in os.getenv("ALLOWED_IDS").replace(" ", "").split(",")]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Hello <b>{update.message.from_user.username}</b>, it's a pleasure to meet you! I am @PeppyWebMonitorBot.\n" \
           "\n My purpose is to track and monitor the websites you want. " \
           "I will notify you whenever one of the websites you are following experiences a change in content.\n\n" \
           "To view a list of available commands, use /help."
    await update.message.reply_text(f"{text}", parse_mode=ParseMode.HTML)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "\nHere is a list of available commands:\n" \
           "/start - restart the bot\n" \
           "/follow - follow a URL\n" \
           "/unfollow - unfollow a URL\n" \
           "/list - display followed URLs\n" \
           "/help - show this list of commands\n"
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, you are in /help command!\n"
                                    f"{text}", parse_mode=ParseMode.HTML)

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    curr_list_url = user_url_dict.get(update.message.from_user.username)
    logging.debug(print(curr_list_url))
    if curr_list_url is not None and len(curr_list_url) > 0:
        text = ""
        for i, item in enumerate(curr_list_url):
            text += f"{i + 1}. {item}\n"
        await update.message.reply_text(text, disable_web_page_preview=True)
    else:
      await update.message.reply_text("You are not currently following any URLs.")


async def trak_routine(update: Update, url) -> None:
    prev_content = None
    try:
        while True:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                curr_content = response.text
                if prev_content is not None:
                    if prev_content != curr_content:
                        logging.debug(print(f"Content has changed for {url}"))
                        await update.message.reply_text(f"Hello, there has been a change in the content of {url}.")
                    else:
                        logging.debug(print(f"Content has not changed for {url}"))
                prev_content = curr_content
                # Wait for the specified interval before the next check
                await asyncio.sleep(60)  #60 * 60 = 1 hour
    except CancelledError:
        await update.message.reply_text(f"Monitoring of {url} has been successfully stopped.", disable_web_page_preview=True)


async def strat_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = context.user_data.get("URL")  # Recupero l'url dal contesto
    curr_user_set = user_url_dict.get(update.message.from_user.username)

    if curr_user_set is None:
        curr_user_set = set()

    if url not in curr_user_set:
        curr_user_set.add(url)
        await update.message.reply_text("URL added successfully!")
        user_url_dict[update.message.from_user.username] = curr_user_set

        logging.debug(print(user_url_dict))
        curr_task = create_task(trak_routine(update, url))
        logging.debug(print(curr_task))
        task_dict[(update.message.from_user.username, url)] = curr_task
    else:
        await update.message.reply_text("This URL has already been added.")


async def validate_url(update: Update, url):
    if validators.url(url):
        return True
    else:
        return False


async def state_request_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = update.message.text.replace("/follow", "").replace(" ", "")

    if len(url) <= 0:
        await update.message.reply_text("The provided URL is empty. Please enter a valid URL:")
        return STATE_REQUEST_URL  #? Rimango in questo stato per attendere l'url da seguire

    # Url without query string
    url = urljoin(url, urlparse(url).path)

    if await validate_url(update, url):
        context.user_data["URL"] = url  #? Salvo l'url nel contesto
        await strat_task(update, context)
        return ConversationHandler.END  #? Se l'url è stato aggiunto o meno, chiudiamo la conversazione
    else:
        await update.message.reply_text("The provided URL is invalid. Please try again or use /cancel.")
        return STATE_REQUEST_URL  #? Rimango in questo stato per attendere l'url da seguire


async def follow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please enter the URL you wish to follow:")
    return STATE_REQUEST_URL  #? Passo in questo stato per attendere l'url da seguire


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Your request has been canceled.")
    logging.debug(print("ConversationHandler.END"))
    return ConversationHandler.END


async def unfollow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    curr_list_url = user_url_dict.get(update.message.from_user.username)
    if curr_list_url is None:
       await update.message.reply_text("You are not following any URLs.")
    else:
        choise = []
        for idx, url in enumerate(curr_list_url):
            choise.append([InlineKeyboardButton(f"{idx + 1}. {url}", callback_data=url)])
        choise_markup = InlineKeyboardMarkup(choise)
        await update.message.reply_text(f"Please select the URL you wish to unfollow:", reply_markup=choise_markup)


async def unfollow_callback(update: Update, context: CallbackContext) -> None:
    option = update.callback_query.data

    curr_list_url = user_url_dict.get(update.effective_user.username)
    curr_list_url.remove(option)

    task_to_remove = task_dict.pop((update.effective_user.username, option), None)

    if task_to_remove is not None and isinstance(task_to_remove, asyncio.Task):
        task_to_remove.cancel()
        await asyncio.sleep(0.1)
        logging.debug(print(f"Task for {option} has been terminated! {task_to_remove.done()}"))

    # Per eliminare l'option selezionata dalla funzione
    await update.callback_query.delete_message()


def main() -> None:
    conv_handler = ConversationHandler(entry_points=[CommandHandler("follow", follow)],
                                       states={
                                            STATE_REQUEST_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, state_request_url),
                                                                CommandHandler("cancel", cancel)],
                                       },
                                       fallbacks=[CommandHandler("start", start)], )

    app = Application.builder().token(TOKEN_API).build()
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("follow", follow, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("cancel", cancel, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("unfollow", unfollow, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CallbackQueryHandler(unfollow_callback))
    app.add_handler(CommandHandler("list", show_list, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("help", show_help, filters=filters.User(ALLOWED_IDS)))

    app.run_polling()


if __name__ == "__main__":
    main()
