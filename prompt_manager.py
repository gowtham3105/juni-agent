from typing import Dict, Any
import json

class PromptManager:
    """Manages all AI prompts used throughout the compliance system"""
    
    def __init__(self):
        self._prompts = self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get the default prompts for all AI operations"""
        return {
            "anchor_extraction": {
                "name": "Anchor Extraction",
                "description": "Extracts identity anchors (names, employers, cities, etc.) from adverse media articles",
                "system_prompt": "You are a compliance expert specializing in identity verification. Extract identity anchors precisely and create neutral summaries.",
                "user_template": """Article to analyze:
Title: {title}
Date: {date}
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
            },
            
            "name_matching": {
                "name": "Name Matching",
                "description": "Intelligently matches names handling nicknames, cultural variants, and name variations",
                "system_prompt": """You are an expert at name matching for compliance purposes. 
You understand nicknames (Bob=Robert, Jim=James), cultural name variations, 
transliterations, maiden names, professional vs legal names, and name order differences.

Analyze if any names from the article could refer to the same person as in the user profile.
Consider:
- Common nicknames and diminutives
- Cultural name variations (José vs Jose)
- Name order (Li Wei vs Wei Li)  
- Professional vs legal names (Dr. Smith vs John Smith)
- Maiden/married names
- Middle name variations
- Transliteration differences

Return a JSON object with:
- "is_match": boolean
- "confidence": float (0-1)
- "matched_name": string (the article name that matched)
- "reasoning": string explaining the match logic""",
                "user_template": """USER PROFILE NAMES: {user_names}
ARTICLE NAMES: {article_names}

Could any article name refer to the same person as the user profile?"""
            },
            

            
            "batch_anchor_verification": {
                "name": "Batch Anchor Verification",
                "description": "Efficiently verifies multiple anchors against user profile in a single AI call",
                "system_prompt": """You are an expert at identity verification for compliance purposes.

For each anchor, determine if it matches, contradicts, or is neutral regarding the user profile.
Consider contextual relationships, temporal context, and intelligent matching:

- Name variations, nicknames, cultural differences
- Company acquisitions, subsidiaries, name changes 
- Geographic relationships (NYC = New York = Manhattan)
- Career progression (CFO promoted to CEO)
- Temporal context (ages calculated from dates)
- Title hierarchies and equivalents
- Partial matches vs clear conflicts

Return a JSON object with:
- "verifications": array of objects, one per anchor with:
  - "index": anchor index
  - "matches": boolean (true if anchor matches profile)
  - "conflict": boolean (true if anchor contradicts profile) 
  - "rationale": string explaining the reasoning""",
                "user_template": """USER PROFILE: {profile_data}

ANCHORS TO VERIFY: {anchors_data}
ARTICLE DATE: {article_date}

For each anchor, determine if it matches or conflicts with the user profile."""
            }
        }
    
    def get_prompt(self, prompt_key: str) -> Dict[str, Any]:
        """Get a specific prompt configuration"""
        return self._prompts.get(prompt_key, {})
    
    def get_all_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Get all prompt configurations"""
        return self._prompts.copy()
    
    def update_prompt(self, prompt_key: str, system_prompt: str = None, user_template: str = None):
        """Update a specific prompt"""
        if prompt_key not in self._prompts:
            raise ValueError(f"Unknown prompt key: {prompt_key}")
        
        if system_prompt is not None:
            self._prompts[prompt_key]["system_prompt"] = system_prompt
        
        if user_template is not None:
            self._prompts[prompt_key]["user_template"] = user_template
    
    def reset_prompt(self, prompt_key: str):
        """Reset a prompt to default"""
        defaults = self._get_default_prompts()
        if prompt_key in defaults:
            self._prompts[prompt_key] = defaults[prompt_key]
    
    def format_user_prompt(self, prompt_key: str, **kwargs) -> str:
        """Format a user prompt template with provided variables"""
        prompt_config = self.get_prompt(prompt_key)
        if not prompt_config:
            raise ValueError(f"Unknown prompt key: {prompt_key}")
        
        template = prompt_config.get("user_template", "")
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable {e} for prompt {prompt_key}")