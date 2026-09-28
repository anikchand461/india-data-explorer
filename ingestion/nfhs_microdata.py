"""
NFHS full unit-level microdata (DHS Program).

Deliberately not implemented. Unit-level NFHS microdata is distributed
by the DHS Program and requires a manual, human-reviewed
research-project application (title + justification, ~24h review) --
it is not self-service and cannot be automated or scripted.

NFHS-5 *aggregate* state/UT factsheets are published as an ordinary
data.gov.in resource and should be added via the `data_gov.resources`
list in config/sources.yaml instead, which is self-service today.

See config/sources.yaml -> nfhs_microdata.excluded_reason.
"""


def fetch_all():
    return []
