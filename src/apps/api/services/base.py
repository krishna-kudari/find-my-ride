"""Base class for ride service providers"""

import ast
import json
from abc import ABC, abstractmethod
from curl_cffi import requests as curl_requests

from .account_pool.account_pool import AccountPool


class BaseRideService(ABC):
    """Base class for ride service providers with common functionality"""

    def __init__(self, service_name: str, api_url: str, default_headers: dict):
        """
        Initialize base ride service.

        Args:
            service_name: Name of the service (e.g., 'uber', 'ola', 'rapido')
            api_url: API endpoint URL for the service
            default_headers: Default headers to use as fallback
        """
        self.service_name = service_name
        self.api_url = api_url
        self.default_headers = default_headers
        self._session = None

    def _get_headers(self) -> dict:
        """
        Get headers from ServiceAccount or fallback to default headers.

        Supports both Python dict syntax (single quotes) and JSON format (double quotes).

        Returns:
            dict: Headers dictionary
        """
        try:
            account = AccountPool().get_service_account(self.service_name)
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
            return self.default_headers.copy()

    def _get_session(self):
        """Get or create a curl_cffi session with Chrome impersonation."""
        if self._session is None:
            self._session = curl_requests.Session(impersonate="chrome")
        return self._session

    def _make_request(self, method: str, **kwargs) -> dict | None:
        """
        Make HTTP request with common error handling.

        Args:
            method: HTTP method ('GET' or 'POST')
            **kwargs: Additional arguments to pass to the request

        Returns:
            dict: Response data or None on error
        """
        session = self._get_session()
        headers = self._get_headers()

        try:
            print(f"calling {self.service_name} api")
            if method.upper() == "GET":
                response = session.get(
                    self.api_url, headers=headers, timeout=30, **kwargs
                )
            elif method.upper() == "POST":
                response = session.post(
                    self.api_url, headers=headers, timeout=30, **kwargs
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            data = response.json()
            print(self.service_name, data)
            return data.get("data", data)
        except (curl_requests.RequestsError, json.JSONDecodeError) as e:
            print(f"error from {self.service_name} api call: {e}")
            return None

    @abstractmethod
    def fetch_prices(self, source: tuple, destination: tuple) -> dict | None:
        """
        Fetch prices from the ride service.

        Args:
            source: Tuple of (latitude, longitude) for pickup location
            destination: Tuple of (latitude, longitude) for drop location

        Returns:
            dict: Price data or None on error
        """
        pass
