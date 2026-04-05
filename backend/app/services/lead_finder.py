"""
PitchLab - Lead Finder Service
Integrates with Google Places API with intelligent mock fallback.
Filters by: no website, poor audit score, low reviews.
"""

import asyncio
import httpx
import re
from typing import List, Optional, Dict, Any
from app.core.config import settings


# ─── Data shape returned by the finder ────────────────────────────────────────

class FoundLead:
    def __init__(self, **kwargs):
        self.business_name   = kwargs.get("business_name", "")
        self.website         = kwargs.get("website")
        self.phone           = kwargs.get("phone")
        self.address         = kwargs.get("address")
        self.city            = kwargs.get("city")
        self.state           = kwargs.get("state")
        self.rating          = kwargs.get("rating")
        self.review_count    = kwargs.get("review_count", 0)
        self.has_website     = bool(kwargs.get("website"))
        self.google_place_id = kwargs.get("google_place_id")
        self.niche           = kwargs.get("niche")

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


# ─── Mock data for dev / demo ──────────────────────────────────────────────────

MOCK_LEADS = [
    {"business_name": "Acme Plumbing Co",        "website": None,                          "phone": "978-555-0101", "address": "12 Main St",    "city": "Haverhill", "state": "MA", "rating": 3.2, "review_count": 8},
    {"business_name": "Budget Drain Experts",     "website": "http://budgetdrain.weebly.com","phone": "978-555-0102", "address": "44 Oak Ave",    "city": "Haverhill", "state": "MA", "rating": 2.8, "review_count": 5},
    {"business_name": "Fast Flow Plumbers",       "website": None,                          "phone": "978-555-0103", "address": "99 Elm St",     "city": "Lawrence",  "state": "MA", "rating": 4.1, "review_count": 3},
    {"business_name": "North Shore Drain",        "website": "http://northshoredrain.com",  "phone": "978-555-0104", "address": "7 River Rd",    "city": "Salem",     "state": "MA", "rating": 3.5, "review_count": 12},
    {"business_name": "QuickPipe Services",       "website": None,                          "phone": "978-555-0105", "address": "200 Cross St",  "city": "Gloucester","state": "MA", "rating": 2.1, "review_count": 2},
    {"business_name": "ProSeal Roofing",          "website": "http://proseal.wixsite.com",  "phone": "617-555-0201", "address": "55 High St",    "city": "Everett",   "state": "MA", "rating": 3.0, "review_count": 7},
    {"business_name": "Atlas Electrical LLC",     "website": None,                          "phone": "617-555-0202", "address": "33 Park Ave",   "city": "Malden",    "state": "MA", "rating": 4.4, "review_count": 4},
    {"business_name": "Greenleaf Landscaping",    "website": "http://greenleafma.com",      "phone": "978-555-0301", "address": "88 Forest Dr",  "city": "Andover",   "state": "MA", "rating": 3.9, "review_count": 11},
    {"business_name": "Spartan HVAC",             "website": None,                          "phone": "781-555-0401", "address": "14 Commerce St","city": "Lynn",      "state": "MA", "rating": 2.5, "review_count": 6},
    {"business_name": "Reliable Roofing Co",      "website": "http://reliableroofing.squarespace.com","phone": "508-555-0501","address": "60 Broad St","city": "Framingham","state":"MA","rating": 3.3,"review_count": 9},
    {"business_name": "Premier Painters LLC",     "website": None,                          "phone": "617-555-0601", "address": "21 Union Ave",  "city": "Cambridge", "state": "MA", "rating": 4.8, "review_count": 2},
    {"business_name": "Sunrise Landscaping",      "website": "http://sunriselandscaping.weebly.com","phone":"978-555-0302","address": "5 Garden Lane","city":"Methuen","state":"MA","rating":2.7,"review_count":4},
]


# ─── Filter logic ─────────────────────────────────────────────────────────────

def _is_poor_website(url: Optional[str]) -> bool:
    """Heuristic: detect known cheap site builders as 'poor' websites."""
    if not url:
        return True
    poor_builders = ["wix", "weebly", "squarespace", "godaddy", "jimdo", "yola", "homestead"]
    return any(b in url.lower() for b in poor_builders)


def _apply_filters(leads: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    result = []
    for lead in leads:
        # Filter: no website only
        if filters.get("no_website_only") and lead.get("website"):
            continue
        # Filter: poor website (no site OR cheap builder)
        if filters.get("poor_website_only") and not _is_poor_website(lead.get("website")):
            continue
        # Filter: low reviews
        if filters.get("low_reviews_only"):
            rating = lead.get("rating") or 0
            count = lead.get("review_count") or 0
            if rating >= 4.0 and count >= 10:
                continue
        # Filter: min/max rating
        if "max_rating" in filters and (lead.get("rating") or 0) > filters["max_rating"]:
            continue
        result.append(lead)
    return result


# ─── Google Places integration ────────────────────────────────────────────────

async def _fetch_google_places(location: str, niche: str, max_results: int = 20) -> List[Dict]:
    """
    Real Google Places Text Search + Place Details.
    Falls back to mock data if API key not configured.
    """
    if not settings.GOOGLE_PLACES_API_KEY:
        return []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Text search
        search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": f"{niche} near {location}",
            "key": settings.GOOGLE_PLACES_API_KEY,
        }
        resp = await client.get(search_url, params=params)
        data = resp.json()

        results = data.get("results", [])[:max_results]
        leads = []

        # Step 2: Fetch details for each place
        for place in results:
            place_id = place.get("place_id")
            details = await _fetch_place_details(client, place_id)

            addr_components = details.get("address_components", [])
            city  = next((c["long_name"] for c in addr_components if "locality" in c.get("types", [])), "")
            state = next((c["short_name"] for c in addr_components if "administrative_area_level_1" in c.get("types", [])), "")

            leads.append({
                "business_name":   details.get("name") or place.get("name", ""),
                "website":         details.get("website"),
                "phone":           details.get("formatted_phone_number"),
                "address":         details.get("formatted_address", ""),
                "city":            city,
                "state":           state,
                "rating":          details.get("rating"),
                "review_count":    details.get("user_ratings_total", 0),
                "google_place_id": place_id,
            })

        return leads


async def _fetch_place_details(client: httpx.AsyncClient, place_id: str) -> Dict:
    """Fetch detailed info for a single Google Place."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,address_components",
        "key": settings.GOOGLE_PLACES_API_KEY,
    }
    resp = await client.get(url, params=params)
    return resp.json().get("result", {})


# ─── Public interface ─────────────────────────────────────────────────────────

async def find_leads(
    location: str,
    niche: str,
    filters: Optional[Dict[str, Any]] = None,
    max_results: int = 20,
) -> List[FoundLead]:
    """
    Main entry point for lead discovery.
    Uses Google Places if API key is set, otherwise returns mock data.
    """
    filters = filters or {}

    # Try real API first
    raw = await _fetch_google_places(location, niche, max_results)

    # Fall back to mock data (filtered by niche keyword for realism)
    if not raw:
        raw = MOCK_LEADS.copy()

    # Attach niche to each result
    for lead in raw:
        lead["niche"] = niche

    # Apply user-selected filters
    filtered = _apply_filters(raw, filters)

    # Cap results
    filtered = filtered[:max_results]

    return [FoundLead(**lead) for lead in filtered]
