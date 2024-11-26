from telegram.ext import Application, CommandHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from httpx import RequestError, HTTPStatusError, AsyncClient
from asyncio import create_task, CancelledError
from urllib.parse import urlparse, urljoin
from telegram.constants import ParseMode
from dotenv import load_dotenv
from httpx import Response
import validators
import logging
import asyncio
import os

# To log into console information and status of application
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# key: username; value: set("url1",...,"urlN")
user_url_dict = {}

# key: (username, url); value: task_id
task_dict = {}

# Load .env (environment) and override system's variables
load_dotenv(override=True)


# Retrieve environment-variables from .env
def load_token_api() -> str:
    try:
        return os.getenv("TOKEN_API")
    except ValueError:
        logging.error("Invalid TOKEN_API in .env file")
        return ""


def load_state_request_url() -> int:
    try:
        return int(os.getenv("STATE_REQUEST_URL"))
    except ValueError:
        logging.error("Invalid STATE_REQUEST_URL in .env file")
        return -1


def load_allowed_ids() -> list[int]:
    try:
        return [int(user_id) for user_id in os.getenv("ALLOWED_IDS").replace(" ", "").split(",")]
    except ValueError:
        logging.error("Invalid ALLOWED_IDS in .env file")
        return []


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"Hello <b>{update.message.from_user.username}</b>, it's a pleasure to meet you! I am @PeppyWebMonitorBot.\n" \
           "\n My purpose is to track and monitor the websites you want. " \
           "I will notify you whenever one of the websites you are following experiences a change in content.\n\n" \
           "To view a list of available commands, use /help."
    await update.message.reply_text(f"{text}", parse_mode=ParseMode.HTML)


async def show_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "\nHere is a list of available commands:\n" \
           "/start - restart the bot\n" \
           "/follow - follow a URL\n" \
           "/unfollow - unfollow a URL\n" \
           "/stop - stop tracking of all URLs\n" \
           "/cancel - cancel command\n" \
           "/list - display followed URLs\n" \
           "/help - show this list of commands\n"
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, you are in /help command!\n"
                                    f"{text}", parse_mode=ParseMode.HTML)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username
    curr_set_urls = user_url_dict.get(username, set())  # Clear all tasks for the user.

    for url in curr_set_urls:
        task: asyncio.Task = task_dict.pop((username, url))
        if task:
            # Delete the task
            task.cancel()

     # Remove user
    user_url_dict.pop(username, None)

    logging.debug(print(user_url_dict))
    logging.debug(print(task_dict))
    await update.message.reply_text("All monitoring has been stopped. You can reactivate me using /start.")


async def show_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    curr_set_urls: set = user_url_dict.get(update.message.from_user.username)
    logging.debug(curr_set_urls)
    if curr_set_urls is not None and len(curr_set_urls) > 0:
        text = ""
        for i, item in enumerate(curr_set_urls):
            text += f"{i + 1}. {item}\n"
        await update.message.reply_text(text, disable_web_page_preview=True)
    else:
        await update.message.reply_text("You are not currently following any URLs.")


async def fetch_url_content(url: str) -> str:
    try:
        async with AsyncClient(timeout=10.0) as client:
            response: Response = await client.get(url)
            response.raise_for_status()
            return response.text
    except HTTPStatusError as e:
        logging.error(f"HTTP error for {url}: {e.response.status_code}")
        return ""
    except RequestError as e:
        logging.error(f"Request error for {url}: {e}")
        return ""


async def check_for_changes(prev_content: str, curr_content: str, url: str, update: Update):
    if prev_content and curr_content and prev_content != curr_content:
        await update.message.reply_text(f"Content changed for {url}.")


async def trak_routine(update: Update, url) -> None:
    prev_content = ""
    try:
        while True:
            curr_content = await fetch_url_content(url)
            await check_for_changes(prev_content, curr_content, url, update)
            prev_content = curr_content
            await asyncio.sleep(TIME)
    except CancelledError:
        await update.message.reply_text(f"Monitoring of {url} stopped.")


async def start_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Retrieve the url from the context.
        url: str = context.user_data.get("URL")

        # If the set of urls for the user does not yet exist, create it
        curr_user_set: set = user_url_dict.get(update.message.from_user.username) or set()

        if url not in curr_user_set:
            # Add url to user's url set
            curr_user_set.add(url)

            # Map the user with the set of his urls
            user_url_dict[update.message.from_user.username] = curr_user_set
            logging.debug(print(user_url_dict))

            await update.message.reply_text("URL added successfully!")

            curr_task: asyncio.Task = create_task(trak_routine(update, url))
            logging.debug(print(curr_task))

            # Map the user to the current task
            task_dict[(update.message.from_user.username, url)] = curr_task
        else:
            await update.message.reply_text("This URL has already been added.")
    except Exception as e:
        await update.message.reply_text("An error occurred while starting the task.")
        logging.error(f"Error in start_task: {e}")


async def validate_url(update: Update, url):
    if not validators.url(url):
        logging.warning(f"Invalid URL provided by user {update.message.from_user.username}: {url}")
        return False
    return True


async def state_request_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url: str = update.message.text.replace("/follow", "").replace(" ", "")

    if len(url) <= 0:
        await update.message.reply_text("The provided URL is empty. Please enter a valid URL:")
        # Return to this state to wait for the url to follow
        return STATE_REQUEST_URL
    else:
        # Url without query string
        url: str = urljoin(url, urlparse(url).path)

        if await validate_url(update, url):

            # Save the url in context
            context.user_data["URL"] = url

            await start_task(update, context)
            return ConversationHandler.END
        else:
            await update.message.reply_text("The provided URL is invalid. Please try again or use /cancel.")
            # Return to this state to wait for the url to follow
            return STATE_REQUEST_URL


async def follow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if user_url_dict.get(update.message.from_user.username) is not None:
        logging.debug(print(f"num.tasks: {len(user_url_dict.get(update.message.from_user.username))}"))
        logging.debug(print(f"tasks: {(user_url_dict.get(update.message.from_user.username))}"))
        if len(user_url_dict.get(update.message.from_user.username)) >= MAX_TASKS_PER_USER:
            await update.message.reply_text("You have reached the maximum number of URLs being tracked.")
            return ConversationHandler.END

    await update.message.reply_text("Please enter the URL you wish to follow:")

    # Return to this state to wait for the url to follow
    return STATE_REQUEST_URL


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Your request has been canceled.")
    logging.debug(print("ConversationHandler.END"))
    return ConversationHandler.END


async def unfollow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    curr_set_urls: set = user_url_dict.get(update.message.from_user.username)
    if curr_set_urls is None or len(curr_set_urls) <= 0:
        await update.message.reply_text("You are not following any URLs.")
    else:
        choise = []
        for idx, url in enumerate(curr_set_urls):
            # If the url is larger than 64 bytes, it is too large to be printed as a button
            if len(url.encode("utf-8")) > 64:
                diff = len(url.encode("utf-8")) - 64
                url = url[:-diff]
            choise.append([InlineKeyboardButton(f"{idx + 1}. {url}", callback_data=url)])
        choise_markup = InlineKeyboardMarkup(choise)
        await update.message.reply_text(f"Please select the URL you wish to unfollow:", reply_markup=choise_markup)


async def unfollow_callback(update: Update, context: CallbackContext) -> None:
    curr_option: str = update.callback_query.data

    curr_set_urls: set = user_url_dict.get(update.effective_user.username)
    curr_set_urls.remove(curr_option)

    task_to_remove: asyncio.Task = task_dict.pop((update.effective_user.username, curr_option))

    if task_to_remove is not None:
        task_to_remove.cancel()
        await asyncio.sleep(0.3)
        logging.debug(print(f"Task for {curr_option} has been terminated! {task_to_remove.done()}"))

    # To delete the selected option from the function
    await update.callback_query.delete_message()

TIME = 60 #Seconds to check whether urls have changed
MAX_TASKS_PER_USER = 5 #Maximum number of tasks per user
ALLOWED_IDS = load_allowed_ids()
TOKEN_API = load_token_api()
STATE_REQUEST_URL = load_state_request_url()


def main() -> None:
    conv_handler = ConversationHandler(entry_points=[CommandHandler("follow", follow_command)],
                                       states={STATE_REQUEST_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, state_request_url), CommandHandler("cancel", cancel_command)], },
                                       fallbacks=[CommandHandler("start", start_command)], )

    app = Application.builder().token(TOKEN_API).build()
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start_command, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("stop", stop_command, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("follow", follow_command, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("cancel", cancel_command, filters=filters.User(ALLOWED_IDS)))

    app.add_handler(CommandHandler("unfollow", unfollow_command, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CallbackQueryHandler(unfollow_callback))

    app.add_handler(CommandHandler("list", show_list_command, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("help", show_help_command, filters=filters.User(ALLOWED_IDS)))

    app.run_polling()


if __name__ == "__main__":
    main()
