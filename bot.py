from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
import psycopg2
import os
import re
from typing import Optional
import yt_dlp
from datetime import datetime
import logging
from dotenv import load_dotenv
import hashlib
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TikTokDownloader:
    def __init__(self, save_path: str = "downloads", use_cookies: bool = True):
        self.save_path = save_path
        self.use_cookies = use_cookies
        os.makedirs(self.save_path, exist_ok=True)

    def _clean_filename(self, title: str) -> str:
        """Clean and shorten the filename to prevent length issues"""
        try:
            # If title is None or not a string, use a default
            if not isinstance(title, str):
                title = "tiktok_video"
            
            # Remove hashtags, mentions, and emojis
            clean_title = re.sub(r'#\w+|@\w+|[^\w\s-]', '', title)
            # Remove multiple spaces
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            # Limit to 50 characters
            clean_title = clean_title[:50].strip()
            # If clean_title is empty after cleaning, use default
            if not clean_title:
                clean_title = "tiktok_video"
            # Create a short hash from the original title
            title_hash = hashlib.md5(str(title).encode()).hexdigest()[:8]
            return f"{clean_title}_{title_hash}"
        except Exception as e:
            logger.error(f"Error cleaning filename: {str(e)}")
            return f"tiktok_video_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"

    def _get_ydl_opts(self, custom_name: Optional[str] = None) -> dict:
        """Generate yt-dlp options dictionary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        def custom_filename(d):
            try:
                if custom_name:
                    return f"{custom_name}.%(ext)s"
                # Get the title from the video info
                title = d.get('title', 'video')
                clean_title = self._clean_filename(title)
                return os.path.join(self.save_path, f"{clean_title}_{timestamp}.%(ext)s")
            except Exception as e:
                logger.error(f"Error in custom_filename: {str(e)}")
                # Fallback to a simple filename if there's an error
                return os.path.join(self.save_path, f"tiktok_video_{timestamp}.%(ext)s")

        return {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': custom_filename,
            'quiet': False,
            'no_warnings': False,
            'merge_output_format': 'mp4',
            'cookiefile': 'cookies.txt' if self.use_cookies and os.path.exists('cookies.txt') else None,
            'progress_hooks': [self._progress_hook],
            'extractor_args': {
                'tiktok': {
                    'format': 'download_addr',
                    'video_data': 'wm'
                }
            },
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'retries': 10,  # Increase retry attempts
            'fragment_retries': 10,
            'extractor_retries': 10,
            'ignoreerrors': True,  # Continue on download errors
            'no_check_certificate': True,  # Skip certificate validation
            'http_headers': {  # Add headers to mimic browser
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        }

    def _progress_hook(self, d: dict):
        """Progress callback for yt-dlp"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', "0.0%")
            speed = d.get('_speed_str', "N/A")
            eta = d.get('_eta_str', "N/A")
            logger.info(f"Downloading: {percent} at {speed} ETA: {eta}")

    def download_video(self, url: str, custom_name: Optional[str] = None) -> Optional[str]:
        """Download a TikTok video"""
        try:
            with yt_dlp.YoutubeDL(self._get_ydl_opts(custom_name)) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        raise Exception("Failed to extract video information")
                    downloaded_file = ydl.prepare_filename(info)
                    if not os.path.exists(downloaded_file):
                        raise Exception("Downloaded file not found")
                    logger.info(f"Download completed: {downloaded_file}")
                    return downloaded_file
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    raise Exception("Failed to parse TikTok response")
                except Exception as e:
                    logger.error(f"Download error: {str(e)}")
                    raise
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return None

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from TikTok URL"""
    patterns = [
        r'https?://(?:www\.|vm\.|)tiktok\.com/.+?/video/(\d+)',
        r'https?://(?:www\.|vm\.|)tiktok\.com/t/([a-zA-Z0-9]+)/?',
        r'https?://(?:www\.|vm\.|)tiktok\.com/@[^/]+/video/(\d+)',
        r'https?://(?:www\.|vm\.|)tiktok\.com/([a-zA-Z0-9]+)/?'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def handle_tiktok_download(update: Update, context: ContextTypes.DEFAULT_TYPE, video_url: str):
    """Handle TikTok download with Telegram progress updates"""
    chat_id = update.effective_chat.id
    message = await context.bot.send_message(chat_id, "⬇️ Starting download...")
    video_path = None
    
    try:
        # Initialize downloader with custom path per user
        user_dir = os.path.join("downloads", str(chat_id))
        downloader = TikTokDownloader(save_path=user_dir)

        # Update status
        await context.bot.edit_message_text(
            "⏳ Downloading video (this may take a minute)...",
            chat_id=chat_id,
            message_id=message.message_id
        )

        # Download video
        video_path = downloader.download_video(video_url)

        if not video_path or not os.path.exists(video_path):
            raise Exception("Download failed - no file created")

        # Check file size (Telegram limit: 50MB)
        file_size = os.path.getsize(video_path) / (1024 * 1024)
        if file_size > 50:
            raise Exception(f"Video too large ({file_size:.2f}MB > 50MB limit)")

        # Upload to Telegram with progress updates
        await context.bot.edit_message_text(
            "📤 Uploading to Telegram (this may take a while)...",
            chat_id=chat_id,
            message_id=message.message_id
        )

        try:
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="Here's your TikTok video! 🎬",
                    supports_streaming=True,
                    read_timeout=120,  # Increased timeout
                    write_timeout=120,  # Increased timeout
                    connect_timeout=120  # Increased timeout
                )
        except Exception as upload_error:
            raise Exception(f"Upload failed: {str(upload_error)}")

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
    
    # Handle TikTok URLs
    if extract_video_id(text):
        await handle_tiktok_download(update, context, text)
        return
    
    await update.message.reply_text("Send a TikTok URL")

if __name__ == '__main__':
    # Check requirements
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp not installed. Run: pip install yt-dlp")
        exit(1)
    
    # Get bot token from environment variable
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables!")
        exit(1)
    
    app = ApplicationBuilder().token(bot_token).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", lambda update, context: context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! Send me TikTok links to download them without watermarks."
    )))
    
    app.add_handler(CommandHandler("download", lambda update, context: update.message.reply_text(
        "Just send me the TikTok URL directly!"
    )))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

