class NDAPClient:
    """
    Placeholder for NDAP integration.

    Verified during the 2026-09 integration pass: ndap.niti.gov.in
    serves a client-side-rendered React SPA (the root page returns an
    empty <div id="root"></div> with no server-rendered content), and
    no public JSON API endpoint could be discovered via direct HTTP
    probing (common REST path guesses all returned 404). The
    requests + BeautifulSoup approach used for microdata.gov.in cannot
    read this site.

    Integrating it for real would require either headless-browser
    automation (Selenium/Playwright) or reverse engineering the site's
    internal API from browser devtools -- neither was attempted here
    since the result would be undocumented and unstable to build on.
    See config/sources.yaml -> ndap.blocked_reason.
    """

    def __init__(self):
        self.base_url = "https://ndap.niti.gov.in"

    def search(self, query):
        return []

    def get_dataset(self, dataset_id):
        return None


def fetch_all():
    return []