"Ola client service"

import ast
import json
from curl_cffi import requests as curl_requests

from .account_pool.account_pool import AccountPool

URL = "https://book.olacabs.com/data-api/category-fare/p2p?"

DEFAULT_HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9,kn;q=0.8",
    "content-type": "application/json",
    "dnt": "1",
    "priority": "u=1, i",
    "referer": "https://book.olacabs.com/home?serviceType=p2p&utm_source=widget_on_olacabs&drop_lat=12.938045&drop_lng=77.624084&drop_name=The%20Koramangala%20Club%2C%20Bengaluru%20Bangalore%20Karnataka%20India%2C%20560095%2C%20India&lat=12.9117&lng=77.6435&pickup_name=Workindia%20HQ%2C%203rd%20Floor%2C%2017%2FN%2C%2018th%20Cross%20Rd%2C%20Above%20Leon%20Grill%2C%20Sector%203%2C%20HSR%20Layout%2C%20Bengaluru%2C%20Karnataka%2C%20560102%2C%20India&pickup=",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "x-fingerprint-id": "226077131",
    "x-requested-with": "XMLHttpRequest",
    "Cookie": "_ga_7QP5L1NN0B=GS2.2.s1769692562$o1$g0$t1769692562$j60$l0$h0; OSRN_v1=1e6wKfFG6jDvU4G8wkvKU4zi; _gcl_au=1.1.327779086.1769692586; _ga_EKVXJMSBW2=GS2.2.s1769692609$o1$g0$t1769692609$j60$l0$h0; _csrf=zzke-boKz97271WbbAv8W7Au; XSRF-TOKEN=Aw1cyuX0-QcnS5e3DaPfFLmL9Ecm74TnENn0; AKA_A2=A; wasc=web-7d7ddc0d-d0f1-4716-b0af-bd3b08bade27__tLLFDRVs0V7V+iK2ZYrNnWrBDD1hGm7s1Tau93m1wenWhC+yePWHcCgJilWJf3svKOokNEpuuqJ7htYuYwyFdMe5VUXd4F/k7tfTiCevRzchh3q//wRoH9o9/qWYbXf2SuDzMSr+f41d42si9U8fwom24rJbcVgb1t/6wb0yzMg; _gid=GA1.2.355179680.1770361461; _gat=1; _ga=GA1.1.1307449666.1769692562; _ga_2TR8WHTK1X=GS2.1.s1770361460$o2$g1$t1770361573$j60$l0$h0; _ga_FR59878HTR=GS2.2.s1770361460$o2$g1$t1770361573$j60$l0$h0",
}

def _get_headers():
    """Get headers from ServiceAccount (client='ola') or fallback to DEFAULT_HEADERS.

    Supports both Python dict syntax (single quotes) and JSON format (double quotes).
    """
    try:
        account = AccountPool().get_service_account("ola")
        creds_str = account.credentials.strip()
        print(account, creds_str)

        # Handle "headers: { ... }" format by extracting the dict part
        if creds_str.startswith("headers:"):
            start_idx = creds_str.find("{")
            end_idx = creds_str.rfind("}")
            if start_idx != -1 and end_idx != -1:
                creds_str = creds_str[start_idx:end_idx + 1]

        # Try parsing as Python dict (single quotes) first
        try:
            return ast.literal_eval(creds_str)
        except (ValueError, SyntaxError):
            print("Error parsing as Python dict")
            # Fall back to JSON parsing (double quotes)
            return json.loads(creds_str)
    except (IndexError, json.JSONDecodeError, TypeError, AttributeError, ValueError, SyntaxError):
        print("Error parsing creds")
        return DEFAULT_HEADERS.copy()

class Ola:
    """Ola pricing via REST. Uses curl_cffi."""

    def fetch_prices(self, source, destination):
        "fetch prices from Ola"
        params = {
            "pickupLat": source[0],
            "pickupLng": source[1],
            "pickupMode": "NOW",
            "leadSource": "desktop_website",
            "dropLat": destination[0],
            "dropLng": destination[1],
            "silent": "false",
            "suggestPickup": "true",
        }
        session = curl_requests.Session(impersonate="chrome")
        headers = _get_headers()
        print("calling ola api", headers)
        r = session.get(URL, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        print("ola", data)
        return data.get("data", data)
