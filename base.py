import logging
from time import sleep

from bs4 import BeautifulSoup

from _db import database
from hdtoday import HDToday
from helper import helper
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class Crawler:
    def crawl_soup(self, url):
        logging.info(f"Crawling {url}")

        html = helper.download_url(url)
        soup = BeautifulSoup(html.content, "html.parser")

        return soup

    def get_episode_details(self, href, title) -> dict:
        if "http" not in href:
            href = CONFIG.KISSANIME_HOMEPAGE + href

        res = {
            "title": title,
        }
        try:
            soup = self.crawl_soup(href)

            res["links"] = helper.get_links_from(soup)

            res["released"] = helper.get_released_from(soup)

        except Exception as e:
            helper.error_log(
                f"Failed to get episode player link\n{href}\n{e}",
                log_file="base.get_episode_details.log",
            )
            return {}

        return res

    def get_episodes_data(self, soup: BeautifulSoup) -> list:
        res = []
        barContentEpisode = soup.find("div", class_="barContentEpisode")
        if not barContentEpisode:
            return

        listing = barContentEpisode.find("ul", class_="listing")
        if not listing:
            return

        items = listing.find_all("li")
        for item in items:
            try:
                a_element = item.find("a")
                episodeTitle = helper.format_text(a_element.get("title"))
                episodeHref = a_element.get("href")

                res.append(self.get_episode_details(episodeHref, episodeTitle))
            except Exception as e:
                helper.error_log(
                    msg=f"Failed to get child episode\n{item}\n{e}",
                    log_file="base.get_episodes_data.log",
                )

        return res

    def crawl_film(self, href: str, post_type: str = "tv"):
        soup = self.crawl_soup(href)

        if soup == 404:
            return

        barContentInfo = soup.find("div", class_="barContentInfo")

        if not barContentInfo:
            helper.error_log(
                f"No bar content info was found in {href}",
                log_file="base.crawl_film.noBarContentInfo.log",
            )

        title = helper.get_title_from(barContentInfo)

        poster_url = helper.get_poster_url(barContentInfo)
        poster_url = helper.add_https_to(poster_url)
        fondo_player = poster_url

        genres = helper.get_genres_from(barContentInfo)
        status = helper.get_status_from(barContentInfo)
        country = helper.get_country_from(barContentInfo)

        description = helper.get_description_from(barContentInfo)
        othername = helper.get_othername_from(barContentInfo)

        if not title:
            helper.error_log(
                msg=f"No title was found\n{href}", log_file="base.no_title.log"
            )
            return

        trailer_id = ""

        extra_info = {
            "Genre": genres,
            "Country": country,
            "othername": othername,
            "status": status,
        }

        episodes_data = self.get_episodes_data(soup)
        if not episodes_data:
            helper.error_log(
                f"No episodes were found: {href}", log_file="base.no_episodes.log"
            )
            return

        if episodes_data[0]:
            first_child = episodes_data[0]
            extra_info["Release"] = first_child["released"]

        film_data = {
            "title": title,
            "description": description,
            "post_type": post_type,
            "trailer_id": trailer_id,
            "fondo_player": fondo_player,
            "poster_url": poster_url,
            "extra_info": extra_info,
        }

        return [film_data, episodes_data]

    def crawl_page(self, url, post_type: str = "tv"):
        soup = self.crawl_soup(url)

        if soup == 404:
            return 0

        listing = soup.find("ul", class_="listing")
        if not listing:
            return 0

        items = listing.find_all("li")
        if not items:
            return 0

        for item in items:
            try:
                href = item.find("a").get("href")

                if "http" not in href:
                    href = CONFIG.KISSANIME_HOMEPAGE + href

                film_data, episodes_data = self.crawl_film(
                    href=href, post_type=post_type
                )

                episodes_dict = {}
                episodes_data.reverse()
                for i, episode in enumerate(episodes_data):
                    episodes_dict[i + 1] = episode

                HDToday(film_data, episodes_dict).insert_film()

            except Exception as e:
                helper.error_log(
                    f"Failed to get href\n{item}\n{e}", "base.crawl_page.log"
                )

        return 1


if __name__ == "__main__":
    Crawler().crawl_film(
        "https://ww1.kissanime.so/info/ijiranaide-nagatoro-san-2nd-attack-dub"
    )
