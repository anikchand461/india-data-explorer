"""
Election Commission of India -- booth-level results.

Deliberately not implemented at booth level. Genuine booth-level
results (Form 20) are published by ECI as scanned, per-constituency
PDFs, not a bulk API or structured file -- every existing open dataset
of this kind (datameet, TCPD) was built by scraping/OCR-ing those PDFs
over years, which is a distinct, larger project on its own.

Constituency-level *aggregate* electoral statistics are ordinary
data.gov.in resources and can be added like any other dataset via the
`data_gov.resources` list in config/sources.yaml -- no separate client
is needed for that case.

See config/sources.yaml -> eci_election.excluded_reason.
"""


def fetch_all():
    return []
