import json
from typing import List, Dict, Any
from datetime import datetime, date
from models import (
    UserProfile, MediaHit, ArticleAnalysis, ComplianceResult, 
    LinkageDecision, OutcomeType, CategoryType
)
from anchor_extractor import AnchorExtractor
from name_matcher import NameMatcher
from decision_engine import DecisionEngine
from config import Config
from utils import get_recency_bucket

class ComplianceAgent:
    """Main compliance agent for AML/KYC adverse media review"""
    
    def __init__(self, progress_callback=None):
        self.config = Config()
        self.anchor_extractor = AnchorExtractor()
        self.name_matcher = NameMatcher()
        self.decision_engine = DecisionEngine()
        self.progress_callback = progress_callback
        self.step_counter = 0
    
    def set_prompt_manager(self, prompt_manager):
        """Update all components to use the given prompt manager"""
        self.anchor_extractor.set_prompt_manager(prompt_manager)
        self.name_matcher.set_prompt_manager(prompt_manager)
        self.decision_engine.set_prompt_manager(prompt_manager)
    
    def _log_progress(self, message: str):
        """Log progress step and call callback if provided"""
        self.step_counter += 1
        full_message = f"Step {self.step_counter}: {message}"
        print(full_message)
        if self.progress_callback:
            self.progress_callback(full_message)
    
    def process_compliance_check(self, user_profile: UserProfile, media_hits: List[MediaHit]) -> ComplianceResult:
        """Process complete compliance check following the 18-step SOP"""
        
        self._log_progress(f"Case intake - Subject: {user_profile.full_name}, DOB {user_profile.date_of_birth}, city {user_profile.city}, employer {user_profile.employer}. Vendor hits: {len(media_hits)} articles.")
        
        analyzed_articles = []
        
        # Process each article through steps 2-13
        for hit in media_hits:
            article_analysis = self._analyze_single_article(user_profile, hit)
            analyzed_articles.append(article_analysis)
        
        # Step 14) Cluster duplicates (simplified - no actual clustering implemented)
        self._log_progress(f"🔄 Checking for duplicate articles...")
        deduplicated_articles = self._cluster_duplicates(analyzed_articles)
        
        # Step 15) Case roll-up - keep only yes/maybe articles
        accepted_articles = [a for a in deduplicated_articles if a.linkage_decision in [LinkageDecision.YES, LinkageDecision.MAYBE]]
        rejected_articles = [a for a in deduplicated_articles if a.linkage_decision == LinkageDecision.NO]
        self._log_progress(f"📋 Case roll-up: {len(accepted_articles)} matched, {len(rejected_articles)} rejected")
        
        # Step 16) Overall decision logic
        self._log_progress(f"🎯 Calculating final compliance decision...")
        final_decision, decision_score, overall_rationale = self._make_overall_decision(accepted_articles)
        self._log_progress(f"🏁 Final Decision: {final_decision.upper()} (score: {decision_score}/100)")
        
        # Step 17) Targeted ask
        targeted_ask = self._generate_targeted_ask(accepted_articles) if final_decision == "escalate" else None
        
        # Step 18) Final memo
        final_memo = self._generate_final_memo(user_profile, accepted_articles, final_decision, targeted_ask or "")
        
        return ComplianceResult(
            user_profile=user_profile,
            total_hits=len(media_hits),
            analyzed_articles=deduplicated_articles,
            matched_hits=accepted_articles,
            non_matched_hits=rejected_articles,
            final_decision=final_decision,
            decision_score=decision_score,
            overall_rationale=overall_rationale,
            targeted_ask=targeted_ask,
            final_memo=final_memo
        )
    
    def _analyze_single_article(self, user_profile: UserProfile, hit: MediaHit) -> ArticleAnalysis:
        """Analyze a single article following steps 2-13 of the SOP"""
        
        # Step 2) Read article & Step 3) Collect anchors
        self._log_progress(f"📄 Analyzing article: '{hit.title}'")
        self._log_progress(f"🤖 AI extracting identity anchors from article content...")
        brief_summary, anchors = self.anchor_extractor.extract_anchors_and_summary(hit, user_profile)
        self._log_progress(f"✅ Found {len(anchors)} identity anchors: {', '.join([f'{a.anchor_type}:{a.value}' for a in anchors[:3]])}{' ...' if len(anchors) > 3 else ''}")
        
        # Step 4) Name match sanity
        self._log_progress(f"🤖 AI analyzing name matches (handles nicknames, cultural variants)...")
        has_name_match, name_analysis, required_anchors = self.name_matcher.analyze_name_match(user_profile, anchors)
        self._log_progress(f"👤 Name analysis: {name_analysis}")
        
        # Step 5) Anchor test  
        self._log_progress(f"🤖 AI verifying each anchor against user profile (contextual matching)...")
        verifications = self.decision_engine.verify_anchors(user_profile, anchors, hit.date)
        matches = [v for v in verifications if v.matches]
        conflicts = [v for v in verifications if v.conflict]
        self._log_progress(f"🔍 Anchor verification: {len(matches)} matches, {len(conflicts)} conflicts")
        
        # Step 6) Contradiction scan
        contradictions = self.decision_engine.detect_contradictions(verifications)
        
        # Step 7) Linkage decision
        self._log_progress(f"⚖️ Making linkage decision based on evidence...")
        linkage_decision, linkage_rationale = self.decision_engine.make_linkage_decision(
            user_profile, anchors, verifications, contradictions, required_anchors, has_name_match
        )
        self._log_progress(f"📊 Decision: {linkage_decision.value} - {linkage_rationale}")
        
        # Skip outcome and category classification as requested by user
        outcome_type = OutcomeType.NONE
        category_type = CategoryType.NONE
        
        # Step 10) Credibility note
        credibility_score = self.config.get_credibility_score(hit.source)
        credibility_note = f"Credibility: {self._get_credibility_tier(credibility_score)} ({hit.source}, {hit.date})"
        
        # Step 11) Recency note  
        recency_bucket = get_recency_bucket(hit.date)
        recency_note = f"Recency: {recency_bucket} ({hit.date})"
        
        # Step 13) Per-article rationale (always 3 lines)
        rationale = self._generate_article_rationale(
            outcome_type, category_type, brief_summary, linkage_rationale, 
            credibility_note, recency_note, hit.url or ""
        )
        
        return ArticleAnalysis(
            hit=hit,
            brief_summary=brief_summary,
            anchors=anchors,
            anchor_verifications=verifications,
            contradictions=contradictions,
            linkage_decision=linkage_decision,
            outcome_type=outcome_type,
            category_type=category_type,
            credibility_note=credibility_note,
            recency_note=recency_note,
            rationale=rationale
        )
    
    def _get_credibility_tier(self, score: int) -> str:
        """Convert credibility score to tier description"""
        if score >= 100:
            return "government/court"
        elif score >= 90:
            return "tier-1 outlet"
        elif score >= 70:
            return "national outlet"
        elif score >= 50:
            return "local outlet"
        else:
            return "blog/low credibility"
    
    def _generate_article_rationale(self, outcome: OutcomeType, category: CategoryType, 
                                  summary: str, linkage: str, credibility: str, 
                                  recency: str, url: str) -> str:
        """Generate 3-line rationale per SOP step 13"""
        line1 = f"Outcome: {outcome.value}, Category: {category.value}. {summary}"
        line2 = linkage
        line3 = f"{credibility}. {recency}. URL: {url or 'not provided'}"
        
        return f"{line1}\n{line2}\n{line3}"
    
    def _cluster_duplicates(self, articles: List[ArticleAnalysis]) -> List[ArticleAnalysis]:
        """Step 14: Cluster duplicate articles (simplified implementation)"""
        # For now, just return as-is. In production, this would implement
        # sophisticated duplicate detection based on title similarity, URLs, etc.
        return articles
    
    def _make_overall_decision(self, accepted_articles: List[ArticleAnalysis]) -> tuple[str, int, str]:
        """Step 16: Make overall decision based on accepted articles"""
        
        if not accepted_articles:
            return "clear", 10, "Decision: clear (score 10/100) because no linked adverse media found."
        
        # Score based on outcome severity and linkage strength
        score = 0
        severe_outcomes = []
        
        for article in accepted_articles:
            # Base score for any linked article
            article_score = 20
            
            # Outcome severity multiplier
            if article.outcome_type in [OutcomeType.CONVICTED, OutcomeType.REGULATOR_ORDER]:
                article_score *= 3
                severe_outcomes.append(article)
            elif article.outcome_type in [OutcomeType.CHARGED]:
                article_score *= 2
            elif article.outcome_type in [OutcomeType.INVESTIGATION]:
                article_score *= 1.5
            
            # Linkage strength multiplier
            if article.linkage_decision == LinkageDecision.YES:
                article_score *= 1.5
            elif article.linkage_decision == LinkageDecision.MAYBE:
                article_score *= 1.0
            
            # Recency bonus
            if "within 12 months" in article.recency_note:
                article_score *= 1.5
            elif "12-36 months" in article.recency_note:
                article_score *= 1.2
            
            score += article_score
        
        score = min(100, int(score))  # Cap at 100
        
        # Decision logic
        if severe_outcomes and any(a.linkage_decision == LinkageDecision.YES for a in severe_outcomes):
            decision = "decline"
            rationale = f"Decision: decline (score {score}/100) because convicted/regulator order within lookback with yes linkage."
        elif any(a.outcome_type in [OutcomeType.CHARGED, OutcomeType.INVESTIGATION] for a in accepted_articles):
            decision = "escalate"
            rationale = f"Decision: escalate (score {score}/100) because charged/investigated with linkage."
        elif score >= 60:
            decision = "escalate"
            rationale = f"Decision: escalate (score {score}/100) because multiple adverse findings with linkage."
        else:
            decision = "clear"
            rationale = f"Decision: clear (score {score}/100) because only weak allegations or maybe linkage."
        
        return decision, score, rationale
    
    def _generate_targeted_ask(self, accepted_articles: List[ArticleAnalysis]) -> str:
        """Step 17: Generate targeted ask for human reviewer"""
        contradictions = []
        missing_anchors = []
        
        for article in accepted_articles:
            contradictions.extend(article.contradictions)
            
            # Check for missing key anchors
            anchor_types = {a.anchor_type for a in article.anchors}
            if "dob" not in anchor_types and "age" not in anchor_types:
                missing_anchors.append("DOB/age verification")
            if "employer" not in anchor_types:
                missing_anchors.append("employment verification")
        
        if contradictions:
            primary_contradiction = contradictions[0]
            if "dob" in primary_contradiction.lower():
                return "Request: government ID to confirm DOB, since article reports conflicting birth date."
            elif "age" in primary_contradiction.lower():
                return "Request: government ID to confirm age, since article reports conflicting age."
            elif "employer" in primary_contradiction.lower():
                return "Request: employment verification to resolve employer contradiction."
        
        if missing_anchors:
            return f"Request: additional documentation to verify {missing_anchors[0]}."
        
        return "Request: manual review of linkage assessment for final confirmation."
    
    def _generate_final_memo(self, user_profile: UserProfile, accepted_articles: List[ArticleAnalysis], 
                           final_decision: str, targeted_ask: str) -> str:
        """Step 18: Generate final compliance memo"""
        
        memo_lines = []
        memo_lines.append(f"ADVERSE MEDIA REVIEW - {user_profile.full_name}")
        memo_lines.append(f"Subject: {user_profile.full_name}, DOB: {user_profile.date_of_birth or 'not provided'}")
        memo_lines.append(f"Decision: {final_decision.upper()}")
        memo_lines.append("")
        
        if accepted_articles:
            memo_lines.append("LINKED ARTICLES:")
            for i, article in enumerate(accepted_articles[:5], 1):  # Max 5 articles
                memo_lines.append(f"• Article {i}: {article.hit.title} ({article.hit.source}, {article.hit.date})")
                memo_lines.append(f"  Linkage: {article.linkage_decision.value}, Outcome: {article.outcome_type.value}")
                if article.contradictions:
                    memo_lines.append(f"  Contradictions: {article.contradictions[0]}")
        else:
            memo_lines.append("• No linked adverse media found")
        
        memo_lines.append("")
        if targeted_ask:
            memo_lines.append(f"NEXT STEP: {targeted_ask}")
        else:
            memo_lines.append("NEXT STEP: Review complete, no further action required.")
        
        memo_lines.append(f"Review completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(memo_lines)
