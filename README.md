# GAF Roofing AI System

AI-powered B2B sales intelligence platform for generating leads and actionable insights for roofing distributor sales teams.

## Overview

This platform leverages public data sources (GAF contractor directory) to pre-generate actionable sales insights and recommendations. The system helps sales teams identify, understand, and effectively engage with decision-makers in the roofing industry.

## Features

- **Data Collection**: Scalable web scraping system for contractor information
- **Data Processing**: ETL pipeline for cleaning and structuring collected data
- **AI Insights Engine**: Integration with OpenAI/Perplexity APIs to generate actionable sales intelligence
- **RESTful API**: FastAPI backend for accessing contractors and insights

## Project Structure

```
gaf-roofing-ai-system/
├── app/
│   ├── __init__.py
│   ├── config/              # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── contractor.py
│   │   └── insight.py
│   ├── data_collection/     # Web scraping
│   │   ├── __init__.py
│   │   └── scraper.py
│   ├── data_processing/     # ETL pipeline
│   │   ├── __init__.py
│   │   └── etl.py
│   ├── ai_insights/         # AI engine
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── backend/             # FastAPI application
│   │   ├── __init__.py
│   │   └── main.py
│   └── utils/               # Utilities
│       ├── __init__.py
│       └── logger.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
- `OPENAI_API_KEY`: Your OpenAI API key
- `PERPLEXITY_API_KEY`: Your Perplexity API key (optional)
- `ANTHROPIC_API_KEY`: Your Anthropic API key (optional)

### 3. Initialize Database

The database will be automatically initialized when you start the application.

## Usage

### Start the API Server

```bash
uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Example API Calls

#### Scrape Contractors

```bash
POST /scrape?zipcode=10013&distance=25
```

#### Get Contractors

```bash
GET /contractors?skip=0&limit=100&zipcode=10013
```

#### Get Contractor Details

```bash
GET /contractors/{contractor_id}
```

#### Get AI Insights

```bash
GET /contractors/{contractor_id}/insights
```

#### Generate New Insights

```bash
POST /contractors/{contractor_id}/generate-insights
```

## Development

### Key Components

1. **Data Collection** (`app/data_collection/scraper.py`)
   - Scrapes contractor data from GAF directory
   - Handles pagination and rate limiting

2. **Data Processing** (`app/data_processing/etl.py`)
   - Cleans and normalizes scraped data
   - Handles deduplication and data quality

3. **AI Insights** (`app/ai_insights/engine.py`)
   - Generates actionable sales insights
   - Integrates with OpenAI API

4. **Backend API** (`app/backend/main.py`)
   - RESTful API endpoints
   - Handles concurrent requests
   - Background task processing

## Next Steps

1. Implement actual GAF page scraping logic (currently placeholder)
2. Add data quality validation rules
3. Implement caching for AI insights
4. Add authentication/authorization
5. Set up proper logging and monitoring
6. Add unit tests

## Notes

- The scraper currently has placeholder logic - you'll need to inspect the actual GAF page structure and implement the parsing accordingly
- Database defaults to SQLite for development - configure PostgreSQL for production
- AI insights generation runs in background tasks for better performance
