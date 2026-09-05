import os
from dotenv import load_dotenv  

load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    GROK_FALLBACK_API_KEY: str = os.getenv("GROK_FALLBACK_API_KEY")
    GROK_MODEL:str = "llama-3.3-70b-versatile"

    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY")
    QDRANT_URL: str = os.getenv("QDRANT_CLUSTER_ENDPOINT")
    QDRANT_COLLECTION:str = "adv_rag"

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    
    


settings = Settings()