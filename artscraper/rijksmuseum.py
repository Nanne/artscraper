"""Module for GoogleArtScraper class."""

import json
from pathlib import Path
from urllib.parse import urlparse
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

from artscraper.base import BaseArtScraper


class RijksmuseumScraper(BaseArtScraper):
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

        # if the Dutch version of the website is loaded, switch to English
        link = re.sub("nl/collectie", "en/collection", link)
        link = re.sub("nl/mijn/verzamelingen", "en/my/collections", link)

        if link == self.link:
            return False
        self.link = link

        if self.output_dir is not None:
            if (self.paint_dir.is_dir() and self.skip_existing
                    and Path(self.paint_dir, "metadata.json").is_file()
                    and Path(self.paint_dir, "painting.png").is_file()):
                return False
            self.paint_dir.mkdir(exist_ok=True, parents=True)

        self.driver.get(link)
        self.wait(self.min_wait)

        # accept cookies
        cookies_button = self.driver.find_element(
            "xpath", '//button[@name="gdprChoice" and contains(., "Accept")]')
        webdriver.ActionChains(
            self.driver).move_to_element(cookies_button).click(cookies_button).perform()
        self.wait(self.min_wait)
        return True

    @property
    def paint_dir(self):
        paint_id = "_".join(urlparse(self.link).path.split("/")[-1])
        return Path(self.output_dir, paint_id)

    def _get_metadata(self):
        if self.output_dir is not None and self.meta_fp.is_file():
            with open(self.meta_fp, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            return metadata

        metadata = {}

        paint_id = urlparse(self.link).path.split("/")[-1]
        self.wait(self.min_wait, update=False)
        base_element = f'//*[@class="object-data mini-page mini-page-compact hidden"]'

        HTML_sections = []
        possible_sections = ['identification', 'creation', 'material and technique', 'subject']
        i=0
        current_sections = []
        while set(current_sections) != set(possible_sections) and i < 10:
            i += 1
            sec_HTML = self.driver.find_element(
                "xpath", f"{base_element}/article[{i}]").get_attribute("innerHTML")
            sec_soup = BeautifulSoup(sec_HTML, features="html.parser")
            sec_title = sec_soup.find("h2").get_text().strip().lower()
            if sec_title in possible_sections:
                sec_inner_HTML = self.driver.find_element(
                "xpath", f"{base_element}/article[{i}]/div[1]").get_attribute("innerHTML")
                sec_soup = BeautifulSoup(sec_inner_HTML, features="html.parser")
                HTML_sections.append(sec_soup.find_all("div", class_="item"))
                current_sections.append(sec_title)

        for HTML in HTML_sections:
            for element in HTML:
                name = element.find("h3").get_text().strip().lower()
                if name == "description":
                    name = "main_text"
                elif name == "what":
                    name = "keywords"
                try:
                    content = []
                    paragraphs = element.find_all("p")
                    for para in paragraphs:
                        content += [para.get_text(separator = '. ').strip().lower()]
                    if len(content) == 0: # if there is no <p> tag, try <ul>
                        content = element.find("ul").text.strip().lower()
                    if len(content) == 1: content = content[0]
                except:
                    continue
                # print(f"Couldnt parse the entry: {name}")

                metadata[name] = content
                # print(f"{name}: {content}")

        metadata["id"] = paint_id
        return metadata


    def get_image(self):
        """Get a binary PNG image in memory."""
        self.wait(self.min_wait)
        # click the zoom button to enlarge the image
        heart_button = self.driver.find_element(
            "xpath", '//button[@data-role="open-tooltip"]')
        detail_button = self.driver.find_element(
            "xpath", '//a[@data-role="save-cutout-dialog"]')
        zoom_out_button = self.driver.find_element(
            "xpath", '//button[@data-role="zoom-full"]')
        closing_button = self.driver.find_element(
            "xpath", '//button[@data-role="lightbox-close"]')
        # click to get details
        webdriver.ActionChains(
            self.driver).move_to_element(heart_button).perform()
        self.wait(self.min_wait)
        webdriver.ActionChains(
            self.driver).move_to_element(detail_button).click(detail_button).perform()
        self.wait(self.min_wait)
        # now zoom to full image
        webdriver.ActionChains(
            self.driver).move_to_element(zoom_out_button).click(zoom_out_button).perform()
        self.wait(self.min_wait * 2, update=False)
        # then take a screenshot of the img element
        img_canvas = self.driver.find_element(
            "xpath", '//*[@class="micrio"]')
        img = img_canvas.screenshot_as_png
        self.wait(self.min_wait * 2, update=False)
        # finally, close the details page
        webdriver.ActionChains(
            self.driver).move_to_element(closing_button).click(closing_button).perform()
        self.wait(self.min_wait)
        # self.driver.find_element("xpath", "/html/body").send_keys(Keys.ESCAPE)
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
