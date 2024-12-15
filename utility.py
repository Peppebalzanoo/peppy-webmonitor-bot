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


class Utility:

    @staticmethod
    async def validate_url(update: Update, url):
        if not validators.url(url):
            logging.warning(f"Invalid URL provided by user {update.message.from_user.username}: {url}")
            return False
        return True

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
