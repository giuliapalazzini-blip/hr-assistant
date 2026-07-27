import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    DOCUMENTS_DIR = "resumes"
    COLLECTION_NAME = "CVs"
    PERSISTENT_DIR = "data/chromadb"

    # Embedding OpenAI
    MODEL_NAME = "text-embedding-3-small"
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")

    # Modelli di completamento OpenAI
    LLM_MODEL = "gpt-4o"
    LLM_MODEL_LOW = "gpt-4o-mini"

    AI_API_URL = "https://api.openai.com/v1/"
    AI_API_KEY = os.getenv("OPENAI_API_KEY")


if not Config.OPENAI_KEY:
    raise ValueError(
        "La variabile OPENAI_API_KEY non è stata trovata. "
        "Controlla che il file .env esista nella cartella principale "
        "del progetto e contenga OPENAI_API_KEY=la_tua_chiave."
    )