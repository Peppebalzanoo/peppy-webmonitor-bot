# PeppyWebMonitorBot 🤖

**PeppyWebMonitorBot** is a friendly Telegram bot designed to help you monitor changes on your favorite websites. With just a few simple commands, you can start following URLs and receive instant notifications whenever the content of a site is updated. It's like having a personal assistant that keeps an eye on the web for you! 👀

## Key Features 🌟
- **Welcome and Setup**: Start your journey with the bot by typing `/start` to get a friendly welcome and overview of its capabilities. 😊
- **Follow Websites**: Use the `/follow` command to start monitoring a URL. The bot will periodically check for changes and notify you if anything changes. 🔔
- **Stop Monitoring**: No longer interested in a particular website? Use `/unfollow` to stop receiving updates from a specific URL. ❌
- **View Your List**: Need a reminder of what you're tracking? Simply type `/list` to see the full list of websites you're currently monitoring. 📜
- **Easy-to-Use Commands**: Explore the available commands at any time with `/help` to ensure you're getting the most out of PeppyWebMonitorBot. 🆘

## How It Works 🔍
PeppyWebMonitorBot continuously monitors the content of the websites you follow. If any changes are detected, you'll receive a notification directly in your Telegram chat. No more manually refreshing pages to see if something's different-let the bot do the hard work for you! 💪

## Getting Started 🛠️
To get started, clone the repository, install the required dependencies, and configure the bot by adding your Telegram bot API token and allowed user IDs to a `.env` file. Then, simply run the bot and start tracking websites with ease! To start the bot, it must be properly configured. This includes adding the appropriate keys to the `.env` file. An example file, `.env.placeholder`, is provided to indicate which variables need to be defined. The bot can run locally or be hosted on hosting services. Some free hosting services provide a list of allowed URLs for making GET requests.

---

### Commands 📝
- `/start`: Get a welcome message and an introduction to the bot. 👋
- `/follow`: Start following a website by providing its URL. 🌐
- `/unfollow`: Stop tracking a URL that you're following. 🚫
- `/stop`: Stop tracking all URLs you're currently monitoring. 🛑
- `/cancel`: Cancel the current operation or command. ❌
- `/list`: Show all the URLs you're currently monitoring. 📚
- `/help`: Display all available commands. ℹ️

---

### Requirements 📋
- Python 3.x
- `python-telegram-bot==21.6`
- `httpx==0.27.2`
- `dotenv`
- `validators==0.34.0`
- `anyio==4.6.0`
- `certifi==2024.8.30`
- `exceptiongroup==1.2.2`
- `h11==0.14.0`
- `httpcore==1.0.6`
- `idna==3.10`
- `load-dotenv==0.1.0`
- `python-dotenv==1.0.1`
- `sniffio==1.3.1`
- `typing_extensions==4.12.2`

