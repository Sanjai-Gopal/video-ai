#!/usr/bin/env python3
"""
AIEntertainer - Fully Automated Roaster/Commentator Channel
Run: python main.py [run|batch|schedule|report|test-script]
"""

import sys
from src.scheduler.scheduler import AIEntertainerPipeline


def main():
    pipeline = AIEntertainerPipeline()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "run":
            print("Running single cycle...")
            pipeline.run_single_cycle()
        elif command == "batch":
            print("Running daily batch...")
            pipeline.run_daily_batch()
        elif command == "schedule":
            print("Starting scheduler...")
            pipeline.start_scheduler()
        elif command == "report":
            period = sys.argv[2] if len(sys.argv) > 2 else "weekly"
            pipeline.generate_report(period)
        elif command == "update-analytics":
            pipeline.update_analytics()
        elif command == "test-script":
            script = pipeline.script_gen.generate_script()
            print(f"Title: {script.title}")
            print(f"Topic: {script.topic}")
            print(f"Hook: {script.hook}")
            for i, line in enumerate(script.roast_lines):
                print(f"  {i+1}. {line}")
            print(f"CTA: {script.cta}")
            print(f"Hashtags: {script.hashtags}")
        else:
            print("Usage: python main.py [run|batch|schedule|report|update-analytics|test-script]")
    else:
        print("AIEntertainer - Automated Roaster Channel")
        print("=========================================")
        print("Commands:")
        print("  python main.py run              - Create & post 1 video")
        print("  python main.py batch            - Create & post 4 videos (daily batch)")
        print("  python main.py schedule         - Start automated scheduler (4x/day)")
        print("  python main.py report [period]  - Show analytics (daily/weekly/monthly)")
        print("  python main.py update-analytics - Fetch view counts from APIs")
        print("  python main.py test-script      - Test script generation only")


if __name__ == "__main__":
    main()