import base64
import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
import google.auth.transport.requests

load_dotenv() 
# Path to your OAuth client secrets JSON
CLIENT_SECRETS_FILE = os.getenv("CLIENT_SECRET_JSON", "client_secrets.json")
# Optional: GitHub Actions secret base64
CLIENT_SECRET_PICKLE_BASE64 = os.getenv("CLIENT_SECRET_PICKLE_BASE64")
# Optional: path to base64 file
BASE64_FILE_PATH = "token_base64.txt"




# If modifying scopes, delete token.pickle
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]
def get_authenticated_service():
    creds = None
    
    # 1️⃣ Try loading from file if exists

    # Check if token exists
    if os.path.exists(BASE64_FILE_PATH):
        with open(BASE64_FILE_PATH, "r") as f:
            try:
                base64_str = f.read().strip()
                pickle_bytes = base64.b64decode(base64_str)
                creds = pickle.loads(pickle_bytes)
                print("✅ Loaded credentials from base64 file")
            except Exception as e:
                print(f"⚠️ Failed to load credentials from file: {e}")
                
    # 2️⃣ Fallback: load from GitHub secret / .env
    elif CLIENT_SECRET_PICKLE_BASE64:
        try:
            pickle_bytes = base64.b64decode(CLIENT_SECRET_PICKLE_BASE64)
            creds = pickle.loads(pickle_bytes)
            print("✅ Loaded credentials from base64 env variable")
        except Exception as e:
            print(f"⚠️ Failed to load credentials from env: {e}")
            
    # 3️⃣ Fallback: local token.pickle
    elif os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
            print("✅ Loaded credentials from token.pickle")
            
            

    # If no valid creds, do OAuth login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            # ⚡ Updated: Use run_local_server instead of run_console
            creds = flow.run_local_server(port=0)

        # Save token for future
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)

    # Build YouTube service
    return build("youtube", "v3", credentials=creds)

def upload_video_to_yt(file_path, title, description="", tags=None, category_id="27", privacy_status="private",made_for_kids=False):
    """
    Uploads a video to the YouTube channel associated with the OAuth credentials.
    """
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploading... {int(status.progress() * 100)}%")

    print(f"\n✅ Video uploaded: https://www.youtube.com/watch?v={response['id']}")
    return response

def set_thumbnail(video_id, thumbnail_path="thumbnail_output.png"):
    """
    Sets a custom thumbnail for the uploaded video.
    """
    youtube = get_authenticated_service()
    
    media = MediaFileUpload(thumbnail_path)
    
    request = youtube.thumbnails().set(
        videoId=video_id,
        media_body=media
    )
    
    response = request.execute()
    print(f"✅ Thumbnail set for video {video_id}")
    return response