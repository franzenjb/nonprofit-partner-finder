"""
Vercel Serverless API for Nonprofit Partner Finder
Production-ready with caching
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

# Simple in-memory cache (resets on cold starts)
cache = {}
CACHE_DURATION = 3600  # 1 hour

def get_cached_or_fetch(cache_key, fetch_func):
    """Simple caching mechanism"""
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_DURATION):
            return cached_data
    
    # Fetch fresh data
    data = fetch_func()
    cache[cache_key] = (data, datetime.now())
    return data

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy', 'service': 'Neil Brockway Partner Finder'}).encode())
            return
        
        # Handle search via GET parameters
        if parsed_path.path == '/api/search':
            params = parse_qs(parsed_path.query)
            query = params.get('q', [''])[0]
            state = params.get('state', [''])[0]
            
            if not query:
                self.send_error(400, "Missing query parameter")
                return
            
            results = self.search_nonprofits(query, state)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            return
        
        # Handle details
        if parsed_path.path.startswith('/api/details/'):
            ein = parsed_path.path.split('/')[-1]
            details = self.get_nonprofit_details(ein)
            
            if details:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(details).encode())
            else:
                self.send_error(404, "Nonprofit not found")
            return
        
        self.send_error(404, "Endpoint not found")
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/search':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                query = data.get('query', '')
                state = data.get('state', '')
                
                if not query:
                    self.send_error(400, "Missing query")
                    return
                
                results = self.search_nonprofits(query, state)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode())
                
            except Exception as e:
                self.send_error(500, str(e))
            return
        
        self.send_error(404, "Endpoint not found")
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def search_nonprofits(self, query, state=''):
        """Search nonprofits using ProPublica API with caching"""
        cache_key = f"search:{query}:{state}"
        
        def fetch():
            url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
            params = {'q': query}
            if state:
                params['state'] = state
            
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
                return results
                
            except Exception as e:
                print(f"Search error: {e}")
                return []
        
        return get_cached_or_fetch(cache_key, fetch)
    
    def get_nonprofit_details(self, ein):
        """Get nonprofit details with caching"""
        cache_key = f"details:{ein}"
        
        def fetch():
            ein_clean = ein.replace('-', '')
            url = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{ein_clean}.json"
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                org = data.get('organization', {})
                
                # Get latest filing
                latest_filing = None
                if 'filings_with_data' in org and org['filings_with_data']:
                    latest_filing = org['filings_with_data'][0]
                
                result = {
                    'name': org.get('name', ''),
                    'city': org.get('city', ''),
                    'state': org.get('state', ''),
                    'mission': org.get('mission'),
                    'website': org.get('website'),
                    'revenue': None,
                    'expenses': None,
                    'assets': None,
                    'program_expense_percent': None,
                    'fundraising_percent': None,
                    'admin_percent': None,
                    'latest_filing_year': None,
                    'propublica_url': f"https://projects.propublica.org/nonprofits/organizations/{ein_clean}"
                }
                
                if latest_filing:
                    result['revenue'] = latest_filing.get('totrevenue')
                    result['expenses'] = latest_filing.get('totfuncexpns')
                    result['assets'] = latest_filing.get('totassetsend')
                    result['latest_filing_year'] = latest_filing.get('tax_prd_yr')
                    
                    # Calculate percentages
                    if latest_filing.get('totfuncexpns') and latest_filing.get('totfuncexpns') > 0:
                        total = latest_filing['totfuncexpns']
                        
                        if latest_filing.get('progsvcs'):
                            result['program_expense_percent'] = (latest_filing['progsvcs'] / total) * 100
                        
                        if latest_filing.get('fundrasing'):
                            result['fundraising_percent'] = (latest_filing['fundrasing'] / total) * 100
                        
                        if latest_filing.get('mgmtandgen'):
                            result['admin_percent'] = (latest_filing['mgmtandgen'] / total) * 100
                
                return result
                
            except Exception as e:
                print(f"Details error for {ein}: {e}")
                return None
        
        return get_cached_or_fetch(cache_key, fetch)