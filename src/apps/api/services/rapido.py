"Rapido client service"

import ast
import json
from curl_cffi import requests as curl_requests

from .account_pool.account_pool import AccountPool

URL = "https://m.rapido.bike/pwa/api/pricing/getFareEstimate"

DEFAULT_HEADERS = {
    "x-consumer-username": "663c81ebbfa8fc234d1a5692:",
    "appid": "2",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiI2NjNjODFlYmJmYThmYzIzNGQxYTU2OTIiLCJmaXJzdE5hbWUiOiJLcmlzaG5hIEt1ZGFyaSIsImxhc3ROYW1lIjoiIiwibW9iaWxlIjoiOTk2NDE0NjEyMyIsImVtYWlsIjoiIiwicm9sZXMiOlsiY3VzdG9tZXIiXSwiZGV2aWNlSWQiOiIiLCJ1c2VySWQiOiI2NjNjODFlYmJmYThmYzIzNGQxYTU2OTIiLCJpYXQiOjE3NzAzNTc1MDMsImlzcyI6InpPSExPUU5YZVBINlZBV25OWDRIR3FuNWVzQ3lvT2dRIn0.V4J9RhVoGOUWgOf8c6k_2zxGfzUJ89_oQv_SNRbdxfU",
    "longitude": "77.64372812854415",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "latitude": "12.912063462247334",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "appversion": "214",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "channel-entity": "customer",
    "Referer": "https://m.rapido.bike/home",
    "channel-name": "pwa",
    "channel-host": "browser",
    "user": '{"_id":"663c81ebbfa8fc234d1a5692"}',
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "DNT": "1",
}


def _get_headers():
    """Get headers from ServiceAccount (client='rapido') or fallback to DEFAULT_HEADERS.

    Supports both Python dict syntax (single quotes) and JSON format (double quotes).
    """
    try:
        account = AccountPool().get_service_account("rapido")
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

class Rapido:
    """Rapido pricing via REST. User curl_cffi"""

    def fetch_prices(self, source, destination):
        print("fetch prices from rapido")
        pickup = {"lat": source[0], "lng": source[1]}
        drop = {"lat": destination[0], "lng": destination[1]}
        payload = {
            "pickupLocation": pickup,
            "dropLocation": drop,
            "paymentType": "cash",
            "serviceType": "57370b61a6855d70057417d1",
            "couponCode": "",
            "customer": "663c81ebbfa8fc234d1a5692",
        }

        session = curl_requests.Session(impersonate="chrome")
        headers = _get_headers()
        print("calling rapido api", headers)
        r = session.post(URL, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        print("rapido",data)
        return data.get("data", data)
