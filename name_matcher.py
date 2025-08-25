from typing import List, Tuple
from models import UserProfile, IdentityAnchor
from config import Config
from utils import normalize_name, calculate_name_similarity
import os
import json
from openai import OpenAI

class NameMatcher:
    """Handle name matching logic with thresholds for common vs rare names"""
    
    def __init__(self):
        self.config = Config()
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    def analyze_name_match(self, user_profile: UserProfile, anchors: List[IdentityAnchor]) -> Tuple[bool, str, int]:
        """
        Analyze name matches and determine threshold requirements
        
        Returns:
            tuple: (has_name_match, name_analysis, required_anchors)
        """
        name_anchors = [a for a in anchors if a.anchor_type == "name"]
        
        if not name_anchors:
            return False, "No name mentions found in article", 0
        
        # Use AI-powered name matching for better accuracy
        user_names = [user_profile.full_name] + user_profile.aliases
        article_names = [anchor.value for anchor in name_anchors]
        
        ai_match_result = self._ai_name_match(user_names, article_names)
        best_match_score = ai_match_result.get("confidence", 0.0)
        best_match_name = ai_match_result.get("matched_name", "")
        
        # Use AI decision for name matching
        has_name_match = ai_match_result.get("is_match", False) or best_match_score >= 0.7
        
        if not has_name_match:
            reasoning = ai_match_result.get("reasoning", f"No strong name match found (best: {best_match_name}, score: {best_match_score:.2f})")
            return False, f"No name match: {reasoning}", 0
        
        # Determine if name is common or rare
        is_common = self.config.is_common_name(user_profile.full_name)
        required_anchors = self.config.COMMON_NAMES_THRESHOLD if is_common else self.config.RARE_NAMES_THRESHOLD
        
        name_analysis = f"{'common' if is_common else 'rare'} name, needs ≥{required_anchors} anchors"
        
        return True, name_analysis, required_anchors
    
    def check_name_forms(self, user_profile: UserProfile, anchors: List[IdentityAnchor]) -> List[str]:
        """Check various forms of names mentioned in the article"""
        name_anchors = [a for a in anchors if a.anchor_type == "name"]
        user_names = [user_profile.full_name] + user_profile.aliases
        
        matches = []
        for name_anchor in name_anchors:
            for user_name in user_names:
                similarity = calculate_name_similarity(name_anchor.value, user_name)
                if similarity >= 0.7:
                    matches.append(f"'{name_anchor.value}' matches '{user_name}' (score: {similarity:.2f})")
        
        return matches
    
    def _ai_name_match(self, user_names: List[str], article_names: List[str]) -> dict:
        """Use AI to intelligently match names, handling nicknames, cultural variants, etc."""
        try:
            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system", 
                        "content": """You are an expert at name matching for compliance purposes. 
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
                        - "reasoning": string explaining the match logic
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""USER PROFILE NAMES: {user_names}
                        ARTICLE NAMES: {article_names}
                        
                        Could any article name refer to the same person as the user profile?"""
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "is_match": result.get("is_match", False),
                "confidence": result.get("confidence", 0.0),
                "matched_name": result.get("matched_name", ""),
                "reasoning": result.get("reasoning", "")
            }
            
        except Exception as e:
            print(f"AI name matching failed: {e}")
            # Fallback to original logic
            best_match_score = 0.0
            best_match_name = ""
            
            for name_anchor in article_names:
                for user_name in user_names:
                    similarity = calculate_name_similarity(name_anchor, user_name)
                    if similarity > best_match_score:
                        best_match_score = similarity
                        best_match_name = name_anchor
            
            return {
                "is_match": best_match_score >= 0.7,
                "confidence": best_match_score,
                "matched_name": best_match_name,
                "reasoning": f"Fallback string similarity: {best_match_score:.2f}"
            }
