"""Scrape art image and metadata from WikiArt and Google Arts."""

from artscraper.googleart import GoogleArtScraper
from artscraper.wikiart import WikiArtScraper
from artscraper.philamuseum import PhiladelphiaMuseumScraper
from artscraper.getty import GettyScraper
from artscraper.rijksmuseum import RijksmuseumScraper
from artscraper.artic import ArticScraper

__all__ = ["GoogleArtScraper", "WikiArtScraper", "PhiladelphiaMuseumScraper", "GettyScraper", "RijksmuseumScraper", "ArticScraper"]
