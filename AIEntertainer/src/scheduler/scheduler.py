import schedule
import time
import yaml
import logging
from datetime import datetime
from typing import List
from dataclasses import asdict

from src.character.character_manager import CharacterManager
from src.content.script_generator import RoastScriptGenerator, RoastScript
from src.video.video_generator import ComfyUIVideoGenerator, VideoClip
from src.editor.auto_editor import AutoEditor, ClipInfo
from src.poster.multi_poster import MultiPlatformPoster, PostResult
from src.analytics.analytics import AnalyticsDB, VideoRecord, AnalyticsReporter


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/ai_entertainer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AIEntertainerPipeline:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.schedule_times = self.config["system"]["schedule_times"]
        self.max_daily = self.config["system"]["max_daily_videos"]
        self.timezone = self.config["system"]["timezone"]
        
        self.character_mgr = CharacterManager(config_path)
        self.script_gen = RoastScriptGenerator(config_path)
        self.video_gen = ComfyUIVideoGenerator(config_path)
        self.editor = AutoEditor(config_path)
        self.poster = MultiPlatformPoster(config_path)
        self.analytics_db = AnalyticsDB(config_path)
        self.reporter = AnalyticsReporter(config_path)
        
        logger.info("AIEntertainer Pipeline initialized")

    def run_single_cycle(self) -> dict:
        """Run one complete video creation and posting cycle"""
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("Starting AIEntertainer cycle")
        logger.info("=" * 50)
        
        results = {
            "started_at": start_time.isoformat(),
            "script": None,
            "clips": [],
            "final_video": None,
            "posts": [],
            "analytics_id": None,
            "errors": []
        }
        
        try:
            # Step 1: Generate script
            logger.info("Step 1: Generating roast script...")
            script = self.script_gen.generate_script()
            results["script"] = asdict(script)
            logger.info(f"Script: {script.title} ({script.category})")
            
            # Step 2: Generate video clips
            logger.info("Step 2: Generating video clips...")
            clips = self.video_gen.generate_script_clips(script, self.character_mgr)
            results["clips"] = [asdict(c) for c in clips]
            logger.info(f"Generated {len(clips)} clips")
            
            # Step 3: Convert to editor format
            editor_clips = []
            for clip in clips:
                duration_sec = float(clip.duration.replace('s', ''))
                editor_clips.append(ClipInfo(
                    path=clip.local_path,
                    duration=duration_sec,
                    text=script.roast_lines[clips.index(clip)] if clips.index(clip) < len(script.roast_lines) else "",
                    expression=clip.expression
                ))
            
            # Step 4: Edit final video
            logger.info("Step 3: Editing final video...")
            final_video = self.editor.assemble_final_video(editor_clips, script)
            results["final_video"] = final_video
            logger.info(f"Final video: {final_video}")
            
            # Step 5: Post to platforms
            logger.info("Step 4: Posting to platforms...")
            post_results = self.poster.post_all(
                final_video, script.title, script.hook, script.hashtags
            )
            results["posts"] = [asdict(p) for p in post_results]
            
            for post in post_results:
                if post.status == "success":
                    logger.info(f"Posted to {post.platform}: {post.url}")
                else:
                    logger.error(f"Failed {post.platform}: {post.error}")
                    results["errors"].append(f"{post.platform}: {post.error}")
            
            # Step 6: Save to analytics
            logger.info("Step 5: Saving to analytics...")
            youtube_post = next((p for p in post_results if p.platform == "youtube"), None)
            ig_post = next((p for p in post_results if p.platform == "instagram"), None)
            tt_post = next((p for p in post_results if p.platform == "tiktok"), None)
            
            record = VideoRecord(
                title=script.title,
                topic=script.topic,
                category=script.category,
                video_file=final_video,
                posted_at=datetime.now().isoformat(),
                youtube_post_id=youtube_post.post_id if youtube_post else "",
                youtube_url=youtube_post.url if youtube_post else "",
                instagram_post_id=ig_post.post_id if ig_post else "",
                tiktok_post_id=tt_post.post_id if tt_post else "",
                status="posted" if any(p.status == "success" for p in post_results) else "failed",
                created_at=datetime.now().isoformat()
            )
            analytics_id = self.analytics_db.insert_video(record)
            results["analytics_id"] = analytics_id
            logger.info(f"Analytics ID: {analytics_id}")
            
        except Exception as e:
            logger.exception("Pipeline failed")
            results["errors"].append(str(e))
        
        results["completed_at"] = datetime.now().isoformat()
        results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Cycle completed in {results['duration_seconds']:.1f}s")
        logger.info("=" * 50)
        
        return results

    def run_daily_batch(self):
        """Run multiple cycles for daily batch"""
        count = self.max_daily
        logger.info(f"Running daily batch: {count} videos")
        
        for i in range(count):
            logger.info(f"\n--- Video {i+1}/{count} ---")
            self.run_single_cycle()
            if i < count - 1:
                time.sleep(30)  # Brief pause between videos

    def update_analytics(self):
        """Update view counts from platform APIs"""
        logger.info("Updating analytics from platform APIs...")
        self.analytics_db.update_daily_stats()
        logger.info("Analytics updated")

    def generate_report(self, period: str = "weekly"):
        """Generate and print analytics report"""
        self.reporter.print_report(period)

    def start_scheduler(self):
        """Start the automated scheduler"""
        logger.info(f"Scheduler started. Daily posts at: {self.schedule_times}")
        
        # Schedule daily batch at each time
        for t in self.schedule_times:
            schedule.every().day.at(t).do(self.run_single_cycle)
        
        # Schedule analytics update every 4 hours
        schedule.every(4).hours.do(self.update_analytics)
        
        # Schedule weekly report on Mondays
        schedule.every().monday.at("09:00").do(lambda: self.generate_report("weekly"))
        
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        
        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    import sys
    
    pipeline = AIEntertainerPipeline()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "run":
            pipeline.run_single_cycle()
        elif command == "batch":
            pipeline.run_daily_batch()
        elif command == "schedule":
            pipeline.start_scheduler()
        elif command == "report":
            period = sys.argv[2] if len(sys.argv) > 2 else "weekly"
            pipeline.generate_report(period)
        elif command == "update-analytics":
            pipeline.update_analytics()
        elif command == "test-script":
            script = pipeline.script_gen.generate_script()
            print(f"Title: {script.title}")
            print(f"Hook: {script.hook}")
            for i, line in enumerate(script.roast_lines):
                print(f"  {i+1}. {line}")
        else:
            print("Commands: run, batch, schedule, report, update-analytics, test-script")
    else:
        print("AIEntertainer Pipeline")
        print("Commands:")
        print("  run              - Run one cycle")
        print("  batch            - Run full daily batch")
        print("  schedule         - Start automated scheduler")
        print("  report [period]  - Generate report (daily/weekly/monthly)")
        print("  update-analytics - Update view counts")
        print("  test-script      - Test script generation")


if __name__ == "__main__":
    main()