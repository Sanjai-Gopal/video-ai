import os
import json
import pickle
import yaml
import requests
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


@dataclass
class PostResult:
    platform: str
    post_id: str
    url: str
    status: str
    error: Optional[str] = None
    posted_at: str = ""


class YouTubePoster:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    
    def __init__(self, config):
        self.config = config["social_media"]["youtube"]
        self.client_secrets = self.config["client_secrets"]
        self.token_file = self.config["token_file"]
        self.category_id = self.config["category_id"]
        self.privacy = self.config["privacy"]
        self.default_tags = self.config["tags"]
        self.credentials = None
        self.service = None

    def authenticate(self):
        creds = None
        token_path = Path(self.token_file)
        
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.credentials = creds
        self.service = build("youtube", "v3", credentials=creds)

    def upload(self, video_path: str, title: str, description: str, tags: List[str]) -> PostResult:
        if not self.service:
            self.authenticate()
        
        full_desc = f"{description}\n\n{' '.join(['#' + t.replace(' ', '') for t in tags])}"
        
        body = {
            "snippet": {
                "title": title[:100],
                "description": full_desc[:5000],
                "tags": tags + self.default_tags,
                "categoryId": self.category_id
            },
            "status": {
                "privacyStatus": self.privacy,
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        
        request = self.service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"YouTube upload: {int(status.progress() * 100)}%")
        
        video_id = response["id"]
        return PostResult(
            platform="youtube",
            post_id=video_id,
            url=f"https://www.youtube.com/shorts/{video_id}",
            status="success",
            posted_at=datetime.now().isoformat()
        )


class InstagramPoster:
    def __init__(self, config):
        self.config = config["social_media"]["instagram"]
        self.access_token_path = self.config["access_token"]
        self.business_account_id = self.config["business_account_id"]
        self.graph_version = "v22.0"
        self.access_token = None
        self._load_token()

    def _load_token(self):
        token_path = Path(self.access_token_path)
        if token_path.exists():
            self.access_token = token_path.read_text().strip()

    def create_container(self, video_url: str, caption: str) -> str:
        url = f"https://graph.facebook.com/{self.graph_version}/{self.business_account_id}/media"
        params = {
            "media_type": "VIDEO",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.access_token
        }
        response = requests.post(url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()["id"]

    def publish_container(self, container_id: str) -> str:
        url = f"https://graph.facebook.com/{self.graph_version}/{self.business_account_id}/media_publish"
        params = {
            "creation_id": container_id,
            "access_token": self.access_token
        }
        response = requests.post(url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()["id"]

    def post(self, video_url: str, title: str, description: str, hashtags: List[str]) -> PostResult:
        caption = f"{title}\n\n{description}\n\n{' '.join(['#' + h for h in hashtags])}"
        
        try:
            container_id = self.create_container(video_url, caption)
            post_id = self.publish_container(container_id)
            
            return PostResult(
                platform="instagram",
                post_id=post_id,
                url=f"https://www.instagram.com/reel/{post_id}/",
                status="success",
                posted_at=datetime.now().isoformat()
            )
        except Exception as e:
            return PostResult(
                platform="instagram",
                post_id="",
                url="",
                status="failed",
                error=str(e),
                posted_at=datetime.now().isoformat()
            )


class TikTokPoster:
    def __init__(self, config):
        self.config = config["social_media"]["tiktok"]
        self.access_token_path = self.config["access_token"]
        self.client_key = self.config["client_key"]
        self.client_secret = self.config["client_secret"]
        self.access_token = None
        self._load_token()

    def _load_token(self):
        token_path = Path(self.access_token_path)
        if token_path.exists():
            self.access_token = token_path.read_text().strip()

    def upload_video(self, video_path: str, title: str, hashtags: List[str]) -> PostResult:
        # TikTok API v2 - direct upload
        url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Initialize upload
        init_data = {
            "post_info": {
                "title": title[:150],
                "privacy_level": "PUBLIC",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": os.path.getsize(video_path),
                "chunk_size": os.path.getsize(video_path),
                "total_chunk_count": 1
            }
        }
        
        response = requests.post(url, headers=headers, json=init_data, timeout=30)
        response.raise_for_status()
        upload_url = response.json()["data"]["upload_url"]
        publish_id = response.json()["data"]["publish_id"]
        
        # Upload video file
        with open(video_path, 'rb') as f:
            upload_headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Range": f"bytes 0-{os.path.getsize(video_path)-1}/{os.path.getsize(video_path)}"
            }
            requests.put(upload_url, headers=upload_headers, data=f, timeout=120)
        
        # Publish
        publish_url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        publish_data = {"publish_id": publish_id}
        
        for _ in range(30):
            response = requests.post(publish_url, headers=headers, json=publish_data, timeout=30)
            if response.json()["data"]["status"] == "PUBLISH_COMPLETE":
                post_id = response.json()["data"]["post_id"]
                return PostResult(
                    platform="tiktok",
                    post_id=post_id,
                    url=f"https://www.tiktok.com/@{self.get_username()}/video/{post_id}",
                    status="success",
                    posted_at=datetime.now().isoformat()
                )
            time.sleep(2)
        
        return PostResult(
            platform="tiktok",
            post_id="",
            url="",
            status="failed",
            error="Publish timeout",
            posted_at=datetime.now().isoformat()
        )

    def get_username(self) -> str:
        url = "https://open.tiktokapis.com/v2/user/info/"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers, timeout=30)
        return response.json()["data"]["user"]["username"]

    def post(self, video_path: str, title: str, description: str, hashtags: List[str]) -> PostResult:
        full_title = f"{title} {' '.join(['#' + h for h in hashtags])}"
        return self.upload_video(video_path, full_title, hashtags)


class MultiPlatformPoster:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.youtube = YouTubePoster(self.config) if self.config["social_media"]["youtube"]["enabled"] else None
        self.instagram = InstagramPoster(self.config) if self.config["social_media"]["instagram"]["enabled"] else None
        self.tiktok = TikTokPoster(self.config) if self.config["social_media"]["tiktok"]["enabled"] else None

    def post_all(self, video_path: str, title: str, description: str, hashtags: List[str], 
                 youtube_url: str = "") -> List[PostResult]:
        results = []
        
        # YouTube first (provides URL for Instagram)
        youtube_result = None
        if self.youtube:
            print("Posting to YouTube Shorts...")
            try:
                youtube_result = self.youtube.upload(video_path, title, description, hashtags)
                results.append(youtube_result)
                print(f"YouTube: {youtube_result.url}")
            except Exception as e:
                print(f"YouTube failed: {e}")
                results.append(PostResult("youtube", "", "", "failed", str(e), datetime.now().isoformat()))
        
        # Instagram (uses YouTube URL)
        if self.instagram and youtube_result and youtube_result.status == "success":
            print("Posting to Instagram Reels...")
            try:
                ig_result = self.instagram.post(youtube_result.url, title, description, hashtags)
                results.append(ig_result)
                print(f"Instagram: {ig_result.url}")
            except Exception as e:
                print(f"Instagram failed: {e}")
                results.append(PostResult("instagram", "", "", "failed", str(e), datetime.now().isoformat()))
        
        # TikTok (direct upload)
        if self.tiktok:
            print("Posting to TikTok...")
            try:
                tt_result = self.tiktok.post(video_path, title, description, hashtags)
                results.append(tt_result)
                print(f"TikTok: {tt_result.url}")
            except Exception as e:
                print(f"TikTok failed: {e}")
                results.append(PostResult("tiktok", "", "", "failed", str(e), datetime.now().isoformat()))
        
        return results


def main():
    poster = MultiPlatformPoster()
    print("MultiPlatformPoster initialized")
    print("Add credentials to credentials/ folder to test")


if __name__ == "__main__":
    main()