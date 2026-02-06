"""Rapido client service"""

from .base import BaseRideService

API_URL = "https://m.rapido.bike/pwa/api/pricing/getFareEstimate"

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


class Rapido(BaseRideService):
    """Rapido pricing via REST. Uses curl_cffi."""

    def __init__(self):
        """Initialize Rapido service."""
        super().__init__(
            service_name="rapido",
            api_url=API_URL,
            default_headers=DEFAULT_HEADERS
        )

    def fetch_prices(self, source: tuple, destination: tuple) -> dict | None:
        """Fetch prices from Rapido."""
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
        return self._make_request("POST", json=payload)
