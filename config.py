import os
from google import genai
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

