from pymongo import MongoClient
from datetime import datetime
import json
from bson import ObjectId

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class Database:
    def __init__(self, uri):
        self.client = MongoClient(uri)
        self.db = self.client['neet_quiz_bot']
        self.users = self.db['users']
        self.questions = self.db['questions']
        self.quiz_results = self.db['quiz_results']
        self.custom_topics = self.db['custom_topics']
    
    def add_user(self, user_id, username, first_name, last_name=""):
        if not self.users.find_one({'user_id': user_id}):
            self.users.insert_one({
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'joined_date': datetime.now(),
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
                'topic_stats': {},
                'last_activity': datetime.now()
            })
        else:
            self.users.update_one(
                {'user_id': user_id},
                {'$set': {'last_activity': datetime.now()}}
            )
    
    def add_questions(self, questions_list, uploaded_by, topic_name=None):
        added_count = 0
        for question in questions_list:
            question['uploaded_by'] = uploaded_by
            question['uploaded_at'] = datetime.now()
            question['times_used'] = 0
            question['times_answered_correctly'] = 0
            if topic_name:
                question['topic'] = topic_name
            self.questions.insert_one(question)
            added_count += 1
        return added_count
    
    def get_random_questions(self, count=5, chapter=None, topic=None, difficulty=None):
        query = {'subject': 'Biology'}
        
        if chapter and chapter != "Mixed":
            query['chapter'] = chapter
        if topic and topic != "Mixed":
            query['topic'] = topic
        if difficulty and difficulty != "Mixed":
            query['difficulty'] = difficulty
        
        pipeline = [
            {'$match': query},
            {'$sample': {'size': count}}
        ]
        
        questions = list(self.questions.aggregate(pipeline))
        return questions
    
    def get_chapters(self):
        pipeline = [
            {'$match': {'subject': 'Biology'}},
            {'$group': {'_id': '$chapter', 'count': {'$sum': 1}}}
        ]
        results = list(self.questions.aggregate(pipeline))
        return {r['_id']: r['count'] for r in results if r['_id']}
    
    def get_topics(self):
        pipeline = [
            {'$match': {'subject': 'Biology', 'topic': {'$exists': True}}},
            {'$group': {'_id': '$topic', 'count': {'$sum': 1}}}
        ]
        results = list(self.questions.aggregate(pipeline))
        return {r['_id']: r['count'] for r in results if r['_id']}
    
    def save_quiz_result(self, user_id, quiz_data, chat_type='private', group_id=None):
        result = {
            'user_id': user_id,
            'chat_type': chat_type,
            'group_id': group_id,
            'timestamp': datetime.now(),
            'score': quiz_data['score'],
            'total_questions': quiz_data['total_questions'],
            'percentage': quiz_data['percentage'],
            'chapter': quiz_data.get('chapter', 'Mixed'),
            'topic': quiz_data.get('topic', 'Mixed'),
            'difficulty': quiz_data.get('difficulty', 'Mixed'),
            'answers': quiz_data['answers']
        }
        self.quiz_results.insert_one(result)
        
        user = self.users.find_one({'user_id': user_id})
        if user:
            total_quizzes = user['total_quizzes_taken'] + 1
            total_questions = user['total_questions_answered'] + quiz_data['total_questions']
            correct_answers = user['correct_answers'] + quiz_data['score']
            average_score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            update_data = {
                'total_quizzes_taken': total_quizzes,
                'total_questions_answered': total_questions,
                'correct_answers': correct_answers,
                'average_score': average_score,
                'last_activity': datetime.now()
            }
            
            # Update difficulty progress
            for answer in quiz_data['answers']:
                difficulty = answer.get('difficulty', 'Easy')
                if difficulty in user['difficulty_progress']:
                    update_data[f'difficulty_progress.{difficulty}.attempted'] = user['difficulty_progress'][difficulty]['attempted'] + 1
                    if answer['correct']:
                        update_data[f'difficulty_progress.{difficulty}.correct'] = user['difficulty_progress'][difficulty]['correct'] + 1
                
                # Update chapter stats
                chapter = answer.get('chapter', 'Unknown')
                if chapter not in user['chapter_stats']:
                    user['chapter_stats'][chapter] = {'attempted': 0, 'correct': 0}
                update_data[f'chapter_stats.{chapter}.attempted'] = user['chapter_stats'][chapter]['attempted'] + 1
                if answer['correct']:
                    update_data[f'chapter_stats.{chapter}.correct'] = user['chapter_stats'][chapter]['correct'] + 1
                
                # Update topic stats
                topic = answer.get('topic', 'General')
                if topic not in user['topic_stats']:
                    user['topic_stats'][topic] = {'attempted': 0, 'correct': 0}
                update_data[f'topic_stats.{topic}.attempted'] = user['topic_stats'][topic]['attempted'] + 1
                if answer['correct']:
                    update_data[f'topic_stats.{topic}.correct'] = user['topic_stats'][topic]['correct'] + 1
            
            # Update difficulty level based on performance
            if quiz_data['percentage'] >= 80:
                update_data['current_difficulty'] = 'Hard'
            elif quiz_data['percentage'] >= 60:
                update_data['current_difficulty'] = 'Medium'
            else:
                update_data['current_difficulty'] = 'Easy'
            
            self.users.update_one({'user_id': user_id}, {'$set': update_data})
    
    def get_user_stats(self, user_id):
        return self.users.find_one({'user_id': user_id})
    
    def get_recent_results(self, user_id, limit=5):
        return list(self.quiz_results.find({'user_id': user_id}).sort('timestamp', -1).limit(limit))
    
    def get_all_results(self, user_id, limit=50):
        return list(self.quiz_results.find({'user_id': user_id}).sort('timestamp', -1).limit(limit))
