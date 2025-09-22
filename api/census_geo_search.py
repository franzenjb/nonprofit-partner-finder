"""
Census TIGER-based geographic search for nonprofits
Uses Census Bureau data for accurate ZIP to county mapping
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import csv
import io

# Cache for API responses
cache = {}
CACHE_DURATION = 3600

# Census Geocoding API
CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/address"

def get_cached_or_fetch(cache_key, fetch_func):
    """Simple caching mechanism"""
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_DURATION):
            return cached_data
    
    data = fetch_func()
    cache[cache_key] = (data, datetime.now())
    return data

def get_county_from_zip(zip_code):
    """Get county info from ZIP using Census Geocoding API"""
    cache_key = f"census_zip:{zip_code}"
    
    def fetch_census_data():
        try:
            # First try to get city/state from Zippopotam
            zip_response = requests.get(f"http://api.zippopotam.us/us/{zip_code}", timeout=5)
            if zip_response.status_code == 200:
                zip_data = zip_response.json()
                if zip_data.get('places'):
                    place = zip_data['places'][0]
                    city = place['place name']
                    state = place['state']
                    state_abbr = place['state abbreviation']
                    
                    # Now get county from Census API using city/state
                    params = {
                        'benchmark': 'Public_AR_Current',
                        'vintage': 'Current_Current',
                        'city': city,
                        'state': state_abbr,
                        'format': 'json'
                    }
                    
                    census_response = requests.get(
                        "https://geocoding.geo.census.gov/geocoder/geographies/address",
                        params=params,
                        timeout=10
                    )
                    
                    if census_response.status_code == 200:
                        census_data = census_response.json()
                        if census_data.get('result', {}).get('addressMatches'):
                            match = census_data['result']['addressMatches'][0]
                            geographies = match.get('geographies', {})
                            counties = geographies.get('Counties', [])
                            if counties:
                                county_name = counties[0].get('NAME', '')
                                return {
                                    'city': city,
                                    'state': state,
                                    'state_abbr': state_abbr,
                                    'county': county_name,
                                    'fips': counties[0].get('GEOID', '')
                                }
                    
                    # Fallback if Census API doesn't work
                    return {
                        'city': city,
                        'state': state,
                        'state_abbr': state_abbr,
                        'county': None
                    }
        except Exception as e:
            print(f"Error fetching census data: {e}")
        
        return None
    
    return get_cached_or_fetch(cache_key, fetch_census_data)

def get_nearby_zips(county_name, state_abbr):
    """Get all ZIP codes in the same county"""
    # For now, return empty list - would need full TIGER data file
    # In production, this would query a database of ZIP-to-county mappings
    return []

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests with Census-based geographic search"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/census-search':
            params = parse_qs(parsed_path.query)
            query = params.get('q', [''])[0]
            
            if not query:
                self.send_error(400, "Missing search query")
                return
            
            results = self.census_search(query)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            return
        
        self.send_error(404, "Endpoint not found")
    
    def census_search(self, query):
        """Search using Census geographic data"""
        parts = query.split()
        
        # Check if first part is a ZIP code
        if parts and len(parts[0]) == 5 and parts[0].isdigit():
            zip_code = parts[0]
            keyword = ' '.join(parts[1:]) if len(parts) > 1 else 'nonprofit'
            
            # Get county from Census data
            geo_info = get_county_from_zip(zip_code)
            
            if geo_info:
                return self.search_by_county(geo_info, keyword, zip_code)
            else:
                # Fallback to keyword search
                return self.search_keyword(query)
        else:
            # Regular keyword search
            return self.search_keyword(query)
    
    def search_by_county(self, geo_info, keyword, zip_code):
        """Search for organizations in the county"""
        city = geo_info.get('city', '')
        state = geo_info.get('state', '')
        state_abbr = geo_info.get('state_abbr', '')
        county = geo_info.get('county', 'Unknown')
        
        # Search ProPublica with state filter
        cache_key = f"search:{keyword}:{state_abbr}"
        
        def fetch_results():
            url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
            # Include state in search to narrow results
            params = {'q': f"{keyword} {state_abbr}"}
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except:
                return {'organizations': []}
        
        data = get_cached_or_fetch(cache_key, fetch_results)
        
        # Filter results by location
        local_results = []
        county_results = []
        state_results = []
        
        for org in data.get('organizations', []):
            org_city = org.get('city', '')
            org_state = org.get('state', '')
            
            org_data = {
                'ein': str(org['ein']),
                'name': org['name'],
                'city': org_city,
                'state': org_state,
                'ntee_code': org.get('ntee_code'),
                'score': org.get('score', 0)
            }
            
            # Prioritize by location match
            if city and city.lower() in org_city.lower():
                org_data['distance'] = 'Same City'
                org_data['match_quality'] = 100
                local_results.append(org_data)
            elif county and county != 'Unknown' and self.is_likely_same_county(org_city, city, state_abbr):
                org_data['distance'] = f'Same County ({county})'
                org_data['match_quality'] = 75
                county_results.append(org_data)
            elif org_state == state_abbr:
                org_data['distance'] = f'Same State ({state_abbr})'
                org_data['match_quality'] = 50
                state_results.append(org_data)
        
        # Sort each group by ProPublica's relevance score
        local_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        county_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        state_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Combine results with local first
        all_results = local_results[:10] + county_results[:5] + state_results[:5]
        
        return {
            'query': f"{zip_code} {keyword}",
            'location': {
                'zip': zip_code,
                'city': city,
                'county': county,
                'state': state,
                'state_abbr': state_abbr
            },
            'counts': {
                'local': len(local_results),
                'county': len(county_results),
                'state': len(state_results),
                'total': len(data.get('organizations', []))
            },
            'results': all_results,
            'message': self.generate_message(len(local_results), len(county_results), city, county, keyword)
        }
    
    def is_likely_same_county(self, org_city, search_city, state):
        """Heuristic to guess if cities are in same county"""
        # Major metro areas where nearby cities are likely same county
        metro_areas = {
            'TX': {
                'Dallas': ['Richardson', 'Plano', 'Irving', 'Garland', 'Mesquite', 'Addison'],
                'Houston': ['Pasadena', 'Sugar Land', 'Katy', 'Spring', 'The Woodlands'],
                'Fort Worth': ['Arlington', 'Euless', 'Bedford', 'North Richland Hills'],
            },
            'FL': {
                'St Petersburg': ['Clearwater', 'Largo', 'Pinellas Park', 'Seminole'],
                'Miami': ['Miami Beach', 'Coral Gables', 'Hialeah', 'Aventura'],
                'Tampa': ['Brandon', 'Riverview', 'Plant City', 'Temple Terrace'],
            },
            'CA': {
                'Los Angeles': ['Hollywood', 'Beverly Hills', 'Santa Monica', 'Pasadena'],
                'San Diego': ['Chula Vista', 'Oceanside', 'Carlsbad', 'El Cajon'],
            }
        }
        
        state_metros = metro_areas.get(state, {})
        for metro_city, nearby_cities in state_metros.items():
            if search_city.lower() == metro_city.lower() or search_city in nearby_cities:
                if org_city in nearby_cities or org_city.lower() == metro_city.lower():
                    return True
        
        return False
    
    def search_keyword(self, keyword):
        """Regular keyword search"""
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
                'message': f"Found {len(results)} organizations matching '{keyword}'"
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'results': []
            }
    
    def generate_message(self, local_count, county_count, city, county, keyword):
        """Generate helpful message about results"""
        if local_count > 0:
            return f"Found {local_count} '{keyword}' organizations in {city}"
        elif county_count > 0:
            return f"Found {county_count} '{keyword}' organizations in {county}"
        elif county != 'Unknown':
            return f"No '{keyword}' organizations found locally. Showing statewide results"
        else:
            return f"Showing best matches for '{keyword}'"
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()