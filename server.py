import os
import time
import json
from utils import choices_referers, choices_user_agents
import warnings
import random
import ssl
import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPProxyAuth
import cloudscraper
from bs4 import BeautifulSoup
from typing import TypedDict, Optional
from fastapi import FastAPI, Query
import urllib.parse

warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Your authenticated proxy configuration
PROXY_HOST = 'rp.scrapegw.com'
PROXY_PORT = '6060'
PROXY_USERNAME = 'jerqt29a3ed8bsf'
PROXY_PASSWORD = 'dak10zt8xlywba9'

class GetHTMLResult(TypedDict):
    success: bool
    error: Optional[str]
    data: Optional[str]

class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.options |= 0x4
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

def get_authenticated_proxy() -> dict:
    """Get your authenticated proxy configuration"""
    proxy_url = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"
    return {
        "http": proxy_url,
        "https": proxy_url
    }

def get_realistic_headers(url: str) -> dict:
    """Generate realistic browser headers"""
    domain = urllib.parse.urlparse(url).netloc
    
    return {
        'User-Agent': random.choice(choices_user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Referer': random.choice(choices_referers)
    }

def get_html(url: str, use_proxy: bool = True, method: str = "auto") -> GetHTMLResult:
    """
    Main function to get HTML with multiple bypass methods
    method options: 'auto', 'basic', 'cloudscraper', 'session', 'stealth'
    """
    if method == "auto":
        # Try different methods in order
        methods = ["basic", "cloudscraper", "stealth", "session"]
        for m in methods:
            result = get_html(url, use_proxy, m)
            if result["success"]:
                return result
        # If all methods fail, return the last error
        return result
    
    if method == "basic":
        return _try_basic_request(url, use_proxy)
    elif method == "cloudscraper":
        return _try_cloudscraper(url, use_proxy)
    elif method == "stealth":
        return _try_stealth_request(url, use_proxy)
    elif method == "session":
        return _try_session_request(url, use_proxy)
    else:
        return _try_basic_request(url, use_proxy)

def _try_basic_request(url: str, use_proxy: bool) -> GetHTMLResult:
    """Basic request with realistic headers"""
    try:
        headers = get_realistic_headers(url)
        
        if use_proxy:
            proxies = get_authenticated_proxy()
            response = requests.get(url, headers=headers, proxies=proxies, timeout=60)
        else:
            response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return {
                "success": True,
                "error": None,
                "data": response.text
            }
        else:
            return {
                "success": False,
                "error": f"Basic request failed - Status: {response.status_code}",
                "data": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Basic request error: {str(e)}",
            "data": None
        }

def _try_cloudscraper(url: str, use_proxy: bool) -> GetHTMLResult:
    """Enhanced cloudscraper with multiple browser profiles"""
    cloud_scraper = None
    
    # Try different browser configurations
    browser_configs = [
        {'browser': 'chrome', 'platform': 'windows', 'mobile': False},
        {'browser': 'firefox', 'platform': 'windows', 'mobile': False},
        {'browser': 'chrome', 'platform': 'darwin', 'mobile': False},
        {'browser': 'safari', 'platform': 'darwin', 'mobile': False},
    ]
    
    for browser_config in browser_configs:
        try:
            cloud_scraper = cloudscraper.create_scraper(browser=browser_config)
            
            # Enhanced headers
            headers = get_realistic_headers(url)
            cloud_scraper.headers.update(headers)
            
            # Add delay to seem more human
            time.sleep(random.uniform(1, 3))
            
            if use_proxy:
                proxies = get_authenticated_proxy()
                response = cloud_scraper.get(url, proxies=proxies, timeout=60)
            else:
                response = cloud_scraper.get(url, timeout=30)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "error": None,
                    "data": response.text
                }
            elif response.status_code == 403:
                # Try next browser config
                continue
                
        except Exception as e:
            if "browser_config" in str(e).lower():
                continue
            else:
                break
        finally:
            if cloud_scraper:
                cloud_scraper.close()
                cloud_scraper = None
    
    return {
        "success": False,
        "error": "All cloudscraper attempts failed",
        "data": None
    }

def _try_stealth_request(url: str, use_proxy: bool) -> GetHTMLResult:
    """Stealth request that mimics real browser behavior"""
    session = None
    try:
        session = requests.Session()
        
        # Set realistic headers
        headers = get_realistic_headers(url)
        session.headers.update(headers)
        
        if use_proxy:
            session.proxies = get_authenticated_proxy()
        
        # First, visit the domain root to establish session
        domain_url = f"{urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}"
        
        try:
            # Visit homepage first
            time.sleep(random.uniform(1, 2))
            session.get(domain_url, timeout=30)
            
            # Add some cookies that might help
            session.cookies.set('cf_clearance', 'dummy_value')
            
        except:
            pass  # Continue even if homepage visit fails
        
        # Now visit the actual URL
        time.sleep(random.uniform(2, 4))
        response = session.get(url, timeout=60)
        
        if response.status_code == 200:
            return {
                "success": True,
                "error": None,
                "data": response.text
            }
        else:
            return {
                "success": False,
                "error": f"Stealth request failed - Status: {response.status_code}",
                "data": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Stealth request error: {str(e)}",
            "data": None
        }
    finally:
        if session:
            session.close()

def _try_session_request(url: str, use_proxy: bool) -> GetHTMLResult:
    """Session-based request with SSL handling"""
    session = None
    try:
        session = requests.Session()
        session.mount('https://', SSLAdapter())
        
        headers = get_realistic_headers(url)
        session.headers.update(headers)
        
        if use_proxy:
            session.proxies = get_authenticated_proxy()
        
        # Multiple attempts with different approaches
        attempts = [
            {"verify": True},
            {"verify": False},
            {"verify": False, "allow_redirects": True, "stream": True}
        ]
        
        for attempt_config in attempts:
            try:
                time.sleep(random.uniform(1, 2))
                response = session.get(url, timeout=60, **attempt_config)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "error": None,
                        "data": response.text
                    }
                    
            except requests.exceptions.SSLError:
                continue
            except Exception:
                continue
        
        return {
            "success": False,
            "error": "All session attempts failed",
            "data": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Session request error: {str(e)}",
            "data": None
        }
    finally:
        if session:
            session.close()

# Alternative: Try with different TLS settings
def _try_with_custom_tls(url: str, use_proxy: bool) -> GetHTMLResult:
    """Try with custom TLS configuration"""
    try:
        import ssl
        import urllib3
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context
        
        # Custom SSL context
        class CustomHTTPAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                context = create_urllib3_context()
                context.set_ciphers('DEFAULT@SECLEVEL=1')
                kwargs['ssl_context'] = context
                return super().init_poolmanager(*args, **kwargs)
        
        session = requests.Session()
        session.mount('https://', CustomHTTPAdapter())
        
        headers = get_realistic_headers(url)
        
        if use_proxy:
            proxies = get_authenticated_proxy()
            response = session.get(url, headers=headers, proxies=proxies, timeout=60)
        else:
            response = session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return {
                "success": True,
                "error": None,
                "data": response.text
            }
        else:
            return {
                "success": False,
                "error": f"Custom TLS failed - Status: {response.status_code}",
                "data": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Custom TLS error: {str(e)}",
            "data": None
        }

# FastAPI app
app = FastAPI(title="Advanced Web Scraper API", description="Advanced web scraping with Cloudflare bypass")

@app.get("/get-html", response_model=GetHTMLResult)
def get_html_wrapper(
    url: str = Query(..., description="URL to scrape"),
    use_proxy: bool = Query(True, description="Whether to use authenticated proxy"),
    method: str = Query("auto", description="Scraping method: auto, basic, cloudscraper, stealth, session")
) -> GetHTMLResult:
    """
    Advanced web scraping with multiple bypass methods
    
    - **url**: The URL to scrape
    - **use_proxy**: Whether to use the authenticated proxy (default: True)
    - **method**: Scraping method to use (default: auto)
    """
    return get_html(url, use_proxy, method)

@app.get("/")
def root():
    return {
        "message": "Advanced Web Scraper API", 
        "endpoints": ["/get-html", "/docs"],
        "methods": ["auto", "basic", "cloudscraper", "stealth", "session"]
    }

# Environment variable support
if os.getenv("PROXY_USERNAME"):
    PROXY_USERNAME = os.getenv("PROXY_USERNAME")
if os.getenv("PROXY_PASSWORD"):
    PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
if os.getenv("PROXY_HOST"):
    PROXY_HOST = os.getenv("PROXY_HOST")
if os.getenv("PROXY_PORT"):
    PROXY_PORT = os.getenv("PROXY_PORT")
