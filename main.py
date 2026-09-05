from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
import json
from datetime import datetime
from config import Config
from database import Database, JSONEncoder
from ai_handler import AIHandler

# Conversation states
SELECT_SUBJECT, SELECT_COUNT, ANSWERING, UPLOAD_QUESTIONS = range(4)

class NEETQuizBot:
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.MONGODB_URI)
        self.ai = AIHandler(self.config.OPENAI_API_KEY)
        self.user_quiz_data = {}
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name or "")
        
        keyboard = [
            [InlineKeyboardButton("📝 Start Quiz", callback_data='start_quiz')],
            [InlineKeyboardButton("📚 Choose Subject", callback_data='choose_subject')],
            [InlineKeyboardButton("📊 My Statistics", callback_data='my_stats')],
            [InlineKeyboardButton("🤖 AI Analysis", callback_data='ai_analysis')],
            [InlineKeyboardButton("📤 Upload Questions", callback_data='upload_instructions')],
            [InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = (
            f"👋 Welcome {user.first_name} to NEET Quiz Bot!\n\n"
            f"🏥 *Your Personal NEET Preparation Assistant*\n\n"
            f"*Features:*\n"
            f"✅ Customized quizzes by subject\n"
            f"✅ AI-powered explanations\n"
            f"✅ Progress tracking\n"
            f"✅ Performance analysis\n\n"
            f"*How to use:*\n"
            f"1️⃣ Click 'Start Quiz' for random questions\n"
            f"2️⃣ Choose specific subjects for targeted practice\n"
            f"3️⃣ Upload your own questions using JSON format\n"
            f"4️⃣ Get AI insights on your performance\n\n"
            f"Ready to begin? Choose an option below! 📚"
        )
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == 'start_quiz':
            keyboard = [
                [InlineKeyboardButton("Physics", callback_data='subject_Physics')],
                [InlineKeyboardButton("Chemistry", callback_data='subject_Chemistry')],
                [InlineKeyboardButton("Biology", callback_data='subject_Biology')],
                [InlineKeyboardButton("Mixed (All Subjects)", callback_data='subject_All')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📚 *Choose Subject for Quiz:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif query.data == 'choose_subject':
            keyboard = [
                [InlineKeyboardButton("Physics", callback_data='subject_Physics')],
                [InlineKeyboardButton("Chemistry", callback_data='subject_Chemistry')],
                [InlineKeyboardButton("Biology", callback_data='subject_Biology')],
                [InlineKeyboardButton("Mixed (All Subjects)", callback_data='subject_All')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📚 *Choose Subject for Quiz:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif query.data.startswith('subject_'):
            subject = query.data.replace('subject_', '')
            await self.start_quiz(update, context, subject)
        
        elif query.data == 'my_stats':
            await self.show_stats(update, context)
        
        elif query.data == 'ai_analysis':
            await self.show_ai_analysis(update, context)
        
        elif query.data == 'upload_instructions':
            await self.show_upload_instructions(update, context)
        
        elif query.data == 'help':
            await self.show_help(update, context)
        
        elif query.data.startswith('answer_'):
            await self.check_answer(update, context)
        
        elif query.data == 'next_question':
            await self.send_question(update, context)
    
    async def start_quiz(self, update, context, subject):
        query = update.callback_query
        user_id = query.from_user.id
        
        questions = self.db.get_random_questions(count=5, subject=subject)
        
        if not questions:
            keyboard = [[InlineKeyboardButton("📤 Upload Questions", callback_data='upload_instructions')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"❌ No questions available for {subject}!\n\n"
                f"Please upload questions first or try another subject.",
                reply_markup=reply_markup
            )
            return
        
        self.user_quiz_data[user_id] = {
            'questions': questions,
            'current_index': 0,
            'score': 0,
            'answers': [],
            'subject': subject,
            'start_time': datetime.now()
        }
        
        await self.send_question(update, context)
    
    async def send_question(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id not in self.user_quiz_data:
            await query.edit_message_text("No active quiz. Start a new quiz!")
            return
        
        quiz_data = self.user_quiz_data[user_id]
        current_index = quiz_data['current_index']
        
        if current_index >= len(quiz_data['questions']):
            await self.finish_quiz(update, context)
            return
        
        current_q = quiz_data['questions'][current_index]
        
        options = current_q['options']
        if isinstance(options, dict):
            options_text = "\n".join([f"{key}. {value}" for key, value in options.items()])
            keyboard = [[InlineKeyboardButton(f"{key}", callback_data=f'answer_{key}')] for key in options.keys()]
        else:
            options_text = str(options)
            keyboard = [[InlineKeyboardButton("A", callback_data='answer_A')]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"*Question {current_index + 1}/{len(quiz_data['questions'])}*\n"
            f"*Subject:* {current_q.get('subject', 'N/A')}\n"
            f"*Chapter:* {current_q.get('chapter', 'N/A')}\n\n"
            f"{current_q['question']}\n\n"
            f"{options_text}"
        )
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def check_answer(self, update, context):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        selected_answer = query.data.replace('answer_', '')
        
        if user_id not in self.user_quiz_data:
            await query.edit_message_text("No active quiz. Start a new quiz!")
            return
        
        quiz_data = self.user_quiz_data[user_id]
        current_q = quiz_data['questions'][quiz_data['current_index']]
        correct_answer = current_q['correct_answer']
        
        is_correct = selected_answer == correct_answer
        
        if is_correct:
            quiz_data['score'] += 1
            response = "✅ *Correct!*"
        else:
            response = f"❌ *Wrong!* Correct answer: {correct_answer}"
        
        # Get AI explanation
        explanation = self.ai.generate_explanation(
            current_q['question'],
            current_q['correct_answer'],
            current_q['options']
        )
        
        quiz_data['answers'].append({
            'question': current_q['question'],
            'subject': current_q.get('subject', 'Unknown'),
            'selected': selected_answer,
            'correct_answer': correct_answer,
            'correct': is_correct
        })
        
        message = (
            f"{response}\n\n"
            f"📚 *Explanation:*\n{explanation}\n\n"
            f"*Score:* {quiz_data['score']}/{quiz_data['current_index'] + 1}"
        )
        
        quiz_data['current_index'] += 1
        
        if quiz_data['current_index'] < len(quiz_data['questions']):
            keyboard = [[InlineKeyboardButton("Next Question ➡️", callback_data='next_question')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                message + "\n\nReady for next question?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(message, parse_mode='Markdown')
            keyboard = [[InlineKeyboardButton("View Results 🎉", callback_data='finish_quiz')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "Quiz complete!",
                reply_markup=reply_markup
            )
    
    async def finish_quiz(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id not in self.user_quiz_data:
            await query.edit_message_text("No active quiz. Start a new quiz!")
            return
        
        quiz_data = self.user_quiz_data[user_id]
        total_questions = len(quiz_data['questions'])
        score = quiz_data['score']
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        
        time_taken = (datetime.now() - quiz_data['start_time']).total_seconds() / 60
        
        self.db.save_quiz_result(user_id, {
            'score': score,
            'total_questions': total_questions,
            'percentage': percentage,
            'subject': quiz_data['subject'],
            'time_taken': time_taken,
            'answers': quiz_data['answers']
        })
        
        if percentage >= 80:
            emoji = "🌟"
            comment = "Excellent! You're NEET ready!"
        elif percentage >= 60:
            emoji = "👍"
            comment = "Good job! Keep practicing!"
        else:
            emoji = "📚"
            comment = "Keep practicing! You'll improve!"
        
        message = (
            f"🎉 *Quiz Completed!*\n\n"
            f"*Subject:* {quiz_data['subject']}\n"
            f"*Score:* {score}/{total_questions}\n"
            f"*Percentage:* {percentage:.1f}%\n"
            f"*Time Taken:* {time_taken:.1f} minutes\n\n"
            f"{emoji} {comment}"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 View Stats", callback_data='my_stats')],
            [InlineKeyboardButton("🤖 AI Analysis", callback_data='ai_analysis')],
            [InlineKeyboardButton("📝 Take Another Quiz", callback_data='start_quiz')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        del self.user_quiz_data[user_id]
    
    async def show_stats(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        
        user_data = self.db.get_user_stats(user_id)
        recent_results = self.db.get_recent_results(user_id, 5)
        
        if not user_data:
            await query.edit_message_text("No statistics available. Take a quiz first!")
            return
        
        message = (
            f"📊 *Your Statistics*\n\n"
            f"*Total Quizzes:* {user_data['total_quizzes_taken']}\n"
            f"*Total Questions:* {user_data['total_questions_answered']}\n"
            f"*Correct Answers:* {user_data['correct_answers']}\n"
            f"*Average Score:* {user_data['average_score']:.1f}%\n\n"
            f"*Subject Performance:*\n"
        )
        
        for subject, stats in user_data['subject_stats'].items():
            attempted = stats['attempted']
            correct = stats['correct']
            accuracy = (correct / attempted * 100) if attempted > 0 else 0
            message += f"• {subject}: {accuracy:.1f}% ({correct}/{attempted})\n"
        
        if recent_results:
            message += f"\n*Recent Results:*\n"
            for result in recent_results:
                message += f"• {result['percentage']:.1f}% - {result['subject']} ({result['timestamp'].strftime('%d/%m/%Y')})\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_ai_analysis(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        
        user_data = self.db.get_user_stats(user_id)
        user_history = self.db.get_all_results(user_id, 10)
        
        if not user_history:
            await query.edit_message_text("No quiz history available for AI analysis. Take a quiz first!")
            return
        
        await query.edit_message_text("🤖 *Analyzing your performance...*", parse_mode='Markdown')
        
        analysis = self.ai.analyze_performance(
            json.loads(json.dumps(user_history, cls=JSONEncoder)),
            user_data['subject_stats'] if user_data else {}
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🤖 *AI Performance Analysis*\n\n{analysis}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_upload_instructions(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != self.config.ADMIN_USER_ID:
            await query.edit_message_text(
                "⚠️ *Admin Only Feature*\n\n"
                "Only the bot admin can upload questions.",
                parse_mode='Markdown'
            )
            return
        
        format_example = {
            "questions": [
                {
                    "question": "Which of the following is the powerhouse of the cell?",
                    "options": {
                        "A": "Nucleus",
                        "B": "Mitochondria",
                        "C": "Ribosome",
                        "D": "Golgi apparatus"
                    },
                    "correct_answer": "B",
                    "subject": "Biology",
                    "chapter": "Cell Biology",
                    "difficulty": "Easy"
                }
            ]
        }
        
        message = (
            "📋 *Question Upload Format*\n\n"
            "Send questions in JSON format using /upload command\n\n"
            "*Example Format:*\n"
            "```json\n"
            f"{json.dumps(format_example, indent=2)}\n"
            "```\n\n"
            "*Rules:*\n"
            "• Must have exactly 4 options (A, B, C, D)\n"
            "• Correct answer must be A, B, C, or D\n"
            "• Subject: Physics, Chemistry, or Biology\n"
            "• Difficulty: Easy, Medium, or Hard\n\n"
            "*To upload:*\n"
            "Type /upload followed by JSON"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_help(self, update, context):
        query = update.callback_query
        
        message = (
            "❓ *Help & Instructions*\n\n"
            "*Commands:*\n"
            "/start - Start the bot\n"
            "/upload - Upload questions (Admin only)\n"
            "/format - Show question format\n"
            "/stats - View your statistics\n"
            "/cancel - Cancel current operation\n\n"
            "*Features:*\n"
            "• Subject-wise quizzes\n"
            "• AI explanations\n"
            "• Performance tracking\n"
            "• AI analysis\n\n"
            "*Subjects:*\n"
            "• Physics\n"
            "• Chemistry\n"
            "• Biology"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def back_to_menu(self, update, context):
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📝 Start Quiz", callback_data='start_quiz')],
            [InlineKeyboardButton("📚 Choose Subject", callback_data='choose_subject')],
            [InlineKeyboardButton("📊 My Statistics", callback_data='my_stats')],
            [InlineKeyboardButton("🤖 AI Analysis", callback_data='ai_analysis')],
            [InlineKeyboardButton("📤 Upload Questions", callback_data='upload_instructions')],
            [InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏥 *NEET Quiz Bot Main Menu*\n\nChoose an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def upload_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id != self.config.ADMIN_USER_ID:
            await update.message.reply_text(
                "⚠️ *Admin Only Feature*\n\n"
                "Only the bot admin can upload questions.",
                parse_mode='Markdown'
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "📋 *Upload Questions*\n\n"
                "Send JSON after /upload command\n"
                "Example:\n"
                "/upload {\"questions\": [...]}\n\n"
                "Use /format to see the exact format",
                parse_mode='Markdown'
            )
            return
        
        try:
            json_text = ' '.join(context.args)
            question_data = json.loads(json_text)
            
            if 'questions' in question_data:
                questions = question_data['questions']
            else:
                questions = [question_data]
            
            valid_questions = []
            errors = []
            
            for q in questions:
                required = ['question', 'options', 'correct_answer', 'subject', 'chapter', 'difficulty']
                missing = [field for field in required if field not in q]
                
                if missing:
                    errors.append(f"Missing fields: {', '.join(missing)}")
                    continue
                
                if len(q['options']) != 4:
                    errors.append("Each question must have exactly 4 options")
                    continue
                
                if q['correct_answer'] not in ['A', 'B', 'C', 'D']:
                    errors.append("Correct answer must be A, B, C, or D")
                    continue
                
                valid_questions.append(q)
            
            if valid_questions:
                added = self.db.add_questions(valid_questions, user_id)
                await update.message.reply_text(
                    f"✅ Successfully uploaded {added} questions!",
                    parse_mode='Markdown'
                )
            
            if errors:
                await update.message.reply_text(
                    f"⚠️ {len(errors)} questions failed:\n" + "\n".join(errors[:5]),
                    parse_mode='Markdown'
                )
        
        except json.JSONDecodeError:
            await update.message.reply_text(
                "❌ Invalid JSON format!\n"
                "Use /format to see the correct format",
                parse_mode='Markdown'
            )
    
    async def format_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        format_example = {
            "questions": [
                {
                    "question": "Which of the following is the powerhouse of the cell?",
                    "options": {
                        "A": "Nucleus",
                        "B": "Mitochondria",
                        "C": "Ribosome",
                        "D": "Golgi apparatus"
                    },
                    "correct_answer": "B",
                    "subject": "Biology",
                    "chapter": "Cell Biology",
                    "difficulty": "Easy"
                }
            ]
        }
        
        await update.message.reply_text(
            "📋 *Question Format*\n\n"
            "```json\n"
            f"{json.dumps(format_example, indent=2)}\n"
            "```",
            parse_mode='Markdown'
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_stats(user_id)
        
        if not user_data:
            await update.message.reply_text("No statistics available. Take a quiz first!")
            return
        
        message = (
            f"📊 *Your Statistics*\n\n"
            f"Total Quizzes: {user_data['total_quizzes_taken']}\n"
            f"Total Questions: {user_data['total_questions_answered']}\n"
            f"Average Score: {user_data['average_score']:.1f}%"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Operation cancelled. Use /start to begin again.")

def main():
    config = Config()
    bot = NEETQuizBot()
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("upload", bot.upload_command))
    application.add_handler(CommandHandler("format", bot.format_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    application.add_handler(CommandHandler("cancel", bot.cancel))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    application.run_polling()

if __name__ == '__main__':
    main()
