import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
You are StackPilot AI Assistant.

Only help with:
- Software Engineering
- Computer Science
- AI/ML
- System Design
- Project building

If user asks unrelated questions, refuse politely.
"""

def get_ai_response(user_input: str):
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=SYSTEM_PROMPT + "\n\nUser: " + user_input
    )

    return response.text