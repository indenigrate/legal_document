import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Check for API key early
if not os.getenv("GOOGLE_API_KEY"):
    raise EnvironmentError("GOOGLE_API_KEY must be set in your environment or .env file.")

# Orchestrator & Thinker: Requires high reasoning capacity
pro_llm = ChatGoogleGenerativeAI(
    model="gemini-3-pro-preview",
    temperature=1.0,  # CRITICAL for Gemini 3.0 models as per plan
    max_retries=2
)

# Workers & Synthesizer: Faster, high-volume generation
flash_llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=1.0  # CRITICAL for Gemini 3.0 models as per plan
)
