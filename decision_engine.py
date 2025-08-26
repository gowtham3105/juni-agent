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
        """Verify all anchors against the user profile in a single AI call"""
        
        # Try batch AI verification first for efficiency
        batch_result = self._ai_verify_all_anchors(user_profile, anchors, article_date)
        
        if batch_result and batch_result.get("success", False):
            return batch_result["verifications"]
        
        # Fallback to individual verification if batch AI fails
        verifications = []
        for anchor in anchors:
            verification = self._verify_single_anchor(user_profile, anchor, article_date)
            verifications.append(verification)
        
        return verifications
    
    def _verify_single_anchor(self, user_profile: UserProfile, anchor: IdentityAnchor, article_date: str) -> AnchorVerification:
        """Verify a single anchor against user profile using AI-powered contextual understanding"""
        
        # Try AI-powered verification first
        ai_result = self._ai_verify_anchor(user_profile, anchor, article_date)
        
        if ai_result and ai_result.get("success", False):
            return AnchorVerification(
                anchor=anchor,
                matches=ai_result["matches"],
                conflict=ai_result["conflict"],
                rationale=ai_result["rationale"]
            )
        
        # Fallback to rule-based verification if AI fails
        anchor_type = anchor.anchor_type.lower()
        anchor_value = anchor.value.strip()
        
        matches = False
        conflict = False
        rationale = ""
        
        if anchor_type == "name":
            matches, conflict, rationale = self._verify_name(user_profile, anchor_value)
        elif anchor_type == "employer":
            matches, conflict, rationale = self._verify_employer(user_profile, anchor_value)
        elif anchor_type == "city":
            matches, conflict, rationale = self._verify_city(user_profile, anchor_value)
        elif anchor_type == "dob":
            matches, conflict, rationale = self._verify_dob(user_profile, anchor_value)
        elif anchor_type == "age":
            matches, conflict, rationale = self._verify_age(user_profile, anchor_value, article_date)
        elif anchor_type == "title":
            matches, conflict, rationale = self._verify_title(user_profile, anchor_value)
        elif anchor_type == "id":
            matches, conflict, rationale = self._verify_id(user_profile, anchor_value)
        else:
            rationale = f"Unknown anchor type: {anchor_type}"
        
        return AnchorVerification(
            anchor=anchor,
            matches=matches,
            conflict=conflict,
            rationale=rationale
        )
    
    def _verify_name(self, user_profile: UserProfile, anchor_value: str) -> Tuple[bool, bool, str]:
        """Verify name anchor"""
        user_names = [user_profile.full_name] + user_profile.aliases
        
        for user_name in user_names:
            norm_user = normalize_name(user_name)
            norm_anchor = normalize_name(anchor_value)
            
            if norm_anchor in norm_user or norm_user in norm_anchor:
                return True, False, f"name matches: '{anchor_value}' found in user names"
        
        return False, False, f"name '{anchor_value}' not found in user profile"
    
    def _verify_employer(self, user_profile: UserProfile, anchor_value: str) -> Tuple[bool, bool, str]:
        """Verify employer anchor"""
        if not user_profile.employer:
            return False, False, "employer: not stated in profile"
        
        user_employer = user_profile.employer.lower()
        anchor_employer = anchor_value.lower()
        
        if anchor_employer in user_employer or user_employer in anchor_employer:
            return True, False, f"employer: matches ({anchor_value})"
        
        return False, True, f"employer: conflict (profile: {user_profile.employer} vs article: {anchor_value})"
    
    def _verify_city(self, user_profile: UserProfile, anchor_value: str) -> Tuple[bool, bool, str]:
        """Verify city anchor"""
        if not user_profile.city:
            return False, False, "city: not stated in profile"
        
        user_city = user_profile.city.lower()
        anchor_city = anchor_value.lower()
        
        if anchor_city in user_city or user_city in anchor_city:
            return True, False, f"city: matches ({anchor_value})"
        
        return False, True, f"city: conflict (profile: {user_profile.city} vs article: {anchor_value})"
    
    def _verify_dob(self, user_profile: UserProfile, anchor_value: str) -> Tuple[bool, bool, str]:
        """Verify date of birth anchor"""
        if not user_profile.date_of_birth:
            return False, False, "dob: not stated in profile"
        
        user_dob = parse_date(user_profile.date_of_birth)
        anchor_dob = parse_date(anchor_value)
        
        if not anchor_dob:
            return False, False, f"dob: could not parse '{anchor_value}'"
        
        if user_dob == anchor_dob:
            return True, False, f"dob: matches ({anchor_value})"
        
        return False, True, f"dob: conflict (profile: {user_profile.date_of_birth} vs article: {anchor_value})"
    
    def _verify_age(self, user_profile: UserProfile, anchor_value: str, article_date: str) -> Tuple[bool, bool, str]:
        """Verify age anchor"""
        if not user_profile.date_of_birth:
            return False, False, "age: cannot verify, no DOB in profile"
        
        try:
            article_age = int(anchor_value)
        except ValueError:
            return False, False, f"age: could not parse '{anchor_value}'"
        
        # Calculate expected age at time of article
        expected_age = calculate_age(user_profile.date_of_birth, article_date)
        if expected_age is None:
            return False, False, "age: could not calculate expected age"
        
        # Allow 1 year tolerance
        if abs(article_age - expected_age) <= 1:
            return True, False, f"age: matches (article: {article_age}, expected: {expected_age})"
        
        return False, True, f"age: conflict (article: {article_age}, expected: {expected_age})"
    
    def _verify_title(self, user_profile: UserProfile, anchor_value: str) -> Tuple[bool, bool, str]:
        """Verify title/position anchor"""
        # For now, we don't have title information in user profile
        return False, False, f"title: not verifiable ('{anchor_value}' mentioned)"
    
    def _verify_id(self, user_profile: UserProfile, anchor_value: str) -> Tuple[bool, bool, str]:
        """Verify ID anchor"""
        if not user_profile.id_data:
            return False, False, f"id: not verifiable ('{anchor_value}' mentioned)"
        
        for id_type, id_value in user_profile.id_data.items():
            if anchor_value in id_value or id_value in anchor_value:
                return True, False, f"id: matches {id_type}"
        
        return False, False, f"id: no match found for '{anchor_value}'"
    
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
    
    def _ai_verify_anchor(self, user_profile: UserProfile, anchor: IdentityAnchor, article_date: str) -> dict:
        """Use AI to contextually verify if an anchor matches the user profile"""
        try:
            # Prepare user profile data
            profile_data = {
                "name": user_profile.full_name,
                "aliases": user_profile.aliases,
                "dob": user_profile.date_of_birth,
                "city": user_profile.city,
                "employer": user_profile.employer
            }
            
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at identity verification for compliance purposes.
                        You understand contextual relationships and can make intelligent judgments about whether 
                        extracted information matches a user profile.
                        
                        Consider:
                        - Name variations, nicknames, cultural differences
                        - Company acquisitions, subsidiaries, name changes 
                        - Geographic relationships (NYC = New York = Manhattan)
                        - Career progression (CFO promoted to CEO)
                        - Temporal context (ages calculated from dates)
                        - Title hierarchies and equivalents
                        - Partial matches vs clear conflicts
                        
                        Return a JSON object with:
                        - "matches": boolean (true if anchor matches profile)
                        - "conflict": boolean (true if anchor contradicts profile) 
                        - "rationale": string explaining the reasoning
                        - "confidence": float (0-1) indicating certainty
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""USER PROFILE: {json.dumps(profile_data, default=str)}
                        
                        ANCHOR TO VERIFY:
                        - Type: {anchor.anchor_type}
                        - Value: {anchor.value}
                        - Context: "{anchor.source_text}"
                        - Article Date: {article_date}
                        
                        Does this anchor match, contradict, or is neutral regarding the user profile?
                        Consider temporal context and contextual relationships."""
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "success": True,
                "matches": result.get("matches", False),
                "conflict": result.get("conflict", False),
                "rationale": f"AI: {result.get('rationale', 'No explanation provided')} (confidence: {result.get('confidence', 0.0):.2f})",
                "confidence": result.get("confidence", 0.0)
            }
            
        except Exception as e:
            print(f"AI anchor verification failed: {e}")
            return {"success": False}
    
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
            
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at identity verification for compliance purposes.
                        
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
                          - "rationale": string explaining the reasoning
                          - "confidence": float (0-1) indicating certainty
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""USER PROFILE: {json.dumps(profile_data, default=str)}
                        
                        ANCHORS TO VERIFY: {json.dumps(anchors_data, default=str)}
                        
                        ARTICLE DATE: {article_date}
                        
                        For each anchor, does it match, contradict, or is neutral regarding the user profile?
                        Consider temporal context and contextual relationships."""
                    }
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
