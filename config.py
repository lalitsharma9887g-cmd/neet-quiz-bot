
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    MONGODB_URI = os.getenv('MONGODB_URI')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))
