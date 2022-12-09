"""Module for SmithsonianScraper class."""

import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.request import urlretrieve

from PIL import Image

from bs4 import BeautifulSoup

from artscraper.base import BaseArtScraper

class SmithsonianScraper(BaseArtScraper):
    """Class for scraping Smithsonian images.

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
        return True

    @property
    def paint_dir(self):
        paint_id = urlparse(self.link).path.split("/")[-1].replace(":", "_")
        return Path(self.output_dir, paint_id)

    def _get_metadata(self):
        if self.output_dir is not None and self.meta_fp.is_file():
            with open(self.meta_fp, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            return metadata

        self.wait(self.min_wait, update=False)
        soup = BeautifulSoup(urlopen(self.link), 'html.parser')
        div = soup.find("div", attrs={'class': 'media-metadata'})
        art_id = div.attrs['data-idsid']

        manifest = urlopen(f"https://ids.si.edu/ids/manifest/{art_id}").read()
        manifest = json.loads(manifest)
        to_val = lambda a: list(a.values())
        metadata = {to_val(i)[0]: to_val(i)[1] for i in manifest['metadata']}
        metadata['img_url'] = manifest['sequences'][0]['canvases'][0] \
                                        ['images'][0]['resource']['@id']

        return metadata

    def get_image(self):
        """Get a binary JPG image in memory."""
        if self._meta_store['data']:
            img_url = self._meta_store['data']['img_url']
        else:
            img_url = self._get_metadata()['img_url']

        return urlopen(img_url).read()

    def save_image(self, img_fp=None, link=None):
        """Save the artwork image to a file."""
        if link is not None:
            self.load_link()

        img_fp = self._convert_img_fp(img_fp, suffix=".jpg")

        if self.skip_existing and img_fp.is_file():
            return
        with open(img_fp, "wb") as f:
            f.write(self.get_image())
