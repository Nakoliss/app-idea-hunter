# Requirements Document

## Introduction

App Idea Hunter is a web application that automatically mines complaints from Reddit and Google Play reviews, filters pain points using sentiment analysis, and uses AI to generate and score startup ideas. The system is designed as a cloud-ready Solo MVP that can run on Fly.io with Supabase Postgres, targeting solo entrepreneurs and indie developers who want to discover data-driven startup opportunities quickly and cost-effectively.

## Requirements

### Requirement 1

**User Story:** As a solo entrepreneur, I want the system to automatically scrape complaints from Reddit and Google Play reviews, so that I can discover pain points without manual research.

#### Acceptance Criteria

1. WHEN the scraper runs THEN the system SHALL collect complaints from Reddit posts and comments using async HTTP requests
2. WHEN the scraper runs THEN the system SHALL collect 1-3 star reviews from Google Play Store using async HTTP requests
3. WHEN scraping encounters rate limits or errors THEN the system SHALL implement exponential backoff retries
4. WHEN scraping fails for specific URLs THEN the system SHALL store failed attempts in an errors table for debugging
5. WHEN the scraper runs THEN the system SHALL be triggered via Fly cron scheduler at 2 AM daily (0 2 * * *)
6. IF a user manually triggers scraping THEN the system SHALL provide a "Run now" button in the UI

### Requirement 2

**User Story:** As a user, I want the system to filter and deduplicate complaints based on sentiment, so that I only see genuine pain points worth exploring.

#### Acceptance Criteria

1. WHEN processing scraped complaints THEN the system SHALL use VADER sentiment analysis to filter complaints with sentiment score < -0.3
2. WHEN storing complaints THEN the system SHALL generate SHA-1 hash of first 120 tokens to identify duplicates
3. WHEN duplicate complaints are detected THEN the system SHALL skip storing the duplicate entry
4. WHEN complaints are processed THEN the system SHALL store raw complaint data in the complaints table with metadata

### Requirement 3

**User Story:** As an entrepreneur, I want AI to generate startup ideas from complaints with structured scoring, so that I can quickly evaluate business opportunities.

#### Acceptance Criteria

1. WHEN processing filtered complaints THEN the system SHALL send complaints to GPT-3.5 using a structured prompt template
2. WHEN GPT-3.5 responds THEN the system SHALL receive JSON with idea text and six numeric scores (market, tech, competition, monetization, feasibility, overall)
3. WHEN storing AI responses THEN the system SHALL save both raw JSON and parsed numeric fields in the ideas table
4. WHEN processing complaints THEN the system SHALL maintain cost under $0.002 per complaint processed
5. IF token usage exceeds 600 tokens per complaint on average THEN the system SHALL fail CI cost guard checks

### Requirement 4

**User Story:** As a user, I want a web interface to browse, filter, and export generated ideas, so that I can efficiently review potential opportunities.

#### Acceptance Criteria

1. WHEN accessing the web UI THEN the system SHALL display ideas in both table and card view formats
2. WHEN browsing ideas THEN the system SHALL implement pagination with 100 rows per page
3. WHEN viewing ideas THEN the system SHALL show joined data from complaints and ideas tables with all scoring metrics
4. WHEN users want to save interesting ideas THEN the system SHALL provide a favorites toggle functionality
5. WHEN users want to export data THEN the system SHALL provide PDF and CSV export options for filtered idea lists
6. WHEN rendering the UI THEN the system SHALL use Tailwind CSS for styling, HTMX for dynamic interactions, and Alpine.js for client-side state

### Requirement 5

**User Story:** As a solo user, I want the system to run cost-effectively in the cloud with automatic scaling, so that I can access it from anywhere without high operational costs.

#### Acceptance Criteria

1. WHEN deployed THEN the system SHALL run on Fly.io with scale-to-zero capability to minimize hosting costs
2. WHEN idle THEN the system SHALL automatically scale down to zero instances
3. WHEN receiving requests THEN the system SHALL automatically scale up from zero within reasonable time
4. WHEN storing data THEN the system SHALL use Supabase Postgres Free tier for the database
5. WHEN managing secrets THEN the system SHALL store API keys and database credentials in Fly secrets store
6. WHEN the system runs THEN the total monthly cost SHALL remain under $5 for solo usage

### Requirement 6

**User Story:** As a developer, I want comprehensive logging and error handling, so that I can monitor system health and debug issues effectively.

#### Acceptance Criteria

1. WHEN the application runs THEN the system SHALL implement JSON structured logging using python-json-logger
2. WHEN errors occur during scraping THEN the system SHALL log detailed error information and continue processing
3. WHEN scraping fails THEN the system SHALL store failed URLs in an errors table with timestamps and error details
4. WHEN API calls fail THEN the system SHALL implement graceful degradation without crashing the system
5. WHEN deployed THEN the system SHALL provide accessible logs through Fly.io logging interface

### Requirement 7

**User Story:** As a cost-conscious user, I want automated cost monitoring, so that I can prevent unexpected expenses from AI API usage.

#### Acceptance Criteria

1. WHEN running CI/CD THEN the system SHALL include a cost guard test that fails if mean tokens per complaint exceeds 600
2. WHEN processing complaints THEN the system SHALL track and log token usage for monitoring
3. WHEN costs approach limits THEN the system SHALL provide visibility into usage patterns
4. IF the cost guard threshold is exceeded THEN the system SHALL prevent deployment until the issue is resolved