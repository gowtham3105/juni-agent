import re
from datetime import datetime, date
from dateutil import parser
from typing import Optional, Tuple

def parse_date(date_string: str) -> Optional[date]:
    """Parse various date formats into a date object"""
    if not date_string:
        return None
    
    try:
        return parser.parse(date_string).date()
    except (ValueError, TypeError):
        return None

def calculate_age(birth_date: str, reference_date: Optional[str] = None) -> Optional[int]:
    """Calculate age from birth date"""
    birth_dt = parse_date(birth_date)
    if not birth_dt:
        return None
    
    ref_dt = parse_date(reference_date) if reference_date else date.today()
    if not ref_dt:
        return None
    
    age = ref_dt.year - birth_dt.year
    if ref_dt.month < birth_dt.month or (ref_dt.month == birth_dt.month and ref_dt.day < birth_dt.day):
        age -= 1
    
    return age

def extract_age_from_text(text: str) -> Optional[int]:
    """Extract age mentions from text"""
    age_patterns = [
        r'age[d]?\s+(\d{1,3})',
        r'(\d{1,3})\s*years?\s+old',
        r'(\d{1,3})\s*-year-old',
        r'aged\s+(\d{1,3})'
    ]
    
    for pattern in age_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            age = int(match.group(1))
            if 0 <= age <= 120:  # Reasonable age range
                return age
    
    return None

def normalize_name(name: str) -> str:
    """Normalize name for comparison"""
    if not name:
        return ""
    
    # Remove titles, suffixes, and normalize
    cleaned = re.sub(r'\b(mr|mrs|ms|dr|prof|sir|lord|lady|jr|sr|ii|iii)\b\.?', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s]', '', cleaned)  # Remove punctuation
    cleaned = ' '.join(cleaned.split())  # Normalize whitespace
    
    return cleaned.lower()

def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two names"""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Simple token-based similarity
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    return len(intersection) / len(union) if union else 0.0

def get_recency_bucket(article_date: str) -> str:
    """Categorize article by recency"""
    article_dt = parse_date(article_date)
    if not article_dt:
        return "unknown"
    
    today = date.today()
    days_diff = (today - article_dt).days
    months_diff = days_diff / 30.44  # Average days per month
    
    if months_diff < 12:
        return "within 12 months"
    elif months_diff < 36:
        return "12-36 months"
    else:
        return "over 36 months"

def extract_quoted_text(text: str) -> list:
    """Extract quoted statements from text"""
    patterns = [
        r'"([^"]*)"',
        r"'([^']*)'",
        r'«([^»]*)»'
    ]
    
    quotes = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        quotes.extend(matches)
    
    return [quote.strip() for quote in quotes if quote.strip()]
