import os
import json
import random
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from instagrapi import Client

# --- 1. SETTINGS & CONFIG ---
SOURCE_FOLDER = os.environ["DRIVE_FOLDER_ID"]
DONE_FOLDER = os.environ["DRIVE_DONE_ID"]

# Motivation Content Data
TITLES = [
    "Never Give Up! 💪 #Motivation",
    "Success Mindset 🧠 #Shorts",
    "Hustle Hard 🔥 #Grind",
    "Believe in Yourself ✨ #Inspiration",
    "Focus on Goals 🎯 #Success",
    "Daily Motivation for You 🚀",
    "Winners Never Quit 🏆"
]

HASHTAGS = """
#motivation #success #hustle #inspiration #mindset #entrepreneur 
#goals #business #wealth #fitness #believe #motivationalquotes 
#successquotes #life #quotes #loveyourself #happy #inspirationalquotes
"""

INSTA_CAPTION = """
Type 'YES' if you agree! 🔥
.
Follow for daily motivation! 🚀
.
.
""" + HASHTAGS

# --- 2. GOOGLE LOGIN FUNCTION ---
def get_google_services():
    creds = Credentials(
        None, 
        refresh_token=os.environ["G_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["G_CLIENT_ID"], 
        client_secret=os.environ["G_CLIENT_SECRET"]
    )
    # Token refresh logic
    if not creds.valid:
        creds.refresh(Request())
    
    drive = build('drive', 'v3', credentials=creds)
    youtube = build('youtube', 'v3', credentials=creds)
    return drive, youtube

# --- 3. MAIN BOT LOGIC ---
def main():
    print("--- Bot Started ---")
    
    try:
        drive, youtube = get_google_services()
    except Exception as e:
        print(f"Google Login Failed: {e}")
        return

    # A. Video Dhundo
    print("Checking Drive for videos...")
    query = f"'{SOURCE_FOLDER}' in parents and mimeType contains 'video/' and trashed=false"
    results = drive.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    files = results.get('files', [])

    if not files:
        print("Folder khali hai. Koi video nahi mili.")
        return

    video = files[0]
    print(f"Video Found: {video['name']}")

    # B. Download Video
    print("Downloading video locally...")
    request = drive.files().get_media(fileId=video['id'])
    video_path = "video.mp4"
    with open(video_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

    # Title Select Karo
    title_text = random.choice(TITLES)

    # C. YOUTUBE UPLOAD
    try:
        print(f"Uploading to YouTube Shorts: {title_text}")
        body = {
            'snippet': {
                'title': title_text,
                'description': f"Best Motivational Video \n\n{HASHTAGS}",
                'tags': ['motivation', 'success', 'shorts', 'hustle', 'inspiration'],
                'categoryId': '27' # Education
            },
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        yt_resp = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print(f"YouTube Success! ID: {yt_resp['id']}")
    except Exception as e:
        print(f"YouTube Upload Failed: {e}")

    # D. INSTAGRAM UPLOAD (Session Magic)
    try:
        print("Logging into Instagram using Session...")
        cl = Client()
        
        # Session Load kar rahe hain
        session_data = json.loads(os.environ["INSTA_SESSION"])
        cl.set_settings(session_data)
        
        # Login Verification
        cl.login(os.environ["INSTA_USERNAME"], os.environ["INSTA_PASSWORD"])
        
        print("Uploading Reel...")
        cl.clip_upload(video_path, f"{title_text}\n\n{INSTA_CAPTION}")
        print("Instagram Success!")
        
    except Exception as e:
        print(f"Instagram Upload Failed: {e}")

    # E. MOVE VIDEO TO DONE FOLDER
    try:
        print("Moving video to 'Uploaded' folder...")
        file_drive = drive.files().get(fileId=video['id'], fields='parents').execute()
        prev_parents = ",".join(file_drive.get('parents'))
        
        drive.files().update(
            fileId=video['id'],
            addParents=DONE_FOLDER,
            removeParents=prev_parents
        ).execute()
        print("Video Moved Successfully.")
    except Exception as e:
        print(f"File Move Failed: {e}")

    print("--- Process Complete ---")

if __name__ == "__main__":
    main()
