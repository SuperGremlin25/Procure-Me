"""
Mistral OCR Client Module

Extracts remedy actions from utility pole reports using Mistral OCR.
Includes mock client for testing without API key.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json


@dataclass
class RemedyAction:
    """A single remedy action from a utility report."""
    pole_id: str
    action_type: str
    action_description: str = ""
    attachment_height: Optional[float] = None
    comm_move: bool = False
    pole_replace: bool = False
    notes: str = ""


@dataclass
class RemedyReport:
    """Parsed remedy report from OCR extraction."""
    utility_company: str
    report_date: str
    total_poles: int
    actions: List[RemedyAction] = field(default_factory=list)
    raw_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockMistralOCRClient:
    """
    Mock Mistral OCR client for testing without API key.
    Returns realistic sample data for development.
    """

    SAMPLE_REPORT = RemedyReport(
        utility_company="AEP",
        report_date="2024-03-13",
        total_poles=3,
        actions=[
            RemedyAction(
                pole_id="AEP-001",
                action_type="COMM_MOVE",
                action_description="Move comm attachments for pole replacement",
                attachment_height=25.5,
                comm_move=True
            ),
            RemedyAction(
                pole_id="AEP-002",
                action_type="POLE_REPLACE",
                action_description="Replace deteriorated pole",
                pole_replace=True
            ),
            RemedyAction(
                pole_id="AEP-003",
                action_type="COMM_MOVE",
                action_description="Relocate fiber attachment",
                attachment_height=22.0,
                comm_move=True
            ),
        ]
    )

    async def extract_remedy_report(self, pdf_bytes: bytes, utility: str) -> RemedyReport:
        """Extract remedy report from PDF bytes."""
        report = self.SAMPLE_REPORT
        report.utility_company = utility
        return report

    async def extract_from_url(self, pdf_url: str, utility: str) -> RemedyReport:
        """Extract remedy report from PDF URL."""
        report = self.SAMPLE_REPORT
        report.utility_company = utility
        return report


class MistralOCRClient:
    """
    Real Mistral OCR client for production use.
    Requires MISTRAL_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is required")

    async def extract_remedy_report(self, pdf_bytes: bytes, utility: str) -> RemedyReport:
        """Extract remedy report using Mistral OCR API."""
        import httpx

        url = "https://api.mistral.ai/v1/ocr"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Upload file first
        async with httpx.AsyncClient() as client:
            # For production, implement proper file upload and OCR processing
            # This is a placeholder for the actual Mistral API integration
            response = await client.post(
                url,
                headers=headers,
                json={"document": {"type": "pdf"}, "include_image_base64": False}
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_ocr_response(data, utility)

    def _parse_ocr_response(self, data: Dict[str, Any], utility: str) -> RemedyReport:
        """Parse Mistral OCR response into RemedyReport."""
        # Parse OCR output - implementation depends on Mistral API response format
        return RemedyReport(
            utility_company=utility,
            report_date="",
            total_poles=0,
            actions=[]
        )
