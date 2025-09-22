"""
Local search API that filters by city
Better geographic filtering for ProPublica data
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs

# ZIP to City mapping (major ZIP codes)
ZIP_TO_CITY = {
    # Dallas Area
    '75201': 'Dallas', '75202': 'Dallas', '75203': 'Dallas', '75204': 'Dallas',
    '75205': 'Dallas', '75206': 'Dallas', '75207': 'Dallas', '75208': 'Dallas',
    '75209': 'Dallas', '75210': 'Dallas', '75211': 'Dallas', '75212': 'Dallas',
    '75214': 'Dallas', '75215': 'Dallas', '75216': 'Dallas', '75217': 'Dallas',
    '75218': 'Dallas', '75219': 'Dallas', '75220': 'Dallas', '75223': 'Dallas',
    '75224': 'Dallas', '75225': 'Dallas', '75226': 'Dallas', '75227': 'Dallas',
    '75228': 'Dallas', '75229': 'Dallas', '75230': 'Dallas', '75231': 'Dallas',
    '75232': 'Dallas', '75233': 'Dallas', '75234': 'Dallas', '75235': 'Dallas',
    '75236': 'Dallas', '75237': 'Dallas', '75238': 'Dallas', '75240': 'Dallas',
    '75241': 'Dallas', '75243': 'Dallas', '75244': 'Dallas', '75246': 'Dallas',
    '75247': 'Dallas', '75248': 'Dallas', '75249': 'Dallas', '75251': 'Dallas',
    '75252': 'Dallas', '75253': 'Dallas', '75254': 'Dallas',
    
    # Houston Area  
    '77001': 'Houston', '77002': 'Houston', '77003': 'Houston', '77004': 'Houston',
    '77005': 'Houston', '77006': 'Houston', '77007': 'Houston', '77008': 'Houston',
    '77009': 'Houston', '77010': 'Houston', '77011': 'Houston', '77012': 'Houston',
    '77013': 'Houston', '77014': 'Houston', '77015': 'Houston', '77016': 'Houston',
    '77017': 'Houston', '77018': 'Houston', '77019': 'Houston', '77020': 'Houston',
    '77021': 'Houston', '77022': 'Houston', '77023': 'Houston', '77024': 'Houston',
    '77025': 'Houston', '77026': 'Houston', '77027': 'Houston', '77028': 'Houston',
    '77029': 'Houston', '77030': 'Houston',
    
    # New York City
    '10001': 'New York', '10002': 'New York', '10003': 'New York', '10004': 'New York',
    '10005': 'New York', '10006': 'New York', '10007': 'New York', '10009': 'New York',
    '10010': 'New York', '10011': 'New York', '10012': 'New York', '10013': 'New York',
    '10014': 'New York', '10016': 'New York', '10017': 'New York', '10018': 'New York',
    '10019': 'New York', '10020': 'New York', '10021': 'New York', '10022': 'New York',
    '10023': 'New York', '10024': 'New York', '10025': 'New York', '10026': 'New York',
    '10027': 'New York', '10028': 'New York', '10029': 'New York',
    
    # Los Angeles
    '90001': 'Los Angeles', '90002': 'Los Angeles', '90003': 'Los Angeles',
    '90004': 'Los Angeles', '90005': 'Los Angeles', '90006': 'Los Angeles',
    '90007': 'Los Angeles', '90008': 'Los Angeles', '90010': 'Los Angeles',
    '90011': 'Los Angeles', '90012': 'Los Angeles', '90013': 'Los Angeles',
    '90014': 'Los Angeles', '90015': 'Los Angeles', '90016': 'Los Angeles',
    '90017': 'Los Angeles', '90018': 'Los Angeles', '90019': 'Los Angeles',
    '90020': 'Los Angeles', '90021': 'Los Angeles',
    
    # Chicago
    '60601': 'Chicago', '60602': 'Chicago', '60603': 'Chicago', '60604': 'Chicago',
    '60605': 'Chicago', '60606': 'Chicago', '60607': 'Chicago', '60608': 'Chicago',
    '60609': 'Chicago', '60610': 'Chicago', '60611': 'Chicago', '60612': 'Chicago',
    '60613': 'Chicago', '60614': 'Chicago', '60615': 'Chicago', '60616': 'Chicago',
    '60617': 'Chicago', '60618': 'Chicago', '60619': 'Chicago', '60620': 'Chicago',
    
    # Miami
    '33101': 'Miami', '33102': 'Miami', '33109': 'Miami Beach', '33110': 'Miami',
    '33111': 'Miami', '33112': 'Miami', '33125': 'Miami', '33126': 'Miami',
    '33127': 'Miami', '33128': 'Miami', '33129': 'Miami', '33130': 'Miami',
    '33131': 'Miami', '33132': 'Miami', '33133': 'Miami', '33134': 'Miami',
    '33135': 'Miami', '33136': 'Miami', '33137': 'Miami', '33138': 'Miami',
    '33139': 'Miami Beach', '33140': 'Miami Beach',
    
    # St. Petersburg / Pinellas County
    '33701': 'St Petersburg', '33702': 'St Petersburg', '33703': 'St Petersburg',
    '33704': 'St Petersburg', '33705': 'St Petersburg', '33706': 'St Petersburg',
    '33707': 'St Petersburg', '33708': 'St Petersburg', '33709': 'St Petersburg',
    '33710': 'St Petersburg', '33711': 'St Petersburg', '33712': 'St Petersburg',
    '33713': 'St Petersburg', '33714': 'St Petersburg', '33715': 'St Petersburg',
    '33716': 'St Petersburg',
    '33755': 'Clearwater', '33756': 'Clearwater', '33757': 'Clearwater',
    '33758': 'Clearwater', '33759': 'Clearwater', '33760': 'Clearwater',
    '33761': 'Clearwater', '33762': 'Clearwater', '33763': 'Clearwater',
    '33764': 'Clearwater', '33765': 'Clearwater', '33767': 'Clearwater',
    '33770': 'Largo', '33771': 'Largo', '33773': 'Largo', '33774': 'Largo',
    '33778': 'Largo', '33779': 'Largo',
}

# Nearby cities for better coverage
NEARBY_CITIES = {
    'Dallas': ['Dallas', 'Richardson', 'Plano', 'Irving', 'Garland', 'Mesquite', 'Carrollton', 'Addison'],
    'Houston': ['Houston', 'Pasadena', 'Sugar Land', 'The Woodlands', 'Katy', 'Spring'],
    'New York': ['New York', 'Brooklyn', 'Bronx', 'Queens', 'Manhattan'],
    'Los Angeles': ['Los Angeles', 'Hollywood', 'Beverly Hills', 'Santa Monica', 'Pasadena'],
    'Chicago': ['Chicago', 'Evanston', 'Oak Park', 'Cicero'],
    'Miami': ['Miami', 'Miami Beach', 'Coral Gables', 'Hialeah', 'Miami Gardens'],
    'St Petersburg': ['St Petersburg', 'Clearwater', 'Largo', 'Pinellas Park', 'Seminole', 'Dunedin'],
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests with local filtering"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/local-search':
            params = parse_qs(parsed_path.query)
            zip_code = params.get('zip', [''])[0]
            keyword = params.get('q', [''])[0]
            
            if not zip_code or not keyword:
                self.send_error(400, "Missing zip or keyword")
                return
            
            results = self.search_local(zip_code, keyword)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            return
        
        self.send_error(404, "Endpoint not found")
    
    def search_local(self, zip_code, keyword):
        """Search for nonprofits locally"""
        # Get city from ZIP
        city = ZIP_TO_CITY.get(zip_code)
        if not city:
            return {
                'error': 'ZIP code not in database',
                'suggestion': 'Try searching with just keyword',
                'results': []
            }
        
        # Get nearby cities
        nearby = NEARBY_CITIES.get(city, [city])
        
        # Search ProPublica
        url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
        params = {'q': keyword}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # FILTER TO LOCAL RESULTS ONLY
            local_results = []
            other_results = []
            
            for org in data.get('organizations', []):
                org_city = org.get('city', '')
                
                # Check if organization is in nearby cities
                is_local = False
                for nearby_city in nearby:
                    if nearby_city.lower() in org_city.lower():
                        is_local = True
                        break
                
                org_data = {
                    'ein': str(org['ein']),
                    'name': org['name'],
                    'city': org_city,
                    'state': org.get('state', ''),
                    'is_local': is_local,
                    'distance': 'Local' if is_local else org.get('state', 'Other')
                }
                
                if is_local:
                    local_results.append(org_data)
                else:
                    other_results.append(org_data)
            
            # Return local results first, then closest others
            return {
                'zip_code': zip_code,
                'city': city,
                'nearby_cities': nearby,
                'keyword': keyword,
                'local_results': local_results[:10],
                'other_results': other_results[:5] if not local_results else [],
                'message': f"Found {len(local_results)} local results in {city} area"
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'results': []
            }
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()