from telegram.ext import Application, CommandHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from httpx import RequestError, HTTPStatusError, AsyncClient, Response
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from database import Database
from utility import Utility
from command import Command
import validators
import logging
import asyncio
import signal
import sys
import os


class WebMonitoringBot:
    # Set the time interval to check whether URLs have changed (in seconds)
    TIME = 60
    # Set the maximum number of tasks per user
    MAX_TASKS_PER_USER = 5

    def __init__(self):
        self._util = Utility()
        # Load .env (environment) and override system's variables
        load_dotenv(override=True)
        # Retrieve environment-variables from .env file
        self._TOKEN_API = self.get_utility().load_token_api()
        self._STATE_REQUEST_URL = self.get_utility().load_state_request_url()
        self._ALLOWED_IDS = self.get_utility().load_allowed_ids()
        # Initialize the database connection
        self._db = Database("miodatabase.db")
        self._command_handler = Command(self._db, self.MAX_TASKS_PER_USER, self._STATE_REQUEST_URL)

    def get_command_handler(self):
        return self._command_handler

    def get_db(self):
        return self._db

    def get_state_request_url(self):
        return self._STATE_REQUEST_URL

    def get_allowed_ids(self):
        return self._ALLOWED_IDS

    def get_utility(self):
        return self._util

    # Cleanup function to perform necessary actions before shutting down the bot
    async def cleanup(self):
        # Log the start of the cleanup process
        logging.info("Performing cleanup before shutdown...")

        # Retrieve all task names from the database
        task_name_list = self.get_db().get_all_tasks()
        # Identify tasks that need to be canceled based on their names
        tasks_to_cancel = [task for task in asyncio.all_tasks() if task.get_name() in task_name_list]
        for task in tasks_to_cancel:
            # Cancel each identified task
            task.cancel()
            # Log the cancellation request for each task
            logging.info(f"{task.get_name()} requested cancellation.")

        await asyncio.gather(*tasks_to_cancel, return_exceptions=False)
        # Log the completion of the cleanup process
        logging.info("Cleanup completed.")

    # Signal handler function to manage shutdown signals
    def signal_handler(self, sig, frame):
        # Log that a signal has been received
        logging.info("Signal received, stopping the bot...")
        asyncio.create_task(self.cleanup())   # Call the cleanup function to perform necessary actions
        sys.exit(0)  # Exit the application gracefully


    async def track_url_changes(self, update: Update, url) -> None:
        prev_content = ""
        try:
            while True:
                curr_content = await self.get_utility().fetch_url_content(url)
                await self.get_utility().check_for_changes(prev_content, curr_content, url, update)
                prev_content = curr_content
                await asyncio.sleep(self.TIME)
        except asyncio.CancelledError:
            await update.message.reply_text(f"Monitoring of {url} stopped.")
            logging.info("Task terminated.")

    async def add_monitoring_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            # Retrieve the URL from user data stored in context.
            url: str = context.user_data.get("URL")
            if not self.get_db().check_link_exists(update.message.from_user.id, url):
                curr_task: asyncio.Task = asyncio.create_task(self.track_url_changes(update, url))
                logging.info(curr_task)
                logging.info(curr_task.get_name())
                # Insert new link into database along with task name.
                self.get_db().insert_link(update.message.from_user.id, url, curr_task.get_name())
                await update.message.reply_text("URL added successfully!")
            else:
                await update.message.reply_text("This URL has already been added.")
        except Exception as e:
            await update.message.reply_text("An error occurred while starting the task.")
            logging.error(f"Error in start_task: {e}")


    async def state_request_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        url: str = update.message.text.replace("/follow", "").replace(" ", "")
        if len(url) <= 0:
            await update.message.reply_text("The provided URL is empty. Please enter a valid URL:")
            # Return to this state to wait for a valid URL input.
            return self.get_state_request_url()
        else:
            # Normalize URL by removing trailing slashes and ensuring proper format.
            url: str = urljoin(url, urlparse(url).path)
            url: str = url[:-1] if url.endswith("/") else url
            if await self.get_utility().validate_url(update, url):
                # Save valid URL into user data context.
                context.user_data["URL"] = url
                await self.add_monitoring_task(update, context)
                return ConversationHandler.END
            else:
                await update.message.reply_text("The provided URL is invalid. Please try again or use /cancel.")
                # Return to this state to wait for a valid URL input.
                return self.get_state_request_url()


    def setup_handlers(self, app):
        conv_handler = (
            ConversationHandler(
                entry_points=[CommandHandler("follow", self.get_command_handler().follow_command)],
                states={
                        self.get_state_request_url(): [
                            MessageHandler(filters.TEXT & ~filters.COMMAND, self.state_request_url),
                            CommandHandler("cancel", self.get_command_handler().cancel_command), ], },
                fallbacks=[CommandHandler("start", self.get_command_handler().start_command)],
            )
        )
        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("start", self.get_command_handler().start_command, filters=filters.User(self.get_allowed_ids())))
        app.add_handler(CommandHandler("stop", self.get_command_handler().stop_command, filters=filters.User(self.get_allowed_ids())))
        app.add_handler(CommandHandler("unfollow", self.get_command_handler().unfollow_command, filters=filters.User(self.get_allowed_ids())))
        app.add_handler(CallbackQueryHandler(self.get_command_handler().unfollow_callback))
        app.add_handler(CommandHandler("list", self.get_command_handler().show_list_command, filters=filters.User(self.get_allowed_ids())))
        app.add_handler(CommandHandler("help", self.get_command_handler().show_help_command, filters=filters.User(self.get_allowed_ids())))


    def main(self) -> None:
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        app = Application.builder().token(self._TOKEN_API).build()
        self.setup_handlers(app)
        app.run_polling()


if __name__ == "__main__":
    # Configure logging settings to log application status and information to console.
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    bot = WebMonitoringBot()
    bot.main()
