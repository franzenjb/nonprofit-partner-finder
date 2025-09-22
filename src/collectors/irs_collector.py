import requests
import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import json
import time
from pathlib import Path

from src.models.nonprofit import (
    Nonprofit, Address, FinancialData, 
    DataSource, NonprofitStatus
)


logger = logging.getLogger(__name__)


class IRS990Collector:
    """
    Collector for IRS 990 form data
    Uses publicly available IRS datasets and APIs
    """
    
    BASE_URL = "https://www.irs.gov/pub/irs-soi"
    AWS_990_URL = "https://s3.amazonaws.com/irs-form-990"
    PROPUBLICA_API = "https://projects.propublica.org/nonprofits/api/v2"
    
    def __init__(self, cache_dir: str = "./data/irs_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NonprofitAnalyzer/1.0 (Red Cross Partner Finder)'
        })
    
    def search_by_zip(self, zip_code: str, radius_miles: int = 25) -> List[Dict[str, Any]]:
        """
        Search for nonprofits in a ZIP code area
        Returns list of basic nonprofit info with EINs
        """
        results = []
        
        # Use ProPublica's nonprofit API for initial search
        try:
            # Search by location
            search_url = f"{self.PROPUBLICA_API}/search.json"
            params = {
                'q': f'zip:{zip_code}',
                'state': self._get_state_from_zip(zip_code)
            }
            
            response = self.session.get(search_url, params=params)
            if response.status_code == 200:
                data = response.json()
                organizations = data.get('organizations', [])
                
                for org in organizations:
                    results.append({
                        'ein': org.get('ein'),
                        'name': org.get('name'),
                        'city': org.get('city'),
                        'state': org.get('state'),
                        'ntee_code': org.get('ntee_code'),
                        'subsection_code': org.get('subsection_code')
                    })
                    
            logger.info(f"Found {len(results)} nonprofits in ZIP {zip_code}")
            
        except Exception as e:
            logger.error(f"Error searching ProPublica API: {e}")
        
        return results
    
    def get_990_data(self, ein: str, years: List[int] = None) -> List[FinancialData]:
        """
        Retrieve 990 form data for a specific EIN
        """
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year - 3, current_year))
        
        financial_data = []
        
        for year in years:
            try:
                # Try ProPublica API first
                data = self._get_propublica_990(ein, year)
                if data:
                    financial_data.append(data)
                    continue
                
                # Fallback to direct 990 XML parsing
                data = self._parse_990_xml(ein, year)
                if data:
                    financial_data.append(data)
                    
            except Exception as e:
                logger.warning(f"Failed to get 990 data for EIN {ein}, year {year}: {e}")
        
        return financial_data
    
    def _get_propublica_990(self, ein: str, year: int) -> Optional[FinancialData]:
        """
        Get 990 data from ProPublica API
        """
        try:
            url = f"{self.PROPUBLICA_API}/organizations/{ein}.json"
            response = self.session.get(url)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            org = data.get('organization', {})
            
            # Find filing for specific year
            filings = org.get('filings_with_data', [])
            for filing in filings:
                if filing.get('tax_prd_yr') == year:
                    return self._parse_propublica_filing(filing, year)
            
        except Exception as e:
            logger.debug(f"ProPublica API error for EIN {ein}: {e}")
        
        return None
    
    def _parse_propublica_filing(self, filing: Dict, year: int) -> FinancialData:
        """
        Parse ProPublica filing data into FinancialData object
        """
        return FinancialData(
            year=year,
            total_revenue=filing.get('totrevenue', 0) or 0,
            total_expenses=filing.get('totfuncexpns', 0) or 0,
            total_assets=filing.get('totassetsend', 0) or 0,
            total_liabilities=filing.get('totliabend', 0) or 0,
            net_assets=filing.get('totnetassetend', 0) or 0,
            program_expenses=filing.get('progsvcs', 0) or 0,
            administrative_expenses=filing.get('mgmtandgen', 0) or 0,
            fundraising_expenses=filing.get('fundrasing', 0) or 0,
            source=DataSource.IRS_990
        )
    
    def _parse_990_xml(self, ein: str, year: int) -> Optional[FinancialData]:
        """
        Parse raw 990 XML from IRS
        """
        # This would connect to the actual IRS 990 XML data
        # For now, returning None as placeholder
        # Full implementation would download and parse XML files
        return None
    
    def get_nonprofit_details(self, ein: str) -> Optional[Nonprofit]:
        """
        Get comprehensive nonprofit details from IRS data
        """
        try:
            # Get basic info from ProPublica
            url = f"{self.PROPUBLICA_API}/organizations/{ein}.json"
            response = self.session.get(url)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            org = data.get('organization', {})
            
            # Create Address object
            address = Address(
                street=org.get('address', ''),
                city=org.get('city', ''),
                state=org.get('state', ''),
                zip_code=org.get('zipcode', '')
            )
            
            # Create Nonprofit object
            nonprofit = Nonprofit(
                ein=ein,
                name=org.get('name', ''),
                address=address,
                mission_statement=org.get('mission', '') or '',
                ntee_code=org.get('ntee_code'),
                year_founded=org.get('ruling_date')[:4] if org.get('ruling_date') else None,
                status=self._map_status(org.get('organization_status'))
            )
            
            # Add financial history
            nonprofit.financial_history = self.get_990_data(ein)
            nonprofit.data_sources.append(DataSource.IRS_990)
            
            return nonprofit
            
        except Exception as e:
            logger.error(f"Error getting nonprofit details for EIN {ein}: {e}")
            return None
    
    def _map_status(self, status_code: str) -> NonprofitStatus:
        """
        Map IRS status codes to our NonprofitStatus enum
        """
        status_map = {
            '01': NonprofitStatus.ACTIVE,
            '02': NonprofitStatus.SUSPENDED,
            '03': NonprofitStatus.INACTIVE,
        }
        return status_map.get(status_code, NonprofitStatus.UNKNOWN)
    
    def _get_state_from_zip(self, zip_code: str) -> str:
        """
        Get state abbreviation from ZIP code
        Simple mapping - would use proper ZIP code database in production
        """
        # Simplified ZIP to state mapping
        zip_prefix = zip_code[:3]
        
        # This is a simplified example - full implementation would use complete mapping
        zip_state_map = {
            '100': 'NY', '101': 'NY', '102': 'NY',  # New York
            '900': 'CA', '901': 'CA', '902': 'CA',  # California
            '600': 'IL', '601': 'IL', '602': 'IL',  # Illinois
            '750': 'TX', '751': 'TX', '752': 'TX',  # Texas
            '331': 'FL', '332': 'FL', '333': 'FL',  # Florida
        }
        
        return zip_state_map.get(zip_prefix, '')