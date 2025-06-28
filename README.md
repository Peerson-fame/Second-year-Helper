# Second Year BOT Telegram Bot

This is a Telegram bot designed to help students easily access and download study materials for the second year. The bot provides an interactive menu in both Arabic and English, allowing users to select their term, subject, and type of material (books, lectures, etc.), and receive files directly from a Telegram group.

## Features
- Multi-language support (Arabic & English)
- Interactive menus for term, subject, and material selection
- Bulk download for all files in a term or subject
- Pagination for lectures
- Reminders for study sessions
- Tracks viewed lectures per user

## File Structure
- `main.py`: Main bot logic and handlers
- `Collect_ids.py`: (Purpose: likely for collecting message/file IDs)
- `files_ids.json`: (Purpose: likely stores file/message IDs)
- `messages.json`: Contains the structure of terms, subjects, lectures, and file IDs
- `requirements.txt`: Python dependencies

## Getting Started

### Prerequisites
- Python 3.8+
- Telegram Bot Token

### Installation
1. Clone this repository or download the files.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Update the bot token in `main.py`:
   ```python
   app = Application.builder().token("YOUR_BOT_TOKEN").build()
   ```
4. Make sure `messages.json` is properly structured and contains the required data.

### Running the Bot
```sh
python main.py
```

## Usage
- Start the bot with `/start` to begin navigating the menu.
- Use `/remind <minutes>` to set a study reminder.
- Use the interactive buttons to select term, subject, and material type.

## Notes
- The bot copies files from a specific Telegram group using message IDs. Ensure the bot has access to the group and the files exist.
- The bot does not store user data persistently; all state is in-memory.

## License
This project is for educational purposes.
