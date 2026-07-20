"""
One-off diagnostic: lists the Gemini models available to your API key.
Run this once to see what's actually usable, then update GEMINI_MODEL
in config.py accordingly. Not part of the main pipeline.
"""
from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

print("Models available to your key:\n")
for m in client.models.list():
    name = getattr(m, "name", "?")
    methods = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None)
    print(f"- {name}   (supports: {methods})")