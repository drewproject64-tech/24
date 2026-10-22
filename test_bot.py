import json
import tempfile
import unittest
from pathlib import Path
from bot import LearningBot, WORDS_BUTTON, QUIZ_BUTTON, PROGRESS_BUTTON

class FakeAPI:
    def __init__(self):
        self.calls = []
    def call(self, method, **kwargs):
        self.calls.append((method, kwargs))
        return {'message_id': len(self.calls)}

class BotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.api = FakeAPI()
        self.path = str(Path(self.temp.name) / 'test.sqlite3')
        self.bot = LearningBot(self.api, self.path)
    def tearDown(self):
        self.bot.db.close()
        self.temp.cleanup()
    def message(self, text):
        self.bot.handle({'message': {'chat': {'id': 1, 'type': 'private'}, 'from': {'id': 1}, 'text': text}})
    def callback(self, data, user=1):
        self.bot.handle({'callback_query': {'id': 'test', 'from': {'id': user}, 'data': data}})
    def test_menu_lessons_restart_and_delete(self):
        self.message('/start')
        self.assertEqual(len(self.api.calls[-1][1]['reply_markup']['keyboard']), 3)
        self.message(WORDS_BUTTON)
        self.message('/words')
        self.assertEqual(self.bot.db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0], 1)
        self.bot.db.close()
        self.bot = LearningBot(self.api, self.path)
        self.message(PROGRESS_BUTTON)
        self.assertIn('៖ 1', self.api.calls[-1][1]['text'])
        self.message('/delete_me')
        self.assertEqual(self.bot.db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0], 0)
    def test_quiz_ownership_and_duplicate_answers(self):
        self.message(QUIZ_BUTTON)
        qid, word, choices = self.bot.db.execute('SELECT id, word, choices FROM quizzes').fetchone()
        answer = json.loads(choices).index(word)
        data = f'q:{qid}:{answer}'
        self.callback(data, user=2)
        self.assertIsNone(self.bot.db.execute('SELECT answer FROM quizzes').fetchone()[0])
        self.callback(data)
        self.callback(data)
        self.assertEqual(self.bot.db.execute('SELECT COUNT(answer), SUM(answer) FROM quizzes').fetchone(), (1, 1))
    def test_wrong_stale_and_malformed_answers(self):
        self.message('/quiz')
        qid, word, choices = self.bot.db.execute('SELECT id, word, choices FROM quizzes').fetchone()
        wrong = next(i for i, choice in enumerate(json.loads(choices)) if choice != word)
        self.callback(f'q:{qid}:{wrong}')
        self.assertEqual(self.bot.db.execute('SELECT answer FROM quizzes').fetchone()[0], 0)
        self.message('/quiz')
        old = self.bot.db.execute('SELECT id FROM quizzes WHERE answer IS NULL').fetchone()[0]
        self.message('/quiz')
        self.callback(f'q:{old}:0')
        self.callback('q:bad:900')
        self.assertEqual(self.bot.db.execute('SELECT COUNT(answer) FROM quizzes').fetchone()[0], 1)
    def test_fallback_and_commands(self):
        for text in ('/help', '/privacy', 'hello', '/unknown', ''):
            self.message(text)
            self.assertEqual(self.api.calls[-1][0], 'sendMessage')
        count = len(self.api.calls)
        self.bot.handle({'message': {'chat': {'type': 'group'}}})
        self.assertEqual(len(self.api.calls), count)

if __name__ == '__main__':
    unittest.main()
