"""
TIGER-based local nonprofit search API
Uses comprehensive ZIP to County mapping for accurate geographic filtering
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import our ZIP to County mapping
try:
    from data.zip_county_mapping import ZIP_COUNTY_MAP, get_location_from_zip, get_cities_in_county
except ImportError:
    ZIP_COUNTY_MAP = {}
    def get_location_from_zip(zip_code):
        return {'found': False}
    def get_cities_in_county(county, state):
        return []

# Simple cache
cache = {}
CACHE_DURATION = 3600

def get_cached_or_fetch(cache_key, fetch_func):
    """Simple caching mechanism"""
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_DURATION):
            return cached_data
    
    data = fetch_func()
    cache[cache_key] = (data, datetime.now())
    return data

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests with TIGER-based local search"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/tiger-search':
            params = parse_qs(parsed_path.query)
            query = params.get('q', [''])[0]
            
            if not query:
                self.send_error(400, "Missing search query")
                return
            
            results = self.tiger_search(query)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            return
        
        self.send_error(404, "Endpoint not found")
    
    def tiger_search(self, query):
        """Search using TIGER Census data mapping"""
        parts = query.split()
        
        # Check if first part is a ZIP code
        if parts and len(parts[0]) == 5 and parts[0].isdigit():
            zip_code = parts[0]
            keyword = ' '.join(parts[1:]) if len(parts) > 1 else 'nonprofit'
            
            # Get location from our comprehensive mapping
            location = get_location_from_zip(zip_code)
            
            if location['found']:
                return self.search_by_location(location, keyword, zip_code)
            else:
                # If ZIP not in our database, try Zippopotam as fallback
                return self.search_with_zippopotam_fallback(zip_code, keyword)
        else:
            # Regular keyword search
            return self.search_keyword(query)
    
    def search_by_location(self, location, keyword, zip_code):
        """Search for organizations in the specified location"""
        city = location['city']
        county = location['county']
        state = location['state']
        
        # Get all cities in the same county
        nearby_cities = get_cities_in_county(county, state)
        
        # Search ProPublica with state filter
        cache_key = f"search:{keyword}:{state}"
        
        def fetch_results():
            url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
            # Search broadly, then filter by location
            params = {'q': keyword}
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except:
                return {'organizations': []}
        
        data = get_cached_or_fetch(cache_key, fetch_results)
        
        # Filter and categorize results
        exact_city_results = []
        same_county_results = []
        same_state_results = []
        
        for org in data.get('organizations', []):
            org_city = org.get('city', '')
            org_state = org.get('state', '')
            
            org_data = {
                'ein': str(org['ein']),
                'name': org['name'],
                'city': org_city,
                'state': org_state,
                'ntee_code': org.get('ntee_code'),
                'score': org.get('score', 0),
                'subsection_code': org.get('subsectn_code'),
                'classification_codes': org.get('classification_codes', []),
                'ruling_date': org.get('ruling_date')
            }
            
            # Check for exact city match
            if city and city.lower() == org_city.lower():
                org_data['distance'] = f'Same City ({city})'
                org_data['match_quality'] = 100
                exact_city_results.append(org_data)
            # Check if in same county (any nearby city)
            elif org_city in nearby_cities:
                org_data['distance'] = f'Same County ({county})'
                org_data['match_quality'] = 80
                same_county_results.append(org_data)
            # Check if same state
            elif org_state == state:
                org_data['distance'] = f'Same State ({state})'
                org_data['match_quality'] = 50
                same_state_results.append(org_data)
        
        # Sort each group by ProPublica's relevance score
        exact_city_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        same_county_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        same_state_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Combine results prioritizing local
        all_results = exact_city_results[:10] + same_county_results[:8] + same_state_results[:2]
        
        return {
            'query': f"{zip_code} {keyword}",
            'location': {
                'zip': zip_code,
                'city': city,
                'county': county,
                'state': state,
                'nearby_cities': nearby_cities[:10]  # Show first 10 nearby cities
            },
            'counts': {
                'exact_city': len(exact_city_results),
                'same_county': len(same_county_results),
                'same_state': len(same_state_results),
                'total': len(data.get('organizations', []))
            },
            'results': all_results,
            'message': self.generate_message(
                len(exact_city_results), 
                len(same_county_results), 
                city, 
                county, 
                keyword
            )
        }
    
    def search_with_zippopotam_fallback(self, zip_code, keyword):
        """Fallback to Zippopotam API if ZIP not in our database"""
        cache_key = f"zip:{zip_code}"
        
        def fetch_zip():
            try:
                response = requests.get(f"http://api.zippopotam.us/us/{zip_code}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('places'):
                        place = data['places'][0]
                        return {
                            'city': place['place name'],
                            'state': place['state'],
                            'state_abbr': place['state abbreviation']
                        }
            except:
                pass
            return None
        
        zip_info = get_cached_or_fetch(cache_key, fetch_zip)
        
        if zip_info:
            # Search with city and state
            cache_key = f"search:{keyword}:{zip_info['state_abbr']}"
            
            def fetch_results():
                url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
                params = {'q': f"{keyword} {zip_info['city']} {zip_info['state_abbr']}"}
                
                try:
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    return response.json()
                except:
                    return {'organizations': []}
            
            data = get_cached_or_fetch(cache_key, fetch_results)
            
            results = []
            for org in data.get('organizations', [])[:20]:
                org_city = org.get('city', '')
                org_state = org.get('state', '')
                
                # Calculate basic distance
                if zip_info['city'].lower() in org_city.lower():
                    distance = 'Local'
                    match_quality = 90
                elif org_state == zip_info['state_abbr']:
                    distance = f"Same State ({zip_info['state_abbr']})"
                    match_quality = 50
                else:
                    distance = 'National'
                    match_quality = 25
                
                results.append({
                    'ein': str(org['ein']),
                    'name': org['name'],
                    'city': org_city,
                    'state': org_state,
                    'ntee_code': org.get('ntee_code'),
                    'distance': distance,
                    'match_quality': match_quality
                })
            
            # Sort by match quality
            results.sort(key=lambda x: x['match_quality'], reverse=True)
            
            return {
                'query': f"{zip_code} {keyword}",
                'location': {
                    'zip': zip_code,
                    'city': zip_info['city'],
                    'state': zip_info['state'],
                    'note': 'ZIP code not in TIGER database, using approximate location'
                },
                'results': results,
                'message': f"Results for '{keyword}' near {zip_info['city']}, {zip_info['state_abbr']}"
            }
        else:
            # Fallback to keyword search
            return self.search_keyword(keyword)
    
    def search_keyword(self, keyword):
        """Regular keyword search without location filtering"""
        url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
        params = {'q': keyword}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for org in data.get('organizations', [])[:20]:
                results.append({
                    'ein': str(org['ein']),
                    'name': org['name'],
                    'city': org.get('city', ''),
                    'state': org.get('state', ''),
                    'ntee_code': org.get('ntee_code'),
                    'distance': 'National Search'
                })
            
            return {
                'query': keyword,
                'results': results,
                'message': f"Found {len(results)} organizations matching '{keyword}' nationwide"
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'results': []
            }
    
    def generate_message(self, exact_count, county_count, city, county, keyword):
        """Generate helpful message about results"""
        if exact_count > 0:
            return f"Found {exact_count} '{keyword}' organizations in {city}"
        elif county_count > 0:
            return f"Found {county_count} '{keyword}' organizations in {county}"
        else:
            return f"No local '{keyword}' organizations found. Showing statewide results"
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()