import logging
import json
from telegram.ext import Application, MessageHandler, filters

logging.basicConfig(level=logging.INFO)

output_file = "files_ids.json"
collected = []

async def log_message(update, context):
    msg = update.message
    entry = None
    if msg.document:
        entry = {"type": "document", "file_name": msg.document.file_name, "message_id": msg.message_id}
    elif msg.photo:
        entry = {"type": "photo", "message_id": msg.message_id}
    elif msg.video:
        entry = {"type": "video", "message_id": msg.message_id}
    elif msg.text:
        entry = {"type": "text", "text": msg.text, "message_id": msg.message_id}
    if entry:
        collected.append(entry)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(collected, f, ensure_ascii=False, indent=2)
        print(entry)

def main():
    app = Application.builder().token("7875502495:AAHpGTDS_Dd4nw2_nz1dLtyGWS0_0bC3tvc").build()
    app.add_handler(MessageHandler(filters.ALL, log_message))
    app.run_polling()

if __name__ == "__main__":
    main()