from telegram.ext import Application, CommandHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from httpx import RequestError, HTTPStatusError, AsyncClient, Response
from urllib.parse import urlparse, urljoin
import validators
import logging
import asyncio
import os
from dotenv import load_dotenv
from database import Database


class WebMonitoringBot:
    def __init__(self):
        # Load .env (environment) and override system's variables
        load_dotenv(override=True)

        # Retrieve environment-variables from .env
        self.TOKEN_API = self.load_token_api()
        self.STATE_REQUEST_URL = self.load_state_request_url()
        self.ALLOWED_IDS = self.load_allowed_ids()
        self.TIME = 60  # Seconds to check whether URLs have changed
        self.MAX_TASKS_PER_USER = 5  # Maximum number of tasks per user

        self.db = Database("miodatabase.db")

    @staticmethod
    def load_token_api() -> str:
        try:
            return os.getenv("TOKEN_API")
        except ValueError:
            logging.error("Invalid TOKEN_API in .env file")
            return ""

    @staticmethod
    def load_state_request_url() -> int:
        try:
            return int(os.getenv("STATE_REQUEST_URL"))
        except ValueError:
            logging.error("Invalid STATE_REQUEST_URL in .env file")
            return -1

    @staticmethod
    def load_allowed_ids() -> list[int]:
        try:
            return [int(user_id) for user_id in os.getenv("ALLOWED_IDS").replace(" ", "").split(",")]
        except ValueError:
            logging.error("Invalid ALLOWED_IDS in .env file")
            return []

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = f"Hello <b>{update.message.from_user.username}</b>, it's a pleasure to meet you! I am @PeppyWebMonitorBot.\n" \
               "My purpose is to track and monitor the websites you want. I will notify you whenever one of the websites you are following experiences a change in content.\n\n" \
               "To view a list of available commands, use /help."
        await update.message.reply_text(f"{text}", parse_mode='HTML')

        # ? Comment this operation
        self.db.insert_user(update.message.from_user.id, update.message.from_user.username)

    @staticmethod
    async def show_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = "\nHere is a list of available commands:\n" \
               "/start - restart the bot\n" \
               "/follow - follow a URL\n" \
               "/unfollow - unfollow a URL\n" \
               "/stop - stop tracking of all URLs\n" \
               "/cancel - cancel command\n" \
               "/list - display followed URLs\n" \
               "/help - show this list of commands\n"
        await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, you are in /help command!\n{text}", parse_mode='HTML')

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Clear all tasks for the user.
        task_name_list = self.db.get_all_tasks(update.message.from_user.id)
        tasks_to_cancel = [task for task in asyncio.all_tasks() if task.get_name() in task_name_list]
        for task in tasks_to_cancel:
            # Delete the task
            task.cancel()
            await asyncio.sleep(0.3)
            logging.info(f"{task.get_name()} requested cancellation.")

        # Delete the user.
        self.db.delete_user(update.message.from_user.id)
        await update.message.reply_text("All monitoring has been stopped. You can reactivate me using /start.")

    async def show_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        urls = self.db.get_links(update.message.from_user.id)
        if urls is not None and len(urls) > 0:
            text = ""
            for i, item in enumerate(urls):
                text += f"{i + 1}. {item}\n"
            await update.message.reply_text(text, disable_web_page_preview=True)
        else:
            await update.message.reply_text("You are not currently following any URLs.")

    @staticmethod
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

    @staticmethod
    async def check_for_changes(prev_content: str, curr_content: str, url: str, update: Update):
        if prev_content and curr_content and prev_content != curr_content:
            await update.message.reply_text(f"Content changed for {url}.")

    async def trak_routine(self, update: Update, url) -> None:
        prev_content = ""
        try:
            while True:
                curr_content = await self.fetch_url_content(url)
                await self.check_for_changes(prev_content, curr_content, url, update)
                prev_content = curr_content
                await asyncio.sleep(self.TIME)
        except asyncio.CancelledError:
            await update.message.reply_text(f"Monitoring of {url} stopped.")
            logging.info("Task terminated.")

    async def start_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            # Retrieve the url from the context.
            url: str = context.user_data.get("URL")


            if not self.db.check_link_exists(update.message.from_user.id, url):
                curr_task: asyncio.Task = asyncio.create_task(self.trak_routine(update, url))
                logging.info(curr_task)
                logging.info(curr_task.get_name())


                self.db.insert_link(update.message.from_user.id, url, curr_task.get_name())
                await update.message.reply_text("URL added successfully!")
            else:
                await update.message.reply_text("This URL has already been added.")

        except Exception as e:
            await update.message.reply_text("An error occurred while starting the task.")
            logging.error(f"Error in start_task: {e}")

    @staticmethod
    async def validate_url(update: Update, url):
        if not validators.url(url):
            logging.warning(f"Invalid URL provided by user {update.message.from_user.username}: {url}")
            return False
        return True

    async def state_request_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        url: str = update.message.text.replace("/follow", "").replace(" ", "")

        if len(url) <= 0:
            await update.message.reply_text("The provided URL is empty. Please enter a valid URL:")
            # Return to this state to wait for the url to follow
            return self.STATE_REQUEST_URL

        else:
            # Url without query string and without "/"
            url: str = urljoin(url, urlparse(url).path)
            url: str = url[:-1] if url.endswith("/") else url

            if await self.validate_url(update, url):
                # Save the url in context
                context.user_data["URL"] = url
                await self.start_task(update, context)
                return ConversationHandler.END

            else:
                await update.message.reply_text("The provided URL is invalid. Please try again or use /cancel.")

                # Return to this state to wait for the url to follow
                return self.STATE_REQUEST_URL

    async def follow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        #? Se è stato chiamato /stop e l'utente non è più presente nel database
        if self.db.get_user(update.message.from_user.id) is None:
            await self.start_command(update, context)

        if self.db.get_count_links(update.message.from_user.id) >= self.MAX_TASKS_PER_USER:
            await update.message.reply_text("You have reached the maximum number of URLs being tracked.")
            return ConversationHandler.END

        await update.message.reply_text("Please enter the URL you wish to follow:")
        # Return to this state to wait for the url to follow
        return self.STATE_REQUEST_URL

    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Your request has been canceled.")
        logging.info("ConversationHandler.END")
        return ConversationHandler.END

    async def unfollow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        urls = self.db.get_links(update.message.from_user.id)

        if urls is None or len(urls) <= 0:
            await update.message.reply_text("You are not following any URLs.")

        else:
            choice = []
            for idx, url in enumerate(urls):
                # If the url is larger than 64 bytes, it is too large to be printed as a button
                if len(url.encode("utf-8")) > 64:
                    diff = len(url.encode("utf-8")) - 64
                    url = url[:-diff]

                choice.append([InlineKeyboardButton(f"{idx + 1}. {url}", callback_data=url)])

            choice_markup = InlineKeyboardMarkup(choice)
            await update.message.reply_text(f"Please select the URL you wish to unfollow:", reply_markup=choice_markup)

    async def unfollow_callback(self, update: Update, context: CallbackContext) -> None:
        curr_option: str = update.callback_query.data
        logging.info(f"current_option: {curr_option}")
        curr_task = self.db.get_task(update.effective_user.id, curr_option)
        for task in asyncio.all_tasks():
            if task.get_name() == curr_task:
                # Delete the task
                task.cancel()

                await asyncio.sleep(0.3)

                logging.info(f"{task.get_name()} requested cancellation...")
                logging.info(f"Task for {curr_option} has been terminated: {True if task.done() else False}!")

                #? Comment
                self.db.delete_link(update.effective_user.id, curr_option)

                # To delete the selected option from the function
                await update.callback_query.delete_message()

    def main(self) -> None:
        app = Application.builder().token(self.TOKEN_API).build()

        conv_handler = (
            ConversationHandler(
                entry_points=[CommandHandler("follow", self.follow_command)],
                states={self.STATE_REQUEST_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.state_request_url),
                    CommandHandler("cancel", self.cancel_command), ], },
                fallbacks=[CommandHandler("start", self.start_command)],
            )
        )
        app.add_handler(conv_handler)

        app.add_handler(CommandHandler("start", self.start_command, filters=filters.User(self.ALLOWED_IDS)))
        app.add_handler(CommandHandler("stop", self.stop_command, filters=filters.User(self.ALLOWED_IDS)))
        app.add_handler(CommandHandler("unfollow", self.unfollow_command, filters=filters.User(self.ALLOWED_IDS)))
        app.add_handler(CallbackQueryHandler(self.unfollow_callback))
        app.add_handler(CommandHandler("list", self.show_list_command, filters=filters.User(self.ALLOWED_IDS)))
        app.add_handler(CommandHandler("help", self.show_help_command, filters=filters.User(self.ALLOWED_IDS)))

        app.run_polling()


if __name__ == "__main__":
    # To log into console information and status of application
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

    bot = WebMonitoringBot()
    bot.main()
