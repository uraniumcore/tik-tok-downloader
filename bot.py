from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
import os
import logging
from dotenv import load_dotenv
import yt_dlp
from datetime import datetime
from typing import Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TikTokDownloader:
    def __init__(self, save_path: str = "downloads"):
        self.save_path = save_path
        os.makedirs(self.save_path, exist_ok=True)

    def download_video(self, url: str) -> Optional[str]:
        """Download a TikTok video"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = os.path.join(self.save_path, f"tiktok_{timestamp}.%(ext)s")
            
            ydl_opts = {
                'format': 'best',
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': False,
                'merge_output_format': 'mp4',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                logger.info(f"Download completed: {downloaded_file}")
                return downloaded_file
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return None

async def handle_tiktok_download(update: Update, context: ContextTypes.DEFAULT_TYPE, video_url: str):
    """Handle TikTok download with Telegram progress updates"""
    chat_id = update.effective_chat.id
    message = await context.bot.send_message(chat_id, "⬇️ Starting download...")
    
    try:
        # Initialize downloader
        downloader = TikTokDownloader(save_path=os.path.join("downloads", str(chat_id)))
        
        # Update status
        await context.bot.edit_message_text(
            "⏳ Downloading video...",
            chat_id=chat_id,
            message_id=message.message_id
        )

        # Download video
        video_path = downloader.download_video(video_url)
        if not video_path or not os.path.exists(video_path):
            raise Exception("Download failed")

        # Upload to Telegram
        await context.bot.edit_message_text(
            "📤 Uploading to Telegram...",
            chat_id=chat_id,
            message_id=message.message_id
        )

        with open(video_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="Here's your TikTok video! 🎬",
                supports_streaming=True
            )

        # Clean up
        os.remove(video_path)
        await context.bot.delete_message(chat_id, message.message_id)

    except Exception as e:
        logger.error(f"Error in handle_tiktok_download: {str(e)}")
        error_msg = f"❌ Download failed: {str(e)}"
        try:
            await context.bot.edit_message_text(
                error_msg,
                chat_id=chat_id,
                message_id=message.message_id
            )
        except:
            await update.message.reply_text(error_msg)

        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Check if it's a TikTok URL
    if "tiktok.com" in text:
        await handle_tiktok_download(update, context, text)
        return
    
    await update.message.reply_text("Send me a TikTok URL!")

if __name__ == '__main__':
    # Get bot token from environment variable
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables!")
        exit(1)
    
    app = ApplicationBuilder().token(bot_token).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", lambda update, context: context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! Send me TikTok links to download them."
    )))
    
    app.add_handler(CommandHandler("download", lambda update, context: update.message.reply_text(
        "Just send me the TikTok URL directly!"
    )))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

