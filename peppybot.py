from telegram.ext import Application, CommandHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler
from telegram.constants import ParseMode
from asyncio import create_task
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import validators
import logging
import asyncio
import httpx
import os

# username : set("url1",...,"urlN")
user_list_dict = {}
STATE_REQUEST_URL = 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, nice to meet you, I'm @PeppyWebMonitorBot. \n"
                                    f"\nMy job is to follow and monitor the websites you want. "
                                    f"I will notify you whenever one of your websites has undergone a change in content.\n\n"
                                    f"For the list of commands use /help", parse_mode=ParseMode.HTML)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "\nHere\'s the list of my commands:\n" \
           "/start - restrat the bot\n" \
           "/follow - follow url\n" \
           "/unfollow - unfollow url\n" \
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
    await shower(update, context)

async def validate_url(update: Update, url):
    if validators.url(url):
        return True
    else:
        return False


async def trak_routine(update: Update, url) -> None:
    prev_content = None
    while True:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            curr_content = response.text
            if prev_content is not None:
                if prev_content != curr_content:
                    print(f"Content has changed for {url}")
                    await update.message.reply_text(f"Hi, some content has changed for {url}")
                else:
                    print(f"Content not changed for {url}")
            prev_content = curr_content
            # Wait for the specified interval before the next check
            await asyncio.sleep(60 * 60)  #1 hour


async def state_request_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = update.message.text.replace("/follow", "").replace(" ", "")

    if len(url) <= 0:
        await update.message.reply_text("Sorry, URL is empty! Please enter a valid URL:")
        return STATE_REQUEST_URL  #? Rimango in questo stato per attendere l'url da seguire

    if await validate_url(update, url):
        context.user_data["URL"] = url  #? Salvo l'url nel contesto
        await insert_url_routine(update, context)
        return ConversationHandler.END  #? Se l'url è stato aggiunto o meno, chiudiamo la conversazione
    else:
        await update.message.reply_text("The URL is invalid, please try again:")
        return STATE_REQUEST_URL  #? Rimango in questo stato per attendere l'url da seguire


async def insert_url_routine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = context.user_data.get("URL")  #? Recupero l'url dal contesto
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


async def follow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Enter the URL to follow:")
    return STATE_REQUEST_URL  #? Passo in questo stato per attendere l'url da seguire


async def unfollow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    curr_list_url = user_list_dict.get(update.message.from_user.username)
    choise = [[InlineKeyboardButton(f"{idx + 1}. {url}", callback_data=url)] for idx, url in enumerate(curr_list_url)]
    choise_markup = InlineKeyboardMarkup(choise)
    await update.message.reply_text(f"Select the URL to unfollow:", reply_markup=choise_markup)


async def callback(update: Update, context: CallbackContext) -> None:
    option = update.callback_query.data

    curr_list_url = user_list_dict.get(update.effective_user.username)
    curr_list_url.remove(option)

    # Per eliminare l'option selezionata dalla funzione
    await update.callback_query.delete_message()

    await update.effective_user.send_message("Done, url removed correctly!")


def main() -> None:
    # Per loggare in console informazioni e status dell'applicazione
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

    # Load .env (environment) and override system's variables
    load_dotenv(override=True)

    # Recupero environment-variables from .env
    TOKEN_API = os.getenv("TOKEN_API")
    ALLOWED_IDS = [int(user_id) for user_id in os.getenv("ALLOWED_IDS").replace(" ", "").split(",")]

    conv_handler = ConversationHandler(entry_points=[CommandHandler("follow", follow)],
                                       states={STATE_REQUEST_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, state_request_url)], },
                                       fallbacks=[CommandHandler("start", start)], )

    app = Application.builder().token(TOKEN_API).build()
    app.add_handler(conv_handler)

    app.add_handler(CommandHandler("start", start, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("follow", follow, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("unfollow", unfollow, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(CommandHandler("list", show_list, filters=filters.User(ALLOWED_IDS)))
    app.add_handler(CommandHandler("help", show_help, filters=filters.User(ALLOWED_IDS)))

    app.run_polling()


if __name__ == "__main__":
    main()
