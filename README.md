# TikTok Downloader Bot

A Python-based bot for downloading TikTok videos.

## Features

- Download TikTok videos
- Handle multiple video formats
- Automatic video processing

## Setup

1. Clone the repository:
```bash
git clone https://github.com/uraniumcore/tik-tok-downloader.git
cd tik-tok-downloader
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Create a `.env` file in the project root
   - Add your Telegram bot token:
   ```
   BOT_TOKEN=your_bot_token_here
   ```
   - Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram

## Usage

Run the bot:
```bash
python bot.py
```

## Project Structure

- `bot.py` - Main bot file
- `requirements.txt` - Project dependencies
- `.env` - Environment variables (not tracked by git)
- `downloads/` - Directory for downloaded videos
- `logs/` - Log files directory

## Security

- Never commit your `.env` file
- Keep your bot token secret
- The `.env` file is automatically ignored by git

## License

This project is licensed under the MIT License - see the LICENSE file for details. 