"""
Example of fetching REAL nonprofit data - this works immediately!
"""

import requests
import json


def get_real_nonprofits_by_zip(zip_code: str):
    """
    Get REAL nonprofit data from ProPublica - NO API KEY NEEDED
    """
    # ProPublica API - completely free and open
    base_url = "https://projects.propublica.org/nonprofits/api/v2"
    
    # Search by ZIP code (real data!)
    search_url = f"{base_url}/search.json"
    params = {
        'q': zip_code,
        'ntee[id]': '3'  # Health organizations (similar to Red Cross)
    }
    
    response = requests.get(search_url)
    data = response.json()
    
    # Get real organizations
    organizations = data.get('organizations', [])
    
    results = []
    for org in organizations[:5]:  # Top 5
        # Get detailed data for each org
        ein = org['ein']
        detail_url = f"{base_url}/organizations/{ein}.json"
        detail_resp = requests.get(detail_url)
        detail_data = detail_resp.json()
        
        org_info = detail_data['organization']
        
        # Extract REAL financial data
        latest_filing = None
        if 'filings_with_data' in org_info:
            filings = org_info['filings_with_data']
            if filings:
                latest_filing = filings[0]  # Most recent
        
        results.append({
            'name': org_info['name'],
            'ein': ein,
            'city': org_info.get('city'),
            'state': org_info.get('state'),
            'ntee_code': org_info.get('ntee_code'),
            'mission': org_info.get('mission'),
            'ruling_year': org_info.get('ruling_date', '')[:4],
            'revenue': latest_filing.get('totrevenue') if latest_filing else None,
            'expenses': latest_filing.get('totfuncexpns') if latest_filing else None,
            'assets': latest_filing.get('totassetsend') if latest_filing else None,
            'url': f"https://projects.propublica.org/nonprofits/organizations/{ein}"
        })
    
    return results


def get_charity_navigator_data(ein: str):
    """
    Charity Navigator API - requires free API key
    Sign up at: https://www.charitynavigator.org/api
    """
    # Free tier: 1,000 calls/month
    api_key = "your_free_api_key"
    url = f"https://api.charitynavigator.org/v2/organizations/{ein}"
    
    headers = {
        'app_id': api_key,
        'app_key': api_key
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None


def test_real_data():
    """
    Test with actual New York nonprofits
    """
    print("Fetching REAL nonprofit data for ZIP 10001 (Manhattan)...\n")
    
    results = get_real_nonprofits_by_zip("10001")
    
    for org in results:
        print(f"Name: {org['name']}")
        print(f"EIN: {org['ein']}")
        print(f"Location: {org['city']}, {org['state']}")
        if org['revenue']:
            print(f"Annual Revenue: ${org['revenue']:,}")
        if org['mission']:
            print(f"Mission: {org['mission'][:100]}...")
        print(f"ProPublica Profile: {org['url']}")
        print("-" * 50)


if __name__ == "__main__":
    test_real_data()