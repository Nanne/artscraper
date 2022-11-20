"""Module for ArticScraper class."""

import json
import time
from pathlib import Path
from random import random
from time import sleep
from urllib.parse import urlparse
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from artscraper.base import BaseArtScraper
from artscraper.googleart import random_wait_time


class ArticScraper(BaseArtScraper):
    """Class for scraping Artic images.

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

    def __init__(self, output_dir=None, skip_existing=True, min_wait=5, driver_options=None):
        super().__init__(output_dir, skip_existing, min_wait=min_wait)
        self.driver = webdriver.Firefox(options=driver_options)
        self.last_request = time.time() - 100

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
            self.paint_dir.mkdir(exist_ok=True, parents=True)

        self.wait(self.min_wait)
        self.driver.get(link)
        return True

    @property
    def paint_dir(self):
        paint_id = "_".join(urlparse(self.link).path.split("/")[-2:])
        return Path(self.output_dir, paint_id)

    def wait(self, min_wait, max_wait=None, update=True):
        """Wait until we are allowed to perform our next action.

        Parameters
        ----------
        min_wait: int or float
            Minimum waiting time before performing the action.
        max_wait: int or float, optional
            Maximum waiting time before performing an action. By default
            3 times the minimum waiting time.
        update: bool, default=True
            If true, reset the timer.
        """
        time_elapsed = time.time() - self.last_request
        wait_time = random_wait_time(min_wait, max_wait) - time_elapsed
        if wait_time > 0:
            sleep(wait_time)
        if update:
            self.last_request = time.time()

    def get_main_text(self):
        """Get the main text for the artwork.

        Returns
        -------
        str:
            The main text that was found.
        """
        # TODO: To be implemented?
        return ""

    def _get_metadata(self):
        if self.output_dir is not None and self.meta_fp.is_file():
            with open(self.meta_fp, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            return metadata

        self.wait(self.min_wait, update=False)
        elem = self.driver.find_element('id', 'dl-artwork-details')
        rows = elem.find_elements('css selector', 'dd')
        # Select last element in rows to extract the .json link
        link = rows[-1].find_element('class name', 'f-secondary').get_attribute('innerHTML')

        with urlopen(link) as url:
            metadata = json.load(url)

        return metadata

    def get_image(self):
        """Get a binary PNG image in memory."""
        self.wait(self.min_wait)
        # Select relevant element
        ul = self.driver.find_element('class name', 'm-article-header__img-actions')
        # Find all buttons in ul, select the first one
        button = ul.find_elements('tag name', 'button')[0]
        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
        self.wait(self.min_wait, update=False)
        webdriver.ActionChains(
            self.driver).click(button).perform()
        self.wait(self.min_wait * 2, update=False)
        elem = self.driver.find_element(
            "class name", "openseadragon-canvas")
        img = elem.screenshot_as_png
        self.wait(self.min_wait)
        self.driver.find_element("xpath", "/html/body").send_keys(Keys.ESCAPE)
        return img

    def save_image(self, img_fp=None, link=None):
        """Save the artwork image to a file.

        Parameters
        ----------
        img_fp: Path.pathlib or str, optional
            Path to where the image should be stored. If no supplied,
            the image_fp is automatically infered with the paint_dir
            and name.
        link: str, optional
            Url to load, optional.
        """
        if link is not None:
            self.load_link(link)

        img_fp = self._convert_img_fp(img_fp, suffix=".png")

        if self.skip_existing and img_fp.is_file():
            return
        with open(img_fp, "wb") as f:
            f.write(self.get_image())

    def close(self):
        self.driver.close()