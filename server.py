from utils import choices_referers, choices_user_agents
import warnings
import random
import ssl
import requests
from requests.adapters import HTTPAdapter
import cloudscraper
from bs4 import BeautifulSoup
from typing import TypedDict, Optional
from fastapi import FastAPI, Query

warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class GetHTMLResult(TypedDict):
    success: bool
    error: Optional[str]
    data: Optional[str]


# class for handling session where the SSL certificate is old
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        # Allow unsafe legacy renegotiation
        context.options |= 0x4  # This sets the SSL_OP_LEGACY_SERVER_CONNECT flag
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)


def get_proxies() -> dict:
    proxyresponse = requests.get("https://www.sslproxies.org/")
    if proxyresponse.status_code == 200:
        soup = BeautifulSoup(proxyresponse.content, 'html.parser')
        table = soup.find('table')
        if not table or not table.tbody:
            return {}
        rows = table.tbody.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            ip = cols[0].text
            port = cols[1].text
            https_support = cols[6].text  # The 'Yes'/'No' column for HTTPS support
            if https_support == "yes":  # Check if the proxy supports HTTPS
                proxy = f"http://{ip}:{port}"  # HTTPS proxy
                proxyresponse.close()
                return {
                    "http": proxy,
                    "https": proxy
                }
            proxyresponse.close()
            return {}
    else:
        proxyresponse.close()
        return {}


class TryWithProxiesError(Exception):
    pass


def get_html(url: str) -> GetHTMLResult:
    response = None
    try:
        response = requests.get(url)
        result = _check_response(response, url)
        response.close()
        return result
    except requests.exceptions.SSLError:
        response = _handle_ssl_error(url)
        result = _check_response(response, url)
        response.close()
        return result
    except Exception as e:
        if response:
            response.close()
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def _check_response(response: requests.Response, url: str) -> GetHTMLResult:
    if response.status_code == 200:
        return {
            "success": True,
            "error": None,
            "data": response.text
        }
    elif response.status_code in [401, 403]:
        # handle cloudflare
        response_cloud = _handle_cloudflare(url)
        if response_cloud.status_code == 200:
            return {
                "success": True,
                "error": None,
                "data": response_cloud.text
            }
        else:
            return {
                "success": False,
                "error": f"Status code: {response_cloud.status_code}, Reason: {response_cloud.reason}",
                "data": None
            }
    else:
        return {
            "success": False,
            "error": f"Status code: {response.status_code}, Reason: {response.reason}",
            "data": None
        }


def _handle_cloudflare(url: str) -> requests.Response:
    # setup Cloudscraper
    cloud_scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    try:
        response = _try_cloudflare_request(cloud_scraper, url, with_proxy=False)
    except TryWithProxiesError:
        response = _try_cloudflare_request(cloud_scraper, url, with_proxy=True)
    finally:
        cloud_scraper.close()
    return response


def _try_cloudflare_request(cloud_scraper: cloudscraper.CloudScraper, url: str, with_proxy: bool = False) -> requests.Response:
    if with_proxy:
        proxies = get_proxies()
        if not proxies:
            raise Exception("No proxy")
    else:
        proxies = None
    # update headers
    cloud_scraper.headers.update({
        'User-Agent': random.choice(choices_user_agents),
        'Referer': random.choice(choices_referers),
        'Accept-Language': 'en-US,en;q=0.9'
    })
    response = cloud_scraper.get(url, proxies=proxies)
    if response.status_code != 200 and not with_proxy:
        raise TryWithProxiesError()
    return response


def _handle_ssl_error(url: str) -> requests.Response:
    # custom headers to use
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        response = _try_session_request(url, headers)
    except requests.exceptions.SSLError:
        response = _try_no_verification_request(url, headers)
    return response


def _try_session_request(url: str, headers: dict) -> requests.Response:
    session = None
    try:
        session = requests.Session()
        session.mount('https://', SSLAdapter())
        response = session.get(url, headers=headers)
    finally:
        session.close()
    return response


def _try_no_verification_request(url, headers) -> requests.Response:
    response = requests.get(url, headers=headers, verify=False)
    return response


app = FastAPI()


@app.get("/get-html", response_model=GetHTMLResult)
def get_html_wrapper(url: str = Query(..., description="URL to scrape")) -> GetHTMLResult:
    return get_html(url)
