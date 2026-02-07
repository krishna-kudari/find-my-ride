"Fare parser to restructure data by category"

import re


# Category mapping: platform-specific names -> common category names
CATEGORY_MAPPING = {
    "ola": {
        "auto": "auto",
        "mini": "mini",
        "prime": "prime",
        "suv": "suv",
    },
    "uber": {
        "auto": "auto",
        "bike saver": "bike",
        "bike": "bike",
        "go non ac": "mini",
        "uber go": "mini",
        "premier": "prime",
        "uberxl": "suv",
        "xl plus": "suv",
        "uber pet": "prime",  # Pet-friendly rides similar to premier
        "electric": "prime",  # Electric sedans similar to premier
    },
    "rapido": {
        # Bike services
        "link": "bike",
        "scooty": "bike",
        "c2c": "bike",
        # Auto services
        "auto": "auto",
        "auto priority": "auto",
        "auto pet": "auto",
        "auto c2c": "auto",
        # Mini/Car services
        "cabeconomy": "mini",
        "cab economy": "mini",
        "cab priority": "mini",
        "cabac": "mini",
        "cab ac": "mini",
        # Prime services
        "cabpremium": "prime",
        "cab premium": "prime",
        # SUV services
        "cab suv": "suv",
        "cabsuv": "suv",
    },
}


def _extract_price_value(price_str):
    """Extract numeric value from price string like '₹145' or '₹90.42'"""
    if not price_str:
        return None
    # Remove currency symbols and extract number
    match = re.search(r"[\d.]+", str(price_str))
    if match:
        return float(match.group())
    return None


def _normalize_category_name(name):
    """Normalize category name to lowercase for mapping"""
    return name.lower().strip()


def parse_ola_fares(ola_data):
    """Parse Ola fare data and extract categories with prices"""
    if not ola_data:
        return {}

    fares = {}
    try:
        # Ola structure: {"p2p": {"categories": {"auto": {"price": "₹145", "fareId": "..."}, ...}}}
        p2p_data = ola_data.get("p2p", {})
        categories = p2p_data.get("categories", {})

        for category_name, category_data in categories.items():
            normalized_name = _normalize_category_name(category_name)
            mapped_category = CATEGORY_MAPPING["ola"].get(normalized_name)

            if mapped_category and category_data:
                price_str = category_data.get("price", "")
                price_value = _extract_price_value(price_str)

                if price_value is not None:
                    fares[mapped_category] = {
                        "price": price_str,
                        "priceValue": price_value,
                        "fareId": category_data.get("fareId"),
                    }
    except (AttributeError, KeyError, TypeError) as e:
        print(f"Error parsing Ola data: {e}")

    return fares


def parse_uber_fares(uber_data):
    """Parse Uber fare data and extract products with final prices"""
    if not uber_data:
        return {}

    fares = {}
    try:
        # Uber structure: {"products": {"tiers": [{"products": [...]}]}}
        products_data = uber_data.get("products", {})
        tiers = products_data.get("tiers", [])

        for tier in tiers:
            products = tier.get("products", [])
            for product in products:
                if not product.get("isAvailable", True):
                    continue

                display_name = product.get("displayName", "")
                normalized_name = _normalize_category_name(display_name)

                # Find mapped category - check exact matches first, then partial
                mapped_category = None

                # Check for exact matches first (more specific)
                if normalized_name in CATEGORY_MAPPING["uber"]:
                    mapped_category = CATEGORY_MAPPING["uber"][normalized_name]
                else:
                    # Check for partial matches (less specific)
                    for uber_name, common_name in CATEGORY_MAPPING["uber"].items():
                        if uber_name in normalized_name:
                            mapped_category = common_name
                            break

                if not mapped_category:
                    continue

                # Get final price from fares array (use the discounted fare, not preAdjustmentValue)
                product_fares = product.get("fares", [])
                if product_fares:
                    fare_data = product_fares[0]
                    final_fare = fare_data.get("fare", "")

                    # Skip if fare is not a valid price (e.g., "Select time")
                    if not final_fare or "select" in final_fare.lower():
                        continue

                    price_value = _extract_price_value(final_fare)

                    if price_value is not None:
                        # If category already exists, keep the cheaper option
                        if mapped_category not in fares or price_value < fares[mapped_category]["priceValue"]:
                            fares[mapped_category] = {
                                "price": final_fare,
                                "priceValue": price_value,
                                "productId": product.get("id"),
                                "productUuid": product.get("productUuid"),
                            }
    except (AttributeError, KeyError, TypeError) as e:
        print(f"Error parsing Uber data: {e}")

    return fares


def parse_rapido_fares(rapido_data):
    """Parse Rapido fare data and extract categories with prices"""
    if not rapido_data:
        return {}

    fares = {}
    try:
        # Rapido structure: {"data": {"quotes": [...]}} or {"quotes": [...]}
        # Handle both nested and direct structures
        if "data" in rapido_data:
            quotes = rapido_data.get("data", {}).get("quotes", [])
        else:
            quotes = rapido_data.get("quotes", [])
        
        for quote in quotes:
            # Skip delivery services
            order_type = quote.get("orderType", "")
            if order_type == "delivery":
                continue
            
            service_name = quote.get("serviceName") or quote.get("serviceDisplayName", "") or quote.get("name", "")
            normalized_name = _normalize_category_name(service_name)
            
            # Find mapped category - check service name first
            mapped_category = None
            
            # Check for exact matches first
            if normalized_name in CATEGORY_MAPPING["rapido"]:
                mapped_category = CATEGORY_MAPPING["rapido"][normalized_name]
            else:
                # Check for partial matches
                for rapido_name, common_name in CATEGORY_MAPPING["rapido"].items():
                    if rapido_name in normalized_name:
                        mapped_category = common_name
                        break
            
            # If still no mapping, use orderType as fallback
            if not mapped_category:
                order_type_normalized = _normalize_category_name(order_type)
                if "auto" in order_type_normalized:
                    mapped_category = "auto"
                elif "cab" in order_type_normalized:
                    # Determine cab type based on orderType
                    if "suv" in order_type_normalized:
                        mapped_category = "suv"
                    elif "premium" in order_type_normalized:
                        mapped_category = "prime"
                    else:
                        mapped_category = "mini"
                elif order_type_normalized in ["app", "scooty", "c2c"]:
                    mapped_category = "bike"
            
            # Final fallback: infer from seating capacity
            if not mapped_category:
                seating_capacity = quote.get("seatingCapacity", 0)
                if seating_capacity == 1:
                    mapped_category = "bike"
                elif seating_capacity == 3:
                    mapped_category = "auto"
                elif seating_capacity == 4:
                    mapped_category = "mini"
                elif seating_capacity >= 6:
                    mapped_category = "suv"
            
            if not mapped_category:
                continue
            
            # Get final price from amountBreakup.final.total or amount field
            amount_breakup = quote.get("amountBreakup", {})
            final_data = amount_breakup.get("final", {})
            final_amount = final_data.get("total")
            
            # Fallback to top-level amount if final.total is not available
            if final_amount is None:
                final_amount = quote.get("amount") or quote.get("displayableRideFare")
            
            if final_amount is not None:
                # Format as currency string
                price_str = f"₹{int(final_amount)}" if isinstance(final_amount, (int, float)) else str(final_amount)
                price_value = float(final_amount)
                
                if price_value > 0:
                    # If category already exists, keep the cheaper option
                    if mapped_category not in fares or price_value < fares[mapped_category]["priceValue"]:
                        fares[mapped_category] = {
                            "price": price_str,
                            "priceValue": price_value,
                            "serviceId": quote.get("serviceId"),
                            "quoteId": quote.get("id"),
                        }
    except (AttributeError, KeyError, TypeError) as e:
        print(f"Error parsing Rapido data: {e}")

    return fares


def restructure_fares_by_category(ola_data=None, uber_data=None, rapido_data=None):
    """
    Restructure fare data to group by category, showing all platforms for each category.

    Returns:
        {
            "auto": {
                "ola": {"price": "₹145", "priceValue": 145.0, "fareId": "..."},
                "uber": {"price": "₹90.42", "priceValue": 90.42, "productId": "..."},
                "rapido": {...}
            },
            "mini": {...},
            ...
        }
    """
    ola_fares = parse_ola_fares(ola_data)
    uber_fares = parse_uber_fares(uber_data)
    rapido_fares = parse_rapido_fares(rapido_data)

    # Collect all unique categories
    all_categories = set()
    all_categories.update(ola_fares.keys())
    all_categories.update(uber_fares.keys())
    all_categories.update(rapido_fares.keys())

    # Restructure by category
    result = {}
    for category in sorted(all_categories):
        result[category] = {}

        if category in ola_fares:
            result[category]["ola"] = ola_fares[category]

        if category in uber_fares:
            result[category]["uber"] = uber_fares[category]

        if category in rapido_fares:
            result[category]["rapido"] = rapido_fares[category]

    return result
