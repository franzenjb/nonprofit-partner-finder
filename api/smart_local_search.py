"""
Smart local search using Zippopotam.us API for ZIP to city mapping
Then filters ProPublica results to show only local organizations
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

# City to County mapping (major cities)
# This covers the most common searches
CITY_TO_COUNTY = {
    # Texas
    'Dallas': {'county': 'Dallas County', 'state': 'TX', 'nearby': ['Richardson', 'Plano', 'Irving', 'Garland', 'Mesquite', 'Carrollton', 'Grand Prairie', 'Addison', 'Farmers Branch']},
    'Houston': {'county': 'Harris County', 'state': 'TX', 'nearby': ['Pasadena', 'Baytown', 'Sugar Land', 'Katy', 'Spring', 'Cypress', 'The Woodlands', 'Humble']},
    'San Antonio': {'county': 'Bexar County', 'state': 'TX', 'nearby': ['Alamo Heights', 'Leon Valley', 'Converse', 'Live Oak', 'Universal City', 'Schertz', 'Selma']},
    'Austin': {'county': 'Travis County', 'state': 'TX', 'nearby': ['Round Rock', 'Cedar Park', 'Pflugerville', 'Georgetown', 'Leander', 'Manor', 'Bee Cave']},
    'El Paso': {'county': 'El Paso County', 'state': 'TX', 'nearby': ['Socorro', 'Horizon City', 'San Elizario', 'Clint', 'Anthony']},
    'Fort Worth': {'county': 'Tarrant County', 'state': 'TX', 'nearby': ['Arlington', 'North Richland Hills', 'Euless', 'Bedford', 'Haltom City', 'Keller', 'Southlake']},
    
    # Florida  
    'Saint Petersburg': {'county': 'Pinellas County', 'state': 'FL', 'nearby': ['St Petersburg', 'Clearwater', 'Largo', 'Pinellas Park', 'Seminole', 'Dunedin', 'Tarpon Springs', 'Safety Harbor', 'Gulfport']},
    'St Petersburg': {'county': 'Pinellas County', 'state': 'FL', 'nearby': ['Saint Petersburg', 'Clearwater', 'Largo', 'Pinellas Park', 'Seminole', 'Dunedin', 'Tarpon Springs', 'Safety Harbor', 'Gulfport']},
    'Clearwater': {'county': 'Pinellas County', 'state': 'FL', 'nearby': ['St Petersburg', 'Largo', 'Dunedin', 'Safety Harbor', 'Tarpon Springs', 'Palm Harbor', 'Oldsmar']},
    'Largo': {'county': 'Pinellas County', 'state': 'FL', 'nearby': ['St Petersburg', 'Clearwater', 'Pinellas Park', 'Seminole', 'Indian Rocks Beach']},
    'Miami': {'county': 'Miami-Dade County', 'state': 'FL', 'nearby': ['Miami Beach', 'Coral Gables', 'Hialeah', 'Aventura', 'Doral', 'Homestead', 'Cutler Bay', 'Miami Lakes', 'North Miami', 'Key Biscayne']},
    'Miami Beach': {'county': 'Miami-Dade County', 'state': 'FL', 'nearby': ['Miami', 'South Beach', 'North Beach', 'Surfside', 'Bal Harbour', 'Bay Harbor Islands']},
    'Orlando': {'county': 'Orange County', 'state': 'FL', 'nearby': ['Winter Park', 'Apopka', 'Ocoee', 'Winter Garden', 'Maitland', 'Altamonte Springs', 'Casselberry']},
    'Tampa': {'county': 'Hillsborough County', 'state': 'FL', 'nearby': ['Brandon', 'Riverview', 'Plant City', 'Temple Terrace', 'Carrollwood', 'Westchase']},
    'Jacksonville': {'county': 'Duval County', 'state': 'FL', 'nearby': ['Jacksonville Beach', 'Neptune Beach', 'Atlantic Beach', 'Orange Park', 'Ponte Vedra Beach']},
    
    # New York
    'New York': {'county': 'New York County', 'state': 'NY', 'nearby': ['Manhattan', 'Brooklyn', 'Bronx', 'Queens', 'Staten Island']},
    'Manhattan': {'county': 'New York County', 'state': 'NY', 'nearby': ['New York', 'Upper West Side', 'Upper East Side', 'Midtown', 'Chelsea', 'Greenwich Village', 'Harlem', 'Lower East Side']},
    'Brooklyn': {'county': 'Kings County', 'state': 'NY', 'nearby': ['New York', 'Park Slope', 'Williamsburg', 'Brooklyn Heights', 'Flatbush', 'Bay Ridge', 'Bensonhurst']},
    'Bronx': {'county': 'Bronx County', 'state': 'NY', 'nearby': ['New York', 'Riverdale', 'Fordham', 'Pelham Bay', 'Morris Park', 'Throggs Neck']},
    'Queens': {'county': 'Queens County', 'state': 'NY', 'nearby': ['New York', 'Flushing', 'Jamaica', 'Astoria', 'Forest Hills', 'Jackson Heights', 'Corona']},
    
    # California
    'Los Angeles': {'county': 'Los Angeles County', 'state': 'CA', 'nearby': ['Hollywood', 'Beverly Hills', 'Santa Monica', 'Pasadena', 'Glendale', 'Burbank', 'Long Beach', 'Torrance', 'Pomona', 'West Covina']},
    'San Diego': {'county': 'San Diego County', 'state': 'CA', 'nearby': ['Chula Vista', 'Oceanside', 'Escondido', 'Carlsbad', 'El Cajon', 'Vista', 'San Marcos', 'Encinitas', 'National City', 'La Mesa']},
    'San Francisco': {'county': 'San Francisco County', 'state': 'CA', 'nearby': ['Oakland', 'Berkeley', 'Daly City', 'San Mateo', 'South San Francisco', 'Sausalito', 'Mill Valley']},
    'San Jose': {'county': 'Santa Clara County', 'state': 'CA', 'nearby': ['Santa Clara', 'Sunnyvale', 'Mountain View', 'Palo Alto', 'Cupertino', 'Milpitas', 'Campbell', 'Los Gatos', 'Saratoga']},
    
    # Illinois
    'Chicago': {'county': 'Cook County', 'state': 'IL', 'nearby': ['Evanston', 'Oak Park', 'Cicero', 'Skokie', 'Des Plaines', 'Schaumburg', 'Palatine', 'Arlington Heights', 'Mount Prospect']},
}

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
        """Handle GET requests with smart local search"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/smart-search':
            params = parse_qs(parsed_path.query)
            query = params.get('q', [''])[0]
            
            if not query:
                self.send_error(400, "Missing search query")
                return
            
            results = self.smart_search(query)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            return
        
        self.send_error(404, "Endpoint not found")
    
    def smart_search(self, query):
        """Smart search that handles ZIP codes and keywords"""
        parts = query.split()
        
        # Check if first part is a ZIP code
        if parts and len(parts[0]) == 5 and parts[0].isdigit():
            zip_code = parts[0]
            keyword = ' '.join(parts[1:]) if len(parts) > 1 else 'nonprofit'
            
            # Get city from ZIP using Zippopotam.us
            cache_key = f"zip:{zip_code}"
            
            def fetch_zip():
                try:
                    response = requests.get(f"http://api.zippopotam.us/us/{zip_code}", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('places'):
                            return {
                                'city': data['places'][0]['place name'],
                                'state': data['places'][0]['state'],
                                'state_abbr': data['places'][0]['state abbreviation']
                            }
                except:
                    pass
                return None
            
            zip_info = get_cached_or_fetch(cache_key, fetch_zip)
            
            if zip_info:
                return self.search_local(zip_info['city'], zip_info['state'], keyword, zip_code)
            else:
                # Fallback to keyword search
                return self.search_keyword(query)
        else:
            # Regular keyword search
            return self.search_keyword(query)
    
    def search_local(self, city, state, keyword, zip_code):
        """Search for local organizations"""
        # Get county info if available
        county_info = CITY_TO_COUNTY.get(city, CITY_TO_COUNTY.get(city.replace(' ', '')))
        
        if county_info:
            nearby_cities = [city] + county_info.get('nearby', [])
            county = county_info.get('county', 'Unknown')
        else:
            nearby_cities = [city]
            county = 'Unknown'
        
        # Search ProPublica
        cache_key = f"search:{keyword}:{state}"
        
        def fetch_results():
            url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
            params = {'q': f"{keyword} {state}"}
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except:
                return {'organizations': []}
        
        data = get_cached_or_fetch(cache_key, fetch_results)
        
        # Filter and categorize results
        local_results = []
        nearby_results = []
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
            }
            
            # Check if local
            is_local = False
            for nearby_city in nearby_cities:
                if nearby_city.lower() in org_city.lower() or org_city.lower() in nearby_city.lower():
                    is_local = True
                    org_data['distance'] = 'Local'
                    org_data['match_quality'] = 100
                    break
            
            if is_local:
                local_results.append(org_data)
            elif org_state == state:
                org_data['distance'] = f'Same State ({state})'
                org_data['match_quality'] = 50
                nearby_results.append(org_data)
                if len(nearby_results) < 10:  # Limit nearby results
                    state_results.append(org_data)
        
        # Combine results
        all_results = local_results[:15] + nearby_results[:5]
        
        return {
            'query': f"{zip_code} {keyword}" if zip_code else keyword,
            'location': {
                'zip': zip_code,
                'city': city,
                'county': county,
                'state': state
            },
            'counts': {
                'local': len(local_results),
                'state': len(nearby_results),
                'total': len(data.get('organizations', []))
            },
            'results': all_results,
            'message': self.generate_message(len(local_results), city, county, keyword)
        }
    
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
    
    def generate_message(self, local_count, city, county, keyword):
        """Generate helpful message about results"""
        if local_count > 0:
            return f"Found {local_count} '{keyword}' organizations in {city} and nearby {county} cities"
        elif county != 'Unknown':
            return f"No '{keyword}' organizations found in {city}. Showing results from elsewhere in {county}"
        else:
            return f"No local results for '{keyword}' in {city}. Showing statewide results"
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()