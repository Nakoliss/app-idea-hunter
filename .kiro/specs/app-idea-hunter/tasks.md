# Implementation Plan

- [x] 1. Set up project structure and core configuration





  - Create FastAPI application structure with proper directory organization (app/, tests/, prompts/)
  - Implement environment configuration management with python-dotenv
  - Set up JSON structured logging configuration using python-json-logger
  - Create Dockerfile and requirements.txt with all necessary dependencies
  - _Requirements: 5.5, 6.1_

- [ ] 2. Implement database models and connection management
  - Create SQLModel classes for Complaint, Idea, Source, and Error tables
  - Implement Supabase connection management with connection pooling
  - Write database initialization and migration utilities
  - Create unit tests for all database models and validation constraints
  - _Requirements: 2.4, 5.4_

- [ ] 3. Build sentiment analysis and deduplication services
  - Implement VADER sentiment analysis service with filtering logic (< -0.3)
  - Create SHA-1 based deduplication service using first 120 tokens
  - Write complaint processing pipeline that combines sentiment filtering and deduplication
  - Create unit tests for sentiment analysis accuracy and deduplication logic
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 4. Develop base scraper infrastructure
  - Create abstract BaseScraper class with common HTTP client functionality
  - Implement exponential backoff retry logic with configurable parameters
  - Add rate limiting handling and user agent rotation
  - Create error logging and failed URL tracking to errors table
  - Write unit tests for retry logic and error handling
  - _Requirements: 1.3, 1.4, 6.2, 6.3_

- [ ] 5. Implement Reddit scraper
  - Create RedditScraper class extending BaseScraper
  - Implement async HTTP requests to Reddit API for posts and comments
  - Add Reddit-specific parsing logic for complaint extraction
  - Integrate with complaint processing pipeline (sentiment + deduplication)
  - Write unit tests with mocked Reddit API responses
  - _Requirements: 1.1_

- [ ] 6. Implement Google Play Store scraper
  - Create GooglePlayScraper class extending BaseScraper
  - Implement async HTTP requests to scrape 1-3 star reviews
  - Add Google Play specific parsing logic for review extraction
  - Integrate with complaint processing pipeline
  - Write unit tests with mocked Google Play responses
  - _Requirements: 1.2_

- [ ] 7. Build AI service for idea generation
  - Create AIService class with OpenAI GPT-3.5 integration
  - Implement prompt template loading from prompts/idea_prompt.txt
  - Add JSON response parsing and validation for idea structure
  - Implement token usage tracking and cost monitoring
  - Create unit tests with mocked OpenAI responses
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 8. Implement cost guard and monitoring
  - Create cost monitoring service to track token usage per complaint
  - Implement CI test that fails if mean tokens per complaint exceeds 600
  - Add cost calculation and logging functionality
  - Create sample_tokens.json for cost guard testing
  - Write automated tests for cost guard thresholds
  - _Requirements: 3.5, 7.1, 7.2_

- [ ] 9. Create FastAPI routes and API endpoints
  - Implement main FastAPI application with route organization
  - Create GET / route for main dashboard with idea display
  - Add POST /scrape route for manual scraping trigger
  - Implement GET /ideas route with pagination (100 rows per page)
  - Add PUT /ideas/{id}/favorite route for favorites toggle
  - Create unit tests for all API endpoints
  - _Requirements: 4.2, 4.3, 4.4, 1.6_

- [ ] 10. Build web UI templates and frontend
  - Create base HTML template with Tailwind CSS styling
  - Implement table view template for ideas with sortable columns
  - Create card view template for visual idea display
  - Add HTMX integration for dynamic pagination and filtering
  - Implement Alpine.js components for client-side state management
  - _Requirements: 4.1, 4.6_

- [ ] 11. Implement export functionality
  - Create ExportService class for PDF and CSV generation
  - Add GET /export/pdf route with filtered data export
  - Implement GET /export/csv route with all data fields
  - Create export UI components with download buttons
  - Write unit tests for export functionality with sample data
  - _Requirements: 4.5_

- [ ] 12. Add scheduling and cron job support
  - Create scheduled scraping service that runs all scrapers
  - Implement cron job handler for daily scraping at 2 AM UTC
  - Add fly.toml configuration for Fly cron scheduling
  - Create monitoring and logging for scheduled jobs
  - Write integration tests for scheduled scraping workflow
  - _Requirements: 1.5_

- [ ] 13. Implement comprehensive error handling and logging
  - Add structured error handling across all services
  - Implement graceful degradation for API failures
  - Create detailed error logging with correlation IDs
  - Add health check endpoint for monitoring
  - Write integration tests for error scenarios
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 14. Create deployment configuration
  - Configure fly.toml for Fly.io deployment with scale-to-zero
  - Set up environment variable management through Fly secrets
  - Create deployment scripts and documentation
  - Add health checks and monitoring configuration
  - Test deployment process in staging environment
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ] 15. Write comprehensive tests and documentation
  - Create integration tests for complete scraping-to-display workflow
  - Add performance tests for concurrent scraping and large datasets
  - Write API documentation and usage examples
  - Create README with setup and deployment instructions
  - Add troubleshooting guide and monitoring documentation
  - _Requirements: 6.4_