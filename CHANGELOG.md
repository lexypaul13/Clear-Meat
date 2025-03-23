# Changelog

All notable changes to the MeatWise project will be documented in this file.

## [Unreleased]

### Added
- Separate storage for enhanced descriptions
- Description enhancement timestamp tracking
- Confidence scoring for AI-generated content
- Original description preservation
- Description enhancement system with caching
- Gemini LLM integration infrastructure
- Product grouping by meat type
- Similarity-based description matching

### Changed
- Modified description enhancement system to preserve originals
- Updated caching system to track both description versions
- Enhanced data quality metrics
- Updated database schema for RAG optimization
- Improved product processing efficiency
- Enhanced caching system for AI responses

### Fixed
- PostgreSQL extension dependency issues
- Cache table structure optimization
- Similarity matching improvements

## [0.2.0] - 2024-03-23

### Added
- Description cache table for AI responses
- Text similarity indexing
- Confidence scoring system
- Meat-type specific processing queues

### Changed
- Optimized database queries
- Improved product grouping logic
- Enhanced cache management

### Technical Details
- Created `description_cache` table with JSON storage
- Implemented two-level cache system
- Added 30-day cache expiration
- Set up confidence scoring
- Added `enhanced_description` column to products table
- Added `description_enhanced_at` timestamp
- Added `description_confidence` score
- Implemented two-level caching strategy

## [0.1.0] - 2024-03-16

### Added
- Initial database schema
- Product collection from Open Food Facts
- Basic API endpoints
- Data validation system

### Changed
- Optimized data collection
- Improved error handling
- Enhanced data validation

### Removed
- Unused API endpoints
- Redundant data fields 