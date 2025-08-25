from typing import List, Tuple
from models import UserProfile, IdentityAnchor
from config import Config
from utils import normalize_name, calculate_name_similarity

class NameMatcher:
    """Handle name matching logic with thresholds for common vs rare names"""
    
    def __init__(self):
        self.config = Config()
    
    def analyze_name_match(self, user_profile: UserProfile, anchors: List[IdentityAnchor]) -> Tuple[bool, str, int]:
        """
        Analyze name matches and determine threshold requirements
        
        Returns:
            tuple: (has_name_match, name_analysis, required_anchors)
        """
        name_anchors = [a for a in anchors if a.anchor_type == "name"]
        
        if not name_anchors:
            return False, "No name mentions found in article", 0
        
        # Check if any name anchor matches the user profile
        user_names = [user_profile.full_name] + user_profile.aliases
        best_match_score = 0.0
        best_match_name = ""
        
        for name_anchor in name_anchors:
            for user_name in user_names:
                similarity = calculate_name_similarity(name_anchor.value, user_name)
                if similarity > best_match_score:
                    best_match_score = similarity
                    best_match_name = name_anchor.value
        
        # Determine if we have a name match (threshold: 0.7)
        has_name_match = best_match_score >= 0.7
        
        if not has_name_match:
            return False, f"No strong name match found (best: {best_match_name}, score: {best_match_score:.2f})", 0
        
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
