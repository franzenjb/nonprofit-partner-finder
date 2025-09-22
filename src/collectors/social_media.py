import tweepy
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from src.models.nonprofit import SocialMediaPresence, DataSource


logger = logging.getLogger(__name__)
load_dotenv()


class SocialMediaCollector:
    """
    Collects and analyzes social media presence of nonprofits
    """
    
    def __init__(self):
        # Twitter/X API setup
        self.twitter_client = None
        self._setup_twitter()
        
        # Facebook Graph API
        self.fb_access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
    
    def _setup_twitter(self):
        """
        Initialize Twitter API client
        """
        try:
            auth = tweepy.OAuthHandler(
                os.getenv('TWITTER_API_KEY'),
                os.getenv('TWITTER_API_SECRET')
            )
            auth.set_access_token(
                os.getenv('TWITTER_ACCESS_TOKEN'),
                os.getenv('TWITTER_ACCESS_SECRET')
            )
            self.twitter_client = tweepy.API(auth, wait_on_rate_limit=True)
        except Exception as e:
            logger.warning(f"Twitter API setup failed: {e}")
    
    def analyze_social_presence(self, nonprofit_name: str, 
                               social_links: Dict[str, str]) -> List[SocialMediaPresence]:
        """
        Analyze social media presence across platforms
        """
        presence = []
        
        # Twitter/X
        if 'twitter' in social_links:
            twitter_data = self._analyze_twitter(social_links['twitter'])
            if twitter_data:
                presence.append(twitter_data)
        
        # Facebook
        if 'facebook' in social_links:
            fb_data = self._analyze_facebook(social_links['facebook'])
            if fb_data:
                presence.append(fb_data)
        
        # LinkedIn
        if 'linkedin' in social_links:
            linkedin_data = self._analyze_linkedin(social_links['linkedin'])
            if linkedin_data:
                presence.append(linkedin_data)
        
        # Instagram
        if 'instagram' in social_links:
            insta_data = self._analyze_instagram(social_links['instagram'])
            if insta_data:
                presence.append(insta_data)
        
        return presence
    
    def _analyze_twitter(self, twitter_url: str) -> Optional[SocialMediaPresence]:
        """
        Analyze Twitter/X account
        """
        if not self.twitter_client:
            return None
        
        try:
            # Extract username from URL
            username = twitter_url.split('/')[-1].replace('@', '')
            
            # Get user data
            user = self.twitter_client.get_user(screen_name=username)
            
            # Get recent tweets for engagement analysis
            tweets = self.twitter_client.user_timeline(
                screen_name=username, 
                count=100, 
                exclude_replies=True, 
                include_rts=False
            )
            
            # Calculate engagement rate
            total_engagement = sum(t.favorite_count + t.retweet_count for t in tweets)
            avg_engagement = total_engagement / len(tweets) if tweets else 0
            engagement_rate = (avg_engagement / user.followers_count * 100) if user.followers_count > 0 else 0
            
            # Get last post date
            last_post_date = tweets[0].created_at if tweets else None
            
            # Simple sentiment analysis (would use proper NLP in production)
            sentiment = self._calculate_sentiment(tweets)
            
            return SocialMediaPresence(
                platform='twitter',
                handle=f"@{username}",
                followers=user.followers_count,
                engagement_rate=engagement_rate,
                last_post_date=last_post_date,
                verified=user.verified,
                sentiment_score=sentiment
            )
            
        except Exception as e:
            logger.debug(f"Twitter analysis failed for {twitter_url}: {e}")
            return None
    
    def _analyze_facebook(self, facebook_url: str) -> Optional[SocialMediaPresence]:
        """
        Analyze Facebook page
        """
        if not self.fb_access_token:
            return None
        
        try:
            # Extract page name/ID from URL
            page_id = facebook_url.split('/')[-1]
            
            # Facebook Graph API request
            url = f"https://graph.facebook.com/v18.0/{page_id}"
            params = {
                'fields': 'name,followers_count,fan_count,engagement,verification_status',
                'access_token': self.fb_access_token
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Get recent posts for engagement
            posts_url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
            posts_params = {
                'fields': 'created_time,likes.summary(true),comments.summary(true),shares',
                'limit': 25,
                'access_token': self.fb_access_token
            }
            
            posts_response = requests.get(posts_url, params=posts_params)
            posts_data = posts_response.json() if posts_response.status_code == 200 else {'data': []}
            
            # Calculate engagement
            followers = data.get('followers_count', data.get('fan_count', 0))
            engagement_rate = 0
            last_post_date = None
            
            if posts_data.get('data'):
                posts = posts_data['data']
                total_engagement = sum(
                    post.get('likes', {}).get('summary', {}).get('total_count', 0) +
                    post.get('comments', {}).get('summary', {}).get('total_count', 0) +
                    (post.get('shares', {}).get('count', 0) if 'shares' in post else 0)
                    for post in posts
                )
                avg_engagement = total_engagement / len(posts) if posts else 0
                engagement_rate = (avg_engagement / followers * 100) if followers > 0 else 0
                
                if posts[0].get('created_time'):
                    last_post_date = datetime.fromisoformat(posts[0]['created_time'].replace('Z', '+00:00'))
            
            return SocialMediaPresence(
                platform='facebook',
                handle=data.get('name', page_id),
                followers=followers,
                engagement_rate=engagement_rate,
                last_post_date=last_post_date,
                verified=data.get('verification_status') == 'blue_verified'
            )
            
        except Exception as e:
            logger.debug(f"Facebook analysis failed for {facebook_url}: {e}")
            return None
    
    def _analyze_linkedin(self, linkedin_url: str) -> Optional[SocialMediaPresence]:
        """
        Analyze LinkedIn page (limited without API access)
        """
        # LinkedIn API requires OAuth and company admin access
        # This is a placeholder for basic data collection
        try:
            # Would need proper LinkedIn API access
            # For now, return basic structure
            company_handle = linkedin_url.split('/')[-1]
            
            return SocialMediaPresence(
                platform='linkedin',
                handle=company_handle,
                followers=0,  # Would need API access
                engagement_rate=0.0,
                last_post_date=None,
                verified=False
            )
        except Exception as e:
            logger.debug(f"LinkedIn analysis failed for {linkedin_url}: {e}")
            return None
    
    def _analyze_instagram(self, instagram_url: str) -> Optional[SocialMediaPresence]:
        """
        Analyze Instagram account (requires Instagram Basic Display API)
        """
        try:
            # Instagram API requires Facebook app approval
            # This is a placeholder
            username = instagram_url.split('/')[-1].rstrip('/')
            
            return SocialMediaPresence(
                platform='instagram',
                handle=f"@{username}",
                followers=0,  # Would need API access
                engagement_rate=0.0,
                last_post_date=None,
                verified=False
            )
        except Exception as e:
            logger.debug(f"Instagram analysis failed for {instagram_url}: {e}")
            return None
    
    def _calculate_sentiment(self, tweets) -> float:
        """
        Calculate sentiment score from tweets
        Simplified version - would use proper NLP in production
        """
        if not tweets:
            return 0.5
        
        positive_words = {'help', 'support', 'thank', 'grateful', 'amazing', 'wonderful', 
                         'excellent', 'success', 'achieve', 'volunteer', 'donate', 'impact'}
        negative_words = {'crisis', 'urgent', 'emergency', 'need', 'struggle', 'difficult',
                         'challenge', 'problem', 'issue', 'concern'}
        
        total_score = 0
        for tweet in tweets:
            text = tweet.text.lower()
            positive_count = sum(1 for word in positive_words if word in text)
            negative_count = sum(1 for word in negative_words if word in text)
            
            # Simple scoring: +1 for positive, -0.5 for negative (crisis words are expected)
            tweet_score = positive_count - (negative_count * 0.5)
            total_score += tweet_score
        
        # Normalize to 0-1 scale
        avg_score = total_score / len(tweets)
        normalized_score = (avg_score + 5) / 10  # Assuming scores range from -5 to +5
        
        return max(0.0, min(1.0, normalized_score))
    
    def search_social_accounts(self, nonprofit_name: str) -> Dict[str, str]:
        """
        Search for nonprofit social media accounts by name
        """
        accounts = {}
        
        # Search Twitter
        if self.twitter_client:
            try:
                users = self.twitter_client.search_users(q=nonprofit_name, count=5)
                if users:
                    # Take first verified account or first result
                    for user in users:
                        if user.verified:
                            accounts['twitter'] = f"https://twitter.com/{user.screen_name}"
                            break
                    if 'twitter' not in accounts and users:
                        accounts['twitter'] = f"https://twitter.com/{users[0].screen_name}"
            except Exception as e:
                logger.debug(f"Twitter search failed for {nonprofit_name}: {e}")
        
        # Would add similar searches for other platforms with API access
        
        return accounts