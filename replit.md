# Overview

This is an AI-powered compliance agent system for AML/KYC adverse media review. The application automates the process of analyzing media hits against user profiles to determine if adverse media articles are linked to specific individuals. It follows an 18-step Standard Operating Procedure (SOP) that extracts identity anchors, verifies matches, classifies risks, and generates compliance recommendations.

The system processes user profiles containing personal information (name, DOB, location, employer) against adverse media articles, using AI to extract identity markers and make linkage decisions. It outputs structured compliance results with rationales for regulatory auditing purposes.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Components

The application follows a modular architecture with distinct components handling specific aspects of the compliance review process:

**ComplianceAgent (main.py)**: Central orchestrator that implements the 18-step SOP workflow. Coordinates between all other components and manages the overall compliance check process from intake to final memo generation.

**AnchorExtractor (anchor_extractor.py)**: Uses OpenAI's GPT-5 model to analyze adverse media articles and extract identity anchors (names, employers, cities, dates of birth, ages, titles, IDs). Also generates neutral summaries of article allegations.

**NameMatcher (name_matcher.py)**: Implements sophisticated name matching logic with different thresholds for common vs rare names. Common names require 2+ matching anchors while rare names may require only 1 anchor for positive linkage.

**DecisionEngine (decision_engine.py)**: Contains core verification logic that checks extracted anchors against user profiles. Implements conflict detection and makes linkage decisions (yes/maybe/no) based on anchor verification results.

## Data Models

The system uses Pydantic models for type safety and validation:

- **UserProfile**: Contains subject identity data (name, DOB, location, employer, aliases)
- **MediaHit**: Represents adverse media articles with title, content, date, and source
- **IdentityAnchor**: Extracted identity markers from articles
- **ComplianceResult**: Final output containing analysis, decisions, and recommendations

Enums define classification systems for linkage decisions (YES/MAYBE/NO), outcome types (allegation, charged, convicted, etc.), and risk categories (fraud, corruption, money laundering, etc.).

## Recent Architectural Changes (August 26, 2025)

**Simplified Anchor Verification Architecture**: Removed single anchor verification fallback mechanism to rely entirely on batch AI processing for cleaner, more consistent behavior. The system now uses only `_ai_verify_all_anchors()` for all anchor verification, eliminating the complex multi-tier fallback system while maintaining efficiency through batch processing.

## AI Integration

The system integrates with OpenAI's GPT-5 model for natural language processing tasks. The AI is used specifically for:

- Extracting identity anchors from unstructured article text
- Generating neutral summaries of allegations
- Analyzing complex textual content for compliance purposes

The prompt engineering is designed to produce structured outputs that can be programmatically processed by downstream components.

## Decision Logic

The system implements a rules-based decision engine with specific thresholds:

- Name matching requires similarity scores above 0.7
- Common surnames require 2+ matching anchors for positive linkage
- Rare names may link with 1+ matching anchor
- Hard conflicts (DOB, age discrepancies) typically result in negative linkage
- Final decisions consider credibility scoring based on source quality

## Workflow Architecture

The 18-step SOP is implemented as a linear workflow:

1. Case intake and subject profiling
2. Article content analysis
3. Identity anchor extraction
4. Name matching assessment
5. Anchor verification against profile
6. Contradiction detection
7. Linkage decision making
8. Outcome classification (legal status)
9. Risk category classification
10. Source credibility assessment
11. Recency bucketing
12. Per-article rationale generation
13. Duplicate article clustering
14. Case roll-up of accepted articles
15. Overall decision logic
16. Targeted ask generation for escalations
17. Final memo creation for audit trail

# External Dependencies

**OpenAI API**: Core dependency for GPT-5 model access. Used for natural language processing, anchor extraction, and content analysis. Requires API key configuration.

**Python Libraries**:
- **Pydantic**: Data validation and serialization framework for type-safe models
- **python-dateutil**: Flexible date parsing for various date formats found in articles
- **typing**: Enhanced type hints for better code maintainability

**Configuration Management**: Environment-based configuration system for API keys, model selection, and business rule parameters (thresholds, lookback periods, publisher classifications).

The system is designed to be self-contained with minimal external dependencies, focusing on the OpenAI API as the primary external service for AI capabilities.