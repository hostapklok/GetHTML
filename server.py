import os
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

def get_proxy_auth():
    """Get proxy authentication object"""
    return HTTPProxyAuth(PROXY_USERNAME, PROXY_PASSWORD)

def get_html(url: str, use_proxy: bool = True) -> GetHTMLResult:
    """Main function to get HTML with optional proxy usage"""
    response = None
    try:
        headers = {
            'User-Agent': random.choice(choices_user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': random.choice(choices_referers)
        }
        
        if use_proxy:
            proxies = get_authenticated_proxy()
            response = requests.get(url, headers=headers, proxies=proxies, timeout=60)
        else:
            response = requests.get(url, headers=headers, timeout=30)
        
        result = _check_response(response, url)
        return result
        
    except requests.exceptions.ProxyError as e:
        if response:
            response.close()
        # If proxy fails, try without proxy
        if use_proxy:
            return get_html(url, use_proxy=False)
        else:
            return {
                "success": False,
                "error": f"Proxy error: {str(e)}",
                "data": None
            }
            
    except requests.exceptions.SSLError:
        if response:
            response.close()
        return _handle_ssl_error(url, use_proxy)
        
    except requests.exceptions.ConnectionError as e:
        if response:
            response.close()
        # Try with cloudflare handling
        return _handle_cloudflare(url, use_proxy)
        
    except Exception as e:
        if response:
            response.close()
        return {
            "success": False,
            "error": str(e),
            "data": None
        }
    finally:
        if response:
            response.close()

def _check_response(response: requests.Response, url: str) -> GetHTMLResult:
    """Check response status and handle different scenarios"""
    if response.status_code == 200:
        return {
            "success": True,
            "error": None,
            "data": response.text
        }
    elif response.status_code in [401, 403, 503]:
        # Try cloudflare bypass
        return _handle_cloudflare(url, use_proxy=True)
    else:
        return {
            "success": False,
            "error": f"Status code: {response.status_code}, Reason: {response.reason}",
            "data": None
        }

def _handle_cloudflare(url: str, use_proxy: bool = True) -> GetHTMLResult:
    """Handle cloudflare protection with your authenticated proxy"""
    cloud_scraper = None
    try:
        cloud_scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        
        # Update headers with random values
        cloud_scraper.headers.update({
            'User-Agent': random.choice(choices_user_agents),
            'Referer': random.choice(choices_referers),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
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
        else:
            # If cloudflare with proxy fails, try without proxy
            if use_proxy:
                return _handle_cloudflare(url, use_proxy=False)
            else:
                return {
                    "success": False,
                    "error": f"Cloudflare bypass failed - Status: {response.status_code}",
                    "data": None
                }
                
    except Exception as e:
        if use_proxy:
            # Try without proxy as fallback
            return _handle_cloudflare(url, use_proxy=False)
        else:
            return {
                "success": False,
                "error": f"Cloudflare handling failed: {str(e)}",
                "data": None
            }
    finally:
        if cloud_scraper:
            cloud_scraper.close()

def _handle_ssl_error(url: str, use_proxy: bool = True) -> GetHTMLResult:
    """Handle SSL errors with authenticated proxy"""
    session = None
    try:
        headers = {
            'User-Agent': random.choice(choices_user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': random.choice(choices_referers)
        }
        
        session = requests.Session()
        session.mount('https://', SSLAdapter())
        
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
                "error": f"SSL retry failed - Status: {response.status_code}",
                "data": None
            }
            
    except requests.exceptions.SSLError:
        # Last resort: disable SSL verification
        try:
            if use_proxy:
                proxies = get_authenticated_proxy()
                response = requests.get(url, headers=headers, proxies=proxies, verify=False, timeout=60)
            else:
                response = requests.get(url, headers=headers, verify=False, timeout=30)
                
            if response.status_code == 200:
                return {
                    "success": True,
                    "error": None,
                    "data": response.text
                }
            else:
                return {
                    "success": False,
                    "error": f"No SSL verification failed - Status: {response.status_code}",
                    "data": None
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"All SSL handling failed: {str(e)}",
                "data": None
            }
    except Exception as e:
        if use_proxy:
            # Try without proxy as fallback
            return _handle_ssl_error(url, use_proxy=False)
        else:
            return {
                "success": False,
                "error": f"SSL error handling failed: {str(e)}",
                "data": None
            }
    finally:
        if session:
            session.close()

# FastAPI app
app = FastAPI(title="Web Scraper API", description="Scrape websites with authenticated proxy support")

@app.get("/get-html", response_model=GetHTMLResult)
def get_html_wrapper(
    url: str = Query(..., description="URL to scrape"),
    use_proxy: bool = Query(True, description="Whether to use authenticated proxy")
) -> GetHTMLResult:
    """
    Scrape HTML from a URL with optional authenticated proxy usage
    
    - **url**: The URL to scrape
    - **use_proxy**: Whether to use the authenticated proxy (default: True)
    """
    return get_html(url, use_proxy)

@app.get("/")
def root():
    return {"message": "Web Scraper API", "endpoints": ["/get-html", "/docs"]}

# Environment variable support (for security)
if os.getenv("PROXY_USERNAME"):
    PROXY_USERNAME = os.getenv("PROXY_USERNAME")
if os.getenv("PROXY_PASSWORD"):
    PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
if os.getenv("PROXY_HOST"):
    PROXY_HOST = os.getenv("PROXY_HOST")
if os.getenv("PROXY_PORT"):
    PROXY_PORT = os.getenv("PROXY_PORT")
