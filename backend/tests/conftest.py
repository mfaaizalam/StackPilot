import os, sys
os.environ.update({
    "DATABASE_URL": "sqlite:///./test.db", "EMAIL_ADDRESS": "x@x.com", "EMAIL_PASSWORD": "x",
    "GEMINI_API_KEY": "x", "SECRET_KEY": "test-secret", "ALGORITHM": "HS256",
    "QDRANT_URL": "http://localhost", "QDRANT_API_KEY": "x", "LLM_FAKE": "1",
})
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
