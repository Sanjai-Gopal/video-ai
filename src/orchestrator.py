import schedule
import time
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.content.ideation import ContentIdeation, VideoConcept
from src.video.generator import ComfyUIVideoGenerator
from src.tts.synthesizer import VideoAssembler
from src.posting.poster import SocialMediaPoster, PostResult
from src.analytics.tracker import AnalyticsDB, VideoRecord, AnalyticsReporter


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/videoai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VideoAIPipeline:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.content_ideation = ContentIdeation(config_path)
        self.video_generator = ComfyUIVideoGenerator(config_path)
        self.video_assembler = VideoAssembler(config_path)
        self.social_poster = SocialMediaPoster(config_path)
        self.analytics_db = AnalyticsDB(config_path)
        self.reporter = AnalyticsReporter(config_path)
        
        self.schedule_time = self.config["system"]["schedule_time"]
        self.timezone = self.config["system"]["timezone"]
        
        logger.info("VideoAI Pipeline initialized")

    def run_daily_cycle(self) -> dict:
        """Run the complete daily video creation and posting cycle"""
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("Starting daily video creation cycle")
        logger.info("=" * 50)
        
        results = {
            "started_at": start_time.isoformat(),
            "concept": None,
            "raw_video": None,
            "final_video": None,
            "posts": [],
            "analytics_id": None,
            "errors": []
        }
        
        try:
            # Step 1: Generate content concept
            logger.info("Step 1: Generating content concept...")
            concept = self.content_ideation.generate_concept()
            results["concept"] = concept.__dict__
            logger.info(f"Generated: {concept.title} ({concept.niche})")
            
            # Step 2: Generate video with ComfyUI
            logger.info("Step 2: Generating video with ComfyUI...")
            raw_video_path = self.video_generator.generate(concept.video_prompt)
            results["raw_video"] = raw_video_path
            logger.info(f"Raw video: {raw_video_path}")
            
            # Step 3: Assemble final video (TTS + captions)
            logger.info("Step 3: Assembling final video with TTS and captions...")
            final_video_path = self.video_assembler.assemble_final_video(
                raw_video_path, concept.script
            )
            results["final_video"] = final_video_path
            logger.info(f"Final video: {final_video_path}")
            
            # Step 4: Post to social media
            logger.info("Step 4: Posting to social media...")
            tags = self.config["social_media"]["youtube"]["tags"] + [concept.topic, concept.niche]
            post_results = self.social_poster.post_all(
                final_video_path, concept.title, concept.script, concept.topic, tags
            )
            results["posts"] = [p.__dict__ for p in post_results]
            
            for post in post_results:
                if post.status == "success":
                    logger.info(f"Posted to {post.platform}: {post.url}")
                else:
                    logger.error(f"Failed to post to {post.platform}: {post.error}")
                    results["errors"].append(f"{post.platform}: {post.error}")
            
            # Step 5: Save to analytics
            logger.info("Step 5: Saving to analytics...")
            record = VideoRecord(
                title=concept.title,
                topic=concept.topic,
                niche=concept.niche,
                script_preview=concept.script[:200],
                video_file=final_video_path,
                posted_at=datetime.now().isoformat(),
                youtube_post_id=next((p.post_id for p in post_results if p.platform == "youtube"), ""),
                youtube_url=next((p.url for p in post_results if p.platform == "youtube"), ""),
                facebook_post_id=next((p.post_id for p in post_results if p.platform == "facebook"), ""),
                instagram_post_id=next((p.post_id for p in post_results if p.platform == "instagram"), ""),
                status="posted" if any(p.status == "success" for p in post_results) else "failed",
                created_at=datetime.now().isoformat()
            )
            analytics_id = self.analytics_db.insert_video(record)
            results["analytics_id"] = analytics_id
            logger.info(f"Saved to analytics (ID: {analytics_id})")
            
        except Exception as e:
            logger.exception("Pipeline failed")
            results["errors"].append(str(e))
        
        results["completed_at"] = datetime.now().isoformat()
        results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Cycle completed in {results['duration_seconds']:.1f}s")
        logger.info("=" * 50)
        
        return results

    def update_analytics(self):
        """Update view counts and revenue estimates from APIs"""
        logger.info("Updating analytics from social media APIs...")
        # This would fetch actual view counts from YouTube/IG/FB APIs
        # For now, update daily stats
        self.analytics_db.update_daily_stats()
        logger.info("Analytics updated")

    def generate_report(self, period: str = "weekly"):
        """Generate and print analytics report"""
        self.reporter.print_report(period)

    def run_scheduler(self):
        """Run the scheduler for daily execution"""
        logger.info(f"Scheduler started. Daily run at {self.schedule_time} ({self.timezone})")
        
        # Schedule daily run
        schedule.every().day.at(self.schedule_time).do(self.run_daily_cycle)
        
        # Schedule analytics update every 6 hours
        schedule.every(6).hours.do(self.update_analytics)
        
        # Schedule weekly report on Mondays
        schedule.every().monday.at("09:00").do(lambda: self.generate_report("weekly"))
        
        # Run once immediately for testing (comment out for production)
        # logger.info("Running initial cycle...")
        # self.run_daily_cycle()
        
        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    import sys
    
    pipeline = VideoAIPipeline()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "run":
            # Run once
            pipeline.run_daily_cycle()
        elif command == "schedule":
            # Run scheduler
            pipeline.run_scheduler()
        elif command == "report":
            period = sys.argv[2] if len(sys.argv) > 2 else "weekly"
            pipeline.generate_report(period)
        elif command == "update-analytics":
            pipeline.update_analytics()
        elif command == "test-concept":
            # Test content generation only
            concept = pipeline.content_ideation.generate_concept()
            print(f"Title: {concept.title}")
            print(f"Topic: {concept.topic}")
            print(f"Script: {concept.script}")
            print(f"Video Prompt: {concept.video_prompt}")
        else:
            print("Usage: python orchestrator.py [run|schedule|report|update-analytics|test-concept]")
    else:
        print("VideoAI Pipeline")
        print("Commands:")
        print("  run              - Run one complete cycle")
        print("  schedule         - Run scheduler (daily at configured time)")
        print("  report [period]  - Generate analytics report (daily/weekly/monthly)")
        print("  update-analytics - Update view counts from APIs")
        print("  test-concept     - Test content generation only")


if __name__ == "__main__":
    main()