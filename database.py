import json
import os
import random
from datetime import datetime

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class Database:
    def __init__(self, uri=None):
        self.data_file = 'bot_data.json'
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.users = data.get('users', {})
                self.questions = data.get('questions', [])
                self.quiz_results = data.get('quiz_results', [])
        else:
            self.users = {}
            self.questions = []
            self.quiz_results = []
            self.save_data()
    
    def save_data(self):
        data = {
            'users': self.users,
            'questions': self.questions,
            'quiz_results': self.quiz_results
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, cls=JSONEncoder, indent=2)
    
    def add_user(self, user_id, username, first_name, last_name=""):
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'joined_date': datetime.now().isoformat(),
                'total_quizzes_taken': 0,
                'total_questions_answered': 0,
                'correct_answers': 0,
                'average_score': 0,
                'current_difficulty': 'Easy',
                'difficulty_progress': {
                    'Easy': {'attempted': 0, 'correct': 0},
                    'Medium': {'attempted': 0, 'correct': 0},
                    'Hard': {'attempted': 0, 'correct': 0}
                },
                'chapter_stats': {},
                'topic_stats': {}
            }
            self.save_data()
    
    def add_questions(self, questions_list, uploaded_by, topic_name=None):
        added_count = 0
        for question in questions_list:
            question['uploaded_by'] = uploaded_by
            question['uploaded_at'] = datetime.now().isoformat()
            question['times_used'] = 0
            question['times_answered_correctly'] = 0
            if topic_name:
                question['topic'] = topic_name
            self.questions.append(question)
            added_count += 1
        self.save_data()
        return added_count
    
    def get_random_questions(self, count=5, chapter=None, topic=None, difficulty=None):
        filtered = []
        for q in self.questions:
            if q.get('subject') != 'Biology':
                continue
            if chapter and chapter != "Mixed" and q.get('chapter') != chapter:
                continue
            if topic and topic != "Mixed" and q.get('topic') != topic:
                continue
            if difficulty and difficulty != "Mixed" and q.get('difficulty') != difficulty:
                continue
            filtered.append(q)
        
        if len(filtered) <= count:
            return filtered
        
        return random.sample(filtered, count)
    
    def get_chapters(self):
        chapters = {}
        for q in self.questions:
            if q.get('subject') == 'Biology' and q.get('chapter'):
                chapter = q['chapter']
                chapters[chapter] = chapters.get(chapter, 0) + 1
        return chapters
    
    def get_topics(self):
        topics = {}
        for q in self.questions:
            if q.get('subject') == 'Biology' and q.get('topic'):
                topic = q['topic']
                topics[topic] = topics.get(topic, 0) + 1
        return topics
    
    def save_quiz_result(self, user_id, quiz_data, chat_type='private', group_id=None):
        user_id = str(user_id)
        result = {
            'user_id': user_id,
            'chat_type': chat_type,
            'group_id': group_id,
            'timestamp': datetime.now().isoformat(),
            'score': quiz_data['score'],
            'total_questions': quiz_data['total_questions'],
            'percentage': quiz_data['percentage'],
            'chapter': quiz_data.get('chapter', 'Mixed'),
            'topic': quiz_data.get('topic', 'Mixed'),
            'difficulty': quiz_data.get('difficulty', 'Mixed'),
            'answers': quiz_data['answers']
        }
        self.quiz_results.append(result)
        
        if user_id in self.users:
            user = self.users[user_id]
            user['total_quizzes_taken'] += 1
            user['total_questions_answered'] += quiz_data['total_questions']
            user['correct_answers'] += quiz_data['score']
            
            total_q = user['total_questions_answered']
            correct = user['correct_answers']
            user['average_score'] = (correct / total_q * 100) if total_q > 0 else 0
            
            for answer in quiz_data['answers']:
                difficulty = answer.get('difficulty', 'Easy')
                if difficulty in user['difficulty_progress']:
                    user['difficulty_progress'][difficulty]['attempted'] += 1
                    if answer['correct']:
                        user['difficulty_progress'][difficulty]['correct'] += 1
                
                chapter = answer.get('chapter', 'Unknown')
                if chapter not in user['chapter_stats']:
                    user['chapter_stats'][chapter] = {'attempted': 0, 'correct': 0}
                user['chapter_stats'][chapter]['attempted'] += 1
                if answer['correct']:
                    user['chapter_stats'][chapter]['correct'] += 1
                
                topic = answer.get('topic', 'General')
                if topic not in user['topic_stats']:
                    user['topic_stats'][topic] = {'attempted': 0, 'correct': 0}
                user['topic_stats'][topic]['attempted'] += 1
                if answer['correct']:
                    user['topic_stats'][topic]['correct'] += 1
            
            if quiz_data['percentage'] >= 80:
                user['current_difficulty'] = 'Hard'
            elif quiz_data['percentage'] >= 60:
                user['current_difficulty'] = 'Medium'
            else:
                user['current_difficulty'] = 'Easy'
        
        self.save_data()
    
    def get_user_stats(self, user_id):
        return self.users.get(str(user_id))
    
    def get_recent_results(self, user_id, limit=5):
        user_id = str(user_id)
        results = [r for r in self.quiz_results if r['user_id'] == user_id]
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return results[:limit]
    
    def get_all_results(self, user_id, limit=50):
        user_id = str(user_id)
        results = [r for r in self.quiz_results if r['user_id'] == user_id]
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return results[:limit]
