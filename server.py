"""Main FastAPI application for DroneDeploy email generation system."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
import pandas as pd

from utils.config import Config
from utils.models import Speaker, CompanyCategory
from utils.data_processor import DataProcessor
from utils.company_classifier import CompanyClassifier
from utils.email_generator import EmailGenerator, EmailGenerationRequest
from utils.speaker_scraper import SpeakerScraper


# Configure logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    logger.info("Starting DroneDeploy Email Generation System")

    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed")
        raise RuntimeError("Invalid configuration")

    logger.info("Configuration validated successfully")

    yield

    # Shutdown
    logger.info("Shutting down DroneDeploy Email Generation System")


# Create FastAPI app
app = FastAPI(
    title="DroneDeploy Email Generation System",
    description="AI-powered system for generating personalized outreach emails to conference speakers",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "DroneDeploy Email Generation System",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "config_valid": Config.validate()}


@app.post("/scrape-website")
async def scrape_website(
    url: str = Query(
        default="https://www.digitalconstructionweek.com/all-speakers/",
        description="URL of the conference website to scrape",
    ),
):
    """Extract speaker information from a conference website URL."""
    try:
        # Validate URL
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Run scraper
        scraper = SpeakerScraper()
        speakers = scraper.scrape_website(url)

        # Save to CSV
        output_path = Path(Config.OUTPUT_DIR) / "speakers.csv"
        scraper.save_to_csv(speakers, str(output_path))

        # Return the CSV file directly
        return FileResponse(
            path=str(output_path), filename="speakers.csv", media_type="text/csv"
        )

    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-speakers")
async def process_speakers(
    file: UploadFile = File(..., description="CSV file with speaker information"),
    max_speakers: Optional[int] = Query(
        None, description="Maximum number of speakers to process"
    ),
):
    """Process speaker list and generate email content."""
    try:
        # Validate file type
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="File must be a CSV")

        # Save uploaded file
        input_path = Path(Config.INPUT_DIR) / file.filename
        input_path.parent.mkdir(parents=True, exist_ok=True)

        with open(input_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Process speakers
        output_path = Path(Config.OUTPUT_DIR) / "email_list.csv"
        processor = DataProcessor()

        await processor.process_speaker_list(
            str(input_path), str(output_path), int(max_speakers)
        )
        return FileResponse(
            path=str(output_path), filename="email_list.csv", media_type="text/csv"
        )

    except Exception as e:
        logger.error(f"Error processing speakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/classify-company")
async def classify_company(company_name: str):
    """Classify a single company."""
    try:
        classifier = CompanyClassifier()
        category = await classifier.classify_company(company_name)

        return {
            "company_name": company_name,
            "category": category.value,
            "description": get_category_description(category),
        }

    except Exception as e:
        logger.error(f"Error classifying company {company_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-email")
async def generate_email(request: EmailGenerationRequest):
    """Generate email content for a single speaker."""
    try:
        generator = EmailGenerator()
        response = await generator.generate_email(request)

        return {
            "speaker_name": request.speaker_name,
            "company_name": request.company_name,
            "category": response.category.value,
            "subject": response.subject,
            "body": response.body,
        }

    except Exception as e:
        logger.error(f"Error generating email for {request.speaker_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/categories")
async def get_categories():
    """Get information about company categories."""
    return {
        "categories": [
            {"value": category.value, "description": get_category_description(category)}
            for category in CompanyCategory
        ]
    }


def get_category_description(category: CompanyCategory) -> str:
    """Get description for a company category."""
    descriptions = {
        CompanyCategory.BUILDER: "Construction, engineering, or building services companies that build things",
        CompanyCategory.OWNER: "Property owners, real estate companies, or asset managers that get things built",
        CompanyCategory.PARTNER: "Potential technology partners or service providers",
        CompanyCategory.COMPETITOR: "Companies in the drone, mapping, or surveying space (competitors)",
        CompanyCategory.OTHER: "Companies that don't clearly fit into the main categories",
    }
    return descriptions.get(category, "Unknown category")


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=Config.LOG_LEVEL.lower(),
    )
