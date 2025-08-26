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
        self.prompt_manager = None
    
    def set_prompt_manager(self, prompt_manager):
        """Set the prompt manager for dynamic prompts"""
        self.prompt_manager = prompt_manager

    def extract_anchors_and_summary(
            self, hit: MediaHit,
            user_profile: UserProfile) -> tuple[str, List[IdentityAnchor]]:
        """Extract identity anchors and generate brief summary from article"""

        # Prepare the article content
        content = hit.full_text if hit.full_text else hit.snippet
        if not content:
            content = hit.title

        # Build profile summary for template
        profile_summary = f"Name: {user_profile.full_name}, DOB: {user_profile.date_of_birth or 'not provided'}, City: {user_profile.city or 'not provided'}, Employer: {user_profile.employer or 'not provided'}"

        # Get prompts from manager if available, otherwise use defaults
        if self.prompt_manager:
            prompt_config = self.prompt_manager.get_prompt("anchor_extraction")
            system_prompt = prompt_config.get("system_prompt", "")
            user_prompt = self.prompt_manager.format_user_prompt(
                "anchor_extraction",
                title=hit.title,
                date=hit.date,
                content=content,
                profile_summary=profile_summary
            )
        else:
            # Fallback to default prompts
            system_prompt = "You are a compliance expert specializing in identity verification. Extract identity anchors precisely and create neutral summaries."
            user_prompt = f"""Article to analyze:
Title: {hit.title}
Date: {hit.date}
Content: {content}

User profile being checked:
{profile_summary}

Extract all identity anchors from this article and create a neutral summary.
Return JSON with:
- "brief_summary": A neutral 1-2 sentence summary of what happened
- "anchors": Array of identity anchors with:
  - "anchor_type": one of [name, employer, city, dob, age, title, id] 
  - "value": the extracted value
  - "confidence": 0-1 confidence score
  - "source_text": the text where this was found"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3)

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
                    source_text=anchor_data.get("source_text", ""))
                anchors.append(anchor)

            brief_summary = result.get("brief_summary",
                                       "Article content analysis failed")

            return brief_summary, anchors

        except Exception as e:
            print(f"Error extracting anchors: {e}")
            return f"Failed to analyze article: {hit.title}", []
