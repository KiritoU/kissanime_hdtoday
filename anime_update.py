import logging
import time

from base import Crawler
from helper import helper
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


crawler = Crawler()

if __name__ == "__main__":
    while True:
        try:
            crawler.crawl_page(CONFIG.KISSANIME_LATEST_PAGE)
        except Exception as e:
            helper.error_log(
                msg=f"anime update failed\n{e}", log_file="anime_update.log"
            )

        time.sleep(CONFIG.WAIT_BETWEEN_LATEST)
