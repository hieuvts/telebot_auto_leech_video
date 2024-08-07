# !/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

from dotenv import load_dotenv
import os
load_dotenv(".env")  # take environment variables
import logging
import html
import json
import traceback
import re
import yt_dlp
from yt_dlp import YoutubeDL
from telegram import ForceReply, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv('BOT_TOKEN')
DEVELOPER_CHAT_ID = os.getenv('DEVELOPER_CHAT_ID')
REGEX_MATCH_URL = re.compile(r"(?P<url>https?://[^\s]+)")
WHITELIST_KEYWORDS = ['vt.tiktok.com', 'fb.watch', 'facebook.com/reel', 'facebook.com/watch', 'youtube.com/shorts']

MIN_LENGTH_VIDEO = 15
MAX_LENGTH_VIDEO = 300 # Seconds
MAX_SIZE_VIDEO = 45000000 # 54MB
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
# logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def handleStartCmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        rf"Bot's alive! 🤖👋"
    )
async def handleHelpCmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        rf"Hỗ trợ các link sau: \n'vt.tiktok.com', 'fb.watch', 'facebook.com/reel', 'facebook.com/watch', 'youtube.com/shorts'"
    )
#TODO: Fix get duration for fb vid
def validate_video_length(info):
    duration = info.get('duration')
    if duration and duration > MAX_LENGTH_VIDEO:
        return 'The video is too long: ' + str(duration) + " (s)"
    elif duration and duration < MIN_LENGTH_VIDEO:
        return 'The video is too short: ' + str(duration) + " (s)"

def download_progress_hook(d):
    if d['status'] == 'finished':
        print('\nDone downloading, now post-processing ...')

ydl_opts = { 
    # 'format': format_selector,
    # 'progress_hooks': [download_progress_hook],
    # 'format': 'bestaudio/best',
    # 'match_filter': validate_video_length, # Not work with facebook video
    'quiet': True,
    'allow_unplayable_formats': False,
    'outtmpl': {'default': 'temp.mp4'},
}


async def handleNormalMessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Ignore Grafana alert
    if update.message is None:
        return
    # Check if message contains video URL
    validUrlFlag = 0
    matchedUrls = REGEX_MATCH_URL.search(update.message.text)
    if (matchedUrls):
        matchedUrl = matchedUrls.group("url")
        for keyword in WHITELIST_KEYWORDS:
            if keyword in matchedUrl:
                print("Message contains valid URL " + matchedUrl)
                await update.message.reply_chat_action(action="upload_video")
                validUrlFlag = 1
                with YoutubeDL(ydl_opts) as ydl:
                    try:
                        error_code = ydl.download(matchedUrl)
                        print("Download finishded. Code -> " + str(error_code))
                    except:
                        print("Download video error")
                        validUrlFlag = -1
    if validUrlFlag == 1:
        # await update.message.reply_text(text="Đường dẫn video hợp lệ " + matchedUrl,
        #                                 reply_to_message_id=update.message.message_id)
        # Check file size
        video_size = os.path.getsize("temp.mp4")
        if (video_size >= MAX_SIZE_VIDEO):
            print("Video is too large " + str(video_size/1000000) + " MB")
            await update.message.reply_text(text="Video is too large " + str(video_size/1000000) + " MB")
        else:
            await update.message.reply_video(video="temp.mp4",
                                reply_to_message_id=update.message.message_id, read_timeout=100, write_timeout=100)
        os.remove("temp.mp4")
    elif validUrlFlag == -1:
        await update.message.reply_text(text="Cannot download video! ⚡")
    print("\n============\n")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)
    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )
    message = (message[:4000] + '..') if len(message) > 4000 else message

    # Finally, send the message
    await context.bot.send_message(
        chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML
    )

async def test_err(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=DEVELOPER_CHAT_ID, text="Error happens", parse_mode=ParseMode.HTML
    )
    raise ValueError('A very specific bad thing happened.') 

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("ping", handleStartCmd))
    application.add_handler(CommandHandler("help", handleHelpCmd))
    application.add_handler(CommandHandler("test", test_err))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handleNormalMessage))
    application.add_error_handler(error_handler)
    print("---Start---\n")
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.MESSAGE)

if __name__ == "__main__":
    main()