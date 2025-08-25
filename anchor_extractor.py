import json
import os
from typing import List, Dict, Any
from openai import OpenAI
from models import MediaHit, IdentityAnchor, UserProfile
from config import Config

class AnchorExtractor:
    """Extract identity anchors from adverse media articles using OpenAI"""
    
    def __init__(self):
        # Using GPT-4 mini as requested by user
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
    
    def extract_anchors_and_summary(self, hit: MediaHit, user_profile: UserProfile) -> tuple[str, List[IdentityAnchor]]:
        """Extract identity anchors and generate brief summary from article"""
        
        # Prepare the article content
        content = hit.full_text if hit.full_text else hit.snippet
        if not content:
            content = hit.title
        
        prompt = f"""
You are analyzing an adverse media article for compliance purposes. Your task is to:
1. Create a 1-line neutral paraphrase of what the article alleges/reports
2. Extract ALL identity anchors mentioned in the article

Subject profile for reference:
- Name: {user_profile.full_name}
- DOB: {user_profile.date_of_birth or 'not provided'}
- City: {user_profile.city or 'not provided'}
- Employer: {user_profile.employer or 'not provided'}

Article to analyze:
Title: {hit.title}
Content: {content}
Date: {hit.date}
Source: {hit.source}

Extract these types of identity anchors if present:
- names (full names, first names, last names, nicknames)
- employer (company names, organizations, job titles)
- city (cities, locations, addresses)
- dob (dates of birth, birth years)
- age (explicit age mentions)
- titles (professional titles, positions)
- ids (passport numbers, ID numbers, license numbers)

For each anchor found, provide:
- anchor_type: one of [name, employer, city, dob, age, title, id]
- value: the exact value found
- confidence: 0.0-1.0 based on how clearly stated it is
- source_text: the exact phrase where you found it

Return your response in JSON format:
{{
    "brief_summary": "one-line neutral paraphrase of the article's main allegation",
    "anchors": [
        {{
            "anchor_type": "employer",
            "value": "ABC Corporation",
            "confidence": 0.9,
            "source_text": "worked at ABC Corporation as CFO"
        }}
    ]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a compliance expert specializing in identity verification. Extract identity anchors precisely and create neutral summaries."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            content: str | None = response.choices[0].message.content
            if content is None:
                return "Failed to get response from AI", []
            result = json.loads(content)
            
            # Parse anchors
            anchors = []
            for anchor_data in result.get("anchors", []):
                anchor = IdentityAnchor(
                    anchor_type=anchor_data.get("anchor_type", "unknown"),
                    value=anchor_data.get("value", ""),
                    confidence=float(anchor_data.get("confidence", 0.0)),
                    source_text=anchor_data.get("source_text", "")
                )
                anchors.append(anchor)
            
            brief_summary = result.get("brief_summary", "Article content analysis failed")
            
            return brief_summary, anchors
            
        except Exception as e:
            print(f"Error extracting anchors: {e}")
            return f"Failed to analyze article: {hit.title}", []
    
