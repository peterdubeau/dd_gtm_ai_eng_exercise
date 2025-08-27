"""Email generation service using OpenAI GPT-4."""

import asyncio
import logging
from typing import Optional
import openai
from .models import CompanyCategory, EmailGenerationRequest, EmailGenerationResponse
from .config import Config

# Configure logger
logger = logging.getLogger(__name__)


class EmailGenerator:
    """Service for generating personalized email content using OpenAI."""

    def __init__(self):
        self.client = (
            openai.AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
            if Config.OPENAI_API_KEY
            else None
        )

    async def generate_email(
        self, request: EmailGenerationRequest
    ) -> EmailGenerationResponse:
        """Generate personalized email content for a speaker."""
        try:
            if not self.client:
                raise ValueError("OpenAI client not initialized - API key required")

            # Generate subject and body concurrently
            subject_task = self._generate_subject(request)
            body_task = self._generate_body(request)

            subject, body = await asyncio.gather(subject_task, body_task)

            return EmailGenerationResponse(
                subject=subject, body=body, category=request.company_category
            )

        except Exception as e:
            logger.error(f"Error generating email for {request.speaker_name}: {e}")
            raise

    async def _generate_subject(self, request: EmailGenerationRequest) -> str:
        """Generate an engaging email subject line."""
        prompt = self._create_subject_prompt(request)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at writing engaging email subject lines for B2B outreach. Keep subjects under 60 characters and make them compelling.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=50,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip().strip('"')
        except Exception as e:
            logger.error(f"Error generating subject for {request.speaker_name}: {e}")
            return self._generate_fallback_email(request).subject

    async def _generate_body(self, request: EmailGenerationRequest) -> str:
        """Generate personalized email body content."""
        prompt = self._create_body_prompt(request)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional B2B sales representative for DroneDeploy. Write concise, personalized emails that are relevant to the recipient's role and company type.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating body for {request.speaker_name}: {e}")
            return self._generate_fallback_email(request).body

    def _create_subject_prompt(self, request: EmailGenerationRequest) -> str:
        """Create prompt for subject line generation."""
        category_context = self._get_category_context(request.company_category)
        additional_instructions = f"""
        ADDITIONAL INSTRUCTIONS:
        {request.additional_instructions}
        """
        return f"""
        Generate an engaging email subject line for a conference speaker outreach email.
        
        Speaker: {request.speaker_name}
        Title: {request.speaker_title}
        Company: {request.company_name}
        Company Category: {request.company_category.value}
        
        Context: {category_context}
        
        The email is inviting them to visit DroneDeploy's booth #42 at the conference for a demo and free gift.
        
        Requirements:
        - Keep under 60 characters
        - Be specific to their role/company type
        - Include a compelling hook
        - Professional but friendly tone

        {additional_instructions if request.additional_instructions else ""}
        """

    def _create_body_prompt(self, request: EmailGenerationRequest) -> str:
        """Create prompt for email body generation."""
        category_context = self._get_category_context(request.company_category)
        additional_instructions = f"""
        ADDITIONAL INSTRUCTIONS:
        {request.additional_instructions}
        """
        return f"""
        Write a personalized email body for a conference speaker outreach.
        
        Speaker: {request.speaker_name}
        Title: {request.speaker_title}
        Company: {request.company_name}
        Company Category: {request.company_category.value}
        
        Context: {category_context}
        
        Email Purpose: Invite them to visit DroneDeploy's booth #42 for a demo and free gift.
        
        Requirements:
        - 3-4 sentences maximum
        - DO NOT include a subject line in the body
        - Reference their specific role/title
        - IMPORTANT: Explain DroneDeploy's relevance to their business
        - Professional but conversational tone
        - Include booth number (#42) and mention free gift
        - End with a clear call to action
        - Use the sender name: {Config.SENDER_NAME}
        - Use the sender title: {Config.SENDER_TITLE}
        - Format as a proper email with greeting, body, and signature        

        {additional_instructions if request.additional_instructions else ""}
        """

    def _get_category_context(self, category: CompanyCategory) -> str:
        """Get context information for different company categories."""
        contexts = {
            CompanyCategory.BUILDER: "This company is in construction, engineering, or building services. They build things and would benefit from DroneDeploy's construction progress tracking, site surveying, and project management capabilities.",
            CompanyCategory.OWNER: "This company owns or manages properties/real estate. They get things built for them and would benefit from DroneDeploy's project oversight, progress monitoring, and asset management features.",
            CompanyCategory.PARTNER: "This company could be a potential technology partner or service provider. They might benefit from DroneDeploy's API, integration capabilities, or partnership opportunities.",
            CompanyCategory.COMPETITOR: "This company is in the drone, mapping, or surveying space. They are competitors and should not receive outreach emails.",
            CompanyCategory.OTHER: "This company doesn't clearly fit into the main categories. Focus on general business benefits of DroneDeploy.",
        }

        return contexts.get(category, contexts[CompanyCategory.OTHER])

    def _generate_fallback_email(
        self, request: EmailGenerationRequest
    ) -> EmailGenerationResponse:
        """Generate fallback email content when AI generation fails."""
        if request.company_category == CompanyCategory.COMPETITOR:
            subject = "Conference Connection"
            body = f"Hi {request.speaker_name}, looking forward to connecting at the conference!"
        else:
            subject = "DroneDeploy Demo at Booth #42"
            body = f"""Hi {request.speaker_name},

I'd love to show you how DroneDeploy can help {request.company_name} with aerial mapping and site documentation. Stop by booth #42 for a demo and free gift!

Best regards,
{Config.SENDER_NAME}
{Config.SENDER_TITLE}
DroneDeploy"""

        return EmailGenerationResponse(
            subject=subject, body=body, category=request.company_category
        )
