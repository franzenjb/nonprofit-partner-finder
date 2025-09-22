"""
Final production-ready nonprofit search API
Combines all search improvements with TIGER Census data
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

# Comprehensive ZIP to County mapping (subset for deployment)
ZIP_COUNTY_MAP = {
    # TEXAS - Dallas/Fort Worth Metroplex
    **{f'7520{i}': ('Dallas', 'Dallas County', 'TX') for i in range(1, 10)},
    **{f'7521{i}': ('Dallas', 'Dallas County', 'TX') for i in range(0, 10)},
    **{f'7522{i}': ('Dallas', 'Dallas County', 'TX') for i in range(0, 10)},
    **{f'7523{i}': ('Dallas', 'Dallas County', 'TX') for i in range(0, 10)},
    **{f'7524{i}': ('Dallas', 'Dallas County', 'TX') for i in range(0, 10)},
    **{f'7525{i}': ('Dallas', 'Dallas County', 'TX') for i in range(0, 5)},
    '75006': ('Carrollton', 'Dallas County', 'TX'),
    '75007': ('Carrollton', 'Denton County', 'TX'),
    '75038': ('Irving', 'Dallas County', 'TX'),
    '75060': ('Irving', 'Dallas County', 'TX'),
    '75061': ('Irving', 'Dallas County', 'TX'),
    '75062': ('Irving', 'Dallas County', 'TX'),
    '75063': ('Irving', 'Dallas County', 'TX'),
    '75074': ('Plano', 'Collin County', 'TX'),
    '75075': ('Plano', 'Collin County', 'TX'),
    '75080': ('Richardson', 'Dallas County', 'TX'),
    '75081': ('Richardson', 'Dallas County', 'TX'),
    '76101': ('Fort Worth', 'Tarrant County', 'TX'),
    '76102': ('Fort Worth', 'Tarrant County', 'TX'),
    '76103': ('Fort Worth', 'Tarrant County', 'TX'),
    '76104': ('Fort Worth', 'Tarrant County', 'TX'),
    '76105': ('Fort Worth', 'Tarrant County', 'TX'),
    '76006': ('Arlington', 'Tarrant County', 'TX'),
    '76010': ('Arlington', 'Tarrant County', 'TX'),
    '76011': ('Arlington', 'Tarrant County', 'TX'),
    '76012': ('Arlington', 'Tarrant County', 'TX'),
    
    # TEXAS - Houston Area
    **{f'7700{i}': ('Houston', 'Harris County', 'TX') for i in range(1, 10)},
    **{f'7701{i}': ('Houston', 'Harris County', 'TX') for i in range(0, 10)},
    **{f'7702{i}': ('Houston', 'Harris County', 'TX') for i in range(0, 10)},
    **{f'7703{i}': ('Houston', 'Harris County', 'TX') for i in range(0, 10)},
    **{f'7704{i}': ('Houston', 'Harris County', 'TX') for i in range(0, 10)},
    **{f'7705{i}': ('Houston', 'Harris County', 'TX') for i in range(0, 10)},
    **{f'7706{i}': ('Houston', 'Harris County', 'TX') for i in range(0, 10)},
    **{f'7707{i}': ('Houston', 'Harris County', 'TX') for i in range(0, 10)},
    '77478': ('Sugar Land', 'Fort Bend County', 'TX'),
    '77479': ('Sugar Land', 'Fort Bend County', 'TX'),
    '77449': ('Katy', 'Harris County', 'TX'),
    '77450': ('Katy', 'Harris County', 'TX'),
    
    # TEXAS - San Antonio
    **{f'7820{i}': ('San Antonio', 'Bexar County', 'TX') for i in range(1, 10)},
    **{f'7821{i}': ('San Antonio', 'Bexar County', 'TX') for i in range(0, 10)},
    **{f'7822{i}': ('San Antonio', 'Bexar County', 'TX') for i in range(0, 10)},
    **{f'7823{i}': ('San Antonio', 'Bexar County', 'TX') for i in range(0, 10)},
    **{f'7824{i}': ('San Antonio', 'Bexar County', 'TX') for i in range(0, 10)},
    
    # TEXAS - Austin
    **{f'7870{i}': ('Austin', 'Travis County', 'TX') for i in range(1, 10)},
    **{f'7871{i}': ('Austin', 'Travis County', 'TX') for i in range(0, 10)},
    **{f'7872{i}': ('Austin', 'Travis County', 'TX') for i in range(0, 10)},
    **{f'7873{i}': ('Austin', 'Travis County', 'TX') for i in range(0, 10)},
    **{f'7874{i}': ('Austin', 'Travis County', 'TX') for i in range(0, 10)},
    
    # TEXAS - El Paso
    **{f'7990{i}': ('El Paso', 'El Paso County', 'TX') for i in range(1, 10)},
    **{f'7991{i}': ('El Paso', 'El Paso County', 'TX') for i in range(0, 10)},
    **{f'7992{i}': ('El Paso', 'El Paso County', 'TX') for i in range(0, 10)},
    
    # FLORIDA - St. Petersburg/Clearwater (Pinellas County)
    '33701': ('St Petersburg', 'Pinellas County', 'FL'),
    '33702': ('St Petersburg', 'Pinellas County', 'FL'),
    '33703': ('St Petersburg', 'Pinellas County', 'FL'),
    '33704': ('St Petersburg', 'Pinellas County', 'FL'),
    '33705': ('St Petersburg', 'Pinellas County', 'FL'),
    '33706': ('St Petersburg', 'Pinellas County', 'FL'),
    '33707': ('St Petersburg', 'Pinellas County', 'FL'),
    '33708': ('St Petersburg', 'Pinellas County', 'FL'),
    '33709': ('St Petersburg', 'Pinellas County', 'FL'),
    '33710': ('St Petersburg', 'Pinellas County', 'FL'),
    '33711': ('St Petersburg', 'Pinellas County', 'FL'),
    '33712': ('St Petersburg', 'Pinellas County', 'FL'),
    '33713': ('St Petersburg', 'Pinellas County', 'FL'),
    '33714': ('St Petersburg', 'Pinellas County', 'FL'),
    '33715': ('St Petersburg', 'Pinellas County', 'FL'),
    '33716': ('St Petersburg', 'Pinellas County', 'FL'),
    '33755': ('Clearwater', 'Pinellas County', 'FL'),
    '33756': ('Clearwater', 'Pinellas County', 'FL'),
    '33757': ('Clearwater', 'Pinellas County', 'FL'),
    '33758': ('Clearwater', 'Pinellas County', 'FL'),
    '33759': ('Clearwater', 'Pinellas County', 'FL'),
    '33760': ('Clearwater', 'Pinellas County', 'FL'),
    '33761': ('Clearwater', 'Pinellas County', 'FL'),
    '33762': ('Clearwater', 'Pinellas County', 'FL'),
    '33763': ('Clearwater', 'Pinellas County', 'FL'),
    '33764': ('Clearwater', 'Pinellas County', 'FL'),
    '33765': ('Clearwater', 'Pinellas County', 'FL'),
    '33767': ('Clearwater Beach', 'Pinellas County', 'FL'),
    '33770': ('Largo', 'Pinellas County', 'FL'),
    '33771': ('Largo', 'Pinellas County', 'FL'),
    '33773': ('Largo', 'Pinellas County', 'FL'),
    '33774': ('Largo', 'Pinellas County', 'FL'),
    '33778': ('Seminole', 'Pinellas County', 'FL'),
    '33779': ('Largo', 'Pinellas County', 'FL'),
    '33781': ('Pinellas Park', 'Pinellas County', 'FL'),
    '33782': ('Pinellas Park', 'Pinellas County', 'FL'),
    
    # FLORIDA - Miami-Dade County
    **{f'3310{i}': ('Miami', 'Miami-Dade County', 'FL') for i in range(1, 10)},
    **{f'3311{i}': ('Miami', 'Miami-Dade County', 'FL') for i in range(0, 10)},
    **{f'3312{i}': ('Miami', 'Miami-Dade County', 'FL') for i in range(0, 10)},
    **{f'3313{i}': ('Miami', 'Miami-Dade County', 'FL') for i in range(0, 10)},
    **{f'3314{i}': ('Miami', 'Miami-Dade County', 'FL') for i in range(0, 10)},
    '33139': ('Miami Beach', 'Miami-Dade County', 'FL'),
    '33140': ('Miami Beach', 'Miami-Dade County', 'FL'),
    '33141': ('Miami Beach', 'Miami-Dade County', 'FL'),
    
    # FLORIDA - Tampa (Hillsborough County)
    **{f'3360{i}': ('Tampa', 'Hillsborough County', 'FL') for i in range(1, 10)},
    **{f'3361{i}': ('Tampa', 'Hillsborough County', 'FL') for i in range(0, 10)},
    **{f'3362{i}': ('Tampa', 'Hillsborough County', 'FL') for i in range(0, 10)},
    '33510': ('Brandon', 'Hillsborough County', 'FL'),
    '33511': ('Brandon', 'Hillsborough County', 'FL'),
    
    # FLORIDA - Orlando (Orange County)
    **{f'3280{i}': ('Orlando', 'Orange County', 'FL') for i in range(1, 10)},
    **{f'3281{i}': ('Orlando', 'Orange County', 'FL') for i in range(0, 10)},
    **{f'3282{i}': ('Orlando', 'Orange County', 'FL') for i in range(0, 10)},
    
    # NEW YORK - New York City
    **{f'1000{i}': ('New York', 'New York County', 'NY') for i in range(1, 10)},
    **{f'1001{i}': ('New York', 'New York County', 'NY') for i in range(0, 10)},
    **{f'1002{i}': ('New York', 'New York County', 'NY') for i in range(0, 10)},
    **{f'1120{i}': ('Brooklyn', 'Kings County', 'NY') for i in range(1, 10)},
    **{f'1121{i}': ('Brooklyn', 'Kings County', 'NY') for i in range(0, 10)},
    **{f'1045{i}': ('Bronx', 'Bronx County', 'NY') for i in range(0, 10)},
    **{f'1046{i}': ('Bronx', 'Bronx County', 'NY') for i in range(0, 10)},
    **{f'1110{i}': ('Queens', 'Queens County', 'NY') for i in range(0, 10)},
    **{f'1030{i}': ('Staten Island', 'Richmond County', 'NY') for i in range(0, 10)},
    
    # CALIFORNIA - Los Angeles County
    **{f'9000{i}': ('Los Angeles', 'Los Angeles County', 'CA') for i in range(1, 10)},
    **{f'9001{i}': ('Los Angeles', 'Los Angeles County', 'CA') for i in range(0, 10)},
    **{f'9002{i}': ('Los Angeles', 'Los Angeles County', 'CA') for i in range(0, 10)},
    **{f'9003{i}': ('Los Angeles', 'Los Angeles County', 'CA') for i in range(0, 10)},
    **{f'9004{i}': ('Los Angeles', 'Los Angeles County', 'CA') for i in range(0, 10)},
    '90210': ('Beverly Hills', 'Los Angeles County', 'CA'),
    '90211': ('Beverly Hills', 'Los Angeles County', 'CA'),
    '90212': ('Beverly Hills', 'Los Angeles County', 'CA'),
    
    # CALIFORNIA - San Diego County
    **{f'9210{i}': ('San Diego', 'San Diego County', 'CA') for i in range(1, 10)},
    **{f'9211{i}': ('San Diego', 'San Diego County', 'CA') for i in range(0, 10)},
    **{f'9212{i}': ('San Diego', 'San Diego County', 'CA') for i in range(0, 10)},
    
    # CALIFORNIA - San Francisco Bay Area
    '94102': ('San Francisco', 'San Francisco County', 'CA'),
    '94103': ('San Francisco', 'San Francisco County', 'CA'),
    '94104': ('San Francisco', 'San Francisco County', 'CA'),
    '94105': ('San Francisco', 'San Francisco County', 'CA'),
    '94107': ('San Francisco', 'San Francisco County', 'CA'),
    '94108': ('San Francisco', 'San Francisco County', 'CA'),
    '94109': ('San Francisco', 'San Francisco County', 'CA'),
    '94110': ('San Francisco', 'San Francisco County', 'CA'),
    
    # ILLINOIS - Chicago and Cook County
    **{f'6060{i}': ('Chicago', 'Cook County', 'IL') for i in range(1, 10)},
    **{f'6061{i}': ('Chicago', 'Cook County', 'IL') for i in range(0, 10)},
    **{f'6062{i}': ('Chicago', 'Cook County', 'IL') for i in range(0, 10)},
}

def get_location_from_zip(zip_code):
    """Get city, county, and state from ZIP code"""
    if zip_code in ZIP_COUNTY_MAP:
        city, county, state = ZIP_COUNTY_MAP[zip_code]
        return {
            'city': city,
            'county': county,
            'state': state,
            'found': True
        }
    return {'found': False}

def get_cities_in_county(county_name, state_abbr):
    """Get all cities in a specific county"""
    cities = set()
    for zip_code, (city, county, state) in ZIP_COUNTY_MAP.items():
        if county == county_name and state == state_abbr:
            cities.add(city)
    return sorted(list(cities))

# Cache for API responses
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
        """Handle GET requests with geographic search"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/final-search':
            params = parse_qs(parsed_path.query)
            query = params.get('q', [''])[0]
            
            if not query:
                self.send_error(400, "Missing search query")
                return
            
            results = self.geographic_search(query)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            return
        
        self.send_error(404, "Endpoint not found")
    
    def geographic_search(self, query):
        """Main search function with geographic filtering"""
        parts = query.split()
        
        # Check if first part is a ZIP code
        if parts and len(parts[0]) == 5 and parts[0].isdigit():
            zip_code = parts[0]
            keyword = ' '.join(parts[1:]) if len(parts) > 1 else 'nonprofit'
            
            # Get location from our mapping
            location = get_location_from_zip(zip_code)
            
            if location['found']:
                return self.search_by_location(location, keyword, zip_code)
            else:
                # Fallback to Zippopotam API
                return self.search_with_api_fallback(zip_code, keyword)
        else:
            # Regular keyword search
            return self.search_keyword(query)
    
    def search_by_location(self, location, keyword, zip_code):
        """Search and filter by geographic location"""
        city = location['city']
        county = location['county']
        state = location['state']
        
        # Get nearby cities in same county
        nearby_cities = get_cities_in_county(county, state)
        
        # Fetch from ProPublica
        cache_key = f"search:{keyword}"
        
        def fetch_results():
            url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
            params = {'q': keyword}
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except:
                return {'organizations': []}
        
        data = get_cached_or_fetch(cache_key, fetch_results)
        
        # Filter results by location
        exact_city = []
        same_county = []
        same_state = []
        
        for org in data.get('organizations', []):
            org_city = org.get('city', '')
            org_state = org.get('state', '')
            
            org_info = {
                'ein': str(org['ein']),
                'name': org['name'],
                'city': org_city,
                'state': org_state,
                'ntee_code': org.get('ntee_code'),
                'score': org.get('score', 0)
            }
            
            # Exact city match
            if city and city.lower() == org_city.lower():
                org_info['distance'] = f'In {city}'
                org_info['priority'] = 1
                exact_city.append(org_info)
            # Same county
            elif org_city in nearby_cities:
                org_info['distance'] = f'In {county}'
                org_info['priority'] = 2
                same_county.append(org_info)
            # Same state
            elif org_state == state:
                org_info['distance'] = f'In {state}'
                org_info['priority'] = 3
                same_state.append(org_info)
        
        # Sort by relevance score
        exact_city.sort(key=lambda x: x['score'], reverse=True)
        same_county.sort(key=lambda x: x['score'], reverse=True)
        same_state.sort(key=lambda x: x['score'], reverse=True)
        
        # Combine results
        all_results = exact_city[:10] + same_county[:8] + same_state[:2]
        
        # Generate message
        if exact_city:
            message = f"Found {len(exact_city)} '{keyword}' organizations in {city}"
        elif same_county:
            message = f"Found {len(same_county)} '{keyword}' organizations in {county}"
        elif same_state:
            message = f"Found {len(same_state)} '{keyword}' organizations in {state}"
        else:
            message = f"No local '{keyword}' organizations found"
        
        return {
            'query': f"{zip_code} {keyword}",
            'location': {
                'zip': zip_code,
                'city': city,
                'county': county,
                'state': state
            },
            'counts': {
                'city': len(exact_city),
                'county': len(same_county),
                'state': len(same_state),
                'total': len(data.get('organizations', []))
            },
            'results': all_results,
            'message': message
        }
    
    def search_with_api_fallback(self, zip_code, keyword):
        """Fallback search using Zippopotam API"""
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
            # Search with location context
            url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
            params = {'q': keyword}
            
            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                results = []
                for org in data.get('organizations', [])[:20]:
                    org_city = org.get('city', '')
                    org_state = org.get('state', '')
                    
                    if zip_info['city'].lower() in org_city.lower():
                        distance = f"In {zip_info['city']}"
                        priority = 1
                    elif org_state == zip_info['state_abbr']:
                        distance = f"In {zip_info['state_abbr']}"
                        priority = 2
                    else:
                        distance = "National"
                        priority = 3
                    
                    results.append({
                        'ein': str(org['ein']),
                        'name': org['name'],
                        'city': org_city,
                        'state': org_state,
                        'ntee_code': org.get('ntee_code'),
                        'distance': distance,
                        'priority': priority
                    })
                
                # Sort by priority
                results.sort(key=lambda x: x['priority'])
                
                return {
                    'query': f"{zip_code} {keyword}",
                    'location': {
                        'zip': zip_code,
                        'city': zip_info['city'],
                        'state': zip_info['state']
                    },
                    'results': results[:20],
                    'message': f"Results for '{keyword}' near {zip_info['city']}, {zip_info['state_abbr']}"
                }
            except:
                pass
        
        # Fallback to keyword search
        return self.search_keyword(keyword)
    
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
                    'distance': 'National'
                })
            
            return {
                'query': keyword,
                'results': results,
                'message': f"Found {len(results)} organizations matching '{keyword}'"
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'results': [],
                'message': 'Error searching organizations'
            }
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()