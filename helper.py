import re
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

import requests
from bs4 import BeautifulSoup
from slugify import slugify

from _db import database
from settings import CONFIG


class Helper:
    def get_header(self):
        header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E150",  # noqa: E501
            "Accept-Encoding": "gzip, deflate",
            # "Cookie": CONFIG.COOKIE,
            "Cache-Control": "max-age=0",
            "Accept-Language": "vi-VN",
            "Referer": "https://mangabuddy.com/",
        }
        return header

    def error_log(self, msg: str, log_file: str = "failed.log"):
        datetime_msg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        Path("log").mkdir(parents=True, exist_ok=True)
        with open(f"log/{log_file}", "a") as f:
            print(f"{datetime_msg} LOG:  {msg}\n{'-' * 80}", file=f)

    def download_url(self, url):
        return requests.get(url, headers=self.get_header())

    def format_text(self, text: str) -> str:
        return text.strip("\n").replace('"', "'").strip()

    def format_slug(self, slug: str) -> str:
        return slug.replace("’", "").replace("'", "")

    def add_https_to(self, url: str) -> str:
        if not url:
            return url

        if "http" not in url:
            url = "https:" + url

        return url

    def get_trailer_id(self, soup: BeautifulSoup) -> str:
        scripts = soup.find_all("script")
        for script in scripts:
            str_script = str(script)
            if "#pop-trailer" in str_script:
                splitted = str_script.split('"')
                for s in splitted:
                    if "https" in s:
                        return s.split("/")[-1]

        return ""

    def get_watching_href_and_fondo(self, soup: BeautifulSoup) -> list:
        try:
            main_detail = soup.find("div", class_="main-detail")
            main_category = main_detail.find("div", class_="main-category")

            watching_href = main_category.find("a", class_="mvi-cover").get("href")
            fondo_player = (
                main_category.find("a", class_="mvi-cover")
                .get("style")
                .replace("background-image: url(", "")
                .replace(");", "")
            )
            return [watching_href, fondo_player]

        except Exception as e:
            self.error_log(
                msg=f"Failed to find watching_href and fondo_player\n{str(soup)}\n{e}",
                log_file="helper.get_watching_href_and_fondo.log",
            )
            return ["", ""]

    def get_season_number(self, strSeason: str) -> int:
        strSeason = strSeason.split(" ")[0]
        res = ""
        for ch in strSeason:
            if ch.isdigit():
                res += ch

        return res

    def isNumber(self, strSeason: str) -> bool:
        try:
            float(strSeason)
            return True
        except Exception as e:
            return False

    def get_title_and_season_number(self, title: str) -> list:
        title = title
        season_number = "1"

        title = " ".join(title.split())
        x = re.search(
            r"(\d+(th|st|nd|rd)\s(Season|Seaon|Seson|Sason))|((Season|Seaon|Seson|Sason)\s\d+)",
            title,
        )
        if x:
            season = x.group()
            title = title.replace(season, "")
            for number in season.split():
                for suffix in ["th", "st", "nd", "rd"]:
                    number = number.replace(suffix, "")

                if self.isNumber(number):
                    season_number = number

        return [
            self.format_text(title),
            self.get_season_number(self.format_text(season_number)),
        ]

    def get_title_and_description(self, soup: BeautifulSoup) -> list:
        try:
            mvi_content = soup.find("div", class_="mvi-content")
            mvic_desc = mvi_content.find("div", class_="mvic-desc")

            title = mvic_desc.find("h3").text
            desc = mvic_desc.find("div", class_="desc").text

            return [self.format_text(title), self.format_text(desc)]

        except Exception as e:
            self.error_log(
                msg=f"Failed to find title and description\n{str(soup)}\n{e}",
                log_file="helper.get_title_and_description.log",
            )
            return ["", ""]

    def get_poster_url(self, barContentInfo: BeautifulSoup) -> str:
        try:
            img_picture_mb = barContentInfo.find("div", class_="img_picture_mb")
            poster_url = img_picture_mb.find("img").get("src")
            return poster_url

        except Exception as e:
            self.error_log(
                msg=f"Failed to get poster URL\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_poster_url.log",
            )
            return ""

    def get_left_data(self, mvici: BeautifulSoup) -> dict:
        res = {}
        for p in mvici.find_all("p"):
            key = p.find("strong").text.replace(":", "").strip()

            value = []
            a_elements = p.find_all("a")
            if (key == "Actor") and (len(a_elements) > 2):
                a_elements = a_elements[:-2]
            for a in a_elements:
                a_title = a.get("title")
                value.append(self.format_text(a_title))

            res[key] = value

        return res

    def get_right_data(self, mvici: BeautifulSoup) -> dict:
        res = {}
        for p in mvici.find_all("p"):
            strong_text = p.find("strong").text
            key = strong_text.replace(":", "").strip()
            value = p.text.replace(strong_text, "").strip()

            res[key] = value

        if "Duration" in res.keys():
            res["Duration"] = res["Duration"].replace("min", "").strip()
        return res

    def get_extra_info(self, soup: BeautifulSoup) -> dict:
        mvici_data = {}
        try:
            mvi_content = soup.find("div", class_="mvi-content")
            mvic_desc = mvi_content.find("div", class_="mvic-desc")
            mvic_info = mvic_desc.find("div", class_="mvic-info")
            mvici_left = mvic_info.find("div", class_="mvici-left")
            mvici_left_data = self.get_left_data(mvici_left)

            mvici_right = mvic_info.find("div", class_="mvici-right")
            mvici_right_data = self.get_right_data(mvici_right)

            mvici_data = {**mvici_left_data, **mvici_right_data}

        except Exception as e:
            self.error_log(
                msg=f"Failed to get extra info\n{str(soup)}\n{e}",
                log_file="helper.get_extra_info.log",
            )

        return mvici_data

    def generate_film_data(
        self,
        title,
        description,
        post_type,
        trailer_id,
        fondo_player,
        poster_url,
        extra_info,
    ):
        post_data = {
            "description": description,
            "title": title,
            "post_type": post_type,
            # "id": "202302",
            "youtube_id": f"[{trailer_id}]",
            # "serie_vote_average": extra_info["IMDb"],
            # "episode_run_time": extra_info["Duration"],
            "fondo_player": fondo_player,
            "poster_url": poster_url,
            # "category": extra_info["Genre"],
            # "stars": extra_info["Actor"],
            # "director": extra_info["Director"],
            # "release-year": [extra_info["Release"]],
            # "country": extra_info["Country"],
        }

        for info_key in CONFIG.KEY_MAPPING.keys():
            if info_key in extra_info.keys():
                post_data[CONFIG.KEY_MAPPING[info_key]] = extra_info[info_key]
        if "Release" in extra_info.keys():
            post_data["annee"] = [extra_info["Release"]]

        for info_key in ["cast", "directors"]:
            if info_key in post_data.keys():
                post_data[f"{info_key}_tv"] = post_data[info_key]

        return post_data

    def get_players_iframes(self, links: list) -> list:
        players = []
        for link in links:
            players.append(CONFIG.IFRAME.format(link))

        return players

    def get_timeupdate(self) -> datetime:
        timeupdate = datetime.now() - timedelta(hours=7)

        return timeupdate

    def format_condition_str(self, equal_condition: str) -> str:
        return equal_condition.replace("\n", "").strip().lower()

    def insert_terms(self, post_id: int, terms: list, taxonomy: str):
        termIds = []
        for term in terms:
            term_name = self.format_condition_str(term)
            cols = "tt.term_taxonomy_id, tt.term_id"
            table = (
                f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
            )
            condition = f't.name = "{term_name}" AND tt.term_id=t.term_id AND tt.taxonomy="{taxonomy}"'

            be_term = database.select_all_from(
                table=table, condition=condition, cols=cols
            )
            if not be_term:
                term_id = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}terms",
                    data=(term, slugify(term), 0),
                )
                termIds = [term_id, True]
                term_taxonomy_id = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
                    data=(term_id, taxonomy, "", 0, 0),
                )
            else:
                term_taxonomy_id = be_term[0][0]
                term_id = be_term[0][1]
                termIds = [term_id, False]

            try:
                database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_relationships",
                    data=(post_id, term_taxonomy_id, 0),
                )
            except:
                pass

        return termIds

    def generate_post(self, post_data: dict) -> tuple:
        timeupdate = self.get_timeupdate()
        data = (
            0,
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            post_data["description"],
            post_data["title"],
            "",
            "publish",
            "open",
            "closed",
            "",
            slugify(self.format_slug(post_data["title"])),
            "",
            "",
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            "",
            0,
            "",
            0,
            post_data["post_type"],
            "",
            0,
        )
        return data

    def insert_post(self, post_data: dict) -> int:
        data = self.generate_post(post_data)
        post_id = database.insert_into(table=f"{CONFIG.TABLE_PREFIX}posts", data=data)
        return post_id

    def insert_film(self, post_data: dict) -> int:
        try:
            post_id = self.insert_post(post_data)
            timeupdate = self.get_timeupdate()

            postmeta_data = [
                (post_id, "_edit_last", "1"),
                (post_id, "_edit_lock", f"{int(timeupdate.timestamp())}:1"),
                # _thumbnail_id
                (post_id, "tr_post_type", "2"),
                (post_id, "field_title", post_data["title"]),
                (
                    post_id,
                    "field_trailer",
                    CONFIG.YOUTUBE_IFRAME.format(post_data["youtube_id"]),
                ),
                (
                    post_id,
                    "poster_hotlink",
                    post_data["poster_url"],
                ),
                (
                    post_id,
                    "backdrop_hotlink",
                    post_data["fondo_player"],
                ),
            ]

            if "rating" in post_data.keys():
                postmeta_data.append((post_id, "rating", post_data["rating"]))

            tvseries_postmeta_data = []
            movie_postmeta_data = []

            if "annee" in post_data.keys():
                annee = (
                    post_id,
                    "field_date",
                    post_data["annee"][0],
                )

                tvseries_postmeta_data.append(annee)
                movie_postmeta_data.append(annee)

            if "field_runtime" in post_data.keys():
                tvseries_postmeta_data.append(
                    (
                        post_id,
                        "field_runtime",
                        "a:1:{i:0;i:" + post_data["field_runtime"] + ";}",
                    )
                )

                movie_postmeta_data.append(
                    (post_id, "field_runtime", f"{post_data['field_runtime']}m"),
                )

            if post_data["post_type"] == "series":
                postmeta_data.extend(tvseries_postmeta_data)
            else:
                postmeta_data.extend(movie_postmeta_data)

            self.insert_postmeta(postmeta_data)

            for taxonomy in CONFIG.TAXONOMIES[post_data["post_type"]]:
                if taxonomy in post_data.keys() and post_data[taxonomy]:
                    self.insert_terms(
                        post_id=post_id, terms=post_data[taxonomy], taxonomy=taxonomy
                    )

            return post_id
        except Exception as e:
            self.error_log(f"Failed to insert film\n{e}")

    def update_meta_key(self, post_id, meta_key, update_value, field) -> list:
        condition = f'post_id={post_id} AND meta_key="{meta_key}"'
        post_temporadas_episodios = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}postmeta", condition=condition
        )
        if post_temporadas_episodios:
            value = int(post_temporadas_episodios[0][-1])
            if value < update_value:
                database.update_table(
                    table=f"{CONFIG.TABLE_PREFIX}postmeta",
                    set_cond=f"meta_value={update_value}",
                    where_cond=condition,
                )
            return []
        else:
            return [
                (
                    post_id,
                    meta_key,
                    update_value,
                ),
                (post_id, f"_{meta_key}", field),
            ]

    def generate_players_postmeta_data(
        self, episode_id, players: list, quality: str
    ) -> list:
        res = []
        for i in range(len(players)):
            iframe = players[i]
            res.extend(
                [
                    (episode_id, f"player_{i}_name_player", ""),
                    (episode_id, f"_player_{i}_name_player", "field_5a6ae00d1df8f"),
                    (episode_id, f"player_{i}_type_player", "p_embed"),
                    (episode_id, f"_player_{i}_type_player", "field_591fd3cc1c291"),
                    (episode_id, f"player_{i}_quality_player", quality),
                    (episode_id, f"_player_{i}_quality_player", "field_5640cc8323220"),
                    (
                        episode_id,
                        f"player_{i}_embed_player",
                        iframe,
                    ),
                    (episode_id, f"_player_{i}_embed_player", "field_5640cc9823221"),
                ]
            )
        return res

    def insert_episode(self, episode_data: dict):
        season_number = int(episode_data["season_number"])
        episode_number = episode_data["episode_number"]

        episode_id = self.insert_post(episode_data)
        players = episode_data["players"]
        temporadas_episodios = (
            f"temporadas_{season_number-1}_episodios_{episode_number}"
        )

        postmeta_data = [
            # (episode_id, "ids", episode_data["ids"]),
            (episode_id, "temporada", season_number),
            (episode_id, "episodio", episode_number + 1),
            (episode_id, "serie", episode_data["serie"]),
            (episode_id, "season_number", season_number),
            (episode_id, "episode_number", episode_number + 1),
            (episode_id, "name", episode_data["name"]),
            # (episode_id, "air_date", episode_data["air_date"]),
            (episode_id, "fondo_player", episode_data["fondo_player"]),
            (episode_id, "poster_serie", episode_data["poster_serie"]),
            (episode_id, "player", str(len(players))),
            (episode_id, "_player", "field_5640ccb223222"),
            (episode_id, "_edit_last", "1"),
            (episode_id, "ep_pagination", "default"),
            (episode_id, "notice_s", "0"),
            (episode_id, "_notice_s", "field_5b4c2d7154b68"),
            (
                episode_data["post_id"],
                f"{temporadas_episodios}_slug",
                slugify(self.format_slug(episode_data["title"])),
            ),
            (
                episode_data["post_id"],
                f"_{temporadas_episodios}_slug",
                "field_58718dccc2bfb",
            ),
            (episode_data["post_id"], f"{temporadas_episodios}_titlee", ""),
            (
                episode_data["post_id"],
                f"_{temporadas_episodios}_titlee",
                "field_58718ddac2bfc",
            ),
        ]

        postmeta_data.extend(
            self.update_meta_key(
                post_id=episode_data["post_id"],
                meta_key="temporadas",
                update_value=season_number,
                field="field_58718d88c2bf9",
            )
        )

        postmeta_data.extend(
            self.update_meta_key(
                post_id=episode_data["post_id"],
                meta_key=f"temporadas_{season_number - 1}_episodios",
                update_value=episode_number + 1,
                field="field_58718dabc2bfa",
            )
        )

        postmeta_data.extend(
            self.generate_players_postmeta_data(
                episode_id, players, episode_data["quality"]
            )
        )

        self.insert_postmeta(postmeta_data)

        sleep(0.01)

    def insert_postmeta(self, postmeta_data: list, table: str = "postmeta"):
        for row in postmeta_data:
            database.insert_into(
                table=f"{CONFIG.TABLE_PREFIX}{table}",
                data=row,
            )
            sleep(0.01)

    def get_title_from(self, barContentInfo: BeautifulSoup) -> str:
        try:
            title = barContentInfo.find("a", class_="bigChar").text

            return self.format_text(title)

        except Exception as e:
            self.error_log(
                msg=f"Failed to find title\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_title_from.log",
            )
            return ""

    def get_genres_from(self, barContentInfo: BeautifulSoup) -> list:
        res = []

        try:
            for p in barContentInfo.find_all("p"):
                if p.find("span"):
                    key = p.find("span").text.replace(":", "").strip()
                    if "genres" in key.lower():
                        a_elements = p.find_all("a")
                        for a in a_elements:
                            a_title = a.get("title")
                            res.append(self.format_text(a_title))

        except Exception as e:
            self.error_log(
                msg=f"Failed to get genres\n{str(barContentInfo)}\n{e}",
                log_file="genres.log",
            )

        return res

    def get_status_from(self, barContentInfo: BeautifulSoup) -> str:
        res = "Ongoing"

        try:
            for p in barContentInfo.find_all("p"):
                if p.find("span"):
                    key = p.find("span").text.replace(":", "").strip()
                    if "status" in key.lower():
                        value = p.text.replace("Status:", "")
                        value = self.format_text(value)

                        return value

        except Exception as e:
            self.error_log(
                msg=f"Failed to get status\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_status_from.log",
            )

        return res

    def get_country_from(self, barContentInfo: BeautifulSoup) -> str:
        res = []

        # try:
        #     for p in barContentInfo.find_all("p"):
        #         if p.find("span"):
        #             key = p.find("span").text.replace(":", "").strip()
        #             if "country" in key.lower():
        #                 value = p.text.replace("Country:", "")
        #                 value = self.format_text(value)

        #                 res += value.split(",")

        # except Exception as e:
        #     self.error_log(
        #         msg=f"Failed to get country\n{str(barContentInfo)}\n{e}",
        #         log_file="helper.get_country_from.log",
        #     )

        return res

    def get_description_from(self, barContentInfo: BeautifulSoup) -> str:
        res = ""

        try:
            des = barContentInfo.find("p", class_="des")
            res = self.format_text(des.text)

        except Exception as e:
            self.error_log(
                msg=f"Failed to get description\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_description_from.log",
            )

        return res

    def get_othername_from(self, barContentInfo: BeautifulSoup) -> str:
        try:
            for p in barContentInfo.find_all("p"):
                if p.find("span"):
                    key = p.find("span").text.replace(":", "").strip()
                    if "other" in key.lower() or "also known as" in key.lower():
                        res = self.format_text(p.text)

        except Exception as e:
            self.error_log(
                msg=f"Failed to get_othername_from\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_othername_from.log",
            )

        return res

    def get_links_from(self, soup: BeautifulSoup) -> str:
        try:
            mutiserver = soup.find("div", class_="mutiserver")
            options = mutiserver.find_all("option")

            return [option.get("value") for option in options]
        except Exception as e:
            self.error_log(
                msg=f"Failed to get links from {soup}\n{e}",
                log_file="helper.get_links_from.log",
            )
            return []

    def get_released_from(self, soup: BeautifulSoup) -> str:
        try:
            release = soup.find("div", class_="Releasew")
            replaceText = release.find("span").text

            res = release.text.replace(replaceText, "").strip().strip("\n").strip()

            return res

        except Exception as e:
            self.error_log(
                msg=f"Failed get_released_from\n{soup}\n{e}",
                log_file="helper.get_released_from.log",
            )
            return ""


helper = Helper()

if __name__ == "__main__":
    print("Helper running...")
