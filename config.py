import os
from google import genai

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyBnqh7CyKty76H1eqBXmOwpkqhRuxX3IDU')
client = genai.Client(api_key=GOOGLE_API_KEY)
