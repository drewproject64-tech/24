"""SB24GZ Official: English learning in Khmer. Python 3.11+, no dependencies."""
import json
import logging
import os
import random
import secrets
import signal
import sqlite3
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

NAME = 'SB24GZ Official'
ABOUT = 'រៀនពាក្យអង់គ្លេស ឆ្លើយសំណួរខ្លីៗ និងតាមដានវឌ្ឍនភាពជាភាសាខ្មែរ។'
DESCRIPTION = ('SB24GZ Official ជាបូតសម្រាប់រៀនភាសាអង់គ្លេស។ '
               'ស្វែងយល់ពាក្យជាមួយអត្ថន័យ និងឧទាហរណ៍ជាភាសាខ្មែរ '
               'សាកល្បងសំណួរខ្លីៗ និងមើលវឌ្ឍនភាពរបស់អ្នក។ ចុច Start ដើម្បីចាប់ផ្តើម។')
WORDS_BUTTON, QUIZ_BUTTON, PROGRESS_BUTTON = 'ពាក្យប្រចាំថ្ងៃ', 'សំណួរខ្លីៗ', 'វឌ្ឍនភាពរបស់ខ្ញុំ'
MENU = {'keyboard': [[{'text': x}] for x in (WORDS_BUTTON, QUIZ_BUTTON, PROGRESS_BUTTON)], 'resize_keyboard': True}
# Stable indices are stored in SQLite; append new entries rather than reordering.
WORDS = [
    ('Hello', 'សួស្តី', 'Hello, my friend.', 'សួស្តី មិត្តរបស់ខ្ញុំ។'),
    ('Water', 'ទឹក', 'I drink water.', 'ខ្ញុំផឹកទឹក។'),
    ('Book', 'សៀវភៅ', 'This is my book.', 'នេះជាសៀវភៅរបស់ខ្ញុំ។'),
    ('School', 'សាលារៀន', 'I go to school.', 'ខ្ញុំទៅសាលារៀន។'),
    ('Friend', 'មិត្តភក្តិ', 'She is my friend.', 'នាងជាមិត្តភក្តិរបស់ខ្ញុំ។'),
    ('House', 'ផ្ទះ', 'This is a big house.', 'នេះជាផ្ទះធំមួយ។'),
    ('Food', 'អាហារ', 'The food is good.', 'អាហារនេះឆ្ងាញ់។'),
    ('Read', 'អាន', 'I read a book.', 'ខ្ញុំអានសៀវភៅ។'),
    ('Write', 'សរសេរ', 'Please write your name.', 'សូមសរសេរឈ្មោះរបស់អ្នក។'),
    ('Learn', 'រៀន', 'I learn English.', 'ខ្ញុំរៀនភាសាអង់គ្លេស។'),
    ('Morning', 'ពេលព្រឹក', 'I study in the morning.', 'ខ្ញុំរៀននៅពេលព្រឹក។'),
    ('Night', 'ពេលយប់', 'I sleep at night.', 'ខ្ញុំគេងនៅពេលយប់។'),
    ('Happy', 'រីករាយ', 'I am happy.', 'ខ្ញុំរីករាយ។'),
    ('Small', 'តូច', 'The bag is small.', 'កាបូបនេះតូច។'),
    ('Big', 'ធំ', 'The tree is big.', 'ដើមឈើនេះធំ។'),
    ('Today', 'ថ្ងៃនេះ', 'I am at home today.', 'ថ្ងៃនេះខ្ញុំនៅផ្ទះ។'),
    ('Tomorrow', 'ថ្ងៃស្អែក', 'See you tomorrow.', 'ជួបគ្នាថ្ងៃស្អែក។'),
    ('Family', 'គ្រួសារ', 'I love my family.', 'ខ្ញុំស្រឡាញ់គ្រួសាររបស់ខ្ញុំ។'),
    ('Work', 'ធ្វើការ', 'I work every day.', 'ខ្ញុំធ្វើការរាល់ថ្ងៃ។'),
    ('Listen', 'ស្តាប់', 'Please listen carefully.', 'សូមស្តាប់ដោយយកចិត្តទុកដាក់។'),
    ('Speak', 'និយាយ', 'I speak Khmer.', 'ខ្ញុំនិយាយភាសាខ្មែរ។'),
    ('Come', 'មក', 'Please come here.', 'សូមមកទីនេះ។'),
    ('Go', 'ទៅ', 'I go home.', 'ខ្ញុំទៅផ្ទះ។'),
    ('Buy', 'ទិញ', 'I buy fruit.', 'ខ្ញុំទិញផ្លែឈើ។'),
    ('Help', 'ជួយ', 'Please help me.', 'សូមជួយខ្ញុំ។'),
    ('Time', 'ពេលវេលា', 'We have time.', 'យើងមានពេលវេលា។'),
    ('Beautiful', 'ស្រស់ស្អាត', 'The flower is beautiful.', 'ផ្កានេះស្រស់ស្អាត។'),
    ('Clean', 'ស្អាត', 'The room is clean.', 'បន្ទប់នេះស្អាត។'),
    ('New', 'ថ្មី', 'This is a new pen.', 'នេះជាប៊ិចថ្មីមួយ។'),
    ('Old', 'ចាស់', 'This is an old house.', 'នេះជាផ្ទះចាស់មួយ។'),
]
STOP = threading.Event()


class APIError(Exception):
    def __init__(self, code, retry_after=3):
        self.code, self.retry_after = code, retry_after
        super().__init__(f'Telegram API error {code}')  # Never log token-bearing URLs.


class Telegram:
    def __init__(self, token):
        self.url = f'https://api.telegram.org/bot{token}/'

    def call(self, method, **payload):
        request = urllib.request.Request(self.url + method, json.dumps(payload).encode(),
                                         {'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                data = json.load(exc)
            except (ValueError, OSError):
                raise APIError(exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise APIError(503) from None
        if not data.get('ok'):
            raise APIError(data.get('error_code', 503), data.get('parameters', {}).get('retry_after', 3))
        return data['result']


class LearningBot:
    def __init__(self, api, path):
        self.api = api
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS lessons(user INTEGER, day TEXT, PRIMARY KEY(user, day));
            CREATE TABLE IF NOT EXISTS quizzes(id TEXT PRIMARY KEY, user INTEGER, word INTEGER,
                choices TEXT, answer INTEGER);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value INTEGER);
        ''')

    def send(self, chat, text, markup=MENU):
        return self.api.call('sendMessage', chat_id=chat, text=text, reply_markup=markup)

    def handle(self, update):
        if 'callback_query' in update:
            return self.answer(update['callback_query'])
        message = update.get('message', {})
        if message.get('chat', {}).get('type') != 'private':
            return
        user = message['from']['id']
        text = message.get('text', '').strip()
        command = text.split()[0].split('@')[0].lower() if text else ''
        if command in ('/start', '/help', '/menu'):
            self.send(user, f'សូមស្វាគមន៍មកកាន់ {NAME}!\n\n'
                      'រៀនពាក្យអង់គ្លេសជាមួយអត្ថន័យជាភាសាខ្មែរ សាកល្បងសំណួរ និងមើលវឌ្ឍនភាព។\n'
                      'ជ្រើសរើសប៊ូតុងខាងក្រោមដើម្បីចាប់ផ្តើម។\n\n/privacy — ព័ត៌មានឯកជនភាព\n/delete_me — លុបទិន្នន័យ')
        elif command == '/words' or text == WORDS_BUTTON:
            today = datetime.now(ZoneInfo('Asia/Phnom_Penh')).date()
            indices = [(today.toordinal() * 3 + i) % len(WORDS) for i in range(3)]
            lesson = '\n\n'.join(f'{WORDS[i][0]} — {WORDS[i][1]}\n{WORDS[i][2]}\n{WORDS[i][3]}' for i in indices)
            self.send(user, 'ពាក្យប្រចាំថ្ងៃ\n\n' + lesson + '\n\nពាក្យថ្មីប្តូររៀងរាល់ថ្ងៃតាមម៉ោងកម្ពុជា។')
            with self.db:
                self.db.execute('INSERT OR IGNORE INTO lessons VALUES (?, ?)', (user, str(today)))
        elif command == '/quiz' or text == QUIZ_BUTTON:
            word = random.randrange(len(WORDS))
            choices = random.sample([i for i in range(len(WORDS)) if i != word], 2) + [word]
            random.shuffle(choices)
            quiz_id = secrets.token_hex(8)
            with self.db:
                self.db.execute('DELETE FROM quizzes WHERE user=? AND answer IS NULL', (user,))
                self.db.execute('INSERT INTO quizzes VALUES (?, ?, ?, ?, NULL)',
                                (quiz_id, user, word, json.dumps(choices)))
            buttons = [[{'text': WORDS[i][1], 'callback_data': f'q:{quiz_id}:{n}'}] for n, i in enumerate(choices)]
            self.send(user, f'តើពាក្យ «{WORDS[word][0]}» មានន័យដូចម្តេច?', {'inline_keyboard': buttons})
        elif command == '/progress' or text == PROGRESS_BUTTON:
            days = self.db.execute('SELECT COUNT(*) FROM lessons WHERE user=?', (user,)).fetchone()[0]
            total, correct = self.db.execute('SELECT COUNT(answer), COALESCE(SUM(answer), 0) FROM quizzes WHERE user=?', (user,)).fetchone()
            self.send(user, f'វឌ្ឍនភាពរបស់អ្នក\n\nថ្ងៃដែលបានរៀន៖ {days}\nសំណួរដែលបានឆ្លើយ៖ {total}\n'
                      f'ចម្លើយត្រឹមត្រូវ៖ {correct}\nភាពត្រឹមត្រូវ៖ {round(correct / total * 100) if total else 0}%')
        elif command == '/privacy':
            self.send(user, 'បូតរក្សាទុកលេខសម្គាល់ Telegram របស់អ្នក ថ្ងៃដែលបានរៀន និងលទ្ធផលសំណួរ '
                      'ដើម្បីបង្ហាញវឌ្ឍនភាព។ បូតមិនរក្សាទុកឈ្មោះ លេខទូរស័ព្ទ ឬសារផ្សេងៗទេ។ '
                      'ប្រើ /delete_me ដើម្បីលុបទិន្នន័យរបស់អ្នក។')
        elif command == '/delete_me':
            with self.db:
                self.db.execute('DELETE FROM lessons WHERE user=?', (user,))
                self.db.execute('DELETE FROM quizzes WHERE user=?', (user,))
            self.send(user, 'ទិន្នន័យរបស់អ្នកត្រូវបានលុបរួចហើយ។')
        else:
            self.send(user, 'សូមជ្រើសរើសប៊ូតុងខាងក្រោម ឬប្រើ /help ដើម្បីមើលរបៀបប្រើ។')

    def answer(self, callback):
        self.api.call('answerCallbackQuery', callback_query_id=callback['id'])
        user = callback['from']['id']
        parts = callback.get('data', '').split(':')
        if len(parts) != 3 or parts[0] != 'q' or parts[2] not in ('0', '1', '2'):
            return
        row = self.db.execute('SELECT word, choices, answer FROM quizzes WHERE id=? AND user=?', (parts[1], user)).fetchone()
        if row is None or row[2] is not None:
            self.send(user, 'សំណួរនេះបានបញ្ចប់ហើយ។ ចុច «សំណួរខ្លីៗ» ដើម្បីបន្ត។')
            return
        word, choices, _ = row
        correct = int(json.loads(choices)[int(parts[2])] == word)
        with self.db:
            self.db.execute('UPDATE quizzes SET answer=? WHERE id=? AND answer IS NULL', (correct, parts[1]))
        entry = WORDS[word]
        self.send(user, ('ត្រឹមត្រូវ!' if correct else 'មិនទាន់ត្រឹមត្រូវទេ។') +
                  f'\n\n{entry[0]} មានន័យថា «{entry[1]}»។\n{entry[2]}\n{entry[3]}\n\nចុច «សំណួរខ្លីៗ» ដើម្បីបន្ត។')

    def run(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='offset'").fetchone()
        offset = row[0] if row else 0
        while not STOP.is_set():
            try:
                updates = self.api.call('getUpdates', offset=offset, timeout=25,
                                        allowed_updates=['message', 'callback_query'])
                for update in updates:
                    try:
                        self.handle(update)
                    except APIError as exc:
                        if exc.code not in (400, 403):
                            raise
                        logging.warning('Skipped unavailable chat or expired request: %s', exc.code)
                    offset = update['update_id'] + 1
                    with self.db:
                        self.db.execute("INSERT OR REPLACE INTO settings VALUES ('offset', ?)", (offset,))
            except APIError as exc:
                if exc.code in (401, 409):
                    raise SystemExit('Invalid token or polling conflict. Check BOT_TOKEN and run only one instance.') from None
                logging.warning('Telegram temporarily unavailable (%s); retrying.', exc.code)
                STOP.wait(max(1, exc.retry_after))


def main():
    token = os.environ.get('BOT_TOKEN', '').strip()
    if not token:
        raise SystemExit('Set BOT_TOKEN in your hosting environment before starting.')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: STOP.set())
    api = Telegram(token)
    bot = LearningBot(api, os.environ.get('DB_PATH', 'data/progress.sqlite3'))
    try:
        api.call('getMe')
        if api.call('getWebhookInfo').get('url'):
            raise SystemExit('An active webhook exists. Remove it before running this polling bot.')
        for method, payload in [
            ('setMyName', {'name': NAME}),
            ('setMyDescription', {'description': DESCRIPTION}),
            ('setMyShortDescription', {'short_description': ABOUT}),
            ('setMyCommands', {'commands': [
                {'command': 'start', 'description': 'ចាប់ផ្តើម'},
                {'command': 'words', 'description': WORDS_BUTTON},
                {'command': 'quiz', 'description': QUIZ_BUTTON},
                {'command': 'progress', 'description': PROGRESS_BUTTON},
                {'command': 'help', 'description': 'ជំនួយ'},
                {'command': 'privacy', 'description': 'ឯកជនភាព'},
                {'command': 'delete_me', 'description': 'លុបទិន្នន័យរបស់ខ្ញុំ'},
            ]}),
        ]:
            api.call(method, **payload)
        logging.info('SB24GZ Official started.')
        bot.run()
    except APIError as exc:
        raise SystemExit(f'Startup failed: Telegram API {exc.code}. Check connectivity and BOT_TOKEN.') from None
    finally:
        bot.db.close()


if __name__ == '__main__':
    main()
