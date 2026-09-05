import openai
import json

class AIHandler:
    def __init__(self, api_key):
        openai.api_key = api_key
        self.user_performance = {}
    
    def generate_explanation(self, question, correct_answer, options, chapter=None):
        try:
            prompt = f"""
            You are a NEET Biology expert. Provide a detailed explanation for this question.
            
            Question: {question}
            Options: {json.dumps(options)}
            Correct Answer: {correct_answer}
            Chapter: {chapter or 'General Biology'}
            
            Please provide:
            1. Why this answer is correct
            2. Key concept tested
            3. Common mistakes students make
            4. Quick revision tip
            
            Keep it concise but comprehensive.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert NEET Biology tutor."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"{correct_answer} is the correct answer."
    
    def analyze_performance(self, user_history, user_stats):
        try:
            prompt = f"""
            Analyze this NEET Biology student's performance:
            
            Recent Quiz Results: {json.dumps(user_history, default=str)}
            User Statistics: {json.dumps(user_stats, default=str)}
            
            Provide:
            1. Overall performance assessment
            2. Chapter-wise strengths and weaknesses
            3. Difficulty level analysis
            4. Specific topics to focus on
            5. Study strategy recommendations
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert NEET Biology coach."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return "Unable to generate AI analysis. Please try again later."
    
    def generate_difficulty_question(self, difficulty, topic=None):
        try:
            prompt = f"""
            Create a NEET Biology MCQ with:
            Difficulty: {difficulty}
            Topic: {topic or 'Any Biology topic'}
            
            Format as JSON:
            {{
                "question": "...",
                "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
                "correct_answer": "A/B/C/D",
                "chapter": "...",
                "difficulty": "{difficulty}",
                "explanation": "..."
            }}
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert NEET Biology question creator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.8
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return None
