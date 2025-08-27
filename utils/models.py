"""Pydantic models for data validation."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CompanyCategory(str, Enum):
    """Company categories for classification."""

    BUILDER = "Builder"
    OWNER = "Owner"
    PARTNER = "Partner"
    COMPETITOR = "Competitor"
    OTHER = "Other"


class Speaker(BaseModel):
    """Speaker information model."""

    name: str = Field(..., description="Speaker's full name")
    title: str = Field(..., description="Speaker's job title/role")
    company: str = Field(..., description="Company name")
    company_category: Optional[CompanyCategory] = Field(
        None, description="Classified company category"
    )
    email_subject: Optional[str] = Field(
        None, description="Generated email subject line"
    )
    email_body: Optional[str] = Field(None, description="Generated email body content")


class EmailGenerationRequest(BaseModel):
    """Request model for email generation."""

    speaker_name: str
    speaker_title: str
    company_name: str
    company_category: CompanyCategory
    additional_instructions: Optional[str] = None


class EmailGenerationResponse(BaseModel):
    """Response model for email generation."""

    subject: str
    body: str
    category: CompanyCategory
