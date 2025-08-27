"""Company classification service using hybrid local + AI approach."""

import asyncio
import logging
import json
from typing import Optional, Dict
from pathlib import Path
import openai
from pydantic import BaseModel
from .models import CompanyCategory
from .config import Config

# Configure logger
logger = logging.getLogger(__name__)


class ClassifierResponse(BaseModel):
    category: CompanyCategory
    confidence: float
    reasoning: str


class CompanyClassifier:
    """Service for classifying companies using hybrid local + AI approach."""

    def __init__(self):
        self.client = (
            openai.AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
            if Config.OPENAI_API_KEY
            else None
        )
        self.cache_file = Path("in/company_classifications.json")
        self.classification_cache = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        """Load company classifications from cache file."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                logger.info(f"Loaded {len(cache)} cached company classifications")
                return cache
            else:
                logger.info("No cache file found, starting with empty cache")
                return {}
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return {}

    def _save_cache(self) -> None:
        """Save company classifications to cache file."""
        try:
            # Ensure the directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.classification_cache, f, indent=2, ensure_ascii=False)

            logger.info(
                f"Saved {len(self.classification_cache)} company classifications to cache"
            )
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _get_cached_classification(
        self, company_name: str
    ) -> Optional[CompanyCategory]:
        """Get cached classification for a company."""
        normalized_name = company_name.strip().lower()
        if normalized_name in self.classification_cache:
            category_value = self.classification_cache[normalized_name]
            try:
                return CompanyCategory(category_value)
            except ValueError:
                logger.warning(
                    f"Invalid cached category '{category_value}' for '{company_name}'"
                )
                return None
        return None

    def _cache_classification(
        self, company_name: str, category: CompanyCategory
    ) -> None:
        """Cache a company classification."""
        normalized_name = company_name.strip().lower()
        self.classification_cache[normalized_name] = category.value
        self._save_cache()

    async def classify_company(self, company_name: str) -> CompanyCategory:
        """Classify a company using hybrid approach with local caching."""
        try:
            # Check cache first
            cached_category = self._get_cached_classification(company_name)
            if cached_category:
                logger.info(
                    f"Using cached classification for '{company_name}': {cached_category.value}"
                )
                return cached_category

            ai_category = await self._ai_classification(company_name)

            self._cache_classification(company_name, ai_category)

            return ai_category

        except Exception as e:
            logger.error(f"Error classifying company {company_name}: {e}")
            return CompanyCategory.OTHER

    async def _ai_classification(self, company_name: str) -> CompanyCategory:
        """Use AI to classify uncertain companies."""
        try:
            # Research the company using web search
            company_info = await self._research_company(company_name)

            # Classify the company based on research results
            category = await self._classify_company_with_research(
                company_name, company_info
            )

            return category

        except Exception as e:
            logger.error(f"AI classification failed for {company_name}: {e}")
            return CompanyCategory.OTHER

    async def _research_company(self, company_name: str) -> str:
        """Research a company using web search and return information about it."""
        try:
            research_prompt = f"""
            Research the company: {company_name}
            
            Please search for information about this company and provide details about:
            - What industry they operate in
            - What products or services they offer
            - Their main business activities
            - Their target market or customers
            - Any recent news or developments
            
            Focus on information that would help classify them in relation to DroneDeploy (construction, real estate, technology, etc.).
            """

            response = await self.client.responses.create(
                model="gpt-5-nano",
                tools=[{"type": "web_search"}],
                input=research_prompt,
            )

            company_info = response.output_text.strip()
            logger.info(f"Researched company '{company_name}' - found information")
            return company_info

        except Exception as e:
            logger.error(f"Research failed for {company_name}: {e}")
            return f"Limited information available for {company_name}"

    async def _classify_company_with_research(
        self, company_name: str, company_info: str
    ) -> CompanyCategory:
        """Classify a company based on research information using structured output."""
        try:
            classification_prompt = f"""
            You are an expert at classifying companies based on their business activities.
            You will be given a company name and research information about them.
            Classify this company into one of these categories in relation to DroneDeploy (https://www.dronedeploy.com/):

            Company: {company_name}
            Research Information: {company_info}
            
            Categories:
            - BUILDER: Construction, engineering, architecture, building services, contractors, project management, BIM, surveying, infrastructure
            - OWNER: Real estate, property management, property developers, asset managers, facility management, landlords, REITs
            - PARTNER: Technology companies, software, SaaS, consulting, services, platforms, APIs, integrations, digital solutions
            - COMPETITOR: Drone companies, aerial mapping, photogrammetry, surveying software, reality capture, 3D scanning, point cloud, lidar
            - OTHER: Everything else that doesn't fit the above categories
            
            Return a JSON object with the following structure:
            {{
                "category": "BUILDER|OWNER|PARTNER|COMPETITOR|OTHER",
                "confidence": 0.95,
                "reasoning": "Brief explanation for the classification"
            }}
            """

            response = await self.client.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at classifying companies. Respond with a valid JSON object containing the category, confidence, and reasoning.",
                    },
                    {"role": "user", "content": classification_prompt},
                ],
                response_format=ClassifierResponse,
            )

            # Parse the JSON response
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)

            # Extract the category from the structured response
            category = result_data.get("category", "OTHER").upper()
            confidence = result_data.get("confidence", 0.5)
            reasoning = result_data.get("reasoning", "No reasoning provided")

            # Map AI response to category
            category_map = {
                "BUILDER": CompanyCategory.BUILDER,
                "OWNER": CompanyCategory.OWNER,
                "PARTNER": CompanyCategory.PARTNER,
                "COMPETITOR": CompanyCategory.COMPETITOR,
                "OTHER": CompanyCategory.OTHER,
            }

            final_category = category_map.get(category, CompanyCategory.OTHER)
            logger.info(
                f"AI classified '{company_name}' as {final_category.value} (confidence: {confidence:.2f})"
            )
            logger.debug(f"Classification reasoning: {reasoning}")

            return final_category

        except Exception as e:
            logger.error(f"Classification failed for {company_name}: {e}")
            return CompanyCategory.OTHER
