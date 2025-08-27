"""Speaker scraper for extracting conference speaker information from HTML and websites."""

import re
import csv
import requests
import logging
from pathlib import Path
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Configure logger
logger = logging.getLogger(__name__)


class SpeakerScraper:
    """Scraper for extracting speaker information from conference websites."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def scrape_website(self, url: str = None) -> List[Dict[str, str]]:
        """Scrape speaker information from a conference website."""
        # Default to Digital Construction Week if no URL provided
        if url is None:
            url = "https://www.digitalconstructionweek.com/all-speakers/"

        try:
            logger.info(f"Fetching website: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            logger.info(
                f"Successfully fetched website (Status: {response.status_code})"
            )
            return self._extract_speaker_info(response.text)

        except requests.RequestException as e:
            logger.error(f"Error fetching website: {e}")
            raise

    def scrape_html_file(self, file_path: str) -> List[Dict[str, str]]:
        """Scrape speaker information from a local HTML file."""
        try:
            logger.info(f"Reading HTML file: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            return self._extract_speaker_info(html_content)

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise

    def _extract_speaker_info(self, html_content: str) -> List[Dict[str, str]]:
        """Extract speaker information from HTML content."""
        soup = BeautifulSoup(html_content, "html5lib")
        speakers = []

        # Find all speaker grid items
        speaker_items = soup.find_all("div", class_="speaker-grid-item")

        logger.info(f"Found {len(speaker_items)} speaker grid items")

        for item in speaker_items:
            speaker_info = self._extract_single_speaker(item)
            if speaker_info:
                speakers.append(speaker_info)

        # Remove duplicates
        unique_speakers = self._remove_duplicates(speakers)
        logger.info(f"Successfully extracted {len(unique_speakers)} unique speakers")
        return unique_speakers

    def _extract_single_speaker(self, speaker_item) -> Optional[Dict[str, str]]:
        """Extract speaker information from a single speaker grid item."""
        try:
            # Find speaker name (h3 tag)
            name_elem = speaker_item.find("h3")
            if not name_elem:
                return None

            name = self._clean_text(name_elem.get_text())

            # Find job title (p tag with class 'speaker-job')
            job_elem = speaker_item.find("p", class_="speaker-job")
            if not job_elem:
                return None

            job_title = self._clean_text(job_elem.get_text())

            # Extract company name from job title
            company = self._extract_company_from_title(job_title)

            return {"name": name, "title": job_title, "company": company}

        except Exception as e:
            logger.error(f"Error extracting speaker info: {e}")
            return None

    def _extract_company_from_title(self, job_title: str) -> str:
        """Extract company name from job title."""
        # Common patterns for extracting company names
        patterns = [
            r"at\s+(.+)$",  # "at Company Name"
            r"with\s+(.+)$",  # "with Company Name"
            r"from\s+(.+)$",  # "from Company Name"
            r"of\s+(.+)$",  # "of Company Name"
        ]

        for pattern in patterns:
            match = re.search(pattern, job_title, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                company = self._clean_company_name(company)
                return company

        # If no pattern matches, try to extract the last part after common separators
        separators = [" at ", " with ", " from ", " of ", " - ", " | "]
        for separator in separators:
            if separator in job_title:
                parts = job_title.split(separator)
                if len(parts) > 1:
                    company = parts[-1].strip()
                    company = self._clean_company_name(company)
                    return company

        # If all else fails, return the full job title
        return self._clean_company_name(job_title)

    def _parse_title_company(
        self, title_company_text: str, name: str
    ) -> Optional[Dict[str, str]]:
        """Parse title and company from text like 'Digital Lead at Laing O'Rourke'."""
        try:
            # Pattern: "Title at Company"
            pattern = r"^(.+?)\s+at\s+(.+)$"
            match = re.search(pattern, title_company_text, re.IGNORECASE)

            if match:
                title = match.group(1).strip()
                company = match.group(2).strip()

                # Clean up
                title = self._clean_text(title)
                company = self._clean_company_name(company)

                return {"name": name, "title": title, "company": company}

            return None

        except Exception as e:
            logger.error(f"Error parsing title/company '{title_company_text}': {e}")
            return None

    def _remove_duplicates(
        self, speakers: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Remove duplicate speakers based on name, title, and company."""
        seen = set()
        unique_speakers = []

        for speaker in speakers:
            # Create a unique key based on name, title, and company
            key = (
                speaker.get("name", "").lower().strip(),
                speaker.get("title", "").lower().strip(),
                speaker.get("company", "").lower().strip(),
            )

            if key not in seen:
                seen.add(key)
                unique_speakers.append(speaker)

        return unique_speakers

    def _clean_text(self, text: str) -> str:
        """Clean up text by removing extra whitespace and line breaks."""
        if not text:
            return ""

        text = text.replace("&amp;", "&").replace("&nbsp;", " ")
        text = re.sub(r"\s+", " ", text)
        text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _clean_company_name(self, company: str) -> str:
        """Clean up company name."""
        if not company:
            return ""

        company = self._clean_text(company)
        company = re.sub(
            r"\s+(Ltd|LLC|Inc|Corp|Limited|Corporation|Company|Co)\.?$",
            "",
            company,
            flags=re.IGNORECASE,
        )
        company = re.sub(r"\s+", " ", company).strip()

        return company

    def save_to_csv(self, speakers: List[Dict[str, str]], output_file: str) -> None:
        """Save speaker data to CSV file."""
        try:
            # Create output directory if it doesn't exist
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove duplicates before saving
            unique_speakers = self._remove_duplicates(speakers)
            logger.info(
                f"Removed {len(speakers) - len(unique_speakers)} duplicate entries"
            )

            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["name", "title", "company"]
                writer = csv.DictWriter(
                    csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL
                )

                writer.writeheader()
                for speaker in unique_speakers:
                    writer.writerow(speaker)

            logger.info(
                f"Saved {len(unique_speakers)} unique speakers to {output_file}"
            )

        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            raise


def main():
    """Main function for testing the scraper."""
    scraper = SpeakerScraper()

    # Example usage for website scraping
    logger.info("Scraping Digital Construction Week speakers...")
    try:
        speakers = scraper.scrape_website()
        scraper.save_to_csv(speakers, "in/speakers.csv")

        # Print sample data
        logger.info("\n📋 Sample extracted data:")
        for i, speaker in enumerate(speakers[:5]):
            logger.info(
                f"{i + 1}. {speaker['name']} - {speaker['title']} at {speaker['company']}"
            )

    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        logger.warning("Falling back to HTML file scraping...")

        # Fallback to HTML file
        html_file = "conference_speaker_list.html"
        if Path(html_file).exists():
            speakers = scraper.scrape_html_file(html_file)
            scraper.save_to_csv(speakers, "in/speakers.csv")
        else:
            logger.error(f"HTML file not found: {html_file}")


if __name__ == "__main__":
    main()
