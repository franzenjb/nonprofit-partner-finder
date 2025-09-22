"""
County-based search for better local results
Uses ZIP to County mapping for accurate geographic filtering
"""

from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import urlparse, parse_qs

# ZIP to County mapping (major counties)
ZIP_TO_COUNTY = {
    # Dallas County, TX
    '75201': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75202': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75203': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75204': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75205': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75206': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75207': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75208': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75209': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75210': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75211': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75212': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75214': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75215': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75216': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75217': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75218': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75219': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75220': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75223': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75224': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75225': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75226': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75227': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75228': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75229': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75230': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75231': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75232': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75233': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75234': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75235': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75236': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75237': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75238': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75240': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75241': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75243': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75244': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75246': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75247': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75248': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75249': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75251': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75252': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75253': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    '75254': {'county': 'Dallas County', 'state': 'TX', 'city': 'Dallas'},
    
    # Harris County, TX (Houston)
    '77001': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77002': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77003': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77004': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77005': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77006': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77007': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77008': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77009': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    '77010': {'county': 'Harris County', 'state': 'TX', 'city': 'Houston'},
    
    # Bexar County, TX (San Antonio)
    '78201': {'county': 'Bexar County', 'state': 'TX', 'city': 'San Antonio'},
    '78202': {'county': 'Bexar County', 'state': 'TX', 'city': 'San Antonio'},
    '78203': {'county': 'Bexar County', 'state': 'TX', 'city': 'San Antonio'},
    '78204': {'county': 'Bexar County', 'state': 'TX', 'city': 'San Antonio'},
    '78205': {'county': 'Bexar County', 'state': 'TX', 'city': 'San Antonio'},
    
    # Travis County, TX (Austin)
    '78701': {'county': 'Travis County', 'state': 'TX', 'city': 'Austin'},
    '78702': {'county': 'Travis County', 'state': 'TX', 'city': 'Austin'},
    '78703': {'county': 'Travis County', 'state': 'TX', 'city': 'Austin'},
    '78704': {'county': 'Travis County', 'state': 'TX', 'city': 'Austin'},
    '78705': {'county': 'Travis County', 'state': 'TX', 'city': 'Austin'},
    
    # El Paso County, TX
    '79901': {'county': 'El Paso County', 'state': 'TX', 'city': 'El Paso'},
    '79902': {'county': 'El Paso County', 'state': 'TX', 'city': 'El Paso'},
    '79903': {'county': 'El Paso County', 'state': 'TX', 'city': 'El Paso'},
    '79904': {'county': 'El Paso County', 'state': 'TX', 'city': 'El Paso'},
    '79905': {'county': 'El Paso County', 'state': 'TX', 'city': 'El Paso'},
    
    # Pinellas County, FL
    '33701': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33702': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33703': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33704': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33705': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33706': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33707': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33708': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33709': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33710': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33711': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33712': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33713': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33714': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33715': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33716': {'county': 'Pinellas County', 'state': 'FL', 'city': 'St Petersburg'},
    '33755': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33756': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33757': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33758': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33759': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33760': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33761': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33762': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33763': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33764': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33765': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33767': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Clearwater'},
    '33770': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Largo'},
    '33771': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Largo'},
    '33773': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Largo'},
    '33774': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Largo'},
    '33778': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Largo'},
    '33779': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Largo'},
    '33781': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Pinellas Park'},
    '33782': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Pinellas Park'},
    '33784': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Pinellas Park'},
    '34683': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Palm Harbor'},
    '34684': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Palm Harbor'},
    '34685': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Palm Harbor'},
    '34698': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Dunedin'},
    '33785': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Indian Rocks Beach'},
    '33786': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Belleair Beach'},
    '33706': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Treasure Island'},
    '33715': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Tierra Verde'},
    '33776': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Seminole'},
    '33777': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Seminole'},
    '33772': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Seminole'},
    '34695': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Safety Harbor'},
    '34677': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Oldsmar'},
    '34689': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Tarpon Springs'},
    '34688': {'county': 'Pinellas County', 'state': 'FL', 'city': 'Tarpon Springs'},
    
    # Miami-Dade County, FL
    '33101': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33102': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33109': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami Beach'},
    '33110': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33111': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33112': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33125': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33126': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33127': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33128': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33129': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33130': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33131': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33132': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33133': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33134': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33135': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33136': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33137': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33138': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami'},
    '33139': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami Beach'},
    '33140': {'county': 'Miami-Dade County', 'state': 'FL', 'city': 'Miami Beach'},
    
    # New York County (Manhattan), NY
    '10001': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10002': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10003': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10004': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10005': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10006': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10007': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10009': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10010': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10011': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10012': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10013': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10014': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10016': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10017': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10018': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10019': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10020': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10021': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10022': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10023': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10024': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10025': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10026': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10027': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10028': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    '10029': {'county': 'New York County', 'state': 'NY', 'city': 'New York'},
    
    # Los Angeles County, CA
    '90001': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90002': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90003': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90004': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90005': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90006': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90007': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90008': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90010': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90011': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90012': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90013': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90014': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90015': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90016': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90017': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90018': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90019': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90020': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90021': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Los Angeles'},
    '90210': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Beverly Hills'},
    '90211': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Beverly Hills'},
    '90212': {'county': 'Los Angeles County', 'state': 'CA', 'city': 'Beverly Hills'},
    
    # Cook County, IL (Chicago)
    '60601': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60602': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60603': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60604': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60605': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60606': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60607': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60608': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60609': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60610': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60611': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60612': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60613': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60614': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60615': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60616': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60617': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60618': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60619': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
    '60620': {'county': 'Cook County', 'state': 'IL', 'city': 'Chicago'},
}

# Cities in each county for filtering
COUNTY_CITIES = {
    'Dallas County': ['Dallas', 'Richardson', 'Plano', 'Irving', 'Garland', 'Mesquite', 
                      'Carrollton', 'Grand Prairie', 'DeSoto', 'Cedar Hill', 'Duncanville',
                      'Lancaster', 'Farmers Branch', 'Balch Springs', 'Coppell', 'Glenn Heights',
                      'Highland Park', 'Addison', 'University Park', 'Sachse', 'Rowlett'],
    'Harris County': ['Houston', 'Pasadena', 'Baytown', 'La Porte', 'Deer Park', 
                      'Bellaire', 'West University Place', 'Humble', 'Katy', 'Spring',
                      'Cypress', 'Tomball', 'Jersey Village'],
    'Bexar County': ['San Antonio', 'Leon Valley', 'Alamo Heights', 'Balcones Heights',
                     'Castle Hills', 'Converse', 'Fair Oaks Ranch', 'Helotes', 'Hill Country Village',
                     'Hollywood Park', 'Kirby', 'Live Oak', 'Olmos Park', 'Schertz', 'Selma',
                     'Shavano Park', 'Terrell Hills', 'Universal City', 'Windcrest'],
    'Travis County': ['Austin', 'Pflugerville', 'Lakeway', 'Cedar Park', 'Bee Cave',
                      'Lago Vista', 'Manor', 'Rollingwood', 'Sunset Valley', 'West Lake Hills'],
    'El Paso County': ['El Paso', 'Socorro', 'Horizon City', 'San Elizario', 'Clint',
                       'Anthony', 'Vinton', 'Canutillo', 'Fort Bliss'],
    'Pinellas County': ['St Petersburg', 'Clearwater', 'Largo', 'Pinellas Park', 'Seminole',
                        'Dunedin', 'Tarpon Springs', 'Safety Harbor', 'Oldsmar', 'Palm Harbor',
                        'Gulfport', 'St Pete Beach', 'Treasure Island', 'Madeira Beach',
                        'Indian Rocks Beach', 'Indian Shores', 'Kenneth City', 'South Pasadena',
                        'Redington Beach', 'Redington Shores', 'North Redington Beach',
                        'Belleair', 'Belleair Beach', 'Belleair Bluffs', 'Belleair Shore'],
    'Miami-Dade County': ['Miami', 'Miami Beach', 'Coral Gables', 'Hialeah', 'Miami Gardens',
                          'Homestead', 'Aventura', 'Doral', 'Cutler Bay', 'Miami Lakes',
                          'Palmetto Bay', 'Sunny Isles Beach', 'North Miami', 'North Miami Beach',
                          'Key Biscayne', 'Bal Harbour', 'Bay Harbor Islands', 'Biscayne Park',
                          'Coral Gables', 'El Portal', 'Florida City', 'Golden Beach',
                          'Hialeah Gardens', 'Indian Creek', 'Medley', 'Miami Shores',
                          'Miami Springs', 'North Bay Village', 'Opa-locka', 'Pinecrest',
                          'South Miami', 'Surfside', 'Sweetwater', 'Virginia Gardens',
                          'West Miami'],
    'New York County': ['New York', 'Manhattan'],
    'Los Angeles County': ['Los Angeles', 'Long Beach', 'Glendale', 'Santa Clarita', 'Pasadena',
                           'Torrance', 'Pomona', 'Palmdale', 'Lancaster', 'West Covina',
                           'Norwalk', 'El Monte', 'Downey', 'Inglewood', 'Burbank',
                           'Santa Monica', 'Beverly Hills', 'Whittier', 'Carson', 'Compton',
                           'Alhambra', 'Lakewood', 'Bellflower', 'Baldwin Park', 'Lynwood',
                           'Redondo Beach', 'Montebello', 'Pico Rivera', 'Monterey Park',
                           'Gardena', 'Huntington Park', 'Arcadia', 'Diamond Bar', 'Paramount'],
    'Cook County': ['Chicago', 'Evanston', 'Skokie', 'Oak Park', 'Cicero', 'Berwyn',
                    'Schaumburg', 'Palatine', 'Des Plaines', 'Orland Park', 'Oak Lawn',
                    'Mount Prospect', 'Hoffman Estates', 'Tinley Park', 'Arlington Heights',
                    'Elgin', 'Joliet', 'Naperville', 'Aurora', 'Waukegan', 'Park Ridge',
                    'Calumet City', 'Wilmette', 'Maywood', 'Oak Forest', 'Harvey',
                    'Blue Island', 'Dolton', 'Elmwood Park', 'Alsip'],
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests with county-based filtering"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/county-search':
            params = parse_qs(parsed_path.query)
            zip_code = params.get('zip', [''])[0]
            keyword = params.get('q', [''])[0]
            
            if not zip_code or not keyword:
                self.send_error(400, "Missing zip or keyword")
                return
            
            results = self.search_by_county(zip_code, keyword)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            return
        
        self.send_error(404, "Endpoint not found")
    
    def search_by_county(self, zip_code, keyword):
        """Search for nonprofits in the same county"""
        # Get county info from ZIP
        county_info = ZIP_TO_COUNTY.get(zip_code)
        
        if not county_info:
            # Try to get state at least
            zip_prefix = zip_code[:3]
            state_map = {
                '750': 'TX', '751': 'TX', '752': 'TX', '753': 'TX', '754': 'TX',
                '755': 'TX', '756': 'TX', '757': 'TX', '758': 'TX', '759': 'TX',
                '337': 'FL', '346': 'FL', '347': 'FL', '336': 'FL', '334': 'FL',
                '100': 'NY', '101': 'NY', '102': 'NY', '103': 'NY', '104': 'NY',
                '900': 'CA', '901': 'CA', '902': 'CA', '903': 'CA', '904': 'CA',
                '606': 'IL', '607': 'IL', '608': 'IL', '609': 'IL', '610': 'IL',
            }
            
            state = state_map.get(zip_prefix)
            if state:
                # Search with state context
                return self.search_with_state(keyword, state, zip_code)
            
            return {
                'error': f'ZIP code {zip_code} not in database',
                'suggestion': f'Try searching for "{keyword}" without ZIP code',
                'results': []
            }
        
        county = county_info['county']
        state = county_info['state']
        city = county_info['city']
        
        # Get all cities in the county
        county_cities = COUNTY_CITIES.get(county, [city])
        
        # Search ProPublica with keyword + state
        url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
        params = {'q': f"{keyword} {state}"}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Filter to organizations in the same county
            local_results = []
            nearby_results = []
            other_state_results = []
            
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
                
                # Check if in same county
                is_in_county = False
                for county_city in county_cities:
                    if county_city.lower() in org_city.lower():
                        is_in_county = True
                        org_data['location_match'] = 'Same County'
                        org_data['distance_score'] = 100
                        break
                
                if is_in_county:
                    local_results.append(org_data)
                elif org_state == state:
                    org_data['location_match'] = 'Same State'
                    org_data['distance_score'] = 50
                    nearby_results.append(org_data)
                else:
                    org_data['location_match'] = 'Other State'
                    org_data['distance_score'] = 10
                    other_state_results.append(org_data)
            
            # Sort each group by name
            local_results.sort(key=lambda x: x['name'])
            nearby_results.sort(key=lambda x: x['name'])
            
            # Combine results: local first, then nearby
            all_results = local_results[:20] + nearby_results[:10]
            
            return {
                'zip_code': zip_code,
                'county': county,
                'city': city,
                'state': state,
                'keyword': keyword,
                'local_count': len(local_results),
                'total_count': len(data.get('organizations', [])),
                'results': all_results,
                'message': f"Found {len(local_results)} organizations in {county}, {len(nearby_results)} others in {state}"
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'results': []
            }
    
    def search_with_state(self, keyword, state, zip_code):
        """Fallback search with just state"""
        url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
        params = {'q': f"{keyword} {state}"}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for org in data.get('organizations', [])[:30]:
                results.append({
                    'ein': str(org['ein']),
                    'name': org['name'],
                    'city': org.get('city', ''),
                    'state': org.get('state', ''),
                    'ntee_code': org.get('ntee_code'),
                    'location_match': 'State Search',
                })
            
            return {
                'zip_code': zip_code,
                'state': state,
                'keyword': keyword,
                'results': results,
                'message': f"Showing results for '{keyword}' in {state} (ZIP code {zip_code} not in detailed database)"
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