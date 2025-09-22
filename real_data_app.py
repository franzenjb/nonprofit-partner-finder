#!/usr/bin/env python3
"""
Simple Flask app that uses REAL ProPublica data
Run this to see actual nonprofits!
"""

from flask import Flask, render_template_string, request, jsonify
import requests
import json

app = Flask(__name__)

# HTML template with embedded JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Real Nonprofit Data - Neil Brockway Partner Finder</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .loading { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
    </style>
</head>
<body class="bg-gray-50">
    <div class="gradient-bg text-white py-8">
        <div class="container mx-auto px-6">
            <h1 class="text-3xl font-bold text-center">Neil Brockway Nonprofit Partner Finder</h1>
            <p class="text-center mt-2">Real Data from ProPublica (1.8M Nonprofits)</p>
        </div>
    </div>

    <div class="container mx-auto px-6 py-8">
        <div class="max-w-4xl mx-auto">
            <!-- Search Box -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Search Real Nonprofits</h2>
                <div class="flex space-x-4">
                    <input type="text" id="searchQuery" placeholder="Enter organization name or keyword" 
                           class="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-600">
                    <select id="stateFilter" class="px-4 py-2 border rounded-lg">
                        <option value="">All States</option>
                        <option value="NY">New York</option>
                        <option value="CA">California</option>
                        <option value="TX">Texas</option>
                        <option value="FL">Florida</option>
                        <option value="IL">Illinois</option>
                        <option value="PA">Pennsylvania</option>
                        <option value="OH">Ohio</option>
                        <option value="GA">Georgia</option>
                        <option value="NC">North Carolina</option>
                        <option value="MI">Michigan</option>
                    </select>
                    <button onclick="searchNonprofits()" 
                            class="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">
                        Search
                    </button>
                </div>
            </div>

            <!-- Results -->
            <div id="loadingIndicator" class="hidden text-center py-8">
                <div class="loading text-purple-600 text-lg">Searching real nonprofits...</div>
            </div>

            <div id="results" class="space-y-4"></div>
        </div>
    </div>

    <script>
        async function searchNonprofits() {
            const query = document.getElementById('searchQuery').value;
            const state = document.getElementById('stateFilter').value;
            
            if (!query) {
                alert('Please enter a search term');
                return;
            }

            document.getElementById('loadingIndicator').classList.remove('hidden');
            document.getElementById('results').innerHTML = '';

            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({query: query, state: state})
                });
                
                const data = await response.json();
                displayResults(data);
            } catch (error) {
                console.error('Search error:', error);
                alert('Search failed. Please try again.');
            } finally {
                document.getElementById('loadingIndicator').classList.add('hidden');
            }
        }

        function displayResults(nonprofits) {
            const resultsDiv = document.getElementById('results');
            
            if (nonprofits.length === 0) {
                resultsDiv.innerHTML = '<p class="text-gray-500 text-center">No results found</p>';
                return;
            }

            let html = '<h3 class="text-lg font-semibold mb-4">Found ' + nonprofits.length + ' Real Nonprofits:</h3>';
            
            nonprofits.forEach((org, index) => {
                html += `
                    <div class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
                        <div class="flex justify-between items-start mb-2">
                            <div>
                                <span class="bg-purple-100 text-purple-600 px-2 py-1 rounded text-sm">#${index + 1}</span>
                                <h4 class="text-lg font-semibold mt-2">${org.name}</h4>
                                <p class="text-gray-600">${org.city}, ${org.state}</p>
                            </div>
                            <button onclick="getDetails('${org.ein}')" 
                                    class="text-purple-600 hover:text-purple-800">
                                View Details →
                            </button>
                        </div>
                        <div class="text-sm text-gray-500">
                            EIN: ${org.ein} | NTEE: ${org.ntee_code || 'N/A'}
                        </div>
                        <div id="details-${org.ein}" class="mt-4 hidden"></div>
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        }

        async function getDetails(ein) {
            const detailsDiv = document.getElementById('details-' + ein);
            
            if (!detailsDiv.classList.contains('hidden')) {
                detailsDiv.classList.add('hidden');
                return;
            }
            
            detailsDiv.innerHTML = '<p class="loading text-gray-500">Loading details...</p>';
            detailsDiv.classList.remove('hidden');
            
            try {
                const response = await fetch('/api/details/' + ein);
                const data = await response.json();
                
                let html = '<div class="border-t pt-4">';
                
                if (data.mission) {
                    html += '<p class="mb-2"><strong>Mission:</strong> ' + data.mission + '</p>';
                }
                
                if (data.revenue !== null) {
                    html += '<div class="grid grid-cols-2 gap-4 mt-4">';
                    html += '<div><strong>Revenue:</strong> $' + data.revenue.toLocaleString() + '</div>';
                    if (data.expenses !== null) {
                        html += '<div><strong>Expenses:</strong> $' + data.expenses.toLocaleString() + '</div>';
                    }
                    if (data.assets !== null) {
                        html += '<div><strong>Assets:</strong> $' + data.assets.toLocaleString() + '</div>';
                    }
                    if (data.program_expense_percent !== null) {
                        html += '<div><strong>Program %:</strong> ' + data.program_expense_percent.toFixed(1) + '%</div>';
                    }
                    html += '</div>';
                }
                
                if (data.latest_filing_year) {
                    html += '<p class="text-sm text-gray-500 mt-2">Latest filing: ' + data.latest_filing_year + '</p>';
                }
                
                html += '<a href="https://projects.propublica.org/nonprofits/organizations/' + ein + '" target="_blank" class="text-purple-600 hover:text-purple-800 text-sm mt-2 inline-block">View on ProPublica →</a>';
                html += '</div>';
                
                detailsDiv.innerHTML = html;
            } catch (error) {
                detailsDiv.innerHTML = '<p class="text-red-500">Failed to load details</p>';
            }
        }

        // Search on Enter key
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('searchQuery').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') searchNonprofits();
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/search', methods=['POST'])
def search():
    """Search nonprofits using ProPublica API"""
    data = request.json
    query = data.get('query', '')
    state = data.get('state', '')
    
    # Build ProPublica API URL
    url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
    params = {'q': query}
    if state:
        params['state'] = state
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        api_data = response.json()
        
        # Format results
        results = []
        for org in api_data.get('organizations', [])[:20]:  # Limit to 20
            results.append({
                'ein': str(org['ein']),
                'name': org['name'],
                'city': org.get('city', ''),
                'state': org.get('state', ''),
                'ntee_code': org.get('ntee_code'),
                'score': org.get('score', 0)
            })
        
        return jsonify(results)
    
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify([])

@app.route('/api/details/<ein>')
def get_details(ein):
    """Get detailed information about a nonprofit"""
    # Clean EIN
    ein_clean = ein.replace('-', '')
    
    url = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{ein_clean}.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        org = data.get('organization', {})
        
        # Get latest filing
        latest_filing = None
        if 'filings_with_data' in org and org['filings_with_data']:
            latest_filing = org['filings_with_data'][0]
        
        # Extract financial data
        result = {
            'name': org.get('name', ''),
            'mission': org.get('mission'),
            'revenue': None,
            'expenses': None,
            'assets': None,
            'program_expense_percent': None,
            'latest_filing_year': None
        }
        
        if latest_filing:
            result['revenue'] = latest_filing.get('totrevenue')
            result['expenses'] = latest_filing.get('totfuncexpns')
            result['assets'] = latest_filing.get('totassetsend')
            result['latest_filing_year'] = latest_filing.get('tax_prd_yr')
            
            # Calculate program expense percentage
            if latest_filing.get('totfuncexpns') and latest_filing.get('totfuncexpns') > 0:
                program_exp = latest_filing.get('progsvcs', 0)
                result['program_expense_percent'] = (program_exp / latest_filing['totfuncexpns']) * 100
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Details error for {ein}: {e}")
        return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Starting Real Nonprofit Data Server")
    print("="*60)
    print("\nOpen your browser to: http://localhost:5000")
    print("\nYou can search for real organizations like:")
    print("  • Red Cross")
    print("  • United Way")
    print("  • Salvation Army")
    print("  • Food Bank")
    print("  • Homeless Shelter")
    print("  • Animal Rescue")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)