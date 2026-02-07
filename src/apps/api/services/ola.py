"""Ola client service"""

import json

from .base import BaseRideService

API_URL = "https://book.olacabs.com/data-api/category-fare/p2p?"
BIKE_API_URL = "https://book.olacabs.com/data-api/prebook?silent=true&utm_source=widget_on_olacabs"

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


class Ola(BaseRideService):
    """Ola pricing via REST. Uses curl_cffi."""

    def __init__(self):
        """Initialize Ola service."""
        super().__init__(
            service_name="ola",
            api_url=API_URL,
            default_headers=DEFAULT_HEADERS
        )

    def _extract_csrf_token(self, headers: dict) -> str | None:
        """Extract CSRF token from Cookie header."""
        cookie = headers.get("Cookie", "")
        if not cookie:
            return None
        
        # Look for XSRF-TOKEN in cookies
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("XSRF-TOKEN="):
                return part.split("=", 1)[1]
        return None

    def _fetch_bike_price(self, source: tuple, destination: tuple) -> dict | None:
        """Fetch bike price from Ola using the prebook endpoint."""
        payload = {
            "fromLocation": {
                "lat": source[0],
                "lng": source[1]
            },
            "toLocation": {
                "lat": destination[0],
                "lng": destination[1]
            },
            "serviceType": "p2p",
            "pickupMode": "NOW",
            "pickupTime": 0,
            "category": "bike",
            "paymentType": 1,
            "couponCode": "",
            "fareId": "",
            "leadSource": "desktop_website",
            "retryCount": 0,
            "liteParams": {}
        }

        session = self._get_session()
        headers = self._get_headers()
        
        # Use CSRF token from headers if present, otherwise extract from cookies
        if "csrf-token" not in headers:
            csrf_token = self._extract_csrf_token(headers)
            if csrf_token:
                headers["csrf-token"] = csrf_token
        
        # Add origin header
        headers["origin"] = "https://book.olacabs.com"
        
        # Update referer to match the bike API endpoint format
        headers["referer"] = f"https://book.olacabs.com/confirm-ride-p2p?serviceType=p2p&utm_source=widget_on_olacabs&drop_lat={destination[0]}&drop_lng={destination[1]}&lat={source[0]}&lng={source[1]}&pickup="

        try:
            print(f"calling {self.service_name} bike api")
            # Send payload as JSON string (matching the curl request)
            response = session.post(
                BIKE_API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            print(self.service_name, "bike", data)
            return data.get("data", data)
        except Exception as e:
            print(f"error from {self.service_name} bike api call: {e}")
            return None

    def fetch_prices(self, source: tuple, destination: tuple) -> dict | None:
        """Fetch prices from Ola, including bike prices."""
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
        main_data = self._make_request("GET", params=params)

        # Fetch bike price separately
        bike_data = self._fetch_bike_price(source, destination)

        # Merge bike data into main response structure
        if main_data and bike_data:
            bike_estimate = bike_data.get("rideEstimate", {})
            if bike_estimate and bike_estimate.get("amount"):
                # Ensure p2p.categories structure exists
                if "p2p" not in main_data:
                    main_data["p2p"] = {}
                if "categories" not in main_data["p2p"]:
                    main_data["p2p"]["categories"] = {}

                # Add bike category to match expected structure
                main_data["p2p"]["categories"]["bike"] = {
                    "price": bike_estimate.get("amount", ""),
                    "fareId": bike_estimate.get("fareId", "")
                }

        return main_data
