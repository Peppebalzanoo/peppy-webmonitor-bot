import os
import asyncio
import requests
import validators
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, ContextTypes

#? Per loggare in console informazioni e status dell'applicazione
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

#? Load .env variables and override system's variables
load_dotenv(override=True)


def is_valid_url(url):
    return validators.url(url)


async def validation_url(update, url):
    if len(url) <= 0:
        await update.message.reply_text("Sorry, empty URL was passed!")
    else:
        validation = is_valid_url(url)
        if validation:
            await update.message.reply_text("Ok, added!")
        else:
            await update.message.reply_text("Sorry, invalid URL was passed!")


async def start(update, context):
    print("Starting bot...")
    await update.message.reply_text("Hi, I'm Peppy WebMonitor Bot!")
    print("Starting done!")


async def routine(update, url):
    while True:
        # Make the HTTP request to the website
        response = requests.get(url)
        if os.path.isfile("content.txt"):
            with open("content.txt", "r", encoding="utf-8") as file:
                previous_content = file.read()
                if response.text != previous_content:
                    print("Website content has changed!")
                    await update.message.reply_text("Hi, website content has changed!")
                else:
                    print("Website content not changed!")

            with open("content.txt", "w", encoding="utf-8") as file:
                # Update the saved content
                file.write(response.text)

        # Wait for the specified interval before the next check
        await asyncio.sleep(60)


async def add(update, context):
    url = update.message.text.replace("/add", "").replace(" ", "")
    print(url)
    await validation_url(update, url)
    await routine(update, url)


app = Application.builder().token(os.getenv("TOKEN_API")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.run_polling()
