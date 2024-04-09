import json
import os
from typing import Dict, Callable

import firebase_admin
import httpx
from deepgram import Deepgram
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from firebase_admin import initialize_app, db
from starlette.middleware.cors import CORSMiddleware
import copy

load_dotenv()

# Deepgram
app = FastAPI(
    title="Live transcription with Deepgram API management",
    description="ReadTheVoice API for managing speech-to-text functionality",
    version="1.0.0"
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="project/src/app/templates")

deepgram_client = Deepgram(os.getenv('DEEPGRAM_API_KEY'))

jwt_authorization = os.getenv('JWT_AUTHORIZATION')

favicon_path = 'project/src/app/static/img/favicon.ico'
styles_file_path = 'project/src/app/templates/css/styles.css'
js_file_path = 'project/src/app/templates/js/utils.js'

# Feel free to modify the model's parameters as you wish!
# {'punctuate': True, 'interim_results': False, 'language': 'en-US', 'model': 'nova-2'}
# We chose "nova-2"
deepgram_options = {
    'punctuate': True,
    # 'interim_results': False,
    'interim_results': True,
    # 'model': 'enhanced',
    'model': 'nova-2',
}

# Database config
firebase_db_url = os.getenv('DATABASE_URL')
initialize_app(options={'databaseURL': firebase_db_url})
root_reference = db.reference()


# @app.on_event("startup")
# async def startup_event():


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    return FileResponse(favicon_path)


@app.get("/css/styles.css", include_in_schema=False)
async def get_styles_file():
    return FileResponse(styles_file_path)


@app.get("/js/utils.js", include_in_schema=False)
async def get_js_file():
    return FileResponse(js_file_path)


@app.get("/css/error-page.css", include_in_schema=False)
async def get_styles_file():
    return FileResponse("project/src/app/templates/css/error-page.css")


@app.get("/js/error-page.js", include_in_schema=False)
async def get_js_file():
    return FileResponse("project/src/app/templates/js/error-page.js")


# @app.get("/", response_class=HTMLResponse)
# def get(request: Request):
#     # return templates.TemplateResponse("index.html", {"request": request})
#     return templates.TemplateResponse("transcription.html", {"request": request})


# @app.get("/transcribe", response_class=HTMLResponse)
# async def get(request: Request, meeting_id: str, token: str):
@app.websocket("/transcribe")
async def get(websocket: WebSocket, meeting_id: str, language: str, token: str):
    error_message = "External URL request failed"
    user_email = ""

    try:
        # Verify token
        url = "https://verifytoken-vpiwklolaa-ey.a.run.app/"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=url,
                headers={
                    "Authorization": jwt_authorization,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "token": token
                }
            )

        data = response.json()

        if response.status_code == 200:
            if "error" in data:
                return templates.TemplateResponse("error.html", {"error": data["error"], "meeting_id": meeting_id})
            elif "email" in data:
                user_email = data["email"]
                user_firstname = data["firstName"]
                user_lastname = data["lastName"]
            else:
                return templates.TemplateResponse("error.html", {"error": error_message})

            return await websocket_endpoint(websocket=websocket, meeting_id=meeting_id, language=language, email_user=user_email)
        else:
            return templates.TemplateResponse("error.html", {"error": error_message})
    except httpx.RequestError as e:
        return templates.TemplateResponse("error.html", {"error": str(e)})


# Websocket Connection Between Server and Browser
async def websocket_endpoint(websocket: WebSocket, meeting_id: str, language: str, email_user: str):
    await websocket.accept()

    try:
        deepgram_socket = await process_audio(websocket, meeting_id, language, email_user)

        while True:
            try:
                data = await websocket.receive_bytes()
                deepgram_socket.send(data)
            except starlette.websockets.WebSocketDisconnect:
                print("Client disconnected")
    except Exception as e:
        raise Exception(f'Could not process audio: {e}')
    finally:
        await websocket.close()

# Process the audio, get the transcript from that audio and connect to Deepgram.
async def process_audio(fast_socket: WebSocket, meeting_id: str, language: str,
                        email_user: str):
    
    saveData = "none"

    async def get_transcript(data: Dict) -> None:
        nonlocal saveData
        if 'channel' in data:
            transcript = data['channel']['alternatives'][0]['transcript']

            isFinal = data['is_final'] 

            if transcript == "" or transcript == " ":
                return

            transcript_reference = root_reference.child('transcripts').child(meeting_id)
            snapshot = transcript_reference.get()
            if isFinal:
                if snapshot:
                    if saveData == "none":
                        dt = snapshot.get("data", "")
                    else:
                        dt = copy.deepcopy(saveData)
                else:
                    dt = ""

                if transcript[0].isupper() and dt.endswith(','):
                    transcript = transcript[0].lower() + transcript[1:]

                if transcript and transcript[0].isupper() and dt and dt[-1] not in [".", "",",", "?", "!", ":", ";"]:
                    dt += ". "
                elif dt and dt[-1] not in [" ", ". ", ", ", "? ", "! ", ": ", "; ", ") ", "] "]:
                    dt += " "

                
                dt += transcript
                updated_data = {
                    'data': dt
                }
                transcript_reference.update(updated_data)
                if transcript:
                    await fast_socket.send_text(dt)
                
                saveData = "none"
            else:
                if snapshot:
                    if saveData == "none":
                        saveData = snapshot.get("data", "")
                    dt = copy.deepcopy(saveData)
                else:
                    dt = ""

                if transcript[0].isupper() and (not dt.endswith(',')):
                    transcript = transcript[0].lower() + transcript[1:]

                if transcript and transcript[0].isupper() and dt and dt[-1] not in [".", "",",", "?", "!", ":", ";"]:
                    dt += ". "
                elif dt and dt[-1] not in [" ", ". ", ", ", "? ", "! ", ": ", "; ", ") ", "] "]:
                    dt += " "

                dt += transcript
                updated_data = {
                    'data': dt
                }
                transcript_reference.update(updated_data)
                if transcript:
                    await fast_socket.send_text(dt)


    deepgram_socket = await connect_to_deepgram(get_transcript, language)

    return deepgram_socket


# Connect to Deepgram.
async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None], language: str):
    try:
        deepgram_options['language'] = language
        socket = await deepgram_client.transcription.live(deepgram_options)

        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)

        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')
