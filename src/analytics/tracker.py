import sqlite3
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import pandas as pd


@dataclass
class VideoRecord:
    id: Optional[int] = None
    title: str = ""
    topic: str = ""
    niche: str = ""
    script_preview: str = ""
    video_file: str = ""
    posted_at: str = ""
    youtube_post_id: str = ""
    youtube_url: str = ""
    facebook_post_id: str = ""
    instagram_post_id: str = ""
    status: str = "pending"
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    estimated_revenue: float = 0.0
    created_at: str = ""


class AnalyticsDB:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.db_path = Path(self.config["analytics"]["db_path"])
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    topic TEXT,
                    niche TEXT,
                    script_preview TEXT,
                    video_file TEXT,
                    posted_at TEXT,
                    youtube_post_id TEXT,
                    youtube_url TEXT,
                    facebook_post_id TEXT,
                    instagram_post_id TEXT,
                    status TEXT DEFAULT 'pending',
                    views INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    estimated_revenue REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    videos_posted INTEGER DEFAULT 0,
                    total_views INTEGER DEFAULT 0,
                    total_likes INTEGER DEFAULT 0,
                    total_comments INTEGER DEFAULT 0,
                    estimated_revenue REAL DEFAULT 0.0
                )
            """)
            conn.commit()

    def insert_video(self, record: VideoRecord) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO videos (title, topic, niche, script_preview, video_file, posted_at,
                                   youtube_post_id, youtube_url, facebook_post_id, instagram_post_id,
                                   status, views, likes, comments, shares, estimated_revenue, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.title, record.topic, record.niche, record.script_preview,
                record.video_file, record.posted_at, record.youtube_post_id,
                record.youtube_url, record.facebook_post_id, record.instagram_post_id,
                record.status, record.views, record.likes, record.comments,
                record.shares, record.estimated_revenue, record.created_at
            ))
            conn.commit()
            return cursor.lastrowid

    def update_video(self, video_id: int, **kwargs):
        allowed = {"youtube_post_id", "youtube_url", "facebook_post_id", "instagram_post_id",
                   "status", "views", "likes", "comments", "shares", "estimated_revenue"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [video_id]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE videos SET {set_clause} WHERE id = ?", values)
            conn.commit()

    def get_video(self, video_id: int) -> Optional[VideoRecord]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()
            if row:
                return VideoRecord(**dict(row))
        return None

    def get_recent_videos(self, days: int = 7) -> List[VideoRecord]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM videos WHERE created_at >= ? ORDER BY created_at DESC",
                (cutoff,)
            )
            return [VideoRecord(**dict(row)) for row in cursor.fetchall()]

    def get_all_videos(self) -> List[VideoRecord]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM videos ORDER BY created_at DESC")
            return [VideoRecord(**dict(row)) for row in cursor.fetchall()]

    def update_daily_stats(self, date: str = None):
        date = date or datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) as count, SUM(views) as views, SUM(likes) as likes,
                       SUM(comments) as comments, SUM(estimated_revenue) as revenue
                FROM videos WHERE date(created_at) = ?
            """, (date,))
            row = cursor.fetchone()
            
            if row and row[0] > 0:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_stats (date, videos_posted, total_views, total_likes, total_comments, estimated_revenue)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (date, row[0], row[1] or 0, row[2] or 0, row[3] or 0, row[4] or 0.0))
                conn.commit()

    def get_daily_stats(self, days: int = 30) -> List[Dict]:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM daily_stats WHERE date >= ? ORDER BY date DESC",
                (cutoff,)
            )
            return [dict(row) for row in cursor.fetchall()]


class AnalyticsReporter:
    def __init__(self, config_path: str = "config.yaml"):
        self.db = AnalyticsDB(config_path)
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def generate_report(self, period: str = "weekly") -> Dict:
        days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 7)
        videos = self.db.get_recent_videos(days)
        daily_stats = self.db.get_daily_stats(days)
        
        total_videos = len(videos)
        total_views = sum(v.views for v in videos)
        total_likes = sum(v.likes for v in videos)
        total_comments = sum(v.comments for v in videos)
        total_shares = sum(v.shares for v in videos)
        total_revenue = sum(v.estimated_revenue for v in videos)
        
        # Per-niche breakdown
        niche_stats = {}
        for v in videos:
            if v.niche not in niche_stats:
                niche_stats[v.niche] = {"count": 0, "views": 0, "revenue": 0.0}
            niche_stats[v.niche]["count"] += 1
            niche_stats[v.niche]["views"] += v.views
            niche_stats[v.niche]["revenue"] += v.estimated_revenue
        
        # Top performing videos
        top_videos = sorted(videos, key=lambda v: v.views, reverse=True)[:5]
        
        # Platform breakdown
        platform_stats = {
            "youtube": {"posted": 0, "views": 0},
            "instagram": {"posted": 0, "views": 0},
            "facebook": {"posted": 0, "views": 0}
        }
        for v in videos:
            if v.youtube_post_id:
                platform_stats["youtube"]["posted"] += 1
                platform_stats["youtube"]["views"] += v.views
            if v.instagram_post_id:
                platform_stats["instagram"]["posted"] += 1
            if v.facebook_post_id:
                platform_stats["facebook"]["posted"] += 1
        
        return {
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_videos": total_videos,
                "total_views": total_views,
                "total_likes": total_likes,
                "total_comments": total_comments,
                "total_shares": total_shares,
                "total_estimated_revenue": round(total_revenue, 2),
                "avg_views_per_video": round(total_views / max(total_videos, 1), 1),
                "avg_revenue_per_video": round(total_revenue / max(total_videos, 1), 4)
            },
            "niche_breakdown": niche_stats,
            "platform_breakdown": platform_stats,
            "top_videos": [
                {
                    "title": v.title,
                    "topic": v.topic,
                    "views": v.views,
                    "revenue": v.estimated_revenue,
                    "youtube_url": v.youtube_url
                } for v in top_videos
            ],
            "daily_trend": daily_stats
        }

    def print_report(self, period: str = "weekly"):
        report = self.generate_report(period)
        print(f"\n{'='*60}")
        print(f"VIDEOAI ANALYTICS REPORT - {period.upper()}")
        print(f"{'='*60}")
        print(f"Generated: {report['generated_at'][:19]}")
        print(f"\nSUMMARY:")
        for k, v in report['summary'].items():
            print(f"  {k.replace('_', ' ').title()}: {v}")
        
        print(f"\nNICHE BREAKDOWN:")
        for niche, stats in report['niche_breakdown'].items():
            print(f"  {niche}: {stats['count']} videos, {stats['views']} views, ${stats['revenue']:.2f}")
        
        print(f"\nPLATFORM BREAKDOWN:")
        for platform, stats in report['platform_breakdown'].items():
            print(f"  {platform.title()}: {stats['posted']} posted")
        
        print(f"\nTOP 5 VIDEOS:")
        for i, v in enumerate(report['top_videos'], 1):
            print(f"  {i}. {v['title'][:50]} - {v['views']} views (${v['revenue']:.4f})")
        
        print(f"{'='*60}\n")
        
        return report

    def export_csv(self, output_path: str = "data/analytics/report.csv"):
        videos = self.db.get_all_videos()
        df = pd.DataFrame([asdict(v) for v in videos])
        df.to_csv(output_path, index=False)
        print(f"Exported {len(videos)} records to {output_path}")


def main():
    reporter = AnalyticsReporter()
    reporter.print_report("weekly")
    reporter.export_csv()


if __name__ == "__main__":
    main()