# -----------------------------------------------------------------------------
# ShortsBot API Helper Functions - STABLE VERSION
# -----------------------------------------------------------------------------
import asyncio, logging, os, json
from datetime import datetime, timedelta, timezone
import yaml
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

TOKEN_FILE = 'token.json'
SCHEDULE_FILE = 'schedule.yaml'

def get_youtube_service(config):
    credentials = None; client_secrets_file = config['youtube']['client_secrets_file']; scopes = config['youtube']['scopes']
    if os.path.exists(TOKEN_FILE): credentials = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token: credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes); credentials = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token: token.write(credentials.to_json())
    return build('youtube', 'v3', credentials=credentials)

def get_next_schedule_time(last_scheduled_timestamp: float | None):
    try:
        with open(SCHEDULE_FILE, 'r') as f: weekly_schedule = yaml.safe_load(f)['schedule']
    except (FileNotFoundError, KeyError):
        logging.error(f"❌ '{SCHEDULE_FILE}' not found or invalid."); return None
    now_utc = datetime.now(timezone.utc); start_time = now_utc
    if last_scheduled_timestamp:
        try:
            timestamp = float(last_scheduled_timestamp)
            last_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            if last_time > start_time: start_time = last_time
        except (ValueError, TypeError):
             logging.warning("Could not parse last_scheduled_time. Starting from now.")
    for i in range(365):
        current_day = start_time + timedelta(days=i); day_of_week = current_day.weekday()
        day_schedule = weekly_schedule.get(day_of_week, [])
        for time_str in day_schedule:
            hour, minute = map(int, time_str.split(':'))
            next_slot = current_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_slot > start_time:
                return next_slot.timestamp()
    return None

async def create_youtube_playlist(youtube, title):
    logging.info(f"Creating new YouTube playlist titled: '{title}'")
    try:
        request_body = {'snippet': {'title': title}, 'status': {'privacyStatus': 'public'}}
        request = youtube.playlists().insert(part='snippet,status', body=request_body)
        response = await asyncio.to_thread(request.execute); return response.get('id')
    except HttpError as e: logging.error(f"❌ Could not create playlist: {e}"); return None

async def upload_video(youtube, config, file_path, title, description, category_id, tags, publish_at_timestamp: float):
    publish_at_iso = datetime.fromtimestamp(publish_at_timestamp, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
    request_body = {'snippet': {'categoryId': category_id, 'title': title, 'description': description, 'tags': tags}, 'status': {'privacyStatus': 'private', 'publishAt': publish_at_iso, 'selfDeclaredMadeForKids': False}}
    media_file = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    max_retries = config['bot']['upload_retry_attempts']
    for attempt in range(max_retries):
        try:
            request = youtube.videos().insert(part='snippet,status', body=request_body, media_body=media_file)
            response = await asyncio.to_thread(request.execute); return response.get('id'), None
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8')); reason = error_details.get('error', {}).get('errors', [{}])[0].get('reason', 'Unknown reason')
            status_code = e.resp.status; error_message = f"{reason} (Error {status_code})"
            if status_code in [400, 401, 403]: return None, error_message
            if attempt < max_retries - 1: await asyncio.sleep(config['bot']['retry_delay_minutes'] * 60)
            else: return None, error_message
        except Exception as e: return None, str(e)
    return None, "Max retries reached."

async def add_video_to_playlist(youtube, playlist_id, video_id):
    try:
        request = youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}})
        await asyncio.to_thread(request.execute); return True
    except HttpError as e: logging.error(f"❌ Could not add video to playlist: {e}"); return False