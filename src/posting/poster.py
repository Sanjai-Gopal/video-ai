import os
import json
import pickle
import yaml
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests


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
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.client_secrets = self.config["social_media"]["youtube"]["client_secrets"]
        self.token_file = self.config["social_media"]["youtube"]["token_file"]
        self.category_id = self.config["social_media"]["youtube"]["category_id"]
        self.privacy = self.config["social_media"]["youtube"]["privacy"]
        self.default_tags = self.config["social_media"]["youtube"]["tags"]
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
        
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags,
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
                print(f"YouTube upload progress: {int(status.progress() * 100)}%")
        
        video_id = response["id"]
        return PostResult(
            platform="youtube",
            post_id=video_id,
            url=f"https://www.youtube.com/shorts/{video_id}",
            status="success",
            posted_at=datetime.now().isoformat()
        )


class InstagramPoster:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.access_token_path = self.config["social_media"]["instagram"]["access_token"]
        self.business_account_id = self.config["social_media"]["instagram"]["business_account_id"]
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

    def post(self, video_url: str, title: str, script: str, topic: str) -> PostResult:
        caption = f"{title}\n\n{script[:500]}\n\n#AI #Technology #Shorts #Reels #Viral #Daily"
        
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


class FacebookPoster:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.access_token_path = self.config["social_media"]["facebook"]["access_token"]
        self.page_id = self.config["social_media"]["facebook"]["page_id"]
        self.graph_version = "v22.0"
        self.access_token = None
        self._load_token()

    def _load_token(self):
        token_path = Path(self.access_token_path)
        if token_path.exists():
            self.access_token = token_path.read_text().strip()

    def post(self, video_path: str, title: str, script: str) -> PostResult:
        url = f"https://graph.facebook.com/{self.graph_version}/{self.page_id}/videos"
        
        description = f"{title}\n\n{script[:1000]}\n\n#AI #Technology #Shorts #Viral"
        
        try:
            with open(video_path, 'rb') as video_file:
                files = {"source": video_file}
                data = {
                    "description": description,
                    "access_token": self.access_token
                }
                response = requests.post(url, files=files, data=data, timeout=120)
                response.raise_for_status()
            
            post_id = response.json()["id"]
            return PostResult(
                platform="facebook",
                post_id=post_id,
                url=f"https://www.facebook.com/{self.page_id}/videos/{post_id}/",
                status="success",
                posted_at=datetime.now().isoformat()
            )
        except Exception as e:
            return PostResult(
                platform="facebook",
                post_id="",
                url="",
                status="failed",
                error=str(e),
                posted_at=datetime.now().isoformat()
            )


class SocialMediaPoster:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.youtube = YouTubePoster(config_path) if self.config["social_media"]["youtube"]["enabled"] else None
        self.instagram = InstagramPoster(config_path) if self.config["social_media"]["instagram"]["enabled"] else None
        self.facebook = FacebookPoster(config_path) if self.config["social_media"]["facebook"]["enabled"] else None

    def post_all(self, video_path: str, title: str, script: str, topic: str, tags: List[str]) -> List[PostResult]:
        results = []
        
        # YouTube upload (gets video URL for Instagram)
        youtube_result = None
        if self.youtube:
            print("Uploading to YouTube...")
            try:
                youtube_result = self.youtube.upload(video_path, title, script, tags)
                results.append(youtube_result)
                print(f"YouTube: {youtube_result.url}")
            except Exception as e:
                print(f"YouTube upload failed: {e}")
                results.append(PostResult(
                    platform="youtube",
                    post_id="",
                    url="",
                    status="failed",
                    error=str(e),
                    posted_at=datetime.now().isoformat()
                ))
        
        # Instagram (needs YouTube URL)
        if self.instagram and youtube_result and youtube_result.status == "success":
            print("Posting to Instagram...")
            try:
                ig_result = self.instagram.post(youtube_result.url, title, script, topic)
                results.append(ig_result)
                print(f"Instagram: {ig_result.url}")
            except Exception as e:
                print(f"Instagram post failed: {e}")
                results.append(PostResult(
                    platform="instagram",
                    post_id="",
                    url="",
                    status="failed",
                    error=str(e),
                    posted_at=datetime.now().isoformat()
                ))
        
        # Facebook (uploads directly)
        if self.facebook:
            print("Posting to Facebook...")
            try:
                fb_result = self.facebook.post(video_path, title, script)
                results.append(fb_result)
                print(f"Facebook: {fb_result.url}")
            except Exception as e:
                print(f"Facebook post failed: {e}")
                results.append(PostResult(
                    platform="facebook",
                    post_id="",
                    url="",
                    status="failed",
                    error=str(e),
                    posted_at=datetime.now().isoformat()
                ))
        
        return results


def main():
    # Test with dummy data
    poster = SocialMediaPoster()
    print("Social media poster initialized")
    print("Configure credentials in credentials/ directory to test")


if __name__ == "__main__":
    main()