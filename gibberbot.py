import json
import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUMMARY_GROUP_ID = os.getenv("SUMMARY_GROUP_ID")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the JSON file
JSON_FILE = 'message_counts.json'

# Load or initialize message counts
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, 'r') as f:
        message_counts = json.load(f)
else:
    message_counts = {}

def save_message_counts():
    with open(JSON_FILE, 'w') as f:
        json.dump(message_counts, f)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! I am a message counting bot.')

def record_message(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.message.chat_id)
    timestamp = datetime.utcnow().isoformat()
    
    if chat_id not in message_counts:
        message_counts[chat_id] = {'total': 0, 'last_24_hours': [], 'last_hour': []}
    
    message_counts[chat_id]['total'] += 1
    message_counts[chat_id]['last_24_hours'].append(timestamp)
    message_counts[chat_id]['last_hour'].append(timestamp)
    
    save_message_counts()

def clean_old_records():
    now = datetime.utcnow()
    for chat_id in message_counts.keys():
        message_counts[chat_id]['last_24_hours'] = [ts for ts in message_counts[chat_id]['last_24_hours'] if datetime.fromisoformat(ts) > now - timedelta(hours=24)]
        message_counts[chat_id]['last_hour'] = [ts for ts in message_counts[chat_id]['last_hour'] if datetime.fromisoformat(ts) > now - timedelta(hours=1)]
    save_message_counts()

def summarize(update: Update, context: CallbackContext) -> None:
    summary_lines = []
    for chat_id, counts in message_counts.items():
        summary_lines.append(
            f"Chat ID {chat_id}: Total: {counts['total']}, Last 24 Hours: {len(counts['last_24_hours'])}, Last Hour: {len(counts['last_hour'])}"
        )
    
    summary_text = "\n".join(summary_lines)
    context.bot.send_message(chat_id=update.message.chat_id, text=summary_text)

def hourly_summary(context: CallbackContext):
    clean_old_records()
    summary_lines = []
    for chat_id, counts in message_counts.items():
        summary_lines.append(
            f"Chat ID {chat_id}: Total: {counts['total']}, Last 24 Hours: {len(counts['last_24_hours'])}, Last Hour: {len(counts['last_hour'])}"
        )
    
    summary_text = "\n".join(summary_lines)
    context.bot.send_message(chat_id=context.job.context, text=summary_text)

def main():
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("summarize", summarize))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, record_message))
    
    # Schedule the hourly summary
    job_queue = updater.job_queue
    job_queue.run_repeating(hourly_summary, interval=3600, first=0, context=SUMMARY_GROUP_ID)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
