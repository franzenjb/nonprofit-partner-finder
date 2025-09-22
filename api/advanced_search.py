"""
Enhanced search API with ZIP code support and keyword filtering
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import re

# ZIP to state mapping (partial - would use full database in production)
ZIP_TO_STATE = {
    # New York
    '10001': 'NY', '10002': 'NY', '10003': 'NY', '10004': 'NY', '10005': 'NY',
    '10006': 'NY', '10007': 'NY', '10008': 'NY', '10009': 'NY', '10010': 'NY',
    '10011': 'NY', '10012': 'NY', '10013': 'NY', '10014': 'NY', '10016': 'NY',
    '10017': 'NY', '10018': 'NY', '10019': 'NY', '10020': 'NY', '10021': 'NY',
    '10022': 'NY', '10023': 'NY', '10024': 'NY', '10025': 'NY', '10026': 'NY',
    '10027': 'NY', '10028': 'NY', '10029': 'NY', '10030': 'NY',
    
    # California
    '90001': 'CA', '90002': 'CA', '90003': 'CA', '90004': 'CA', '90005': 'CA',
    '90006': 'CA', '90007': 'CA', '90008': 'CA', '90009': 'CA', '90010': 'CA',
    '90011': 'CA', '90012': 'CA', '90013': 'CA', '90014': 'CA', '90015': 'CA',
    '90016': 'CA', '90017': 'CA', '90018': 'CA', '90019': 'CA', '90020': 'CA',
    '90021': 'CA', '90022': 'CA', '90023': 'CA', '90024': 'CA', '90025': 'CA',
    '90026': 'CA', '90027': 'CA', '90028': 'CA', '90029': 'CA', '90030': 'CA',
    '94102': 'CA', '94103': 'CA', '94104': 'CA', '94105': 'CA', '94107': 'CA',
    '94108': 'CA', '94109': 'CA', '94110': 'CA', '94111': 'CA', '94112': 'CA',
    
    # Texas
    '75001': 'TX', '75201': 'TX', '75202': 'TX', '75203': 'TX', '75204': 'TX',
    '75205': 'TX', '75206': 'TX', '75207': 'TX', '75208': 'TX', '75209': 'TX',
    '75210': 'TX', '75211': 'TX', '75212': 'TX', '75214': 'TX', '75215': 'TX',
    '77001': 'TX', '77002': 'TX', '77003': 'TX', '77004': 'TX', '77005': 'TX',
    '77006': 'TX', '77007': 'TX', '77008': 'TX', '77009': 'TX', '77010': 'TX',
    '78701': 'TX', '78702': 'TX', '78703': 'TX', '78704': 'TX', '78705': 'TX',
    
    # Florida
    '33101': 'FL', '33102': 'FL', '33109': 'FL', '33110': 'FL', '33111': 'FL',
    '33112': 'FL', '33113': 'FL', '33114': 'FL', '33115': 'FL', '33116': 'FL',
    '33122': 'FL', '33124': 'FL', '33125': 'FL', '33126': 'FL', '33127': 'FL',
    '33128': 'FL', '33129': 'FL', '33130': 'FL', '33131': 'FL', '33132': 'FL',
    
    # Illinois
    '60601': 'IL', '60602': 'IL', '60603': 'IL', '60604': 'IL', '60605': 'IL',
    '60606': 'IL', '60607': 'IL', '60608': 'IL', '60609': 'IL', '60610': 'IL',
    '60611': 'IL', '60612': 'IL', '60613': 'IL', '60614': 'IL', '60615': 'IL',
    '60616': 'IL', '60617': 'IL', '60618': 'IL', '60619': 'IL', '60620': 'IL',
}

def get_state_from_zip(zip_code):
    """Get state from ZIP code"""
    # Direct lookup
    if zip_code in ZIP_TO_STATE:
        return ZIP_TO_STATE[zip_code]
    
    # Try prefix matching for broader coverage
    zip_prefix = zip_code[:3]
    state_map = {
        # Northeast
        '100': 'NY', '101': 'NY', '102': 'NY', '103': 'NY', '104': 'NY',
        '105': 'NY', '106': 'NY', '107': 'NY', '108': 'NY', '109': 'NY',
        '110': 'NY', '111': 'NY', '112': 'NY', '113': 'NY', '114': 'NY',
        '115': 'NY', '116': 'NY', '117': 'NY', '118': 'NY', '119': 'NY',
        '120': 'NY', '121': 'NY', '122': 'NY', '123': 'NY', '124': 'NY',
        '125': 'NY', '126': 'NY', '127': 'NY', '128': 'NY', '129': 'NY',
        '130': 'NY', '131': 'NY', '132': 'NY', '133': 'NY', '134': 'NY',
        '135': 'NY', '136': 'NY', '137': 'NY', '138': 'NY', '139': 'NY',
        '140': 'NY', '141': 'NY', '142': 'NY', '143': 'NY', '144': 'NY',
        '145': 'NY', '146': 'NY', '147': 'NY', '148': 'NY', '149': 'NY',
        
        # California
        '900': 'CA', '901': 'CA', '902': 'CA', '903': 'CA', '904': 'CA',
        '905': 'CA', '906': 'CA', '907': 'CA', '908': 'CA', '910': 'CA',
        '911': 'CA', '912': 'CA', '913': 'CA', '914': 'CA', '915': 'CA',
        '916': 'CA', '917': 'CA', '918': 'CA', '919': 'CA', '920': 'CA',
        '921': 'CA', '922': 'CA', '923': 'CA', '924': 'CA', '925': 'CA',
        '926': 'CA', '927': 'CA', '928': 'CA', '930': 'CA', '931': 'CA',
        '932': 'CA', '933': 'CA', '934': 'CA', '935': 'CA', '936': 'CA',
        '937': 'CA', '938': 'CA', '939': 'CA', '940': 'CA', '941': 'CA',
        '942': 'CA', '943': 'CA', '944': 'CA', '945': 'CA', '946': 'CA',
        '947': 'CA', '948': 'CA', '949': 'CA', '950': 'CA', '951': 'CA',
        '952': 'CA', '953': 'CA', '954': 'CA', '955': 'CA', '956': 'CA',
        '957': 'CA', '958': 'CA', '959': 'CA', '960': 'CA', '961': 'CA',
        
        # Texas
        '750': 'TX', '751': 'TX', '752': 'TX', '753': 'TX', '754': 'TX',
        '755': 'TX', '756': 'TX', '757': 'TX', '758': 'TX', '759': 'TX',
        '760': 'TX', '761': 'TX', '762': 'TX', '763': 'TX', '764': 'TX',
        '765': 'TX', '766': 'TX', '767': 'TX', '768': 'TX', '769': 'TX',
        '770': 'TX', '772': 'TX', '773': 'TX', '774': 'TX', '775': 'TX',
        '776': 'TX', '777': 'TX', '778': 'TX', '779': 'TX', '780': 'TX',
        '781': 'TX', '782': 'TX', '783': 'TX', '784': 'TX', '785': 'TX',
        '786': 'TX', '787': 'TX', '788': 'TX', '789': 'TX', '790': 'TX',
        '791': 'TX', '792': 'TX', '793': 'TX', '794': 'TX', '795': 'TX',
        '796': 'TX', '797': 'TX', '798': 'TX', '799': 'TX',
        
        # Florida
        '320': 'FL', '321': 'FL', '322': 'FL', '323': 'FL', '324': 'FL',
        '325': 'FL', '326': 'FL', '327': 'FL', '328': 'FL', '329': 'FL',
        '330': 'FL', '331': 'FL', '332': 'FL', '333': 'FL', '334': 'FL',
        '335': 'FL', '336': 'FL', '337': 'FL', '338': 'FL', '339': 'FL',
        '341': 'FL', '342': 'FL', '344': 'FL', '346': 'FL', '347': 'FL',
        '349': 'FL',
        
        # Illinois
        '600': 'IL', '601': 'IL', '602': 'IL', '603': 'IL', '604': 'IL',
        '605': 'IL', '606': 'IL', '607': 'IL', '608': 'IL', '609': 'IL',
        '610': 'IL', '611': 'IL', '612': 'IL', '613': 'IL', '614': 'IL',
        '615': 'IL', '616': 'IL', '617': 'IL', '618': 'IL', '619': 'IL',
        '620': 'IL', '622': 'IL', '623': 'IL', '624': 'IL', '625': 'IL',
        '626': 'IL', '627': 'IL', '628': 'IL', '629': 'IL',
        
        # Pennsylvania
        '150': 'PA', '151': 'PA', '152': 'PA', '153': 'PA', '154': 'PA',
        '155': 'PA', '156': 'PA', '157': 'PA', '158': 'PA', '159': 'PA',
        '160': 'PA', '161': 'PA', '162': 'PA', '163': 'PA', '164': 'PA',
        '165': 'PA', '166': 'PA', '167': 'PA', '168': 'PA', '169': 'PA',
        '170': 'PA', '171': 'PA', '172': 'PA', '173': 'PA', '174': 'PA',
        '175': 'PA', '176': 'PA', '177': 'PA', '178': 'PA', '179': 'PA',
        '180': 'PA', '181': 'PA', '182': 'PA', '183': 'PA', '184': 'PA',
        '185': 'PA', '186': 'PA', '187': 'PA', '188': 'PA', '189': 'PA',
        '190': 'PA', '191': 'PA', '192': 'PA', '193': 'PA', '194': 'PA',
        '195': 'PA', '196': 'PA',
        
        # Ohio
        '430': 'OH', '431': 'OH', '432': 'OH', '433': 'OH', '434': 'OH',
        '435': 'OH', '436': 'OH', '437': 'OH', '438': 'OH', '439': 'OH',
        '440': 'OH', '441': 'OH', '442': 'OH', '443': 'OH', '444': 'OH',
        '445': 'OH', '446': 'OH', '447': 'OH', '448': 'OH', '449': 'OH',
        '450': 'OH', '451': 'OH', '452': 'OH', '453': 'OH', '454': 'OH',
        '455': 'OH', '456': 'OH', '457': 'OH', '458': 'OH',
        
        # Michigan
        '480': 'MI', '481': 'MI', '482': 'MI', '483': 'MI', '484': 'MI',
        '485': 'MI', '486': 'MI', '487': 'MI', '488': 'MI', '489': 'MI',
        '490': 'MI', '491': 'MI', '492': 'MI', '493': 'MI', '494': 'MI',
        '495': 'MI', '496': 'MI', '497': 'MI', '498': 'MI', '499': 'MI',
        
        # Georgia
        '300': 'GA', '301': 'GA', '302': 'GA', '303': 'GA', '304': 'GA',
        '305': 'GA', '306': 'GA', '307': 'GA', '308': 'GA', '309': 'GA',
        '310': 'GA', '311': 'GA', '312': 'GA', '313': 'GA', '314': 'GA',
        '315': 'GA', '316': 'GA', '317': 'GA', '318': 'GA', '319': 'GA',
    }
    
    return state_map.get(zip_prefix)

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
        """Handle GET requests with enhanced search"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/search-advanced':
            params = parse_qs(parsed_path.query)
            query = params.get('q', [''])[0]
            
            # Check if query is a ZIP code
            if re.match(r'^\d{5}$', query):
                # It's a ZIP code
                zip_code = query
                keyword = params.get('keyword', [''])[0]
                results = self.search_by_zip(zip_code, keyword)
            else:
                # Check if it's "ZIP keyword" format
                parts = query.split()
                if len(parts) >= 2 and re.match(r'^\d{5}$', parts[0]):
                    zip_code = parts[0]
                    keyword = ' '.join(parts[1:])
                    results = self.search_by_zip(zip_code, keyword)
                else:
                    # Regular keyword search
                    results = self.search_by_keyword(query)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            return
        
        self.send_error(404, "Endpoint not found")
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def search_by_zip(self, zip_code, keyword=''):
        """Search nonprofits by ZIP code and optional keyword"""
        state = get_state_from_zip(zip_code)
        if not state:
            return {'error': 'ZIP code not recognized', 'results': []}
        
        # Build cache key
        cache_key = f"zip:{zip_code}:{keyword}"
        
        def fetch():
            # First search by state
            url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
            
            # If we have a keyword, search for it in the state
            if keyword:
                params = {'q': keyword, 'state': state}
            else:
                # Just get nonprofits in the state
                params = {'state': state}
            
            try:
                response = requests.get(url, params=params, timeout=10)
                
                # ProPublica limits state-only searches, so use a workaround
                if response.status_code == 500 and not keyword:
                    # Search for common terms instead
                    params = {'q': 'foundation OR charity OR nonprofit', 'state': state}
                    response = requests.get(url, params=params, timeout=10)
                
                if response.status_code != 200:
                    return {'error': 'API error', 'results': []}
                
                api_data = response.json()
                organizations = api_data.get('organizations', [])
                
                # Filter by keyword if provided
                if keyword and organizations:
                    keyword_lower = keyword.lower()
                    filtered = []
                    for org in organizations:
                        name_lower = org.get('name', '').lower()
                        if keyword_lower in name_lower:
                            filtered.append(org)
                    organizations = filtered
                
                # Format results
                results = []
                for org in organizations[:20]:  # Limit to 20
                    results.append({
                        'ein': str(org['ein']),
                        'name': org['name'],
                        'city': org.get('city', ''),
                        'state': org.get('state', ''),
                        'ntee_code': org.get('ntee_code'),
                        'score': org.get('score', 0)
                    })
                
                return {
                    'zip_code': zip_code,
                    'state': state,
                    'keyword': keyword,
                    'count': len(results),
                    'results': results
                }
                
            except Exception as e:
                print(f"Search error: {e}")
                return {'error': str(e), 'results': []}
        
        return get_cached_or_fetch(cache_key, fetch)
    
    def search_by_keyword(self, keyword):
        """Regular keyword search"""
        cache_key = f"keyword:{keyword}"
        
        def fetch():
            url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
            params = {'q': keyword}
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                api_data = response.json()
                
                results = []
                for org in api_data.get('organizations', [])[:20]:
                    results.append({
                        'ein': str(org['ein']),
                        'name': org['name'],
                        'city': org.get('city', ''),
                        'state': org.get('state', ''),
                        'ntee_code': org.get('ntee_code'),
                        'score': org.get('score', 0)
                    })
                
                return {
                    'keyword': keyword,
                    'count': len(results),
                    'results': results
                }
                
            except Exception as e:
                print(f"Search error: {e}")
                return {'error': str(e), 'results': []}
        
        return get_cached_or_fetch(cache_key, fetch)