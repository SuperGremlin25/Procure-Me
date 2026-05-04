"""
FastAPI Backend for GIS Processing

This runs on Render/Railway and handles the heavy lifting:
- Spatial joins between remedy data and shapefiles
- Bid generation from joined data
- KMZ export for visualization
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import geopandas as gpd
import tempfile
import os
from pathlib import Path
import httpx
import socket
import ipaddress
from urllib.parse import urlparse

# Import our modules
from src.gis_spatial_join import GISRemedyIntegrator
from src.remedy_action_mapper import RemedyActionMapper
from src.mistral_ocr_client import RemedyReport

app = FastAPI(title="GIS Remedy Processing API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class SpatialJoinRequest(BaseModel):
    jobId: str
    remedyData: Dict[str, Any]
    shapefileUrl: str
    poleIdField: Optional[str] = 'pole_id'
    matchMethod: Optional[str] = 'pole_id'


class BidGenerationRequest(BaseModel):
    jobId: str
    marginRate: Optional[float] = 0.10
    taxRate: Optional[float] = 0.0825


# Authentication
async def verify_token(authorization: str = Header(None)):
    """Verify API token from Cloudflare Worker."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = authorization.replace("Bearer ", "")
    expected_token = os.getenv("BACKEND_API_KEY")
    
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "GIS Remedy Processing API",
        "version": "1.0.0"
    }


@app.post("/api/spatial-join")
async def spatial_join(
    request: SpatialJoinRequest,
    token: str = Depends(verify_token)
):
    """
    Perform spatial join between remedy data and shapefile.
    
    This is the core function that creates the "aware" shapefile.
    """
    try:
        # Initialize integrator
        integrator = GISRemedyIntegrator()
        
        # Download shapefile
        shapefile_path = await download_file(request.shapefileUrl)
        
        # Load design file
        design_gdf = integrator.load_design_file(
            shapefile_path,
            pole_id_field=request.poleIdField
        )
        
        # Load remedy report
        remedy_report = integrator.load_remedy_report(request.remedyData)
        
        # Perform spatial join
        joined_gdf = integrator.perform_spatial_join(
            match_method=request.matchMethod
        )
        
        # Get summary statistics
        stats = integrator.get_summary_statistics()
        
        # Export to KMZ
        kmz_path = os.path.join(tempfile.gettempdir(), f"{request.jobId}_remedy_map.kmz")
        integrator.export_to_kmz(kmz_path, include_normal=False)
        
        # Upload KMZ to storage (would use R2 in production)
        kmz_url = await upload_to_storage(kmz_path, request.jobId)
        
        return {
            "success": True,
            "jobId": request.jobId,
            "statistics": stats,
            "kmzUrl": kmz_url,
            "totalPoles": len(design_gdf),
            "polesWithRemediation": stats['poles_with_remediation'],
            "remediationPercentage": stats['remediation_percentage']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-bid")
async def generate_bid(
    request: BidGenerationRequest,
    token: str = Depends(verify_token)
):
    """
    Generate bid from spatially joined data.
    
    This takes the aware shapefile and produces the dollar amounts.
    """
    try:
        # Load joined GeoDataFrame from storage
        joined_gdf = await load_joined_gdf(request.jobId)
        
        if joined_gdf is None:
            raise HTTPException(status_code=404, detail="Spatial join data not found")
        
        # Initialize mapper
        mapper = RemedyActionMapper()
        
        # Generate bid
        bid = mapper.generate_bid_from_joined_gdf(
            joined_gdf,
            margin_rate=request.marginRate,
            tax_rate=request.taxRate
        )
        
        # Generate timeline estimate
        timeline = mapper.estimate_project_timeline(joined_gdf)
        
        # Combine results
        result = {
            "success": True,
            "jobId": request.jobId,
            "bid": bid,
            "timeline": timeline
        }
        
        # Store bid result
        await store_bid_result(request.jobId, result)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-bid/{jobId}")
async def download_bid(jobId: str):
    """Download bid as Excel file."""
    try:
        # Load bid data
        bid_data = await load_bid_result(jobId)
        
        if not bid_data:
            raise HTTPException(status_code=404, detail="Bid not found")
        
        # Generate Excel file
        excel_path = await generate_bid_excel(bid_data, jobId)
        
        from fastapi.responses import FileResponse
        return FileResponse(
            excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"bid_{jobId}.xlsx"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-kmz/{jobId}")
async def download_kmz(jobId: str):
    """Download KMZ file."""
    try:
        kmz_path = os.path.join(tempfile.gettempdir(), f"{jobId}_remedy_map.kmz")
        
        if not os.path.exists(kmz_path):
            raise HTTPException(status_code=404, detail="KMZ file not found")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            kmz_path,
            media_type="application/vnd.google-earth.kmz",
            filename=f"remedy_map_{jobId}.kmz"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
ALLOWED_SHAPEFILE_HOSTS = {
    # Add trusted storage hosts here, for example:
    # "example-bucket.s3.amazonaws.com",
}


def _is_public_ip(ip_str: str) -> bool:
    ip_obj = ipaddress.ip_address(ip_str)
    return not (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def _validate_outbound_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Invalid URL scheme")

    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL host")

    hostname = parsed.hostname.lower()

    if ALLOWED_SHAPEFILE_HOSTS and hostname not in ALLOWED_SHAPEFILE_HOSTS:
        raise HTTPException(status_code=400, detail="Host not allowed")

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Unable to resolve host")

    resolved_ips = {item[4][0] for item in addrinfo}
    if not resolved_ips:
        raise HTTPException(status_code=400, detail="Unable to resolve host")

    for ip_str in resolved_ips:
        if not _is_public_ip(ip_str):
            raise HTTPException(status_code=400, detail="URL resolves to a non-public address")


async def download_file(url: str) -> str:
    """Download file from URL to temp location."""
    _validate_outbound_url(url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        
        # Save to temp file
        suffix = Path(url).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(response.content)
            return tmp.name


async def upload_to_storage(file_path: str, job_id: str) -> str:
    """Upload file to R2 storage (placeholder)."""
    # In production, this would upload to Cloudflare R2
    # For now, return a placeholder URL
    return f"https://storage.example.com/kmz/{job_id}_remedy_map.kmz"


async def load_joined_gdf(job_id: str) -> Optional[gpd.GeoDataFrame]:
    """Load joined GeoDataFrame from storage."""
    # In production, this would load from R2 or database
    # For now, return None (would need to cache in Redis or similar)
    cache_path = os.path.join(tempfile.gettempdir(), f"{job_id}_joined.geojson")
    
    if os.path.exists(cache_path):
        return gpd.read_file(cache_path)
    
    return None


async def store_bid_result(job_id: str, result: Dict[str, Any]) -> None:
    """Store bid result for later retrieval."""
    import json
    cache_path = os.path.join(tempfile.gettempdir(), f"{job_id}_bid.json")
    
    with open(cache_path, 'w') as f:
        json.dump(result, f)


async def load_bid_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Load bid result from storage."""
    import json
    cache_path = os.path.join(tempfile.gettempdir(), f"{job_id}_bid.json")
    
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)
    
    return None


async def generate_bid_excel(bid_data: Dict[str, Any], job_id: str) -> str:
    """Generate Excel file from bid data."""
    import pandas as pd
    from io import BytesIO
    
    output_path = os.path.join(tempfile.gettempdir(), f"{job_id}_bid.xlsx")
    
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        # Summary sheet
        summary_df = pd.DataFrame([
            {'Item': 'Materials', 'Amount': bid_data['bid']['cost_breakdown']['materials_subtotal']},
            {'Item': 'Labor', 'Amount': bid_data['bid']['cost_breakdown']['labor_subtotal']},
            {'Item': 'Margin', 'Amount': bid_data['bid']['cost_breakdown']['margin']},
            {'Item': 'Tax', 'Amount': bid_data['bid']['cost_breakdown']['tax']},
            {'Item': 'Total', 'Amount': bid_data['bid']['cost_breakdown']['total']}
        ])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Detailed items
        items_df = pd.DataFrame(bid_data['bid']['detailed_items'])
        items_df.to_excel(writer, sheet_name='Detailed Items', index=False)
        
        # Timeline
        timeline_df = pd.DataFrame([bid_data['timeline']])
        timeline_df.to_excel(writer, sheet_name='Timeline', index=False)
    
    return output_path


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
