"""
Land records (state portals: Bhoomi, Dharani, Bhulekh, NGDRS, etc.)

Deliberately not implemented. No unified national API exists -- each
state runs its own portal, almost all requiring an individual
survey-number/khata lookup (frequently behind a captcha) rather than
bulk export. Beyond the fragmentation, bulk-collecting individual
land-ownership records into a central database raises privacy/legal
concerns distinct from the engineering effort. This is an intentional
exclusion, not a missing feature -- see config/sources.yaml ->
land_records.excluded_reason.
"""


def fetch_all():
    return []
