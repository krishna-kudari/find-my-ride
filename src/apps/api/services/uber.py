"""Uber client service"""

import json
from curl_cffi import requests as curl_requests

from .base import BaseRideService

API_URL = "https://m.uber.com/go/graphql"

# Fallback headers when no ServiceAccount for client "uber" is configured.
DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9,kn;q=0.8",
    "content-type": "application/json",
    "dnt": "1",
    "origin": "https://m.uber.com",
    "priority": "u=1, i",
    "referer": "https://m.uber.com/go/product-selection?adults=1&check_in=2026-02-19&check_out=2026-02-22&lat=12.9753&lng=77.591",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "x-csrf-token": "x",
    "x-uber-botdefense-id": "438472f6-fe89-467f-995e-c5ef063bfe11",
    "x-uber-rv-initial-load-city-id": "130",
    "x-uber-rv-session-type": "desktop_session",
    "Cookie": 'u.bdid=438472f6-fe89-467f-995e-c5ef063bfe11; marketing_vistor_id=3e9da597-d8eb-41ca-a9a1-83b76e6bb152; u-cookie-prefs=eyJ2ZXJzaW9uIjoxMDAsImRhdGUiOjE3Njk2ODIxMjMzOTcsImNvb2tpZUNhdGVnb3JpZXMiOlsiYWxsIl0sImltcGxpY2l0Ijp0cnVlfQ%3D%3D; UBER_CONSENTMGR=1769682123397|consent:true; CONSENTMGR=1769682123398|consent:true; _gcl_au=1.1.2099676187.1769682124; _ga=GA1.1.2012124157.1769682124; udi-id=GDAh89YhTaBR2TO4oYrQwwgQYcjdjQGhRcIfc+Sn6VzkPNOZRuHRChQs8QhlfVnnYT5Htz5GUEMNhH9q5ScRtDhqbtd6EkBjOl6Gpmx809KwgMC8ygj29l/CGx0Pb2z9YotU0HWipGUfilEC4uQ/kaY87vNq/fBqmiINmIAdKKluiFMjOakBYC+vv7Vkyh/mFCJGTEL7LqJybNW6GKrqSg==xtkizS/FyeRf4Qtzjqqbug==VWSo6PpnJ3EoGFnr+WOlZk5Q3gRqqWxnKV407JI9x2E=; sid=QA.CAESEP06cC7fYkPxu34OA7Y5m-EY1IWi0wYiATEqJGJhOGM1MDUzLTFjMTUtNDg4NC1iZTYwLTkxNTRjZjQzMjk4ODJA7um5ivYXLGyslrhmjd3x5Sq5-afgnZpCEM8D6EOFHWI0YSKtjP-vfZxm9oMz9aOcHkQrcaZbHQiVJpiLBj_vZjoBMUIIdWJlci5jb20.vNwTQI_-cfNvv8mTqr8NhekoONwaWeKlcsj-P_6oGqw; smeta={"expiresAt":1785234132216}; csid=1.1772274133437.w7oxclOTUSVtI+CI07FcUKVnvct/QuF35utuy8tRdYk=; _fbp=fb.1.1769682135333.1761880516212930.Bg; _yjsu_yjad=1769682135.bfb42722-3a93-4e91-bb14-3cceaae43dfe; _cc=AetSSoHPxseBYBJbi4FfR9Co; allow-geolocation=true; _tt_enable_cookie=1; _ttp=01KG4Y958KTAH1C96B9QKD1AJC_.tt.1; ttcsid=1769692501269::4e1fM6OPI__oCTCiL3Wq.2.1769692511274.0; ttcsid_CRG9VSJC77U326FJDN5G=1769692501268::2n9YgSucxCR-6mNubydY.2.1769692511275.1; _gcl_gs=2.1.k1$i1770305889$u134343605; _gcl_dc=GCL.1770305892.Cj0KCQiAnJHMBhDAARIsABr7b84BIPY5hL1ah-tGlv75fk220I-wGTtebzihTVxQEZ94cS3jW0wlzScaAh8ZEALw_wcB; _clck=1t4k8yl%5E2%5Eg3b%5E0%5E2220; _clsk=1oc9hxr%5E1770305893333%5E1%5E0%5Ea.clarity.ms%2Fcollect; city_id_cookie_key=130; _gcl_aw=GCL.1770305911.Cj0KCQiAnJHMBhDAARIsABr7b84BIPY5hL1ah-tGlv75fk220I-wGTtebzihTVxQEZ94cS3jW0wlzScaAh8ZEALw_wcB; _ua={"session_id":"b25c20f8-1f41-4d03-a598-b331cc9e2950","session_time_ms":1770318324581}; jwt-session=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7InNsYXRlLWV4cGlyZXMtYXQiOjE3NzAzMjAxMjQ1ODIsIlVzZXItQWdlbnQiOiIiLCJ4LXViZXItY2xpZW50LWlkIjoiIiwieC11YmVyLWRldmljZSI6IiIsIngtdWJlci1jbGllbnQtdXNlci1zZXNzaW9uLWlkIjoiIiwidGVuYW5jeSI6InViZXIvcHJvZHVjdGlvbiJ9LCJpYXQiOjE3NzAzMDU5MDcsImV4cCI6MTc3MDM5MjMwN30.A7pYgNTLozJp2ToYa2B0eNKvcC3QN9SEwYMWAh2_GHo; utag_main__sn=4; utag_main_ses_id=1770318385841%3Bexp-session; utag_main__ss=0%3Bexp-session; __cf_bm=a_JOXH2P0wDkSZpfdh_7Z51X8s75edgTMOqViL6bhro-1770318386-1.0.1.1-wcy3PCFwb6F0FS7u5AiWkDlqGdd_5Jkrk6wzaUyCW2ta43VlVk3y6XadHkqDsAcTJtiqe.WOi.67Ph4Avj3QpCL4dknkfKBoqIBjxPBf8g0; udi-fingerprint=c1IXooH1vscN0dKPJomK6tsz5rOWzH88N4YINSDLefPgRC3T8PV+nZhBXnoz37zo3kfLYmu/EbKeJguNMw0NWg==j4KKzhDfiCmBi5melS3g8DO6mNHX2fZpBRmE6H8EerQ=; _ga_XTGQLY6KPT=GS2.1.s1770318385$o5$g1$t1770318489$j60$l0$h0; utag_main__pn=3%3Bexp-session; utag_main__se=19%3Bexp-session; utag_main__st=1770320289544%3Bexp-session; _uetsid=ada684a002a811f191bccd85b9e830ab; _uetvid=5b0d7a60fcfc11f0b608cfb40bcaa6ee; marketing_vistor_id=3e9da597-d8eb-41ca-a9a1-83b76e6bb152; _ua={"session_id":"b25c20f8-1f41-4d03-a598-b331cc9e2950","session_time_ms":1770318324581}; jwt-session=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7InNsYXRlLWV4cGlyZXMtYXQiOjE3NzAzMjAyOTg4MjYsIlVzZXItQWdlbnQiOiIiLCJ4LXViZXItY2xpZW50LWlkIjoiIiwieC11YmVyLWRldmljZSI6IiIsIngtdWJlci1jbGllbnQtdXNlci1zZXNzaW9uLWlkIjoiIiwidGVuYW5jeSI6InViZXIvcHJvZHVjdGlvbiJ9LCJpYXQiOjE3NzAzMDU5MDcsImV4cCI6MTc3MDM5MjMzMH0.LxlIH6oOVl2BEC7YbF2WwvKCTpqVwbzmbWxT1F9dOLI',
}

PRODUCTS_QUERY = """
query Products($capacity: Int, $destinations: [InputCoordinate!]!, $includeRecommended: Boolean = false, $isRiderCurrentUser: Boolean, $payment: InputPayment, $paymentProfileUUID: String, $pickup: InputCoordinate!, $pickupFormattedTime: String, $profileType: String, $profileUUID: String, $returnByFormattedTime: String, $stuntID: String, $targetProductType: EnumRVWebCommonTargetProductType) {
  products(
    capacity: $capacity
    destinations: $destinations
    includeRecommended: $includeRecommended
    isRiderCurrentUser: $isRiderCurrentUser
    payment: $payment
    paymentProfileUUID: $paymentProfileUUID
    pickup: $pickup
    pickupFormattedTime: $pickupFormattedTime
    profileType: $profileType
    profileUUID: $profileUUID
    returnByFormattedTime: $returnByFormattedTime
    stuntID: $stuntID
    targetProductType: $targetProductType
  ) {
    ...ProductsFragment
    __typename
  }
}
fragment ProductsFragment on RVWebCommonProductsResponse {
  defaultVVID
  hourlyTiersWithMinimumFare { ...HourlyTierFragment __typename }
  intercity { ...IntercityFragment __typename }
  links { iFrame text url __typename }
  productsUnavailableMessage
  tiers { ...TierFragment __typename }
  __typename
}
fragment BadgesFragment on RVWebCommonProductBadge {
  backgroundColor color contentColor icon inactiveBackgroundColor inactiveContentColor text __typename
}
fragment HourlyTierFragment on RVWebCommonHourlyTier {
  description distance fare fareAmountE5 farePerHour minutes packageVariantUUID preAdjustmentValue __typename
}
fragment IntercityFragment on RVWebCommonIntercityInfo {
  oneWayIntercityConfig(destinations: $destinations, pickup: $pickup) { ...IntercityConfigFragment __typename }
  roundTripIntercityConfig(destinations: $destinations, pickup: $pickup) { ...IntercityConfigFragment __typename }
  __typename
}
fragment IntercityConfigFragment on RVWebCommonIntercityConfig {
  description onDemandAllowed reservePickup { ...IntercityTimePickerFragment __typename } returnBy { ...IntercityTimePickerFragment __typename }
  __typename
}
fragment IntercityTimePickerFragment on RVWebCommonIntercityTimePicker {
  bookingRange { maximum minimum __typename } header { subTitle title __typename }
  __typename
}
fragment TierFragment on RVWebCommonProductTier {
  products { ...ProductFragment __typename } title __typename
}
fragment ProductFragment on RVWebCommonProduct {
  badges { ...BadgesFragment __typename }
  cityID currencyCode description detailedDescription discountPrimary displayName estimatedTripTime etaStringShort
  fares { capacity discountPrimary fare fareAmountE5 hasPromo hasRidePass meta preAdjustmentValue __typename }
  hasPromo hasRidePass hasBenefitsOnFare
  hourly { tiers { ...HourlyTierFragment __typename } overageRates { ...HourlyOverageRatesFragment __typename } __typename }
  iconType id is3p isAvailable legalConsent { ...ProductLegalConsentFragment __typename }
  parentProductUuid preAdjustmentValue productImageUrl productUuid reserveEnabled __typename
}
fragment ProductLegalConsentFragment on RVWebCommonProductLegalConsent {
  header image { url width __typename } description enabled ctaUrl ctaDisplayString buttonLabel showOnce shouldBlockRequest __typename
}
fragment HourlyOverageRatesFragment on RVWebCommonHourlyOverageRates {
  perDistanceUnit perTemporalUnit __typename
}
"""


class Uber(BaseRideService):
    """Uber pricing via GraphQL. Uses curl_cffi with Chrome impersonation so TLS matches browser/Postman."""

    def __init__(self):
        """Initialize Uber service."""
        super().__init__(
            service_name="uber",
            api_url=API_URL,
            default_headers=DEFAULT_HEADERS
        )

    def fetch_prices(self, source: tuple, destination: tuple) -> dict | None:
        """Fetch prices from Uber."""
        pickup = {"latitude": source[0], "longitude": source[1]}
        destinations = [{"latitude": destination[0], "longitude": destination[1]}]
        variables = {
            "includeRecommended": False,
            "destinations": destinations,
            "payment": {"uberCashToggleOn": True},
            "pickup": pickup,
        }
        payload = {"query": PRODUCTS_QUERY.strip(), "variables": variables}

        session = self._get_session()
        headers = self._get_headers()

        try:
            print("calling uber api")
            response = session.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except (curl_requests.RequestsError, json.JSONDecodeError):
            print("error from api call")
            return None

        print("uber", data)
        errors = data.get("errors") or []

        for err in errors:
            if isinstance(err, dict) and "bd-challenge" in str(err.get("message", "")):
                return None
            if isinstance(err, dict) and "bd-challenge" in str(err.get("extensions", "")):
                return None

        print(data)
        return data.get("data", data)
