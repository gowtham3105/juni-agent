import os
from typing import Dict

class Config:
    """Configuration settings for the compliance agent"""
    
    # OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "default_key")
    OPENAI_MODEL = "gpt-4o-mini"  # Using GPT-4 mini as requested by user
    
    # Name matching thresholds
    COMMON_NAMES_THRESHOLD = 2  # Require >=2 anchors for common names
    RARE_NAMES_THRESHOLD = 1    # 1 anchor may suffice for rare names
    
    # Lookback period in years
    LOOKBACK_YEARS = 7
    
    # Common names list (can be expanded)
    COMMON_NAMES = {
        "smith", "johnson", "williams", "brown", "jones", "garcia", "miller",
        "davis", "rodriguez", "martinez", "hernandez", "lopez", "gonzalez",
        "wilson", "anderson", "thomas", "taylor", "moore", "jackson", "martin",
        "lee", "perez", "thompson", "white", "harris", "sanchez", "clark",
        "ramirez", "lewis", "robinson", "walker", "young", "allen", "king",
        "wright", "scott", "torres", "nguyen", "hill", "flores", "green",
        "adams", "nelson", "baker", "hall", "rivera", "campbell", "mitchell"
    }
    
    # Credibility scoring
    CREDIBILITY_SCORES = {
        "government": 100,
        "court": 100,
        "tier1": 90,
        "national": 70,
        "local": 50,
        "blog": 30
    }
    
    # Publisher classifications
    TIER1_PUBLISHERS = {
        "financial times", "wall street journal", "bloomberg", "reuters",
        "associated press", "bbc", "cnn", "new york times", "washington post"
    }
    
    @classmethod
    def is_common_name(cls, name: str) -> bool:
        """Check if a name is considered common"""
        last_name = name.split()[-1].lower() if name else ""
        return last_name in cls.COMMON_NAMES
    
    @classmethod
    def get_credibility_score(cls, publisher: str) -> int:
        """Get credibility score for a publisher"""
        publisher_lower = publisher.lower()
        
        if any(gov_term in publisher_lower for gov_term in ["gov", "court", "tribunal", "regulator"]):
            return cls.CREDIBILITY_SCORES["government"]
        elif publisher_lower in cls.TIER1_PUBLISHERS:
            return cls.CREDIBILITY_SCORES["tier1"]
        elif any(nat_term in publisher_lower for nat_term in ["national", "times", "post", "herald"]):
            return cls.CREDIBILITY_SCORES["national"]
        elif any(local_term in publisher_lower for local_term in ["local", "gazette", "tribune"]):
            return cls.CREDIBILITY_SCORES["local"]
        elif any(blog_term in publisher_lower for blog_term in ["blog", "wordpress", "medium"]):
            return cls.CREDIBILITY_SCORES["blog"]
        else:
            return cls.CREDIBILITY_SCORES["national"]  # Default to national
