import json
from google import genai
from app.prompts.project_prompt import SYSTEM_PROMPT
from app.core.config import settings
from app.schemas.ai import ProjectGenerateResponse

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)

def clean_json(text: str)->str:
    text = text.replace("```json", "")
    text = text.replace("```", "")
    return text.strip()

def generate_project(project_name: str,project_type:str, requirements: str)->ProjectGenerateResponse:
    user_prompt = f"""
    Project Name:
    {project_name}

    Project Type:
    {project_type}

    Requirements:
    {requirements}
    """
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        SYSTEM_PROMPT,
        user_prompt
    ]
    )
    try:
        cleaned = clean_json(response.text)
        data = json.loads(cleaned)
        return ProjectGenerateResponse.model_validate(data)

    except json.JSONDecodeError:
        raise ValueError("Stack Pilot returned invalid JSON.")