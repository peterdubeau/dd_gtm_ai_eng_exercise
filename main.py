"""Test script to run the email generation pipeline with limited speakers."""
import asyncio
import os
import logging
from pathlib import Path
from utils.data_processor import DataProcessor
from utils.speaker_scraper import SpeakerScraper

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Run the email generation pipeline with limited speakers for testing."""
    logger.info("🧪 Running DroneDeploy Email Generation Pipeline")
    logger.info("=" * 60)
    
    # Check if speakers.csv exists
    input_file = "in/speakers.csv"
    if not Path(input_file).exists():
        logger.warning(f"❌ Input file not found: {input_file}")
        logger.info("Running speaker scraper...")
        scraper = SpeakerScraper()
        speakers = scraper.scrape_website()
        scraper.save_to_csv(speakers, "in/speakers.csv")
    logger.info(f"🔢 Processing limit: {os.environ['MAX_SPEAKERS']} speakers")
    
    # Check if OpenAI API key is set
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.info("⚠️  OPENAI_API_KEY not found - running classification only")
        logger.info("To test email generation, set: export OPENAI_API_KEY=your_key")
        logger.info()
    
    # Process speakers
    logger.info(f"📊 Processing speakers from {input_file}...")
    processor = DataProcessor()
    
    try:
        await processor.process_speaker_list(input_file, "out/email_list.csv")
        logger.info("\n✅ Emails successfully generated!")
        logger.info(f"📁 Output saved to: out/email_list.csv")
        
        if not openai_key:
            logger.info("\n📝 Note: Email content was not generated due to missing OpenAI API key")
            logger.info("The CSV contains speaker data and company classifications only.")
        
    except Exception as e:
        logger.error(f"❌ Error during processing: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())
