# PeppyWebMonitorBot

**PeppyWebMonitorBot** is a friendly Telegram bot designed to help you monitor changes on your favorite websites. With just a few simple commands, you can start following URLs and receive instant notifications whenever the content of a site is updated. It's like having a personal assistant that keeps an eye on the web for you!

## Key Features
- **Welcome and Setup**: Start your journey with the bot by typing `/start` to get a friendly welcome and overview of its capabilities.
- **Follow Websites**: Use the `/follow` command to start monitoring a URL. The bot will periodically check for changes and notify you if anything changes.
- **Stop Monitoring**: No longer interested in a particular website? Use `/unfollow` to stop receiving updates from a specific URL.
- **View Your List**: Need a reminder of what you're tracking? Simply type `/list` to see the full list of websites you're currently monitoring.
- **Easy-to-Use Commands**: Explore the available commands at any time with `/help` to ensure you're getting the most out of PeppyWebMonitorBot.

## How It Works
PeppyWebMonitorBot continuously monitors the content of the websites you follow. If any changes are detected, you'll receive a notification directly in your Telegram chat. No more manually refreshing pages to see if something's different—let the bot do the hard work for you!

## Getting Started
To get started, clone the repository, install the required dependencies, and configure the bot by adding your Telegram bot API token and allowed user IDs to a `.env` file. Then, simply run the bot and start tracking websites with ease!

### Requirements
- Python 3.x
- `python-telegram-bot`
- `httpx`
- `dotenv`
- `validators`

### Commands
- `/start`: Get a welcome message and an introduction to the bot.
- `/follow [URL]`: Start following a website by providing its URL.
- `/unfollow`: Stop tracking a URL that you're following.
- `/list`: Show all the URLs you're currently monitoring.
- `/help`: Display all available commands.

---

This version is formatted with appropriate headers, making it ideal for a GitHub `README.md` file.
