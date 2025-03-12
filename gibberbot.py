import json
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Path to the JSON file
JSON_FILE = 'message_counts.json'

# Load or initialize message counts
if os.path.exists(JSON_FILE):
    try:
        with open(JSON_FILE, 'r') as f:
            content = f.read().strip()
            message_counts = json.loads(content) if content else {}
            logger.info(f"Loaded message counts from {JSON_FILE}")
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from message_counts.json")
        message_counts = {}
else:
    message_counts = {}
    logger.info(f"{JSON_FILE} not found, initialized empty message counts.")

def save_message_counts():
    with open(JSON_FILE, 'w') as f:
        json.dump(message_counts, f)
    logger.info("Saved message counts to JSON file")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello! I am a message counting bot.')
    logger.info("Start command issued")

async def record_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.chat_id)
    timestamp = datetime.utcnow().isoformat()
    
    logger.info(f"Received message in chat {chat_id} at {timestamp}")
    
    if chat_id not in message_counts:
        message_counts[chat_id] = {'total': 0, 'last_hour': []}
        logger.info(f"Initialized message count for chat {chat_id}")
    
    message_counts[chat_id]['last_hour'].append(timestamp)
    logger.info(f"Updated message count for chat {chat_id}: {message_counts[chat_id]['last_hour']}")

    save_message_counts()

def clean_old_records():
    now = datetime.utcnow()
    for chat_id in message_counts.keys():
        original_count = len(message_counts[chat_id]['last_hour'])
        message_counts[chat_id]['last_hour'] = [ts for ts in message_counts[chat_id]['last_hour'] if datetime.fromisoformat(ts) > now - timedelta(hours=1)]
        new_count = len(message_counts[chat_id]['last_hour'])
        logger.info(f"Cleaned old records for chat {chat_id}: {original_count} -> {new_count}")

        # Update total count
        message_counts[chat_id]['total'] += new_count
    save_message_counts()

def generate_summary():
    summary_lines = []
    
    now = datetime.utcnow()
    for chat_id, counts in message_counts.items():
        last_hour_msg_count = len([ts for ts in counts['last_hour'] if datetime.fromisoformat(ts) > now - timedelta(hours=1)])
        summary_lines.append(
            f"Chat ID {chat_id}:\nTotal Messages: {counts['total']}\nMessages in Last Hour: {last_hour_msg_count}"
        )
    
    summary_text = "\n".join(summary_lines)
    logger.info(f"Generated summary: {summary_text}")
    return summary_text

async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    summary_text = generate_summary()
    await update.message.reply_text(summary_text)
    logger.info("Summary sent to chat")

async def minute_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    clean_old_records()
    summary_text = generate_summary()
    print(summary_text)

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("summarize", summarize))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, record_message))

    # Schedule the minute summary
    application.job_queue.run_repeating(minute_summary, interval=60, first=0)

    application.run_polling()

if __name__ == '__main__':
    main()
