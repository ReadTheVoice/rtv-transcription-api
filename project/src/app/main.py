from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

app = FastAPI(
    title="Deepgram api management",
    description="ReadTheVoice API for managing the speech-to-text",
    version="1.0.0"
)


# @app.on_event("startup")
# async def startup_event():


# app.include_router()