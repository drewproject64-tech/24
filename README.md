# SB24GZ Official

A private-chat Telegram bot teaching English through Khmer. Python 3.11+; no third-party Python packages.

## Features

- Exactly three main menu buttons: daily words, quick quiz, and progress.
- 30 vocabulary entries with English examples and Khmer translations.
- Three words per day, rotating on Cambodia time (Asia/Phnom_Penh). The starter set repeats after ten days; append entries in `WORDS` to expand it.
- Three-answer quizzes, instant explanations, and duplicate-answer protection. Starting another quiz replaces the unanswered quiz.
- SQLite progress survives process restarts when the database is on persistent storage.
- `/start`, `/help`, `/menu`, `/words`, `/quiz`, `/progress`, `/privacy`, and `/delete_me`.
- No redirects or promotional broadcasts.

## Run

1. Create your bot with @BotFather and choose an available username.
2. Set `BOT_TOKEN` through your hosting provider's secret/environment settings. Never commit it or paste it in public logs.
3. Optionally set `DB_PATH` to an absolute path on a persistent disk, e.g. `/data/progress.sqlite3`. Default: `data/progress.sqlite3`.
4. Start: `python bot.py`.

Use an always-running worker or VPS with outbound HTTPS access to api.telegram.org. There is no HTTP server or web-service port. Run exactly **one** process per bot token. An active webhook must be explicitly removed before switching to polling; this script does not remove it automatically. A second polling instance causes a conflict and shutdown.

On successful startup, the bot sets its default display name to **SB24GZ Official**, plus its Khmer description, about text, and commands. If the bot previously had language-specific profile overrides, clear those in BotFather. Set a profile picture separately in BotFather; the code cannot supply your brand image. The bot's username remains the one you choose in BotFather.

## Docker

Build: `docker build -t sb24gz .`

Run with BOT_TOKEN already exported in your shell:

```sh
docker run --restart unless-stopped -e BOT_TOKEN -e DB_PATH=/data/progress.sqlite3 -v sb24gz-data:/data sb24gz
```

## Verify

```sh
python -m unittest -v
```

Tests use a fake Telegram API and a temporary database. After deploying, verify `/start`, all three menu buttons, correct and incorrect answers, progress after restart, and `/delete_me` in your real bot. Live Telegram behavior requires a valid token and has not been verified by the offline tests.

## Telegram Ads

Suggested Khmer copy:

រៀនពាក្យអង់គ្លេសជាមួយ SB24GZ Official។ មើលអត្ថន័យជាភាសាខ្មែរ ឆ្លើយសំណួរខ្លីៗ និងតាមដានវឌ្ឍនភាពក្នុងបូត។

Use the real bot username as your destination and target Khmer-language channels. Before submitting, complete the profile and confirm the hosted bot works. Telegram determines approval; this project does not guarantee it. Keep the advertised educational purpose consistent with the actual bot.

## Data and operational notes

Stores Telegram user IDs, dates of opened lessons, quiz choices and results, and the polling offset. It does not store names, phone numbers, or message text. `/delete_me` removes the user's lesson and quiz records. Protect the database and any backups; deleted data may remain in operator-managed backups until those expire. Back up the persistent disk as needed.

Network failures retry without logging token-bearing URLs. Quiz scores cannot be counted twice. As with simple polling systems, a crash between sending a message and saving the update offset may repeat a response; Telegram message delivery is not exactly-once. An API failure after a quiz score is saved may prevent delivery of its explanation, but progress remains available.
