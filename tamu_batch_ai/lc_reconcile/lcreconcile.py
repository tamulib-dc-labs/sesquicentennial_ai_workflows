import requests
import difflib
from urllib.parse import quote
from lxml import etree
from bs4 import BeautifulSoup as bSoup
import logging


class Recon:
    """Reconciliation object representing a LoC heading and its match score."""
    def __init__(self, score):
        self.score = score[0]
        self.header, self.uri = score[1]
        self.id = self.uri.split("/")[-1]

    def __str__(self):
        return f"{self.header} ({self.score:.3f})"

    @staticmethod
    def reconcile(original, term_pairs, sort=False, limit=20):
        """
        Appends a reconciliation score to each term-identifier pair.

        Args:
            original (str): The term to reconcile.
            term_pairs (list): List of (term, URI) tuples.
            sort (bool): Whether to sort by score.
            limit (int): Maximum results to return.

        Returns:
            list: List of [score, (term, URI)] pairs.
        """
        recon_scores = []
        for term, uri in term_pairs:
            clean_term = term.lower().replace("&amp;", "&").rstrip(".")
            sim_ratio = round(difflib.SequenceMatcher(
                None, original.lower(), clean_term).ratio(), 3)
            recon_scores.append([sim_ratio, (term, uri)])

        if sort:
            recon_scores.sort(key=lambda x: x[0], reverse=True)
        return recon_scores[:limit]


class SearchLoC:
    """Searches the Library of Congress Authorities and Vocabularies."""
    logging.basicConfig(level=logging.INFO)
    LOGGER = logging.getLogger(__name__)

    def __init__(self, term, term_type=''):
        self.term = term
        self.term_type = term_type  # will trigger setter
        self.suggest_uri = f"http://id.loc.gov/authorities{self.term_type}/suggest/?q="
        self.__raw_uri_start = "http://id.loc.gov/search/?q="
        self.__raw_uri_end = (
            "&q=cs%3Ahttp%3A%2F%2Fid.loc.gov%2Fauthorities%2F" + self.term_type[1:]
        )

    def __str__(self):
        return str(self.search_terms())

    @property
    def term_type(self):
        return self._term_type

    @term_type.setter
    def term_type(self, val):
        valid = {"", "all", "names", "/names", "subjects", "/subjects"}
        if val in valid:
            if val in {"all", ""}:
                self._term_type = ""
            else:
                self._term_type = val if val.startswith("/") else f"/{val}"
        else:
            self._term_type = ""

    def search_terms(self):
        """Query the Suggest API for a term."""
        self.LOGGER.debug(f"HTTP request on Suggest API for {self.term}")
        try:
            response = requests.get(self.suggest_uri + quote(self.term), timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            self.LOGGER.error(f"Suggest API request failed: {e}")
            return []
        result = response.json()
        return self.__process_results(result)

    @staticmethod
    def __process_results(results):
        """Parse suggest API results into (term, URI) pairs."""
        id_pairs = []
        for i, _ in enumerate(results[1]):
            term_name = results[1][i]
            term_id = results[3][i]
            if term_id and term_name:
                id_pairs.append((term_name, term_id))
        return id_pairs

    def did_you_mean(self):
        """Query the Did You Mean API."""
        dym_base = f"http://id.loc.gov/authorities{self.term_type}/didyoumean/?label="
        dym_url = dym_base + quote(self.term)
        self.LOGGER.debug(f"Querying DidYouMean with URL {dym_url}")
        try:
            response = requests.get(dym_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            self.LOGGER.error(f"DidYouMean request failed: {e}")
            return []
        tree = etree.fromstring(response.content)
        return [(child.text, child.attrib["uri"]) for child in iter(tree)]

    def search_terms_raw(self):
        """Scrape the first page of LoC search results if APIs fail."""
        self.LOGGER.debug(f"Web scraping page 1 of web results for {self.term}")
        search_uri = f"{self.__raw_uri_start}{quote(self.term)}{self.__raw_uri_end}"
        try:
            response = requests.get(search_uri, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            self.LOGGER.error(f"Scrape request failed: {e}")
            return []

        parser = bSoup(response.text, "html.parser")
        results = []
        for link in parser.select("td > a[href^='/authorities']"):
            heading = link.text.strip()
            term_id = link["href"].split("/")[-1]
            term_uri = self.get_term_uri(term_id)
            if term_uri and heading:
                results.append((heading, term_uri))
        return results

    def full_search(self, suggest=True, didyoumean=True, scrape=True):
        """Run all search methods (suggest → did you mean → scraping)."""
        results = []
        if suggest:
            results = self.search_terms()
        if not results and didyoumean:
            results = self.did_you_mean()
        if not results and scrape:
            results = self.search_terms_raw()
        return results

    def get_term_uri(self, term_id, extension="html", include_ext=False):
        """Return the URI of a term given its ID."""
        term_uri = f"http://id.loc.gov/authorities{self.term_type}/{term_id}"
        return f"{term_uri}.{extension}" if include_ext else term_uri


if __name__ == "__main__":
    search_term = "Faculty"
    searcher = SearchLoC(term=search_term, term_type="/subjects")
    results = searcher.full_search()
    print("Search results:", results)

    recon_ = Recon.reconcile(search_term, results, sort=True, limit=5)
    print("\nTop matches:")
    for ro in recon_:
        print(Recon(ro))
