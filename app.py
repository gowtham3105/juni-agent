#!/usr/bin/env python3
"""
FastAPI web server for AI Compliance Agent
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from models import UserProfile, MediaHit, ComplianceResult, HitType
from compliance_agent import ComplianceAgent

app = FastAPI(title="AI Compliance Agent", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize compliance agent
agent = ComplianceAgent()

class ComplianceRequest(BaseModel):
    """Request model for compliance check"""
    user_profile: UserProfile
    media_hits: List[MediaHit]

class ComplianceResponse(BaseModel):
    """Response model for compliance check results"""
    success: bool
    message: str
    result: Optional[ComplianceResult] = None
    processing_time_seconds: Optional[float] = None

@app.get("/")
async def root():
    """Serve the web interface"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/compliance/check", response_model=ComplianceResponse)
async def process_compliance_check(request: ComplianceRequest):
    """Process a complete compliance check"""
    try:
        start_time = datetime.now()
        
        # Process compliance check using the existing agent
        result = agent.process_compliance_check(
            request.user_profile, 
            request.media_hits
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ComplianceResponse(
            success=True,
            message="Compliance check completed successfully",
            result=result,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        print(f"Error processing compliance check: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing compliance check: {str(e)}"
        )

@app.get("/compliance/sample")
async def get_sample_data():
    """Get sample data for testing"""
    user_profile = UserProfile(
        full_name="John Michael Smith",
        date_of_birth="1985-03-15",
        city="New York",
        employer="ABC Financial Corp",
        id_data={"passport": "P12345678", "ssn": "XXX-XX-1234"},
        aliases=["John Smith", "J.M. Smith"]
    )
    
    media_hits = [
        MediaHit(
            title="ABC Financial Corp CFO Charged with Securities Fraud",
            snippet="John Smith, 39, Chief Financial Officer at ABC Financial Corp in New York, was charged yesterday with securities fraud by federal prosecutors.",
            full_text="Federal prosecutors announced charges against John Michael Smith, age 39, the Chief Financial Officer of ABC Financial Corp based in New York City. Smith is accused of securities fraud in connection with the alleged manipulation of quarterly earnings reports submitted to the SEC between 2020 and 2023. According to court documents filed in the Southern District of New York, Smith allegedly worked with other executives to inflate revenue figures and hide mounting losses. 'This case represents a serious breach of fiduciary duty,' said prosecutor Jane Wilson. Smith's attorney declined to comment. ABC Financial Corp is a mid-sized investment firm with offices in Manhattan. The company's stock has fallen 40% since the charges were announced. Smith joined ABC Financial in 2018 as CFO after working at rival firm XYZ Capital. Court records show Smith was born March 15, 1985 and resides in Manhattan.",
            date="2024-11-15",
            source="Financial Times",
            url="https://ft.com/content/abc-cfo-charged"
        ),
        MediaHit(
            title="Investment Firm Executive Denies Fraud Allegations", 
            snippet="John Smith of ABC Financial Corp denies all allegations of securities fraud. His lawyer says the charges are unfounded and they will fight them vigorously in court.",
            date="2024-11-16",
            source="Reuters",
            url="https://reuters.com/business/abc-executive-denies"
        ),
        MediaHit(
            title="Local Man Arrested for DUI",
            snippet="John Smith, 45, of Boston was arrested for driving under the influence on Highway 95. Smith works as a mechanic at Joe's Auto Repair.",
            date="2024-11-10",
            source="Boston Herald",
            url="https://bostonherald.com/local/dui-arrest"
        )
    ]
    
    return {
        "user_profile": user_profile.model_dump(),
        "media_hits": [hit.model_dump() for hit in media_hits]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)