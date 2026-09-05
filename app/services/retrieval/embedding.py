import logfire
import time
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings


BATCH_SIZE = 100
_GEMINI_DIM = 3072
_FALLBACK_DIM = 768 #all-mpnet-base-v2 sentrnce-transformer-base-multilingual


_active_model = None
_model_type:str |  None = None # gemini or fallback

