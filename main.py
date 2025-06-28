import json
import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# Load the message data (structure of terms, subjects, lectures, etc.) from a JSON file
with open("messages.json", "r", encoding="utf-8") as f:
    MESSAGE_DATA = json.load(f)

# The Telegram group chat ID where files are originally posted
GROUP_CHAT_ID = -1002521943338  

logger = logging.getLogger(__name__)

# In-memory dictionary to store user-specific state (term, subject, page, etc.)
user_data = {}  

# Helper function to get the user's first name from the update object
def get_first_name(update):
    if update.message:
        return update.message.from_user.first_name
    elif update.callback_query:
        return update.callback_query.from_user.first_name
    return "Friend"

# Handler for the /start command. Sends the initial term selection menu.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_name = get_first_name(update)
    # Build the keyboard for term selection
    keyboard = [
        [InlineKeyboardButton("📚 First Term / الترم الأول", callback_data="term_1")],
        [InlineKeyboardButton("📚 Second Term / الترم الثاني", callback_data="term_2")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Welcome message in both Arabic and English
    message = (
        f"👋 السلام عليكم يا {first_name}\n\n"
        "📝 قبل ما نبدأ مذاكرة، محتاج اعرف انهي ترم هنبدأ بيه؟\n\n"
        f"🕊️ Peace be upon you, {first_name}.\n"
        "Before we start studying, may I know which Term are we starting with?"
    )
    await update.message.reply_text(message, reply_markup=reply_markup)

# Handler for all button presses (callback queries)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Always answer the callback query to avoid Telegram timeout errors
    try:
        await query.answer()
    except Exception:
        pass

    # Delete the previous menu message to keep the chat clean
    await delete_previous_menu_message(query)

    user_id = query.message.chat_id
    # Initialize user_data for this user if not present
    if user_id not in user_data:
        user_data[user_id] = {}
    # Track viewed lectures for this user
    if "viewed_lectures" not in user_data[user_id]:
        user_data[user_id]["viewed_lectures"] = set()

    # Handle term selection
    if query.data.startswith("term_"):
        term = "First Term" if query.data == "term_1" else "Second Term"
        term_arabic = "الترم الأول" if term == "First Term" else "الترم الثاني"
        user_data[user_id]["term"] = term
        subjects = MESSAGE_DATA[term]
        # Build subject selection keyboard
        keyboard = [
            [InlineKeyboardButton(
                f"📘 {subj} / {subjects[subj].get('arabic', '')}",
                callback_data=f"subj_{subj}_{term}"
            )]
            for subj in subjects
        ]
        # Add "Everything" and "Back" buttons
        keyboard.append([InlineKeyboardButton("📦 Everything until now / كل شيء حتي الأن", callback_data=f"everything_{term}")])
        keyboard.append([InlineKeyboardButton("🔙 Back / رجوع", callback_data="back_to_term_selection")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = (
            f"✅ انت اخترت {term_arabic}، تقدر دلوقتي تختار المادة\n\n"
            f"✅ You have chosen {term}, kindly pick the Subject 👇"
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup
        )

    # Handle "Everything" bulk download for a term
    elif query.data.startswith("everything_") and not query.data.startswith("everything_subject_"):
        _, term = query.data.split("_", 1)
        all_files = []
        # Collect all files for all subjects in the selected term
        for subject in MESSAGE_DATA[term]:
            subj = MESSAGE_DATA[term][subject]
            all_files.extend(subj.get("Books", []))
            lectures = subj.get("Lectures", {})
            for lec in lectures.values():
                for files in lec.values():
                    all_files.extend(files)
        if all_files:
            await query.message.reply_text("⏳ Sending all files for this term...\n⏳ جاري إرسال كل الملفات لهذا الترم...")
            await send_files_by_message_ids(update, context, all_files)
        else:
            await query.message.reply_text("❌ No files found for this term.\n❌ لا توجد ملفات لهذا الترم.")

    # Handle "Everything" bulk download for a subject
    elif query.data.startswith("everything_subject_"):
        rest = query.data[len("everything_subject_"):]
        term, subject = rest.split("_", 1)
        subj = MESSAGE_DATA[term][subject]
        all_files = []
        all_files.extend(subj.get("Books", []))
        lectures = subj.get("Lectures", {})
        for lec in lectures.values():
            for files in lec.values():
                all_files.extend(files)
        if all_files:
            await query.message.reply_text("⏳ Sending all files for this subject...\n⏳ جاري إرسال كل الملفات لهذه المادة...")
            await send_files_by_message_ids(update, context, all_files)
        else:
            await query.message.reply_text("❌ No files found for this subject.\n❌ لا توجد ملفات لهذه المادة.")

    # Handle subject selection
    elif query.data.startswith("subj_"):
        _, subject, term = query.data.split("_")
        user_data[user_id]["term"] = term
        user_data[user_id]["subject"] = subject
        subject_arabic = MESSAGE_DATA[term][subject].get('arabic', '')
        # Build category selection keyboard (Books, Lectures, Everything, Back, Main Menu)
        keyboard = [
            [InlineKeyboardButton("📚 Books / كتب", callback_data=f"type_Books_{term}_{subject}")],
            [InlineKeyboardButton("🎥 Lectures / محاضرات", callback_data=f"type_Lectures_{term}_{subject}")],
            [InlineKeyboardButton("📦 Everything until now / كل شيء حتي الأن", callback_data=f"everything_subject_{term}_{subject}")],
            [InlineKeyboardButton("🔙 Back / رجوع", callback_data="back_to_term")],
            [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="back_to_term_selection")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = (
            f"📖 You have chosen {subject}. Which type of data do you want?\n\n"
            f"📖 انت اخترت {subject_arabic}، حابب ابعتلك ايه في المادة دي؟"
        )
        await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)

    # Handle category selection (Books or Lectures)
    elif query.data.startswith("type_"):
        _, category, term, subject = query.data.split("_")
        user_data[user_id]["term"] = term
        user_data[user_id]["subject"] = subject
        user_data[user_id]["category"] = category

        keyboard = [
            [InlineKeyboardButton("🔙 Back / رجوع", callback_data="back_to_subject")],
            [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="back_to_term_selection")]
        ]

        if category == "Books":
            message_ids = MESSAGE_DATA[term][subject].get("Books", [])
            if message_ids:
                await send_files_by_message_ids(update, context, message_ids)
            else:
                await query.message.reply_text(
                    "❌ Sorry, no files found for this category.\n"
                    "⏳ please wait until the admin uploads files.\n"
                    "❌ للأسف، لم يتم العثور على ملفات لهذه الفئة. \n⏳ فضلا انتظر الادمن يرفع الملفات.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        elif category == "Lectures":
            lectures = MESSAGE_DATA[term][subject].get("Lectures", {})
            if not lectures:
                await query.message.reply_text(
                    "❌ Sorry, no lectures found for this category.\n"
                    "⏳ please wait until the admin uploads files.\n"
                    "❌ للأسف، لم يتم العثور على محاضرات لهذه الفئة. \n⏳ فضلا انتظر الادمن يرفع الملفات.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                user_data[user_id]["page"] = 0
                await show_lectures(update, context, user_id)

    # Handle lecture category selection (Photos, Records, Notes)
    elif query.data.startswith("lecture_"):
        _, category, lecture_num, term, subject = query.data.split("_")
        files = MESSAGE_DATA[term][subject]["Lectures"][lecture_num].get(category, [])
        if files:
            await send_files_by_message_ids(update, context, files)
        else:
            keyboard = [
                [InlineKeyboardButton("🔙 Back / رجوع", callback_data="back")],
                [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="back_to_term_selection")]
            ]
            await query.message.reply_text(
                f"❌ Sorry, no files found for {category} in Lecture #{lecture_num}.\n"
                f"⏳ Please wait until the admin uploads files.\n"
                f"❌ للاسف، لم يتم العثور على ملفات لفئة {category} في المحاضرة رقم {lecture_num}.\n⏳ فضلا انتظر الادمن يرفع الملفات.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # Handle pagination: next page
    elif query.data == "next":
        user_data[user_id]["page"] += 1
        await show_lectures(update, context, user_id)

    # Handle pagination: previous page
    elif query.data == "back":
        user_data[user_id]["page"] -= 1
        await show_lectures(update, context, user_id)

    # Go back to subject menu
    elif query.data == "back_to_subject":
        term = user_data[user_id].get("term")
        subject = user_data[user_id].get("subject")
        if not term or not subject:
            keyboard = [
                [InlineKeyboardButton("📚 First Term / الترم الأول", callback_data="term_1")],
                [InlineKeyboardButton("📚 Second Term / الترم الثاني", callback_data="term_2")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ Please select a term first.\n⚠️ من فضلك اختر الترم أولاً.",
                reply_markup=reply_markup
            )
            return
        subject_arabic = MESSAGE_DATA[term][subject].get('arabic', '')
        keyboard = [
            [InlineKeyboardButton("📚 Books / كتب", callback_data=f"type_Books_{term}_{subject}")],
            [InlineKeyboardButton("🎥 Lectures / محاضرات", callback_data=f"type_Lectures_{term}_{subject}")],
            [InlineKeyboardButton("🔙 Back / رجوع", callback_data="back_to_term")],
            [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="back_to_term_selection")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = (
            f"📖 You have chosen {subject}. Which type of data do you want?\n\n"
            f"📖 انت اخترت {subject_arabic}، حابب ابعتلك ايه في المادة دي؟"
        )
        await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)

    # Go back to term menu
    elif query.data == "back_to_term":
        term = user_data[user_id].get("term")
        if not term:
            keyboard = [
                [InlineKeyboardButton("📚 First Term / الترم الأول", callback_data="term_1")],
                [InlineKeyboardButton("📚 Second Term / الترم الثاني", callback_data="term_2")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ Please select a term first.\n⚠️ من فضلك اختر الترم أولاً.",
                reply_markup=reply_markup
            )
            return
        term_arabic = "الترم الأول" if term == "First Term" else "الترم الثاني"
        subjects = MESSAGE_DATA[term]
        keyboard = [
            [InlineKeyboardButton(
                f"📘 {subj} / {subjects[subj].get('arabic', '')}",
                callback_data=f"subj_{subj}_{term}"
            )]
            for subj in subjects
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back / رجوع", callback_data="back_to_term_selection")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = f"انت اخترت {term_arabic}، تقدر دلوقتي تختار المادة\n\nYou have chosen {term_arabic}, Kindly pick the Subject"
        await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)

    # Go back to the very first menu (term selection)
    elif query.data == "back_to_term_selection":
        keyboard = [
            [InlineKeyboardButton("📚 First Term / الترم الأول", callback_data="term_1")],
            [InlineKeyboardButton("📚 Second Term / الترم الثاني", callback_data="term_2")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text="السلام عليكم يا صديقي\nقبل ما نبدأ مذاكرة، محتاج اعرف انهي ترم هنبدأ بيه؟\n\n"
                 "Peace be upon you, Friend. Before we start studying, May I know which Term are we starting with?",
            reply_markup=reply_markup
        )

    # Show lecture menu for a specific lecture (choose Photos, Records, Notes)
    elif query.data.startswith("lecturemenu_"):
        _, lecture_num, term, subject = query.data.split("_")
        user_data[user_id]["lecture_num"] = lecture_num
        user_data[user_id]["viewed_lectures"].add((term, subject, lecture_num))
        keyboard = [
            [InlineKeyboardButton("🖼️ Photos / صور", callback_data=f"lecture_Photos_{lecture_num}_{term}_{subject}")],
            [InlineKeyboardButton("🎙️ Records / تسجيلات", callback_data=f"lecture_Records_{lecture_num}_{term}_{subject}")],
            [InlineKeyboardButton("📝 Notes / ملاحظات", callback_data=f"lecture_Notes_{lecture_num}_{term}_{subject}")],
            [InlineKeyboardButton("🔙 Back / رجوع", callback_data="back")],
            [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="back_to_term_selection")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📖 Lecture #{lecture_num} / محاضرة #{lecture_num}\n\n👇 Choose a category:\n👇 اختر الفئة:",
            reply_markup=reply_markup
        )

# Show a paginated list of lectures for the selected subject
async def show_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    term = user_data[user_id]["term"]
    subject = user_data[user_id]["subject"]
    page = user_data[user_id]["page"]
    lectures = MESSAGE_DATA[term][subject]["Lectures"]
    lecture_numbers = sorted(lectures.keys(), key=int)
    start = page * 5
    end = start + 5
    paginated_lectures = lecture_numbers[start:end]
    viewed = user_data[user_id].get("viewed_lectures", set())
    # Build lecture selection keyboard with ✅ for viewed lectures
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅ ' if (term, subject, num) in viewed else ''}📖 Lecture #{num} / محاضرة #{num}",
            callback_data=f"lecturemenu_{num}_{term}_{subject}"
        )]
        for num in paginated_lectures
    ]
    if page > 0:
        keyboard.insert(0, [InlineKeyboardButton("🔙 Back / السابق", callback_data="back")])
    if end < len(lecture_numbers):
        keyboard.append([InlineKeyboardButton("➡️ Next / التالي", callback_data="next")])
    keyboard.append([InlineKeyboardButton("🔙 Back / رجوع", callback_data="back_to_subject")])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="back_to_term_selection")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text="📚 اختر المحاضرة\n\nChoose a lecture:", reply_markup=reply_markup)

# Send files by their message IDs (from the group/channel)
async def send_files_by_message_ids(update: Update, context: ContextTypes.DEFAULT_TYPE, message_ids):
    query = update.callback_query
    chat_id = query.message.chat_id
    # Send each file by copying from the group/channel
    for msg_id in message_ids:
        try:
            await context.bot.copy_message(chat_id=chat_id, from_chat_id=GROUP_CHAT_ID, message_id=msg_id)
        except Exception as e:
            await query.message.reply_text(f"⚠️ Failed to send file with message ID {msg_id}: {e}\n⚠️ فشل إرسال الملف بالمعرف {msg_id}: {e}")
    # Show a main menu button after sending all files
    main_menu_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="back_to_term_selection")]
    ])
    await query.message.reply_text(
        "✅ These are all the files you ordered!\n✅ دي كل الملفات اللي طلبتها!",
        reply_markup=main_menu_keyboard
    )

# /remind command handler: sets a reminder after a number of minutes
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(context.args[0])
        await update.message.reply_text(f"⏰ Reminder set! I will remind you in {minutes} minutes.")
        await asyncio.sleep(minutes * 60)
        await update.message.reply_text("🔔 Time to study! 📚")
    except Exception:
        await update.message.reply_text("❗ Usage: /remind <minutes>\nمثال: /remind 30")

# Utility: Delete previous menu message (but never delete study material)
async def delete_previous_menu_message(query):
    try:
        if query.message and query.message.reply_markup:
            # Only delete if message does NOT contain study material (no media, has buttons)
            if not (query.message.photo or query.message.document or query.message.audio or query.message.video):
                await query.message.delete()
    except Exception:
        pass

# Main function to start the bot and register handlers
def main():
    app = Application.builder().token("7875502495:AAHpGTDS_Dd4nw2_nz1dLtyGWS0_0bC3tvc").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Starting the bot....")
    app.run_polling()

if __name__ == "__main__":
    main()
