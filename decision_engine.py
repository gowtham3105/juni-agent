from typing import List, Tuple
from datetime import datetime, date
from models import UserProfile, IdentityAnchor, AnchorVerification, LinkageDecision
from utils import parse_date, calculate_age, extract_age_from_text, normalize_name
from config import Config
import os
import json
from openai import OpenAI

class DecisionEngine:
    """Core decision logic for linkage determination"""
    
    def __init__(self):
        self.config = Config()
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.prompt_manager = None
    
    def set_prompt_manager(self, prompt_manager):
        """Set the prompt manager for dynamic prompts"""
        self.prompt_manager = prompt_manager
    
    def verify_anchors(self, user_profile: UserProfile, anchors: List[IdentityAnchor], article_date: str) -> List[AnchorVerification]:
        """Verify all anchors against the user profile using batch AI processing"""
        
        # Use batch AI verification for all anchor processing
        batch_result = self._ai_verify_all_anchors(user_profile, anchors, article_date)
        
        if batch_result and batch_result.get("success", False):
            return batch_result["verifications"]
        
        # If batch processing fails, return empty verifications with error message
        print(f"Warning: Batch anchor verification failed for {len(anchors)} anchors")
        return []
    

    
    def detect_contradictions(self, verifications: List[AnchorVerification]) -> List[str]:
        """Detect hard conflicts in anchor verifications"""
        contradictions = []
        
        for verification in verifications:
            if verification.conflict:
                contradictions.append(verification.rationale)
        
        return contradictions
    
    def make_linkage_decision(self, user_profile: UserProfile, anchors: List[IdentityAnchor], 
                            verifications: List[AnchorVerification], contradictions: List[str],
                            required_anchors: int, has_name_match: bool) -> Tuple[LinkageDecision, str]:
        """Make the final linkage decision based on all evidence"""
        
        if not has_name_match:
            return LinkageDecision.NO, "Linkage: no - no name match found"
        
        # Count successful anchor matches (excluding name anchors)
        non_name_matches = [v for v in verifications if v.matches and v.anchor.anchor_type != "name"]
        match_count = len(non_name_matches)
        
        # Check for hard conflicts
        if contradictions:
            if match_count >= required_anchors + 1:  # Multiple stronger anchors can overrule
                decision = LinkageDecision.MAYBE
                rationale = f"Linkage: maybe - {match_count} anchors match but conflicts exist: {'; '.join(contradictions[:2])}"
            else:
                decision = LinkageDecision.NO
                rationale = f"Linkage: no - conflicts detected: {'; '.join(contradictions[:2])}"
            return decision, rationale
        
        # Apply anchor threshold logic
        if match_count >= required_anchors:
            anchor_list = [f"{v.anchor.anchor_type}:{v.anchor.value}" for v in non_name_matches[:3]]
            decision = LinkageDecision.YES
            rationale = f"Linkage: yes - name match + {match_count} anchors ({', '.join(anchor_list)})"
        elif match_count > 0:
            anchor_list = [f"{v.anchor.anchor_type}:{v.anchor.value}" for v in non_name_matches]
            decision = LinkageDecision.MAYBE  
            rationale = f"Linkage: maybe - name match + {match_count} anchors ({', '.join(anchor_list)}) below threshold"
        else:
            decision = LinkageDecision.NO
            rationale = "Linkage: no - name match only, no supporting anchors"
        
        return decision, rationale
    

    
    def _ai_verify_all_anchors(self, user_profile: UserProfile, anchors: List[IdentityAnchor], article_date: str) -> dict:
        """Use AI to verify all anchors in a single efficient call"""
        try:
            # Prepare user profile data
            profile_data = {
                "name": user_profile.full_name,
                "aliases": user_profile.aliases,
                "dob": user_profile.date_of_birth,
                "city": user_profile.city,
                "employer": user_profile.employer
            }
            
            # Prepare anchors data
            anchors_data = []
            for i, anchor in enumerate(anchors):
                anchors_data.append({
                    "index": i,
                    "type": anchor.anchor_type,
                    "value": anchor.value,
                    "context": anchor.source_text,
                    "confidence": anchor.confidence
                })
            
            # Get prompts from manager if available, otherwise use defaults
            if self.prompt_manager:
                prompt_config = self.prompt_manager.get_prompt("batch_anchor_verification")
                system_prompt = prompt_config.get("system_prompt", "")
                user_prompt = self.prompt_manager.format_user_prompt(
                    "batch_anchor_verification",
                    profile_data=json.dumps(profile_data, default=str),
                    anchors_data=json.dumps(anchors_data, default=str),
                    article_date=article_date
                )
            else:
                # Fallback to default prompts if prompt manager not available
                system_prompt = """You are an expert at identity verification for compliance purposes.

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
  - "rationale": string explaining the reasoning"""

                user_prompt = f"""USER PROFILE: {json.dumps(profile_data, default=str)}

ANCHORS TO VERIFY: {json.dumps(anchors_data, default=str)}
ARTICLE DATE: {article_date}

For each anchor, determine if it matches or conflicts with the user profile."""

            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            verifications = []
            
            for verification_data in result.get("verifications", []):
                anchor_index = verification_data.get("index", 0)
                if anchor_index < len(anchors):
                    anchor = anchors[anchor_index]
                    verification = AnchorVerification(
                        anchor=anchor,
                        matches=verification_data.get("matches", False),
                        conflict=verification_data.get("conflict", False),
                        rationale=f"AI: {verification_data.get('rationale', 'No explanation')} (confidence: {verification_data.get('confidence', 0.0):.2f})"
                    )
                    verifications.append(verification)
            
            return {"success": True, "verifications": verifications}
            
        except Exception as e:
            print(f"AI batch anchor verification failed: {e}")
            return {"success": False}
