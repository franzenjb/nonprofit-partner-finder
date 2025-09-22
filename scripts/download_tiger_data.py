#!/usr/bin/env python3
"""
Download and process TIGER Census data for ZIP to County mapping
Creates a comprehensive database of geographic relationships
"""

import requests
import zipfile
import csv
import json
import os
from pathlib import Path

# Census Bureau TIGER data URLs
TIGER_BASE_URL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020"
ZCTA_TO_COUNTY_URL = f"{TIGER_BASE_URL}/zcta520_county20_natl.txt"

def download_tiger_data():
    """Download TIGER ZCTA to County relationship file"""
    print("Downloading TIGER Census data...")
    
    try:
        response = requests.get(ZCTA_TO_COUNTY_URL, timeout=30)
        response.raise_for_status()
        
        # Save raw data
        data_dir = Path("../data/tiger")
        data_dir.mkdir(parents=True, exist_ok=True)
        
        raw_file = data_dir / "zcta_county_rel.txt"
        with open(raw_file, 'w') as f:
            f.write(response.text)
        
        print(f"Downloaded TIGER data to {raw_file}")
        return raw_file
    
    except Exception as e:
        print(f"Error downloading TIGER data: {e}")
        return None

def parse_tiger_data(file_path):
    """Parse TIGER relationship file into usable format"""
    print("Parsing TIGER data...")
    
    zip_to_county = {}
    county_to_zips = {}
    
    try:
        with open(file_path, 'r') as f:
            # First line contains headers
            headers = f.readline().strip().split('|')
            
            # Find column indices
            zcta_idx = headers.index('ZCTA5_20') if 'ZCTA5_20' in headers else 0
            state_idx = headers.index('STATE_20') if 'STATE_20' in headers else 1
            county_idx = headers.index('COUNTY_20') if 'COUNTY_20' in headers else 2
            county_name_idx = headers.index('NAMELSAD_20') if 'NAMELSAD_20' in headers else 5
            
            for line in f:
                parts = line.strip().split('|')
                if len(parts) > max(zcta_idx, state_idx, county_idx):
                    zip_code = parts[zcta_idx]
                    state_fips = parts[state_idx]
                    county_fips = parts[county_idx]
                    county_name = parts[county_name_idx] if county_name_idx < len(parts) else ''
                    
                    # Create mapping
                    if zip_code:
                        zip_to_county[zip_code] = {
                            'state_fips': state_fips,
                            'county_fips': county_fips,
                            'county_name': county_name.replace(' County', ''),
                            'full_county_name': county_name
                        }
                        
                        # Reverse mapping
                        county_key = f"{state_fips}_{county_fips}"
                        if county_key not in county_to_zips:
                            county_to_zips[county_key] = {
                                'name': county_name,
                                'zips': []
                            }
                        county_to_zips[county_key]['zips'].append(zip_code)
        
        print(f"Parsed {len(zip_to_county)} ZIP codes")
        return zip_to_county, county_to_zips
    
    except Exception as e:
        print(f"Error parsing TIGER data: {e}")
        return {}, {}

def get_state_abbreviations():
    """FIPS state codes to abbreviations"""
    return {
        '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA',
        '08': 'CO', '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL',
        '13': 'GA', '15': 'HI', '16': 'ID', '17': 'IL', '18': 'IN',
        '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME',
        '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN', '28': 'MS',
        '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH',
        '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND',
        '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI',
        '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT',
        '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV', '55': 'WI',
        '56': 'WY'
    }

def enhance_with_city_data(zip_to_county):
    """Add city names using Zippopotam API for major ZIPs"""
    print("Enhancing with city data (sample)...")
    
    state_abbrevs = get_state_abbreviations()
    enhanced = {}
    
    # Sample of important ZIP codes to enhance
    sample_zips = [
        '75201', '75234', '77001', '10001', '90001', '60601',  # Major cities
        '33701', '33755', '33770',  # Pinellas County, FL
        '78701', '94102', '02101', '98101', '85001'  # More major cities
    ]
    
    for zip_code in sample_zips:
        if zip_code in zip_to_county:
            try:
                response = requests.get(f"http://api.zippopotam.us/us/{zip_code}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('places'):
                        place = data['places'][0]
                        
                        county_info = zip_to_county[zip_code]
                        state_fips = county_info['state_fips']
                        
                        enhanced[zip_code] = {
                            'city': place['place name'],
                            'state': place['state'],
                            'state_abbr': state_abbrevs.get(state_fips, ''),
                            'county': county_info['county_name'],
                            'county_fips': f"{state_fips}{county_info['county_fips']}",
                            'lat': place.get('latitude'),
                            'lon': place.get('longitude')
                        }
                        print(f"  {zip_code}: {place['place name']}, {county_info['county_name']}")
            except:
                pass
    
    return enhanced

def save_data(zip_to_county, county_to_zips, enhanced_data):
    """Save processed data to JSON files"""
    data_dir = Path("../data/tiger")
    
    # Save full ZIP to county mapping
    with open(data_dir / "zip_to_county.json", 'w') as f:
        json.dump(zip_to_county, f, indent=2)
    
    # Save county to ZIPs mapping
    with open(data_dir / "county_to_zips.json", 'w') as f:
        json.dump(county_to_zips, f, indent=2)
    
    # Save enhanced sample data
    with open(data_dir / "enhanced_zip_data.json", 'w') as f:
        json.dump(enhanced_data, f, indent=2)
    
    # Create a Python module for easy import
    with open(data_dir / "__init__.py", 'w') as f:
        f.write("""# TIGER Census Data Module
import json
from pathlib import Path

data_dir = Path(__file__).parent

def load_zip_to_county():
    with open(data_dir / 'zip_to_county.json', 'r') as f:
        return json.load(f)

def load_county_to_zips():
    with open(data_dir / 'county_to_zips.json', 'r') as f:
        return json.load(f)

def load_enhanced_data():
    with open(data_dir / 'enhanced_zip_data.json', 'r') as f:
        return json.load(f)

# Load data on import
ZIP_TO_COUNTY = load_zip_to_county()
COUNTY_TO_ZIPS = load_county_to_zips()
ENHANCED_DATA = load_enhanced_data()
""")
    
    print(f"Saved processed data to {data_dir}")

def main():
    """Main processing pipeline"""
    print("TIGER Census Data Processor")
    print("=" * 40)
    
    # Download data
    raw_file = download_tiger_data()
    if not raw_file:
        print("Failed to download data")
        return
    
    # Parse data
    zip_to_county, county_to_zips = parse_tiger_data(raw_file)
    
    if not zip_to_county:
        print("Failed to parse data")
        return
    
    # Enhance with city data
    enhanced_data = enhance_with_city_data(zip_to_county)
    
    # Save processed data
    save_data(zip_to_county, county_to_zips, enhanced_data)
    
    print("\nProcessing complete!")
    print(f"Total ZIP codes: {len(zip_to_county)}")
    print(f"Total counties: {len(county_to_zips)}")
    print(f"Enhanced samples: {len(enhanced_data)}")

if __name__ == "__main__":
    main()