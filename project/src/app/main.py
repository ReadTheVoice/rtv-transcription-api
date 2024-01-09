import os
import uuid

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from deepgram import Deepgram
from typing import Dict, Callable
# from firebase import firebase as fire
import firebase.firebase as fire

import firebase_admin
from firebase_admin import credentials, db

from starlette.middleware.cors import CORSMiddleware

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

# Feel free to modify your model's parameters as you wish!
# {'punctuate': True, 'interim_results': False, 'language': 'en-US', 'model': 'nova-2'}
# Instead of "nova-2 "as model, we chose "enhanced" (which allowed us to stream in French)
deepgram_options = {
    'punctuate': True,
    # 'interim_results': True,
    'interim_results': False,
    'language': 'fr',
    'model': 'enhanced',
}

# Database config
firebase_db_url = os.getenv('DATABASE_URL')
credentials_file_path = os.getenv('CREDENTIALS_FILE_PATH')

# /project/credentials/moonlight-sharonn-firebase-adminsdk-fzc3n-e47c86335b.json
# cred = credentials.Certificate("project/credentials/moonlight-sharonn-firebase-adminsdk-fzc3n-e47c86335b.json")
cred = credentials.Certificate(credentials_file_path)
firebase_admin.initialize_app(cred, {'databaseURL': firebase_db_url})
root_ref = db.reference()

# token=...&meetingId=...

# @app.on_event("startup")
# async def startup_event():

# app.include_router()


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    return FileResponse(favicon_path)


@app.get("/css/styles.css", include_in_schema=False)
async def get_styles_file():
    return FileResponse(styles_file_path)


@app.get("/js/utils.js", include_in_schema=False)
async def get_js_file():
    return FileResponse(js_file_path)


@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/verify_token")
async def is_token_valid(token: str):
    try:
        url = "https://verifytoken-vpiwklolaa-ey.a.run.app/"
        async with httpx.AsyncClient() as client:
            # // Access-Control-Allow-Origin

            response = await client.post(
                url=url,
                headers={
                    "Authorization": jwt_authorization,
                    "Content-Type": "application/json",
                },
                json={
                    "token": token
                }
            )

        if response.status_code == 200:
            print("response.json()")
            print(response.json())

            return response.json()
            # return {"data": response.json()}
            # return True
        else:
            raise HTTPException(status_code=response.status_code, detail="External URL request failed")

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"HTTP request error: {str(e)}")


@app.get("/transcribe", response_class=HTMLResponse)
def get(request: Request):  # , user_id: str, meeting_id: str):
    return templates.TemplateResponse("transcription.html", {"request": request})


# Websocket Connection Between Server and Browser
@app.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):  # Must pass the meetingId argument
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

            print("**********************************************************************")
            start_time = data["start"]
            print(start_time)

            fb_data = {
                "meeting_id": "uuid",
                "user_id": "uuid",
                "start": start_time,
                "data": transcript
            }

            users_ref = root_ref.child('transcript')
            snapshot = users_ref.get()

            if snapshot:
                test = users_ref.order_by_child("meeting_id").equal_to("uuid").get()
                if test:
                    ky = test
                    # OrderedDict([('-NnjqZx3Tz52UXo5MJ1f', {'data': '', 'meeting_id': 'uuid', 'start': 0.0, 'user_id': 'uuid'})])
                    for key, values in ky.items():
                        print(key)
                        print(values)
                        dt = values["data"]
                        st = values["start"]

                        if st != start_time:
                            dt += "."

                        dt += transcript
                        updated_data = {
                            'data': dt,
                            "start": start_time
                        }
                        users_ref.child(f"{key}").update(updated_data)
            else:
                users_ref.push(fb_data)

            # fb = fire.FirebaseApplication(firebase_db_url, None)
            # result = fb.get('/users', '1')
            # print("fb result")
            # print(result)
            # # {'1': 'John Doe'}

            print("**********************************************************************")

            if transcript:
                await fast_socket.send_text(transcript)

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket


# Connect to Deepgram.
async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]):
    try:
        # socket = await deepgram_client.transcription.live({'punctuate': True, 'interim_results': False})
        socket = await deepgram_client.transcription.live(deepgram_options)

        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)

        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')
