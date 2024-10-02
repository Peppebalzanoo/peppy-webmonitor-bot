import os
import logging
import random

from pkg_resources import file_ns_handler

from qa_db import q_and_a_dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# Per usare MARKDOWN/HTML nella formattazione
from telegram.constants import ParseMode

from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.ext import CallbackContext, CallbackQueryHandler

# Load .env variables and override system's variables
load_dotenv(override=True)

# Per loggare in console informazioni e status dell'applicazione
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def callback(update: Update, context: CallbackContext) -> None:
    option = update.callback_query.data
    match option:
        case "male":
            await update.effective_user.send_message(f"Benvenuto {update.effective_user.username}")
        case "female":
            await update.effective_user.send_message(f"Benvenuta {update.effective_user.username}")
        case "other":
            await update.effective_user.send_message(f"Benvenuto {update.effective_user.username}")

    #? Per eliminare l'option selezionata dalla funzione
    await update.callback_query.delete_message()


# Utilizziamo async per definire funzioni asincrone
# Utilizziamo await per chiamare un metodo in modo asincrono
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, let me introduce myself...\nmy name is <b>Menu Bot</b> and I am <i>bot with test menu</i>!", parse_mode=ParseMode.HTML)

    choise = [[
        InlineKeyboardButton("Male", callback_data="male"),
        InlineKeyboardButton("Female", callback_data="female"),
        InlineKeyboardButton("Other", callback_data="other")
    ]]
    choise_markup = InlineKeyboardMarkup(choise)
    await update.message.reply_text(f"Di che sesso sei?", reply_markup=choise_markup)

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    random_question = random.choice(list(q_and_a_dict.keys()))
    context.user_data["random_question"] = random_question
    await update.message.reply_text(random_question)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    curr_user_question = context.user_data.get("random_question")
    curr_user_answer = update.message.text

    # await update.message.reply_text(f"[@Bot]: Mi ricordo che alla domanda '{curr_user_question}' a cui hai risposto con '{curr_user_answer}'")

    if curr_user_question is not None:
        correct_answer = q_and_a_dict[curr_user_question]
        if curr_user_answer == correct_answer:
            await update.message.reply_text(f"Correct!")
            context.user_data.pop("random_question")
        else:
            await update.message.reply_text(f"Incorrect! Riprova!")
    else:
        await update.message.reply_text(f"Usa /question per ricevere una domanda!")

def main() -> None:

    app = Application.builder().token(os.getenv("TOKEN_API")).build()

    # Handler del comando start
    app.add_handler(CommandHandler("start", start))

    # Handeler per la funzione di callback
    app.add_handler(CallbackQueryHandler(callback))

    app.add_handler(CommandHandler("question", handle_question))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))



    # Bot in ascolto (pooling)
    app.run_polling()


if __name__ == "__main__":
    main()
