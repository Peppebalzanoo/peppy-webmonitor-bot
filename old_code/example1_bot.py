import os
import logging
from telegram import Update
from dotenv import load_dotenv
#? Per usare MARKDOWN/HTML nella formattazione
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

#? Load .env variables and override system's variables
load_dotenv(override=True)

#? Per loggare in console informazioni e status dell'applicazione
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

#? Utilizziamo async per definire funzioni asincrone
#? Utilizziamo await per chiamare un metodo in modo asincrono
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, let me introduce myself...\nmy name is <b>Peppy</b> and I am <i>website monitoring bot</i>!", parse_mode=ParseMode.HTML)


# async def handle_message_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     print("handle_message_all()")
#     await update.message.reply_text(f"Thanks {update.message.from_user.username} for writing me!")
#     with open(f"chats_log/{update.message.chat_id}_{update.message.from_user.username}.log", "a") as file:
#         file.write(f"[Bot]: {None}\n")
#         file.write(f"[{update.message.from_user.username}]: {update.message.text}\n")

async def handle_message_regex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("handle_message_regex()")
    msg = f"Grazie {update.message.from_user.username} per avermi scritto! Ti saluto volentieri!"
    await update.message.reply_text(msg)
    with open(f"chats_log/{update.message.chat_id}_{update.message.from_user.username}.log", "a") as file:
        file.write(f"[@Bot]: {msg}\n[@{update.message.from_user.username}]: {update.message.text}\n\n")

def main() -> None:

    app = Application.builder().token(os.getenv("TOKEN_API")).build()

    #? Handler del comando start
    app.add_handler(CommandHandler("start", start))

    #? Handler dei messaggi in chat: filters.ALL per attivare su tutto
    # app.add_handler(MessageHandler(filters.ALL, handle_message_all))

    #? Handler dei messaggi in chat: filters.Regex per attivare sulle Regex
    #? Case-Insensitive: (?i)
    app.add_handler(MessageHandler(filters.Regex(r"(?i)saluto"), handle_message_regex))

    #? Bot in ascolto (pooling)
    app.run_polling()


if __name__ == "__main__":
    main()
