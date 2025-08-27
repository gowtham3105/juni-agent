import time
from typing import List, Tuple

import config
from models import UserProfile, IdentityAnchor
from config import Config
from prompt_manager import PromptManager
from utils import normalize_name, calculate_name_similarity
import os
import json
from openai import OpenAI

class NameMatcher:
    """Handle name matching logic with thresholds for common vs rare names"""
    
    def __init__(self):
        self.config = Config()
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.prompt_manager = PromptManager()
    
    def set_prompt_manager(self, prompt_manager):
        """Set the prompt manager for dynamic prompts"""
        self.prompt_manager = prompt_manager
    
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
            # Get prompts from manager if available, otherwise use defaults
            prompt_config = self.prompt_manager.get_prompt("name_matching")
            system_prompt = prompt_config.get("system_prompt", "")
            user_prompt = self.prompt_manager.format_user_prompt(
                "name_matching",
                user_names=user_names,
                article_names=article_names
            )


            # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
            # do not change this unless explicitly requested by the user
            st = time.time()
            response = self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            print(f"Name matching took {time.time() - st:.2f}s")
            
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
