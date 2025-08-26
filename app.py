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
import requests
from bs4 import BeautifulSoup
import re

from models import UserProfile, MediaHit, ComplianceResult, HitType
from compliance_agent import ComplianceAgent
from prompt_manager import PromptManager

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

# Initialize compliance agent and prompt manager
prompt_manager = PromptManager()
agent = ComplianceAgent()
agent.set_prompt_manager(prompt_manager)

# Progress tracking for real-time updates
progress_logs = []

def progress_callback(message: str):
    """Callback to track progress logs"""
    global progress_logs
    progress_logs.append(message)
    print(f"[PROGRESS] {message}")


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

        # Reset progress logs and create agent with callback
        global progress_logs
        progress_logs = []
        
        # Create agent instance with progress callback
        progress_agent = ComplianceAgent(progress_callback=progress_callback)
        
        # Process compliance check using the progress agent
        result = progress_agent.process_compliance_check(request.user_profile,
                                                request.media_hits)

        processing_time = (datetime.now() - start_time).total_seconds()

        return ComplianceResponse(
            success=True,
            message="Compliance check completed successfully",
            result=result,
            processing_time_seconds=processing_time)

    except Exception as e:
        print(f"Error processing compliance check: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error processing compliance check: {str(e)}")

@app.get("/compliance/progress")
async def get_progress():
    """Get current progress logs"""
    global progress_logs
    return {"logs": progress_logs}


@app.get("/compliance/sample")
async def get_sample_data():
    """Get sample data for testing"""
    user_profile = UserProfile(full_name="John Michael Smith",
                               date_of_birth="1985-03-15",
                               city="New York",
                               employer="ABC Financial Corp",
                               id_data={
                                   "passport": "P12345678",
                                   "ssn": "XXX-XX-1234"
                               },
                               aliases=["John Smith", "J.M. Smith"])

    media_hits = [
        MediaHit(
            title="ABC Financial Corp CFO Charged with Securities Fraud",
            snippet=
            "John Smith, 39, Chief Financial Officer at ABC Financial Corp in New York, was charged yesterday with securities fraud by federal prosecutors.",
            full_text=
            "Federal prosecutors announced charges against John Michael Smith, age 39, the Chief Financial Officer of ABC Financial Corp based in New York City. Smith is accused of securities fraud in connection with the alleged manipulation of quarterly earnings reports submitted to the SEC between 2020 and 2023. According to court documents filed in the Southern District of New York, Smith allegedly worked with other executives to inflate revenue figures and hide mounting losses. 'This case represents a serious breach of fiduciary duty,' said prosecutor Jane Wilson. Smith's attorney declined to comment. ABC Financial Corp is a mid-sized investment firm with offices in Manhattan. The company's stock has fallen 40% since the charges were announced. Smith joined ABC Financial in 2018 as CFO after working at rival firm XYZ Capital. Court records show Smith was born March 15, 1985 and resides in Manhattan.",
            date="2024-11-15",
            source="Financial Times",
            url="https://ft.com/content/abc-cfo-charged"),
        MediaHit(
            title="Investment Firm Executive Denies Fraud Allegations",
            snippet=
            "John Smith of ABC Financial Corp denies all allegations of securities fraud. His lawyer says the charges are unfounded and they will fight them vigorously in court.",
            date="2024-11-16",
            source="Reuters",
            url="https://reuters.com/business/abc-executive-denies"),
        MediaHit(
            title="Local Man Arrested for DUI",
            snippet=
            "John Smith, 45, of Boston was arrested for driving under the influence on Highway 95. Smith works as a mechanic at Joe's Auto Repair.",
            date="2024-11-10",
            source="Boston Herald",
            url="https://bostonherald.com/local/dui-arrest")
    ]

    return {
        "user_profile": user_profile.model_dump(),
        "media_hits": [hit.model_dump() for hit in media_hits]
    }


@app.post("/compliance/fetch-url")
async def fetch_article_from_url(request: Dict[str, str]):
    """Fetch article content from URL"""
    try:
        url = request.get("url", "").strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()

        # Extract main content
        content = ""

        # Try common article selectors
        article_selectors = [
            'article', '.article-content', '.post-content', '.entry-content',
            '.content', 'main', '[role="main"]'
        ]

        for selector in article_selectors:
            article_element = soup.select_one(selector)
            if article_element:
                # Remove script, style, nav, header, footer elements
                for element in article_element.find_all(
                    ['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()
                content = article_element.get_text(separator=' ', strip=True)
                break

        # Fallback to body if no article content found
        if not content:
            body = soup.find('body')
            if body:
                for element in body.find_all(
                    ['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()
                content = body.get_text(separator=' ', strip=True)

        # Clean up content
        content = re.sub(r'\s+', ' ', content).strip()

        # Limit content length
        if len(content) > 5000:
            content = content[:5000] + "..."

        # Extract source from URL
        source = url.split('/')[2] if '/' in url else url

        return {
            "success": True,
            "title": title,
            "content": content,
            "source": source,
            "url": url
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=400,
                            detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error processing URL: {str(e)}")


# Prompt Management Endpoints
class PromptUpdateRequest(BaseModel):
    """Request model for updating prompts"""
    system_prompt: Optional[str] = None
    user_template: Optional[str] = None


@app.get("/prompts")
async def get_all_prompts():
    """Get all configured prompts"""
    try:
        return {"success": True, "prompts": prompt_manager.get_all_prompts()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prompts: {str(e)}")


@app.get("/prompts/{prompt_key}")
async def get_prompt(prompt_key: str):
    """Get a specific prompt configuration"""
    try:
        prompt_config = prompt_manager.get_prompt(prompt_key)
        if not prompt_config:
            raise HTTPException(status_code=404, detail=f"Prompt '{prompt_key}' not found")
        return {"success": True, "prompt": prompt_config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prompt: {str(e)}")


@app.put("/prompts/{prompt_key}")
async def update_prompt(prompt_key: str, request: PromptUpdateRequest):
    """Update a specific prompt configuration"""
    try:
        prompt_manager.update_prompt(
            prompt_key=prompt_key,
            system_prompt=request.system_prompt,
            user_template=request.user_template
        )
        
        # Update all agent components to use the new prompt manager
        agent.set_prompt_manager(prompt_manager)
        
        return {"success": True, "message": f"Prompt '{prompt_key}' updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating prompt: {str(e)}")


@app.post("/prompts/{prompt_key}/reset")
async def reset_prompt(prompt_key: str):
    """Reset a prompt to its default configuration"""
    try:
        prompt_manager.reset_prompt(prompt_key)
        
        # Update all agent components to use the new prompt manager
        agent.set_prompt_manager(prompt_manager)
        
        return {"success": True, "message": f"Prompt '{prompt_key}' reset to default"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting prompt: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
