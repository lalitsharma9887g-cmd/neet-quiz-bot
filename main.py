import asyncio
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import Config
from database import Database, JSONEncoder
from ai_handler import AIHandler

class NEETBiologyBot:
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.MONGODB_URI)
        self.ai = AIHandler(self.config.OPENAI_API_KEY)
        self.user_quiz_data = {}
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_type = update.effective_chat.type
        self.db.add_user(user.id, user.username, user.first_name, user.last_name or "")
        
        keyboard = [
            [InlineKeyboardButton("📝 Start Biology Quiz", callback_data='start_quiz')],
            [InlineKeyboardButton("📚 Choose Chapter", callback_data='choose_chapter')],
            [InlineKeyboardButton("🏷️ Custom Topics", callback_data='choose_topic')],
            [InlineKeyboardButton("📊 My Statistics", callback_data='my_stats')],
            [InlineKeyboardButton("🤖 AI Analysis", callback_data='ai_analysis')],
            [InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        
        if user.id == self.config.ADMIN_USER_ID:
            keyboard.append([InlineKeyboardButton("📤 Upload Questions", callback_data='upload_instructions')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = (
            f"👋 Welcome {user.first_name} to NEET Biology Bot!\n\n"
            f"🧬 *Your Ultimate Biology Preparation Assistant*\n\n"
            f"*Features:*\n"
            f"✅ Biology quizzes by chapter\n"
            f"✅ Custom topic quizzes\n"
            f"✅ Dynamic difficulty (Easy → Medium → Hard)\n"
            f"✅ AI-powered explanations\n"
            f"✅ Works in groups & private chat\n"
            f"✅ Performance tracking\n\n"
            f"*How to use:*\n"
            f"1️⃣ Click 'Start Quiz' for mixed questions\n"
            f"2️⃣ Choose specific chapters or topics\n"
            f"3️⃣ Answer questions to increase difficulty\n"
            f"4️⃣ Get AI insights on your performance\n\n"
            f"Ready to begin? Choose an option! 📚"
        )
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if query.data == 'start_quiz':
            keyboard = [
                [InlineKeyboardButton("🎲 Random (Any Chapter)", callback_data='chapter_Mixed')],
                [InlineKeyboardButton("📚 Choose Chapter", callback_data='choose_chapter')],
                [InlineKeyboardButton("🏷️ Choose Topic", callback_data='choose_topic')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🧬 *Start Biology Quiz*\n\nChoose your quiz mode:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif query.data == 'choose_chapter':
            chapters = self.db.get_chapters()
            if not chapters:
                await query.edit_message_text(
                    "❌ No questions available!\n\nAdmin needs to upload questions first."
                )
                return
            
            keyboard = []
            for chapter in list(chapters.keys())[:10]:
                keyboard.append([InlineKeyboardButton(f"📖 {chapter}", callback_data=f'chapter_{chapter}')])
            
            keyboard.append([InlineKeyboardButton("🎲 Mixed (All Chapters)", callback_data='chapter_Mixed')])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_menu')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📚 *Choose Biology Chapter:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif query.data == 'choose_topic':
            topics = self.db.get_topics()
            if not topics:
                await query.edit_message_text(
                    "❌ No custom topics available!\n\nAdmin can upload questions with custom topics."
                )
                return
            
            keyboard = []
            for topic in list(topics.keys())[:10]:
                keyboard.append([InlineKeyboardButton(f"🏷️ {topic}", callback_data=f'topic_{topic}')])
            
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back_to_menu')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🏷️ *Choose Custom Topic:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif query.data.startswith('chapter_'):
            chapter = query.data.replace('chapter_', '')
            await self.start_quiz(update, context, chapter=chapter)
        
        elif query.data.startswith('topic_'):
            topic = query.data.replace('topic_', '')
            await self.start_quiz(update, context, topic=topic)
        
        elif query.data == 'my_stats':
            await self.show_stats(update, context)
        
        elif query.data == 'ai_analysis':
            await self.show_ai_analysis(update, context)
        
        elif query.data == 'upload_instructions':
            await self.show_upload_instructions(update, context)
        
        elif query.data == 'help':
            await self.show_help(update, context)
        
        elif query.data == 'back_to_menu':
            await self.back_to_menu(update, context)
        
        elif query.data.startswith('answer_'):
            await self.check_answer(update, context)
        
        elif query.data == 'next_question':
            await self.send_question(update, context)
        
        elif query.data == 'finish_quiz':
            await self.finish_quiz(update, context)
    
    async def start_quiz(self, update, context, chapter=None, topic=None):
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        chat_type = query.message.chat.type
        
        user_data = self.db.get_user_stats(user_id)
        difficulty = user_data.get('current_difficulty', 'Easy') if user_data else 'Easy'
        
        questions = self.db.get_random_questions(count=5, chapter=chapter, topic=topic, difficulty=difficulty)
        
        if not questions:
            questions = self.db.get_random_questions(count=5, chapter=chapter, topic=topic)
        
        if not questions:
            await query.edit_message_text(
                "❌ No questions available!\n\nAdmin needs to upload questions first."
            )
            return
        
        quiz_key = f"{chat_id}_{user_id}"
        self.user_quiz_data[quiz_key] = {
            'questions': questions,
            'current_index': 0,
            'score': 0,
            'answers': [],
            'chapter': chapter or 'Mixed',
            'topic': topic or 'Mixed',
            'difficulty': difficulty,
            'start_time': datetime.now(),
            'chat_type': chat_type,
            'chat_id': chat_id
        }
        
        await self.send_question(update, context)
    
    async def send_question(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        quiz_key = f"{chat_id}_{user_id}"
        
        if quiz_key not in self.user_quiz_data:
            await query.edit_message_text("No active quiz. Start a new quiz!")
            return
        
        quiz_data = self.user_quiz_data[quiz_key]
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
            f"🧬 *NEET Biology Quiz*\n"
            f"*Question {current_index + 1}/{len(quiz_data['questions'])}*\n\n"
            f"*Chapter:* {current_q.get('chapter', 'N/A')}\n"
            f"*Difficulty:* {current_q.get('difficulty', quiz_data['difficulty'])}\n\n"
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
        chat_id = query.message.chat_id
        quiz_key = f"{chat_id}_{user_id}"
        selected_answer = query.data.replace('answer_', '')
        
        if quiz_key not in self.user_quiz_data:
            await query.edit_message_text("No active quiz. Start a new quiz!")
            return
        
        quiz_data = self.user_quiz_data[quiz_key]
        current_q = quiz_data['questions'][quiz_data['current_index']]
        correct_answer = current_q['correct_answer']
        
        is_correct = selected_answer == correct_answer
        
        if is_correct:
            quiz_data['score'] += 1
            response = "✅ *Correct!*"
        else:
            response = f"❌ *Wrong!* Correct answer: {correct_answer}"
        
        explanation = self.ai.generate_explanation(
            current_q['question'],
            current_q['correct_answer'],
            current_q['options'],
            current_q.get('chapter', None)
        )
        
        quiz_data['answers'].append({
            'question': current_q['question'],
            'chapter': current_q.get('chapter', 'Unknown'),
            'topic': current_q.get('topic', 'General'),
            'difficulty': current_q.get('difficulty', quiz_data['difficulty']),
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
        chat_id = query.message.chat_id
        quiz_key = f"{chat_id}_{user_id}"
        
        if quiz_key not in self.user_quiz_data:
            await query.edit_message_text("No active quiz. Start a new quiz!")
            return
        
        quiz_data = self.user_quiz_data[quiz_key]
        total_questions = len(quiz_data['questions'])
        score = quiz_data['score']
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        
        self.db.save_quiz_result(
            user_id,
            {
                'score': score,
                'total_questions': total_questions,
                'percentage': percentage,
                'chapter': quiz_data['chapter'],
                'topic': quiz_data['topic'],
                'difficulty': quiz_data['difficulty'],
                'answers': quiz_data['answers']
            },
            chat_type=quiz_data['chat_type'],
            group_id=chat_id if quiz_data['chat_type'] != 'private' else None
        )
        
        if percentage >= 80:
            emoji = "🌟"
            comment = "Excellent! Moving to harder questions!"
            next_difficulty = "Hard"
        elif percentage >= 60:
            emoji = "👍"
            comment = "Good job! Difficulty increasing!"
            next_difficulty = "Medium"
        else:
            emoji = "📚"
            comment = "Keep practicing! Stay at this level."
            next_difficulty = "Easy"
        
        message = (
            f"🎉 *Quiz Completed!*\n\n"
            f"*Chapter:* {quiz_data['chapter']}\n"
            f"*Topic:* {quiz_data['topic']}\n"
            f"*Difficulty:* {quiz_data['difficulty']}\n"
            f"*Score:* {score}/{total_questions}\n"
            f"*Percentage:* {percentage:.1f}%\n\n"
            f"{emoji} {comment}\n"
            f"*Next Level:* {next_difficulty}"
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
        
        del self.user_quiz_data[quiz_key]
    
    async def show_stats(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        
        user_data = self.db.get_user_stats(user_id)
        
        if not user_data or user_data['total_quizzes_taken'] == 0:
            await query.edit_message_text("No statistics available. Take a quiz first!")
            return
        
        message = (
            f"📊 *Your Biology Statistics*\n\n"
            f"*Total Quizzes:* {user_data['total_quizzes_taken']}\n"
            f"*Total Questions:* {user_data['total_questions_answered']}\n"
            f"*Correct Answers:* {user_data['correct_answers']}\n"
            f"*Average Score:* {user_data['average_score']:.1f}%\n"
            f"*Current Difficulty:* {user_data['current_difficulty']}\n\n"
            f"*Difficulty Progress:*\n"
        )
        
        for level in ['Easy', 'Medium', 'Hard']:
            stats = user_data['difficulty_progress'].get(level, {'attempted': 0, 'correct': 0})
            attempted = stats['attempted']
            correct = stats['correct']
            accuracy = (correct / attempted * 100) if attempted > 0 else 0
            message += f"• {level}: {accuracy:.1f}% ({correct}/{attempted})\n"
        
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
        
        await query.edit_message_text("🤖 *Analyzing your Biology performance...*", parse_mode='Markdown')
        
        analysis = self.ai.analyze_performance(
            json.loads(json.dumps(user_history, cls=JSONEncoder)),
            json.loads(json.dumps(user_data, cls=JSONEncoder)) if user_data else {}
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🤖 *AI Biology Performance Analysis*\n\n{analysis}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_upload_instructions(self, update, context):
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != self.config.ADMIN_USER_ID:
            await query.edit_message_text(
                "⚠️ *Admin Only Feature*\n\nOnly the bot admin can upload questions.",
                parse_mode='Markdown'
            )
            return
        
        message = (
            "📋 *Question Upload Format*\n\n"
            "Send questions using /upload command\n\n"
            "*Format:*\n"
            "```json\n"
            "{\n"
            '  "topic_name": "Cell Organelles",\n'
            '  "questions": [\n'
            "    {\n"
            '      "question": "Which organelle is the powerhouse?",\n'
            '      "options": {\n'
            '        "A": "Nucleus",\n'
            '        "B": "Mitochondria",\n'
            '        "C": "Ribosome",\n'
            '        "D": "Golgi"\n'
            "      },\n"
            '      "correct_answer": "B",\n'
            '      "chapter": "Cell Biology",\n'
            '      "difficulty": "Easy"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "```\n\n"
            "*Commands:*\n"
            "/upload - Upload questions\n"
            "/format - See format"
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
            "/upload - Upload questions (Admin)\n"
            "/format - Question format\n"
            "/stats - Your statistics\n"
            "/cancel - Cancel operation\n\n"
            "*Features:*\n"
            "• Chapter-wise Biology quizzes\n"
            "• Custom topic quizzes\n"
            "• Dynamic difficulty levels\n"
            "• AI explanations\n"
            "• Performance tracking\n"
            "• AI analysis\n\n"
            "*Works in:*\n"
            "• Private chat\n"
            "• Groups (add bot as admin)"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def back_to_menu(self, update, context):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        keyboard = [
            [InlineKeyboardButton("📝 Start Biology Quiz", callback_data='start_quiz')],
            [InlineKeyboardButton("📚 Choose Chapter", callback_data='choose_chapter')],
            [InlineKeyboardButton("🏷️ Custom Topics", callback_data='choose_topic')],
            [InlineKeyboardButton("📊 My Statistics", callback_data='my_stats')],
            [InlineKeyboardButton("🤖 AI Analysis", callback_data='ai_analysis')],
            [InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        
        if user_id == self.config.ADMIN_USER_ID:
            keyboard.append([InlineKeyboardButton("📤 Upload Questions", callback_data='upload_instructions')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🧬 *NEET Biology Bot Main Menu*\n\nChoose an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def upload_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id != self.config.ADMIN_USER_ID:
            await update.message.reply_text(
                "⚠️ *Admin Only Feature*\n\nOnly the bot admin can upload questions.",
                parse_mode='Markdown'
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "📋 *Upload Questions*\n\n"
                "Send JSON after /upload command\n"
                "Example:\n"
                "/upload {\"questions\": [...]}\n\n"
                "Use /format to see exact format",
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
            
            topic_name = question_data.get('topic_name', None)
            
            valid_questions = []
            errors = []
            
            for q in questions:
                q['subject'] = 'Biology'
                
                required = ['question', 'options', 'correct_answer', 'chapter', 'difficulty']
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
                
                if q['difficulty'] not in ['Easy', 'Medium', 'Hard']:
                    errors.append("Difficulty must be Easy, Medium, or Hard")
                    continue
                
                if topic_name:
                    q['topic'] = topic_name
                
                valid_questions.append(q)
            
            if valid_questions:
                added = self.db.add_questions(valid_questions, user_id, topic_name)
                await update.message.reply_text(
                    f"✅ Successfully uploaded {added} Biology questions!",
                    parse_mode='Markdown'
                )
            
            if errors:
                await update.message.reply_text(
                    f"⚠️ {len(errors)} questions failed:\n" + "\n".join(errors[:5]),
                    parse_mode='Markdown'
                )
        
        except json.JSONDecodeError:
            await update.message.reply_text(
                "❌ Invalid JSON format!\nUse /format to see correct format",
                parse_mode='Markdown'
            )
    
    async def format_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        format_example = {
            "topic_name": "Cell Organelles",
            "questions": [
                {
                    "question": "Which organelle is the powerhouse of the cell?",
                    "options": {
                        "A": "Nucleus",
                        "B": "Mitochondria",
                        "C": "Ribosome",
                        "D": "Golgi apparatus"
                    },
                    "correct_answer": "B",
                    "chapter": "Cell Biology",
                    "difficulty": "Easy"
                }
            ]
        }
        
        await update.message.reply_text(
            "📋 *Biology Question Format*\n\n"
            "```json\n"
            f"{json.dumps(format_example, indent=2)}\n"
            "```\n\n"
            "*Note:* `topic_name` is optional for custom topic grouping",
            parse_mode='Markdown'
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db.get_user_stats(user_id)
        
        if not user_data or user_data['total_quizzes_taken'] == 0:
            await update.message.reply_text("No statistics available. Take a quiz first!")
            return
        
        message = (
            f"📊 *Your Biology Statistics*\n\n"
            f"Total Quizzes: {user_data['total_quizzes_taken']}\n"
            f"Total Questions: {user_data['total_questions_answered']}\n"
            f"Average Score: {user_data['average_score']:.1f}%\n"
            f"Current Difficulty: {user_data['current_difficulty']}"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Operation cancelled. Use /start to begin again.")


def main():
    config = Config()
    bot = NEETBiologyBot()
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("upload", bot.upload_command))
    application.add_handler(CommandHandler("format", bot.format_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    application.add_handler(CommandHandler("cancel", bot.cancel))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Fix for Python 3.14
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application.run_polling()


if __name__ == '__main__':
    main()
