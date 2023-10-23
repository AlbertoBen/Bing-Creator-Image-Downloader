import logging
import sys

import aiofiles
import asyncio
from datetime import date
import time
import os
import platform
import zipfile

import aiohttp
import structlog

from arsenic import get_session
from arsenic.browsers import Firefox
from arsenic.constants import SelectorType
from arsenic.services import Geckodriver


async def get_image_tuples(img_url_list: list):
    results = []
    for url in img_url_list:
        image = await get_image_from_url_sequential(url)
        results.append(image)
    return results


async def get_image_from_url_sequential(url):
    service = Geckodriver(
        binary='C:\\downloadBingCollection\\geckodriver-v0.33.0-win64\\geckodriver.exe',
        log_file=os.devnull
    )
    options = Firefox(**{
        "moz:firefoxOptions": {
            "args": ["-headless"]
        }
    })
    
    async with get_session(service, options) as session:
        await session.get(url)
        logging.info(f"Getting image for URL: {url}")
        try:
            img = await session.wait_for_element(20, "//div[@class='imgContainer']/img", SelectorType.xpath)
            src = await img.get_attribute("src")
            alt = await img.get_attribute("alt")
        except arsenic.errors.NoSuchElement as e:
            return null,null
        logging.info(f"Getting image for URL: {src}")
        
        return src, alt


async def download_and_zip_images(image_tuples: list):
    zip_file = zipfile.ZipFile(f"bing_images_{date.today()}.zip", "w")
    async with aiohttp.ClientSession() as session:
        for index, (src, alt) in enumerate(image_tuples):
            file_name = await download_and_save_image(session, src, alt, index)
            if file_name is not None:
                zip_file.write(file_name)
    zip_file.close()


async def download_and_save_image(session, src, alt, index):
    try:
        async with session.get(src) as response:
            if response.status == 200:
                filename = f"{alt}_{str(index)}.jpg"
                async with aiofiles.open(filename, "wb") as f:
                    await f.write(await response.read())
                logging.info(f"Downloading image from: {src}")
                return filename
            else:
                print(f"Failed to download {src}")
    except Exception as e:
        print(e)


def set_arsenic_log_level(level=logging.WARNING):
    logger = logging.getLogger('arsenic')

    def logger_factory():
        return logger

    structlog.configure(logger_factory=logger_factory)
    logger.setLevel(level)


async def main():
    start = time.time()

    with open("images_clipboard.txt", "r") as f:
        content = f.read().splitlines()
    lines = [line for line in content
             if line != "www.bing.com" and line != ""]
    image_url_list = [lines[i + 1] for i in range(0, len(lines), 2)]
    logging.info(f"Preparing {len(image_url_list)} URLs for download...")
    image_tuples = await get_image_tuples(image_url_list)
    await download_and_zip_images(image_tuples)

    end = time.time()
    elapsed = end - start
    logging.info(f"Finished downloading {len(image_url_list)} images in {round(elapsed, 2)} seconds.")


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    set_arsenic_log_level()
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
