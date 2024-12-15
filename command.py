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


class Command:
    def __init__(self, database, max_tasks_for_user, state_request_url):
        self._db = database
        self._db = database
        self._max_tasks_for_user = max_tasks_for_user
        self._state_request_url = state_request_url

    def get_state_request_url(self):
        return self._state_request_url

    def get_max_tasks_per_user(self):
        return self._max_tasks_for_user
    
    def get_db(self):
        return self._db

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Create a greeting message for the user when they start the bot
        text = f"Hello <b>{update.message.from_user.username}</b>, it's a pleasure to meet you! I am @PeppyWebMonitorBot.\n" \
               "My purpose is to track and monitor the websites you want. I will notify you whenever one of the websites you are following experiences a change in content.\n\n" \
               "To view a list of available commands, use /help."
        # Send the greeting message to the user with HTML formatting
        await update.message.reply_text(f"{text}", parse_mode='HTML')
        # Insert the user into the database for tracking purposes
        self.get_db().insert_user(update.message.from_user.id, update.message.from_user.username)

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
        task_name_list = self.get_db().get_tasks(update.message.from_user.id)
        tasks_to_cancel = [task for task in asyncio.all_tasks() if task.get_name() in task_name_list]

        for task in tasks_to_cancel:
            # Cancel each task that matches the user's tasks.
            task.cancel()
            await asyncio.sleep(0.3)
            logging.info(f"{task.get_name()} requested cancellation.")
        # Delete the user from the database after stopping monitoring.
        self.get_db().delete_user(update.message.from_user.id)
        await update.message.reply_text("All monitoring has been stopped. You can reactivate me using /start.")

    async def show_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Retrieve and display all URLs currently being followed by the user.
        urls = self.get_db().get_links(update.message.from_user.id)
        if urls is not None and len(urls) > 0:
            text = ""
            for i, item in enumerate(urls):
                text += f"{i + 1}. {item}\n"
            await update.message.reply_text(text, disable_web_page_preview=True)
        else:
            await update.message.reply_text("You are not currently following any URLs.")

    async def follow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Check if user exists in database; if not call start_command.
        if self.get_db().get_user(update.message.from_user.id) is None:
            await self.start_command(update, context)

        if self.get_db().get_count_links(update.message.from_user.id) >= self.get_max_tasks_per_user():
            await update.message.reply_text("You have reached the maximum number of URLs being tracked.")
            return ConversationHandler.END

        await update.message.reply_text("Please enter the URL you wish to follow:")
        # Return to this state to wait for a valid URL input.
        return self.get_state_request_url()

    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Notify user that their request has been canceled.
        await update.message.reply_text("Your request has been canceled.")
        logging.info("ConversationHandler.END")
        return ConversationHandler.END


    async def unfollow_callback(self, update: Update, context: CallbackContext) -> None:
        curr_option: str = update.callback_query.data
        logging.info(f"current_option: {curr_option}")
        curr_task = self.get_db().get_task(update.effective_user.id, curr_option)
        for task in asyncio.all_tasks():
            if task.get_name() == curr_task:
                # Cancel and delete the selected task.
                task.cancel()
                logging.info(f"{task.get_name()} requested cancellation...")
                # Wait for the task deletion to be completed.
                await asyncio.sleep(0.3)
                logging.info(f"Task for {curr_option} has been terminated: {True if task.done() else False}!")
                logging.info(f"Attempting to delete message for user {update.effective_user.id}")
                try:
                    await update.callback_query.delete_message()
                    logging.info(f"Message deleted successfully for user {update.effective_user.id}")
                except Exception as e:
                    logging.error(f"Error deleting message: {e} for user {update.effective_user.id}")
        # Delete link from database after unfollowing.
        self.get_db().delete_link(update.effective_user.id, curr_option)

    async def unfollow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        urls = self.get_db().get_links(update.message.from_user.id)
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
