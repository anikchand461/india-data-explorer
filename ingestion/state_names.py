"""
One canonical spelling for each of India's 36 current states/UTs, so
every oral-cancer source (NFHS-5 report, NFHS-5/6 factsheets, GATS-2,
DHS boundaries) joins on the same key.

Each source spells states its own way ("Jammu & Kashmir" vs "Jammu and
Kashmir", "NCT of Delhi" vs "Delhi", "Maharastra" -- a real typo in one
district extraction). canonical_state() normalizes punctuation and
case, then resolves the remaining spelling variants via ALIASES.
"""

import re

CANONICAL_STATES = [
    "Andaman & Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra & Nagar Haveli and Daman & Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu & Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]

# Region groupings exactly as the NFHS-5 report tables use them.
STATE_REGION = {
    "Chandigarh": "North", "Delhi": "North", "Haryana": "North",
    "Himachal Pradesh": "North", "Jammu & Kashmir": "North",
    "Ladakh": "North", "Punjab": "North", "Rajasthan": "North",
    "Uttarakhand": "North",
    "Chhattisgarh": "Central", "Madhya Pradesh": "Central",
    "Uttar Pradesh": "Central",
    "Bihar": "East", "Jharkhand": "East", "Odisha": "East",
    "West Bengal": "East",
    "Arunachal Pradesh": "Northeast", "Assam": "Northeast",
    "Manipur": "Northeast", "Meghalaya": "Northeast",
    "Mizoram": "Northeast", "Nagaland": "Northeast",
    "Sikkim": "Northeast", "Tripura": "Northeast",
    "Dadra & Nagar Haveli and Daman & Diu": "West", "Goa": "West",
    "Gujarat": "West", "Maharashtra": "West",
    "Andaman & Nicobar Islands": "South", "Andhra Pradesh": "South",
    "Karnataka": "South", "Kerala": "South", "Lakshadweep": "South",
    "Puducherry": "South", "Tamil Nadu": "South", "Telangana": "South",
}


def _key(name):

    name = str(name).lower().replace("&", "and")

    return re.sub(r"[^a-z]", "", name)


ALIASES = {
    "nctofdelhi": "Delhi",
    "nctdelhi": "Delhi",
    "andamanandnicobarisland": "Andaman & Nicobar Islands",
    "maharastra": "Maharashtra",
    "dadraandnagarhaveliandd": "Dadra & Nagar Haveli and Daman & Diu",
    "dadraandnagarhavelianddamananddiu": (
        "Dadra & Nagar Haveli and Daman & Diu"
    ),
}

_LOOKUP = {_key(s): s for s in CANONICAL_STATES}
_LOOKUP.update(ALIASES)


def canonical_state(name):
    """
    Returns the canonical spelling, or None for a name that isn't one
    of the 36 current states/UTs (e.g. "India", or the pre-2020
    separate "Daman & Diu" -- callers decide how to handle those).
    """

    return _LOOKUP.get(_key(name))
