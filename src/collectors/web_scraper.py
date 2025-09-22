import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import logging
from typing import Dict, List, Optional, Set
import time
import re
from datetime import datetime

from src.models.nonprofit import Nonprofit, DataSource


logger = logging.getLogger(__name__)


class NonprofitWebScraper:
    """
    Web scraper for nonprofit organization websites
    Extracts mission, programs, leadership, and contact information
    """
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; NonprofitAnalyzer/1.0; Red Cross Partner Finder)'
        })
    
    def scrape_nonprofit_website(self, nonprofit: Nonprofit) -> Dict[str, Any]:
        """
        Scrape comprehensive data from nonprofit website
        """
        if not nonprofit.website:
            logger.warning(f"No website URL for {nonprofit.name}")
            return {}
        
        try:
            # Clean up URL
            url = self._normalize_url(nonprofit.website)
            
            # Get main page
            main_page = self._fetch_page(url)
            if not main_page:
                return {}
            
            # Extract data from main page
            data = {
                'mission': self._extract_mission(main_page, url),
                'programs': self._extract_programs(main_page, url),
                'leadership': self._extract_leadership(main_page, url),
                'contact': self._extract_contact(main_page),
                'news': self._extract_recent_news(main_page, url),
                'social_media': self._extract_social_links(main_page)
            }
            
            # Try to find and parse About page
            about_url = self._find_about_page(main_page, url)
            if about_url:
                time.sleep(self.delay)
                about_page = self._fetch_page(about_url)
                if about_page:
                    self._update_data_from_about(data, about_page, about_url)
            
            # Update nonprofit object
            if data['mission'] and not nonprofit.mission_statement:
                nonprofit.mission_statement = data['mission']
            
            if data['programs']:
                nonprofit.programs.extend(data['programs'])
                nonprofit.programs = list(set(nonprofit.programs))  # Remove duplicates
            
            if data['leadership']:
                nonprofit.leadership.extend(data['leadership'])
            
            if data['contact']:
                if data['contact'].get('email') and not nonprofit.email:
                    nonprofit.email = data['contact']['email']
                if data['contact'].get('phone') and not nonprofit.phone:
                    nonprofit.phone = data['contact']['phone']
            
            nonprofit.data_sources.append(DataSource.WEBSITE)
            nonprofit.last_updated = datetime.now()
            
            return data
            
        except Exception as e:
            logger.error(f"Error scraping website for {nonprofit.name}: {e}")
            return {}
    
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a web page
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to ensure proper format
        """
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url.rstrip('/')
    
    def _extract_mission(self, soup: BeautifulSoup, base_url: str) -> str:
        """
        Extract mission statement from website
        """
        mission = ""
        
        # Look for common mission statement patterns
        mission_patterns = [
            {'class': re.compile('mission', re.I)},
            {'id': re.compile('mission', re.I)},
            {'class': re.compile('about', re.I)},
        ]
        
        for pattern in mission_patterns:
            element = soup.find(['div', 'section', 'p'], pattern)
            if element:
                text = element.get_text(strip=True)
                if len(text) > 50 and len(text) < 2000:
                    mission = text
                    break
        
        # Look for mission in meta tags
        if not mission:
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                mission = meta_desc['content']
        
        return mission
    
    def _extract_programs(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract program/service information
        """
        programs = []
        
        # Look for programs/services sections
        program_sections = soup.find_all(['div', 'section'], 
                                        class_=re.compile('(program|service)', re.I))
        
        for section in program_sections[:5]:  # Limit to avoid too much noise
            # Look for list items or headers
            items = section.find_all(['h3', 'h4', 'li'])
            for item in items[:10]:
                text = item.get_text(strip=True)
                if 10 < len(text) < 100:
                    programs.append(text)
        
        # Also check navigation menu for program pages
        nav = soup.find('nav')
        if nav:
            links = nav.find_all('a', href=re.compile('(program|service)', re.I))
            for link in links[:10]:
                text = link.get_text(strip=True)
                if text and len(text) < 50:
                    programs.append(text)
        
        return list(set(programs))  # Remove duplicates
    
    def _extract_leadership(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """
        Extract leadership/board information
        """
        leadership = []
        
        # Look for leadership sections
        leader_sections = soup.find_all(['div', 'section'], 
                                       class_=re.compile('(leader|board|staff|team)', re.I))
        
        for section in leader_sections[:3]:
            # Look for person cards or lists
            people = section.find_all(['div', 'li'], class_=re.compile('(person|member|staff)', re.I))
            
            for person in people[:20]:
                name_elem = person.find(['h3', 'h4', 'strong', 'b'])
                title_elem = person.find(['p', 'span'], class_=re.compile('(title|position|role)', re.I))
                
                if name_elem:
                    leader = {
                        'name': name_elem.get_text(strip=True),
                        'title': title_elem.get_text(strip=True) if title_elem else ''
                    }
                    if leader['name']:
                        leadership.append(leader)
        
        return leadership
    
    def _extract_contact(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract contact information
        """
        contact = {}
        
        # Email
        email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
        email_matches = email_pattern.findall(str(soup))
        if email_matches:
            # Filter out common non-contact emails
            for email in email_matches:
                if not any(x in email.lower() for x in ['example', 'domain', 'email']):
                    contact['email'] = email
                    break
        
        # Phone
        phone_pattern = re.compile(r'[\(]?\d{3}[\)]?[-\s]?\d{3}[-\s]?\d{4}')
        phone_matches = phone_pattern.findall(str(soup))
        if phone_matches:
            contact['phone'] = phone_matches[0]
        
        # Address - look for address tags or schema.org markup
        address_elem = soup.find(['address', 'div'], {'itemtype': 'http://schema.org/PostalAddress'})
        if address_elem:
            contact['address'] = address_elem.get_text(strip=True)
        
        return contact
    
    def _extract_recent_news(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """
        Extract recent news/updates
        """
        news = []
        
        # Look for news/blog sections
        news_sections = soup.find_all(['div', 'section'], 
                                     class_=re.compile('(news|blog|update|announce)', re.I))
        
        for section in news_sections[:2]:
            articles = section.find_all(['article', 'div'], limit=5)
            
            for article in articles:
                title_elem = article.find(['h2', 'h3', 'h4'])
                date_elem = article.find(['time', 'span'], class_=re.compile('date', re.I))
                
                if title_elem:
                    news_item = {
                        'title': title_elem.get_text(strip=True),
                        'date': date_elem.get_text(strip=True) if date_elem else '',
                        'url': ''
                    }
                    
                    # Get link if available
                    link = article.find('a')
                    if link and link.get('href'):
                        news_item['url'] = urljoin(base_url, link['href'])
                    
                    news.append(news_item)
        
        return news
    
    def _extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract social media links
        """
        social = {}
        
        social_patterns = {
            'facebook': re.compile(r'facebook\.com/[\w\.-]+', re.I),
            'twitter': re.compile(r'twitter\.com/[\w\.-]+', re.I),
            'linkedin': re.compile(r'linkedin\.com/[\w\.-/]+', re.I),
            'instagram': re.compile(r'instagram\.com/[\w\.-]+', re.I),
            'youtube': re.compile(r'youtube\.com/[\w\.-]+', re.I)
        }
        
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            for platform, pattern in social_patterns.items():
                if platform not in social and pattern.search(href):
                    social[platform] = href
        
        return social
    
    def _find_about_page(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Find the About page URL
        """
        about_links = soup.find_all('a', text=re.compile(r'^about', re.I))
        
        for link in about_links:
            href = link.get('href')
            if href:
                return urljoin(base_url, href)
        
        # Try href pattern
        about_links = soup.find_all('a', href=re.compile(r'/about', re.I))
        if about_links:
            return urljoin(base_url, about_links[0]['href'])
        
        return None
    
    def _update_data_from_about(self, data: Dict, soup: BeautifulSoup, url: str):
        """
        Update data dictionary with information from About page
        """
        # Try to get better mission statement
        if not data['mission'] or len(data['mission']) < 100:
            mission = self._extract_mission(soup, url)
            if mission and len(mission) > len(data.get('mission', '')):
                data['mission'] = mission
        
        # Get more leadership info
        leadership = self._extract_leadership(soup, url)
        if leadership:
            existing_names = {l['name'] for l in data.get('leadership', [])}
            for leader in leadership:
                if leader['name'] not in existing_names:
                    data['leadership'].append(leader)