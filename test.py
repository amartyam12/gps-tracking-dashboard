from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("API_KEY")
chat_model = os.getenv("CHAT_MODEL")

print(api_key)
print(chat_model)