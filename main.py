#!/usr/bin/env python3
"""
AI Compliance Agent for AML/KYC Adverse Media Review
Main entry point for processing compliance checks
"""

import json
import sys
from typing import List, Dict, Any
from models import UserProfile, MediaHit, ComplianceResult
from compliance_agent import ComplianceAgent

def load_sample_data() -> tuple[UserProfile, List[MediaHit]]:
    """Load sample data for testing (replace with actual data loading)"""
    
    # Sample user profile
    user_profile = UserProfile(
        full_name="John Michael Smith",
        date_of_birth="1985-03-15",
        city="New York",
        employer="ABC Financial Corp",
        id_data={"passport": "P12345678", "ssn": "XXX-XX-1234"},
        aliases=["John Smith", "J.M. Smith"]
    )
    
    # Sample media hits
    media_hits = [
        MediaHit(
            title="ABC Financial Corp CFO Charged with Securities Fraud",
            snippet="John Smith, 39, Chief Financial Officer at ABC Financial Corp in New York, was charged yesterday with securities fraud by federal prosecutors. The charges relate to alleged manipulation of quarterly earnings reports between 2020-2023.",
            full_text="Federal prosecutors announced charges against John Michael Smith, age 39, the Chief Financial Officer of ABC Financial Corp based in New York City. Smith is accused of securities fraud in connection with the alleged manipulation of quarterly earnings reports submitted to the SEC between 2020 and 2023. According to court documents filed in the Southern District of New York, Smith allegedly worked with other executives to inflate revenue figures and hide mounting losses. 'This case represents a serious breach of fiduciary duty,' said prosecutor Jane Wilson. Smith's attorney declined to comment. ABC Financial Corp is a mid-sized investment firm with offices in Manhattan. The company's stock has fallen 40% since the charges were announced. Smith joined ABC Financial in 2018 as CFO after working at rival firm XYZ Capital. Court records show Smith was born March 15, 1985 and resides in Manhattan.",
            date="2024-11-15",
            source="Financial Times",
            url="https://ft.com/content/abc-cfo-charged"
        ),
        MediaHit(
            title="Investment Firm Executive Denies Fraud Allegations",
            snippet="John Smith of ABC Financial Corp denies all allegations of securities fraud. His lawyer says the charges are unfounded and they will fight them vigorously in court.",
            date="2024-11-16", 
            source="Reuters",
            url="https://reuters.com/business/abc-executive-denies"
        ),
        MediaHit(
            title="Local Man Arrested for DUI",
            snippet="John Smith, 45, of Boston was arrested for driving under the influence on Highway 95. Smith works as a mechanic at Joe's Auto Repair.",
            date="2024-11-10",
            source="Boston Herald", 
            url="https://bostonherald.com/local/dui-arrest"
        )
    ]
    
    return user_profile, media_hits

def print_results(result: ComplianceResult):
    """Print compliance results in a structured format"""
    
    print("\n" + "="*80)
    print("COMPLIANCE REVIEW RESULTS")
    print("="*80)
    
    print(f"\nSUBJECT: {result.user_profile.full_name}")
    print(f"DOB: {result.user_profile.date_of_birth}")
    print(f"CITY: {result.user_profile.city}")
    print(f"EMPLOYER: {result.user_profile.employer}")
    
    print(f"\nTOTAL HITS PROCESSED: {result.total_hits}")
    print(f"MATCHED HITS: {len(result.matched_hits)}")
    print(f"NON-MATCHED HITS: {len(result.non_matched_hits)}")
    
    print(f"\nFINAL DECISION: {result.final_decision.upper()}")
    print(f"DECISION SCORE: {result.decision_score}/100")
    print(f"RATIONALE: {result.overall_rationale}")
    
    if result.targeted_ask:
        print(f"\nTARGETED ASK: {result.targeted_ask}")
    
    print("\n" + "-"*60)
    print("ARTICLE ANALYSIS DETAILS")
    print("-"*60)
    
    for i, article in enumerate(result.analyzed_articles, 1):
        print(f"\nARTICLE {i}: {article.hit.title}")
        print(f"Source: {article.hit.source} ({article.hit.date})")
        print(f"Summary: {article.brief_summary}")
        print(f"Linkage Decision: {article.linkage_decision.value}")
        print(f"Anchors Found: {len(article.anchors)}")
        
        if article.anchors:
            print("  Identity Anchors:")
            for anchor in article.anchors:
                print(f"    - {anchor.anchor_type}: {anchor.value} (confidence: {anchor.confidence:.2f})")
        
        if article.contradictions:
            print(f"  Contradictions: {'; '.join(article.contradictions)}")
        
        print(f"  Outcome: {article.outcome_type.value}")
        print(f"  Category: {article.category_type.value}")
        print(f"  {article.credibility_note}")
        print(f"  {article.recency_note}")
        
        print("\n  3-Line Rationale:")
        for line in article.rationale.split('\n'):
            print(f"    {line}")
    
    print("\n" + "="*80)
    print("FINAL MEMO")
    print("="*80)
    print(result.final_memo)

def main():
    """Main execution function"""
    
    print("AI Compliance Agent - Adverse Media Review")
    print("Loading OpenAI GPT-5 for anchor extraction...")
    
    try:
        # Initialize compliance agent
        agent = ComplianceAgent()
        
        # Load data (in production, this would come from API calls or file uploads)
        user_profile, media_hits = load_sample_data()
        
        print(f"\nProcessing compliance check for: {user_profile.full_name}")
        print(f"Analyzing {len(media_hits)} media hits...")
        
        # Process compliance check
        result = agent.process_compliance_check(user_profile, media_hits)
        
        # Display results
        print_results(result)
        
        # Optionally save results to JSON file
        output_file = f"compliance_result_{user_profile.full_name.replace(' ', '_').lower()}_{result.processing_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            # Convert result to dict for JSON serialization
            result_dict = result.model_dump()
            json.dump(result_dict, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
