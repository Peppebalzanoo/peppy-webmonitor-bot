from telegram.ext import Application, CommandHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from httpx import RequestError, HTTPStatusError, AsyncClient, Response
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from database import Database
import validators
import logging
import asyncio
import signal
import sys
import os


class WebMonitoringBot:
    def __init__(self):
        # Load .env (environment) and override system's variables
        load_dotenv(override=True)
        # Retrieve environment-variables from .env file
        self.TOKEN_API = self.load_token_api()
        self.STATE_REQUEST_URL = self.load_state_request_url()
        self.ALLOWED_IDS = self.load_allowed_ids()
        # Set the time interval to check whether URLs have changed (in seconds)
        self.TIME = 60
        # Set the maximum number of tasks per user
        self.MAX_TASKS_PER_USER = 5

        # Initialize the database connection
        self.db = Database("miodatabase.db")

    # Cleanup function to perform necessary actions before shutting down the bot
    def cleanup(self):
        # Log the start of the cleanup process
        logging.info("Performing cleanup before shutdown...")

        # Retrieve all task names from the database
        task_name_list = self.db.get_all_tasks()
        # Identify tasks that need to be canceled based on their names
        tasks_to_cancel = [task for task in asyncio.all_tasks() if task.get_name() in task_name_list]
        for task in tasks_to_cancel:
            # Cancel each identified task
            task.cancel()
            # Log the cancellation request for each task
            logging.info(f"{task.get_name()} requested cancellation.")

        # Log the completion of the cleanup process
        logging.info("Cleanup done.")

    # Signal handler function to manage shutdown signals
    def signal_handler(self, frame):
        # Log that a signal has been received
        logging.info("Signal received, stopping the bot...")
        self.cleanup()  # Call the cleanup function to perform necessary actions
        sys.exit(0)  # Exit the application gracefully

    @staticmethod
    def load_token_api() -> str:
        try:
            # Retrieve the TOKEN_API from environment variables
            return os.getenv("TOKEN_API")
        except ValueError:
            # Log an error if TOKEN_API is invalid in the .env file
            logging.error("Invalid TOKEN_API in .env file")
            return ""

    @staticmethod
    def load_state_request_url() -> int:
        try:
            # Retrieve the STATE_REQUEST_URL from environment variables and convert to int
            return int(os.getenv("STATE_REQUEST_URL"))
        except ValueError:
            # Log an error if STATE_REQUEST_URL is invalid in the .env file
            logging.error("Invalid STATE_REQUEST_URL in .env file")
            return -1

    @staticmethod
    def load_allowed_ids() -> list[int]:
        try:
            # Retrieve and convert ALLOWED_IDS from environment variables to a list of integers
            return [int(user_id) for user_id in os.getenv("ALLOWED_IDS").replace(" ", "").split(",")]
        except ValueError:
            # Log an error if ALLOWED_IDS is invalid in the .env file
            logging.error("Invalid ALLOWED_IDS in .env file")
            return []

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Create a greeting message for the user when they start the bot
        text = f"Hello <b>{update.message.from_user.username}</b>, it's a pleasure to meet you! I am @PeppyWebMonitorBot.\n" \
               "My purpose is to track and monitor the websites you want. I will notify you whenever one of the websites you are following experiences a change in content.\n\n" \
               "To view a list of available commands, use /help."
        # Send the greeting message to the user with HTML formatting
        await update.message.reply_text(f"{text}", parse_mode='HTML')
        # Insert the user into the database for tracking purposes
        self.db.insert_user(update.message.from_user.id, update.message.from_user.username)



    @staticmethod
    async def show_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Create a help message listing all available commands for the user
        text = "\nHere is a list of available commands:\n" \
               "/start - restart the bot\n" \
               "/follow - follow a URL\n" \
               "/unfollow - unfollow a URL\n" \
               "/stop - stop tracking of all URLs\n" \
               "/cancel - cancel command\n" \
               "/list - display followed URLs\n" \
               "/help - show this list of commands\n"
        # Send the help message to the user with HTML formatting
        await update.message.reply_text(f"Hi <b>{update.message.from_user.username}</b>, you are in /help command!\n{text}", parse_mode='HTML')

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Clear all tasks associated with the user when they stop monitoring URLs.
        task_name_list = self.db.get_tasks(update.message.from_user.id)
        tasks_to_cancel = [task for task in asyncio.all_tasks() if task.get_name() in task_name_list]

        for task in tasks_to_cancel:
            # Cancel each task that matches the user's tasks.
            task.cancel()
            await asyncio.sleep(0.3)
            logging.info(f"{task.get_name()} requested cancellation.")

        # Delete the user from the database after stopping monitoring.
        self.db.delete_user(update.message.from_user.id)
        await update.message.reply_text("All monitoring has been stopped. You can reactivate me using /start.")

    async def show_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Retrieve and display all URLs currently being followed by the user.
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
            # Log HTTP errors encountered while fetching URL content.
            logging.error(f"HTTP error for {url}: {e.response.status_code}")
            return ""

        except RequestError as e:
            # Log request errors encountered while fetching URL content.
            logging.error(f"Request error for {url}: {e}")
            return ""

    @staticmethod
    async def check_for_changes(prev_content: str, curr_content: str, url: str, update: Update):
        # Check if there are changes between previous and current content.
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
            # Retrieve the URL from user data stored in context.
            url: str = context.user_data.get("URL")

            if not self.db.check_link_exists(update.message.from_user.id, url):
                curr_task: asyncio.Task = asyncio.create_task(self.trak_routine(update, url))
                logging.info(curr_task)
                logging.info(curr_task.get_name())

                # Insert new link into database along with task name.
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
            # Return to this state to wait for a valid URL input.
            return self.STATE_REQUEST_URL

        else:
            # Normalize URL by removing trailing slashes and ensuring proper format.
            url: str = urljoin(url, urlparse(url).path)
            url: str = url[:-1] if url.endswith("/") else url

            if await self.validate_url(update, url):
                # Save valid URL into user data context.
                context.user_data["URL"] = url

                await self.start_task(update, context)
                return ConversationHandler.END

            else:
                await update.message.reply_text("The provided URL is invalid. Please try again or use /cancel.")
                # Return to this state to wait for a valid URL input.
                return self.STATE_REQUEST_URL

    async def follow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Check if user exists in database; if not call start_command.
        if self.db.get_user(update.message.from_user.id) is None:
            await self.start_command(update, context)

        if self.db.get_count_links(update.message.from_user.id) >= self.MAX_TASKS_PER_USER:
            await update.message.reply_text("You have reached the maximum number of URLs being tracked.")
            return ConversationHandler.END

        await update.message.reply_text("Please enter the URL you wish to follow:")

        # Return to this state to wait for a valid URL input.
        return self.STATE_REQUEST_URL

    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Notify user that their request has been canceled.
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
                # If the URL length exceeds 64 bytes it will be truncated for display purposes.
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
                # Cancel and delete the selected task.
                task.cancel()
                await asyncio.sleep(0.3)
                logging.info(f"{task.get_name()} requested cancellation...")
                logging.info(f"Task for {curr_option} has been terminated: {True if task.done() else False}!")

        # Delete link from database after unfollowing.
        self.db.delete_link(update.effective_user.id, curr_option)
        await update.callback_query.delete_message()

    def main(self) -> None:

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

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
    # Configure logging settings to log application status and information to console.
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    bot = WebMonitoringBot()
    bot.main()
