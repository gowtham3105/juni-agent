from typing import List, Tuple
from datetime import datetime, date
from models import UserProfile, IdentityAnchor, AnchorVerification, LinkageDecision
from utils import parse_date, calculate_age, extract_age_from_text, normalize_name
from config import Config

class DecisionEngine:
    """Core decision logic for linkage determination"""
    
    def __init__(self):
        self.config = Config()
    
    def verify_anchors(self, user_profile: UserProfile, anchors: List[IdentityAnchor], article_date: str) -> List[AnchorVerification]:
        """Verify each anchor against the user profile"""
        verifications = []
        
        for anchor in anchors:
            verification = self._verify_single_anchor(user_profile, anchor, article_date)
            verifications.append(verification)
        
        return verifications
    
    def _verify_single_anchor(self, user_profile: UserProfile, anchor: IdentityAnchor, article_date: str) -> AnchorVerification:
        """Verify a single anchor against user profile"""
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
