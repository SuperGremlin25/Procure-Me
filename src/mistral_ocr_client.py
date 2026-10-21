"""
Mistral OCR Client Module

Extracts remedy actions from utility pole reports using Mistral OCR.
Includes mock client for testing without API key.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json
import re


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
    Mistral OCR client for production use.
    Requires the MISTRAL_API_KEY environment variable (or an ``api_key`` argument).
    """

    OCR_URL = "https://api.mistral.ai/v1/ocr"

    def __init__(self, api_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is required")

    async def _ocr(self, document: Dict[str, Any]) -> Dict[str, Any]:
        import httpx

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": "mistral-ocr-latest", "document": document, "include_image_base64": False}
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(self.OCR_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def extract_remedy_report(self, pdf_bytes: bytes, utility: str) -> RemedyReport:
        """Extract remedy report from PDF bytes using the Mistral OCR API."""
        import base64

        b64 = base64.b64encode(pdf_bytes).decode()
        data = await self._ocr({"type": "document_url", "document_url": f"data:application/pdf;base64,{b64}"})
        return self._parse_ocr_response(data, utility)

    async def extract_from_url(self, pdf_url: str, utility: str) -> RemedyReport:
        """Extract remedy report from a publicly reachable PDF URL."""
        data = await self._ocr({"type": "document_url", "document_url": pdf_url})
        return self._parse_ocr_response(data, utility)

    def _parse_ocr_response(self, data: Dict[str, Any], utility: str) -> RemedyReport:
        """Parse a Mistral OCR response (``pages[].markdown``) into a RemedyReport."""
        markdown = "\n".join(p.get("markdown", "") for p in data.get("pages", []))
        actions = parse_remedy_markdown(markdown)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", markdown)
        return RemedyReport(
            utility_company=utility,
            report_date=date_match.group(1) if date_match else "",
            total_poles=len({a.pole_id for a in actions}),
            actions=actions,
            raw_text=markdown,
            metadata={"pages": len(data.get("pages", []))},
        )


def _height_ft(text: str) -> Optional[float]:
    """25'-6\" -> 25.5, 22' -> 22.0, 22.5 -> 22.5."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:'|ft)?\s*-?\s*(?:(\d+)\s*(?:\"|in))?", text)
    if not m:
        return None
    feet = float(m.group(1))
    return feet + (int(m.group(2)) / 12 if m.group(2) else 0.0)


def parse_remedy_markdown(markdown: str) -> List[RemedyAction]:
    """Read pole remedy rows out of markdown tables (pole id / action / height / notes columns)."""
    actions: List[RemedyAction] = []
    header: List[str] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            header = []
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        lowered = [c.lower() for c in cells]
        if not header and any(k in " ".join(lowered) for k in ("pole", "structure")) and \
                any(k in " ".join(lowered) for k in ("action", "remedy", "make", "work", "description")):
            header = lowered
            continue
        if not header or len(cells) < 2:
            continue

        def col(*keys: str) -> str:
            for i, h in enumerate(header):
                if any(k in h for k in keys) and i < len(cells):
                    return cells[i]
            return ""

        pole_id = col("pole", "structure", "id")
        if not pole_id:
            continue
        desc = col("action", "remedy", "make", "work", "description")
        notes = col("note", "comment", "remark")
        text = f"{desc} {notes}".lower()
        pole_replace = bool(re.search(r"replace|new pole|set pole|change.?out", text))
        comm_move = bool(re.search(r"comm|fiber|attach|lower|raise|move|transfer|relocat", text))
        action_type = "POLE_REPLACE" if pole_replace else ("COMM_MOVE" if comm_move else "OTHER")
        actions.append(RemedyAction(
            pole_id=pole_id, action_type=action_type, action_description=desc,
            attachment_height=_height_ft(col("height", "attach")) if col("height", "attach") else None,
            comm_move=comm_move and not pole_replace, pole_replace=pole_replace, notes=notes))
    return actions
