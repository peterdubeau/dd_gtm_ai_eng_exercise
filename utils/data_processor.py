"""Data processing utilities for handling speaker data and CSV operations."""

import pandas as pd
import asyncio
import logging
from typing import List, Optional
from pathlib import Path
from .models import Speaker, CompanyCategory
from .company_classifier import CompanyClassifier
from .email_generator import EmailGenerator, EmailGenerationRequest
from .config import Config

# Configure logger
logger = logging.getLogger(__name__)


class DataProcessor:
    """Handles data processing and CSV operations."""

    def __init__(self):
        self.classifier = CompanyClassifier()
        self.email_generator = EmailGenerator()

    async def process_speaker_list(
        self, input_file: str, output_file: str, max_speakers: Optional[int] = None
    ) -> None:
        """Process speaker list and generate email content."""
        try:
            # Read input data
            speakers = self._read_speaker_data(input_file)

            # Apply speaker limit for testing
            if max_speakers is None:
                max_speakers = Config.MAX_SPEAKERS
            if len(speakers) > max_speakers:
                logger.warning(
                    f"Limiting processing to {max_speakers} speakers (out of {len(speakers)} total)"
                )
                speakers = speakers[:max_speakers]

            # Process speakers asynchronously
            processed_speakers = await self._process_speakers(speakers)

            # Write output
            self._write_output(processed_speakers, output_file)

            logger.info(f"Successfully processed {len(processed_speakers)} speakers")
            logger.info(f"Output saved to: {output_file}")

        except Exception as e:
            logger.error(f"Error processing speaker list: {e}")
            raise

    def _read_speaker_data(self, input_file: str) -> List[Speaker]:
        """Read speaker data from CSV file."""
        try:
            # Try to read as CSV first
            if input_file.endswith(".csv"):
                return self._read_csv_file(input_file)
            else:
                return self._parse_text_file(input_file)

        except Exception as e:
            logger.error(f"Error reading speaker data: {e}")
            raise

    def _read_csv_file(self, input_file: str) -> List[Speaker]:
        """Read speaker data from CSV file with deduplication."""
        df = pd.read_csv(input_file, encoding="utf-8")

        # Find required columns
        name_col = self._find_column(
            df, ["name", "Name", "speaker_name", "Speaker Name"]
        )
        title_col = self._find_column(
            df, ["title", "Title", "speaker_title", "Speaker Title", "job_title"]
        )
        company_col = self._find_column(
            df, ["company", "Company", "speaker_company", "Speaker Company"]
        )

        if not all([name_col, title_col, company_col]):
            raise ValueError("CSV must contain name, title, and company columns")

        # Remove duplicates based on name, title, and company
        df_clean = df.drop_duplicates(
            subset=[name_col, title_col, company_col], keep="first"
        )

        if len(df) != len(df_clean):
            logger.warning(
                f"Removed {len(df) - len(df_clean)} duplicate entries from CSV"
            )

        speakers = []
        for _, row in df_clean.iterrows():
            speaker = Speaker(
                name=str(row[name_col]).strip(),
                title=str(row[title_col]).strip(),
                company=str(row[company_col]).strip(),
            )
            speakers.append(speaker)

        return speakers

    def _parse_csv_data(self, df: pd.DataFrame) -> List[Speaker]:
        """Parse CSV data into Speaker objects."""
        speakers = []

        # Handle different possible column names
        name_col = self._find_column(
            df, ["name", "speaker", "speaker_name", "full_name"]
        )
        title_col = self._find_column(df, ["title", "job_title", "role", "position"])
        company_col = self._find_column(
            df, ["company", "organization", "firm", "employer"]
        )

        if not all([name_col, title_col, company_col]):
            raise ValueError("Required columns (name, title, company) not found in CSV")

        for _, row in df.iterrows():
            speaker = Speaker(
                name=str(row[name_col]).strip(),
                title=str(row[title_col]).strip(),
                company=str(row[company_col]).strip(),
            )
            speakers.append(speaker)

        return speakers

    def _find_column(
        self, df: pd.DataFrame, possible_names: List[str]
    ) -> Optional[str]:
        """Find column by possible names."""
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    def _parse_text_file(self, input_file: str) -> List[Speaker]:
        """Parse text file with speaker information."""
        speakers = []

        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Try to parse line with common separators
            for separator in ["|", ",", ";", "\t"]:
                parts = [part.strip() for part in line.split(separator)]
                if len(parts) >= 3:
                    speaker = Speaker(name=parts[0], title=parts[1], company=parts[2])
                    speakers.append(speaker)
                    break

        return speakers

    async def _process_speakers(self, speakers: List[Speaker]) -> List[Speaker]:
        """Process speakers with classification and email generation."""
        processed_speakers = []

        # Process speakers in batches to avoid overwhelming APIs
        batch_size = 5
        for i in range(0, len(speakers), batch_size):
            batch = speakers[i : i + batch_size]
            tasks = [self._process_single_speaker(speaker) for speaker in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing speaker: {result}")
                else:
                    processed_speakers.append(result)

            # Small delay between batches
            if i + batch_size < len(speakers):
                await asyncio.sleep(1)

        return processed_speakers

    async def _process_single_speaker(self, speaker: Speaker) -> Speaker:
        """Process a single speaker with classification and email generation."""
        try:
            # Classify company
            category = await self.classifier.classify_company(speaker.company)
            speaker.company_category = category

            # Skip email generation for competitors
            if category == CompanyCategory.COMPETITOR:
                speaker.email_subject = "N/A - Competitor"
                speaker.email_body = "N/A - Competitor"
                return speaker

            # Generate email content
            request = EmailGenerationRequest(
                speaker_name=speaker.name,
                speaker_title=speaker.title,
                company_name=speaker.company,
                company_category=category,
            )

            email_response = await self.email_generator.generate_email(request)
            speaker.email_subject = email_response.subject
            speaker.email_body = email_response.body

            return speaker

        except Exception as e:
            logger.error(f"Error processing speaker {speaker.name}: {e}")
            # Return speaker with error indicators
            speaker.company_category = CompanyCategory.OTHER
            speaker.email_subject = "Error generating email"
            speaker.email_body = "Error generating email content"
            return speaker

    def _write_output(self, speakers: List[Speaker], output_file: str) -> None:
        """Write processed speakers to CSV file."""
        # Create output directory if it doesn't exist
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to DataFrame
        data = []
        for speaker in speakers:
            data.append(
                {
                    "Speaker Name": speaker.name,
                    "Speaker Title": speaker.title,
                    "Speaker Company": speaker.company,
                    "Company Category": speaker.company_category.value
                    if speaker.company_category
                    else "Unknown",
                    "Email Subject": speaker.email_subject or "N/A",
                    "Email Body": speaker.email_body or "N/A",
                }
            )

        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False, encoding="utf-8")

        # Print summary statistics
        self._print_summary(speakers)

    def _print_summary(self, speakers: List[Speaker]) -> None:
        """Print summary statistics of processed speakers."""
        categories = {}
        for speaker in speakers:
            category = (
                speaker.company_category.value
                if speaker.company_category
                else "Unknown"
            )
            categories[category] = categories.get(category, 0) + 1

        logger.info("\n=== Processing Summary ===")
        logger.info(f"Total speakers processed: {len(speakers)}")
        logger.info("\nCategory breakdown:")
        for category, count in categories.items():
            logger.info(f"  {category}: {count}")

        # Count emails generated (excluding competitors)
        emails_generated = sum(
            1 for s in speakers if s.company_category != CompanyCategory.COMPETITOR
        )
        logger.info(f"\nEmails generated: {emails_generated}")
        logger.info(
            f"Competitors excluded: {categories.get(CompanyCategory.COMPETITOR.value, 0)}"
        )
