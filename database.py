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
                'subject_stats': {
                    'Physics': {'attempted': 0, 'correct': 0},
                    'Chemistry': {'attempted': 0, 'correct': 0},
                    'Biology': {'attempted': 0, 'correct': 0}
                },
                'last_activity': datetime.now()
            })
        else:
            self.users.update_one(
                {'user_id': user_id},
                {'$set': {'last_activity': datetime.now()}}
            )
    
    def add_questions(self, questions_list, uploaded_by):
        added_count = 0
        for question in questions_list:
            question['uploaded_by'] = uploaded_by
            question['uploaded_at'] = datetime.now()
            question['times_used'] = 0
            question['times_answered_correctly'] = 0
            self.questions.insert_one(question)
            added_count += 1
        return added_count
    
    def get_random_questions(self, count=10, subject=None):
        query = {}
        if subject and subject != "All":
            query['subject'] = subject
        
        pipeline = [
            {'$match': query},
            {'$sample': {'size': count}}
        ]
        
        questions = list(self.questions.aggregate(pipeline))
        return questions
    
    def save_quiz_result(self, user_id, quiz_data):
        result = {
            'user_id': user_id,
            'timestamp': datetime.now(),
            'score': quiz_data['score'],
            'total_questions': quiz_data['total_questions'],
            'percentage': quiz_data['percentage'],
            'subject': quiz_data.get('subject', 'Mixed'),
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
            
            for answer in quiz_data['answers']:
                subject = answer.get('subject', 'Unknown')
                if subject in user['subject_stats']:
                    update_data[f'subject_stats.{subject}.attempted'] = user['subject_stats'][subject]['attempted'] + 1
                    if answer['correct']:
                        update_data[f'subject_stats.{subject}.correct'] = user['subject_stats'][subject]['correct'] + 1
            
            self.users.update_one({'user_id': user_id}, {'$set': update_data})
    
    def get_user_stats(self, user_id):
        return self.users.find_one({'user_id': user_id})
    
    def get_recent_results(self, user_id, limit=5):
        return list(self.quiz_results.find({'user_id': user_id}).sort('timestamp', -1).limit(limit))
    
    def get_all_results(self, user_id, limit=50):
        return list(self.quiz_results.find({'user_id': user_id}).sort('timestamp', -1).limit(limit))
    
    def count_questions_by_subject(self):
        pipeline = [
            {'$group': {'_id': '$subject', 'count': {'$sum': 1}}}
        ]
        results = list(self.questions.aggregate(pipeline))
        return {r['_id']: r['count'] for r in results}
