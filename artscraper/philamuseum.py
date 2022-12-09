"""Module for Philadelphia Museum class."""

import json
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

from artscraper.base import BaseArtScraper


class PhiladelphiaMuseumScraper(BaseArtScraper):
    """Class for scraping Philadelphia Museum images.

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

    def __init__(self, output_dir=None, skip_existing=True, min_wait=5):
        super().__init__(output_dir, skip_existing, min_wait=min_wait)
        self.driver = webdriver.Firefox()

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
        paint_id = "_".join(urlparse(self.link).path.split("/")[-1])
        return Path(self.output_dir, paint_id)

    def get_main_text(self):
        """Get the main text for the artwork.

        Returns
        -------
        str:
            The main text that was found.
        """
        # no main text for the artwork
        return ''

    def _get_metadata(self):
        if self.output_dir is not None and self.meta_fp.is_file():
            with open(self.meta_fp, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            return metadata

        paint_id = urlparse(self.link).path.split("/")[-1]
        self.wait(self.min_wait, update=False)
        elem = self.driver.find_element("xpath", f'//*[@aria-labelledby="object decription"]/tbody')
        inner_HTML = elem.get_attribute("innerHTML")
        soup = BeautifulSoup(inner_HTML, features="html.parser")

        metadata = {}
        metadata["main_text"] = self.get_main_text()

        table_HTML = soup.find_all("tr")

        for element in table_HTML:
            elems_HTML = element.find_all("td")
            name = elems_HTML[0].span.text.strip().lower()
            metadata[name] = elems_HTML[1].span.text.strip().lower()
        metadata["id"] = paint_id
        return metadata

    def get_image(self):
        """Get a binary PNG image in memory."""
        self.wait(self.min_wait)
        # click the zoom button to enlarge the image
        zoom_button = self.driver.find_element(
            "xpath", "/html/body/div[1]/div/div[7]/div/div/div[1]/div[1]/button[1]")
        webdriver.ActionChains(
            self.driver).move_to_element(zoom_button).click(zoom_button).perform()
        self.wait(self.min_wait * 2, update=False)
        # then take a screenshot of the img element
        elem = self.driver.find_element(
            "xpath", "/html/body/div[1]/div/div[7]/div/div/div[1]/micr-io/canvas")
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
