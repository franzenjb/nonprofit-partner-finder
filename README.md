# Red Cross Nonprofit Partner Finder

An AI-powered system that analyzes publicly available data on nonprofit organizations to identify and rank those that best align with the Red Cross mission. The system helps Red Cross chapters identify high-value partners, allocate resources strategically, and strengthen community impact.

## Features

- **Comprehensive Data Collection**
  - IRS 990 form analysis for financial data
  - Website scraping for mission and program information
  - Social media analysis for engagement metrics
  - News and media monitoring

- **Advanced Mission Alignment Scoring**
  - Natural Language Processing for semantic similarity
  - Keyword matching with weighted categories
  - Service overlap analysis
  - Program compatibility assessment

- **ROI Calculation**
  - Resource sharing potential
  - Cost savings estimation
  - Impact multiplication factors
  - Reach expansion metrics

- **Intelligent Ranking System**
  - Multi-criteria weighted scoring
  - Customizable ranking parameters
  - Explainable AI with clear rationale
  - Side-by-side comparisons

## Installation

1. Clone the repository:
```bash
git clone https://github.com/redcross/nonprofit-partner-finder.git
cd nonprofit-partner-finder
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

## Quick Start

### Command Line Interface

Search for nonprofits in a ZIP code:
```bash
python cli.py search 10001 --top 10
```

Analyze a specific nonprofit:
```bash
python cli.py analyze 13-1234567 --deep
```

Compare two nonprofits:
```bash
python cli.py compare 13-1234567 13-7654321
```

### API Server

Start the FastAPI server:
```bash
uvicorn src.api.main:app --reload
```

Access the API:
- Documentation: http://localhost:8000/docs
- Search endpoint: `POST /search`
- Nonprofit details: `GET /nonprofit/{ein}`
- Ranking endpoint: `POST /rank`

### Example API Usage

```python
import requests

# Search nonprofits by ZIP code
response = requests.post(
    "http://localhost:8000/search",
    json={
        "zip_code": "10001",
        "radius_miles": 25,
        "max_results": 20
    }
)

results = response.json()
for nonprofit in results[:5]:
    print(f"{nonprofit['rank']}. {nonprofit['name']}")
    print(f"   Score: {nonprofit['overall_score']:.1%}")
    print(f"   Mission Alignment: {nonprofit['mission_alignment_score']:.1%}")
    print(f"   ROI Potential: ${nonprofit['roi_potential']:,.0f}")
```

## System Architecture

```
nonprofit-partner-finder/
├── src/
│   ├── models/          # Data models
│   ├── collectors/      # Data collection modules
│   │   ├── irs_collector.py
│   │   ├── web_scraper.py
│   │   └── social_media.py
│   ├── analyzers/       # Analysis engines
│   │   ├── mission_alignment.py
│   │   └── roi_calculator.py
│   ├── core/            # Core system components
│   │   └── ranking_engine.py
│   └── api/             # FastAPI endpoints
│       └── main.py
├── config/              # Configuration files
│   └── red_cross_mission.yaml
├── tests/               # Unit tests
├── data/                # Data storage
└── docs/                # Documentation
```

## Mission Alignment Criteria

The system evaluates nonprofits based on:

### Primary Keywords (Highest Weight)
- Disaster relief
- Emergency response
- Humanitarian aid
- Blood donation
- Health and safety

### Service Categories
- **Disaster Services**: Emergency shelter, mass feeding, relief supplies
- **Health & Safety**: Blood services, safety training, health education
- **Support Services**: Military families, volunteer coordination, community preparation

### Scoring Weights
- Mission Alignment: 35%
- ROI Potential: 25%
- Financial Stability: 15%
- Organizational Capacity: 15%
- Data Quality: 10%

## ROI Calculation Factors

### Resource Sharing
- Facilities and equipment
- Volunteer networks
- Expertise and training capabilities
- Technology and systems

### Impact Multiplication
- Geographic reach expansion
- Service enhancement
- Cost reduction through efficiency
- Community trust building

### Sustainability Metrics
- Funding stability
- Long-term viability
- Growth potential
- Partnership history

## API Endpoints

### Core Endpoints

- `POST /search` - Search nonprofits by ZIP code
- `GET /nonprofit/{ein}` - Get detailed nonprofit information
- `POST /analyze/{ein}` - Perform deep analysis
- `POST /rank` - Rank a list of nonprofits
- `GET /compare` - Compare two nonprofits
- `GET /export` - Export results to CSV or JSON

### Request/Response Examples

See the API documentation at `/docs` for interactive examples and detailed schemas.

## Configuration

### Red Cross Mission Configuration

Edit `config/red_cross_mission.yaml` to customize:
- Mission keywords and weights
- Service categories
- Scoring criteria
- ROI factors

### Environment Variables

Required API keys and settings in `.env`:
- IRS data access credentials
- Social media API keys
- OpenAI API key for NLP
- Database connections

## Testing

Run unit tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src tests/
```

## Data Sources

- **IRS 990 Forms**: ProPublica Nonprofit Explorer API
- **Website Data**: Direct web scraping with consent
- **Social Media**: Twitter, Facebook, LinkedIn APIs
- **Financial Data**: GuideStar, Charity Navigator (when available)

## Privacy and Compliance

- All data collected is publicly available
- Respects robots.txt and rate limits
- No personal donor information collected
- GDPR and data protection compliant

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

For questions or support, please contact:
- Email: partner-finder@redcross.org
- Issues: https://github.com/redcross/nonprofit-partner-finder/issues

## Acknowledgments

- Red Cross Digital Services Team
- ProPublica for nonprofit data access
- Open source community contributors

---

**Note**: This system is designed to assist in partner identification but should not replace human judgment and due diligence in partnership decisions.