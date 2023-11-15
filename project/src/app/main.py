import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from deepgram import Deepgram
from typing import Dict, Callable

load_dotenv()

# Deepgram
app = FastAPI(
    title="Live transcription with Deepgram API management",
    description="ReadTheVoice API for managing speech-to-text functionality",
    version="1.0.0"
)

templates = Jinja2Templates(directory="project/src/app/templates")

deepgram_client = Deepgram(os.getenv('DEEPGRAM_API_KEY'))

favicon_path = 'project/src/app/static/img/favicon.ico'

# token=...&meetingId=...

# @app.on_event("startup")
# async def startup_event():

# app.include_router()


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    return FileResponse(favicon_path)


@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Websocket Connection Between Server and Browser
@app.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        deepgram_socket = await process_audio(websocket)

        while True:
            data = await websocket.receive_bytes()
            deepgram_socket.send(data)
    except Exception as e:
        raise Exception(f'Could not process audio: {e}')
    finally:
        await websocket.close()


# Process the audio, get the transcript from that audio and connect to Deepgram.
async def process_audio(fast_socket: WebSocket):
    async def get_transcript(data: Dict) -> None:
        if 'channel' in data:
            transcript = data['channel']['alternatives'][0]['transcript']

            if transcript:
                await fast_socket.send_text(transcript)

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket


# Connect to Deepgram.
async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]):
    try:
        socket = await deepgram_client.transcription.live({'punctuate': True, 'interim_results': False})
        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)

        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')




