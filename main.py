import os
import json
import random
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from instagrapi import Client

# --- VIDEO EDITING LIBRARY ---
from moviepy.editor import VideoFileClip, vfx

# --- SETTINGS ---
SOURCE_FOLDER = os.environ["DRIVE_FOLDER_ID"]
DONE_FOLDER = os.environ["DRIVE_DONE_ID"]

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
"""

INSTA_CAPTION = """
Type 'YES' if you agree! 🔥
.
Follow for daily motivation! 🚀
.
.
""" + HASHTAGS

# --- GOOGLE AUTH ---
def get_google_services():
    creds = Credentials(
        None, 
        refresh_token=os.environ["G_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["G_CLIENT_ID"], 
        client_secret=os.environ["G_CLIENT_SECRET"]
    )
    if not creds.valid:
        creds.refresh(Request())
    
    return build('drive', 'v3', credentials=creds), build('youtube', 'v3', credentials=creds)

# --- EDITING FUNCTION (Speed + Filter + Gap) ---
def edit_video(input_path, output_path):
    print("Editing Start: Adding Speed, Filter, and Border...")
    
    # 1. Video Load
    clip = VideoFileClip(input_path)
    
    # 2. Speed 1.1x (Fast)
    clip = clip.fx(vfx.speedx, 1.1)
    
    # 3. Filter (Color Vibrance 1.2x - Thoda Bright aur Colors Change)
    clip = clip.fx(vfx.colorx, 1.2)
    
    # 4. Border/Gap (White Color padding)
    # top, bottom, left, right = 40 pixels ka gap
    # color=(255, 255, 255) Matlab White. Black chahiye to (0,0,0) kar dena.
    clip = clip.margin(top=40, bottom=40, left=40, right=40, color=(255, 255, 255))
    
    # 5. Save Final Video
    clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, verbose=False, logger=None)
    print("Editing Complete! Video ready for upload.")

# --- MAIN BOT ---
def main():
    print("--- Bot Started ---")
    
    try:
        drive, youtube = get_google_services()
    except Exception as e:
        print(f"Login Failed: {e}")
        return

    # 1. Drive Check
    print("Checking Drive for videos...")
    query = f"'{SOURCE_FOLDER}' in parents and mimeType contains 'video/' and trashed=false"
    results = drive.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    files = results.get('files', [])

    if not files:
        print("Folder khali hai.")
        return

    video = files[0]
    print(f"Video Found: {video['name']}")

    # 2. Download Raw Video
    print("Downloading raw video...")
    raw_video = "raw_video.mp4"
    final_video = "final_video.mp4"
    
    request = drive.files().get_media(fileId=video['id'])
    with open(raw_video, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

    # 3. Apply Editing
    try:
        edit_video(raw_video, final_video)
        video_to_upload = final_video
    except Exception as e:
        print(f"Editing Failed (Error: {e}). Uploading Raw Video instead.")
        video_to_upload = raw_video

    title_text = random.choice(TITLES)

    # 4. YouTube Upload
    try:
        print(f"Uploading to YouTube: {video_to_upload}")
        body = {
            'snippet': {
                'title': title_text,
                'description': f"Motivational Video \n\n{HASHTAGS}",
                'tags': ['motivation', 'shorts', 'hustle'],
                'categoryId': '27'
            },
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }
        media = MediaFileUpload(video_to_upload, chunksize=-1, resumable=True)
        yt_resp = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print(f"YouTube Success! ID: {yt_resp['id']}")
    except Exception as e:
        print(f"YouTube Error: {e}")

    # 5. Instagram Upload
    try:
        print("Uploading to Instagram...")
        cl = Client()
        session_data = json.loads(os.environ["INSTA_SESSION"])
        cl.set_settings(session_data)
        cl.login(os.environ["INSTA_USERNAME"], os.environ["INSTA_PASSWORD"])
        
        cl.clip_upload(video_to_upload, f"{title_text}\n\n{INSTA_CAPTION}")
        print("Instagram Success!")
    except Exception as e:
        print(f"Instagram Error: {e}")

    # 6. Cleanup & Move
    print("Moving video to Done folder...")
    file_drive = drive.files().get(fileId=video['id'], fields='parents').execute()
    prev_parents = ",".join(file_drive.get('parents'))
    
    drive.files().update(
        fileId=video['id'],
        addParents=DONE_FOLDER,
        removeParents=prev_parents
    ).execute()
    
    # Remove local files to save space
    if os.path.exists(raw_video): os.remove(raw_video)
    if os.path.exists(final_video): os.remove(final_video)
    
    print("--- Process Complete ---")

if __name__ == "__main__":
    main()
