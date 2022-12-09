"""Module for MetScraper class."""

import json
from pathlib import Path
import requests
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from artscraper.base import BaseArtScraper


class MetMuseumScraper(BaseArtScraper):
    """Class for scraping Met Museum images.

    Parameters
    ----------
    output_dir: Path.pathlib or str, optional
        Output directory to store the images in.
    skip_existing: bool, default=True
        Skip exisisting images/urls.
    min_wait: int or float, default=5
        Before performing another action, ensure a waiting time
        of at least this value in seconds. The actual waiting time
        is randomly drawn from a polynomial distribution.
    """
    def __init__(self, output_dir=None, skip_existing=True, min_wait=5,
                 geckodriver_path="geckodriver"):
        super().__init__(output_dir, skip_existing, min_wait=min_wait)
        self.driver = webdriver.Firefox(executable_path=geckodriver_path)

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.driver.close()

    def load_link(self, link):
        if link == self.link:
            return False
        self.link = link

        if self.output_dir is not None:
            if (self.paint_dir.is_dir() and self.skip_existing
                    and Path(self.paint_dir, "metadata.json").is_file()
                    and Path(self.paint_dir, "painting.png").is_file()):
                return False
            self.paint_dir.mkdir(exist_ok=True)

        self.wait(self.min_wait)
        self.driver.get(link)
        return True

    @property
    def paint_dir(self):
        paint_id = urlparse(self.link).path.split("/")[4]
        return Path(self.output_dir, paint_id)

    def _get_metadata(self):
        if self.output_dir is not None and self.meta_fp.is_file():
            with open(self.meta_fp, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            return metadata

        self.wait(self.min_wait, update=False)
        paint_id = urlparse(self.link).path.split("/")[4]
        resp = requests.get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{paint_id}")
        metadata = resp.json()
        metadata['main_text'] = self.get_main_text()

        if not metadata.get('primaryImage', False):
            metadata['primaryImage'] = self.get_image_url()

        return metadata

    def get_image_url(self):
        elem = self.driver.find_element("xpath", '//meta[@property="og:image"]')
        return elem

    def get_main_text(self):
        self.wait(self.min_wait, update=False)
        try:
            elem = self.driver.find_element(By.CLASS_NAME, 'artwork__intro__desc')
        except NoSuchElementException:
            return ''
        inner_HTML = elem.get_attribute("innerHTML")
        return BeautifulSoup(inner_HTML, features="html.parser").text

    def get_image(self):
        """Get a binary JPG image in memory."""
        if self._meta_store['data']:
            img_url = self._meta_store['data']['primaryImage']
        else:
            img_url = self._get_metadata()['primaryImage']

        return requests.get(img_url).content

    def save_image(self, img_fp=None, link=None):
        """Save the artwork image to a file."""
        if link is not None:
            self.load_link()

        img_fp = self._convert_img_fp(img_fp, suffix=".jpg")

        if self.skip_existing and img_fp.is_file():
            return
        with open(img_fp, "wb") as f:
            f.write(self.get_image())
