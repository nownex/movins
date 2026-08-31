import json
import re
import html
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup


# =========================================================
# MOVINS — MOVIE NEWS ENGINE
# =========================================================


MAX_ARTICLES = 30


SOURCES = [

    {
        "name": "Variety",
        "feed": "https://variety.com/v/film/feed/",
        "category": "أخبار الأفلام"
    },

    {
        "name": "Deadline",
        "feed": "https://deadline.com/feed/",
        "category": "أخبار السينما"
    },

    {
        "name": "The Hollywood Reporter",
        "feed": "https://www.hollywoodreporter.com/topic/movies/feed/",
        "category": "هوليوود"
    },

    {
        "name": "IndieWire",
        "feed": "https://www.indiewire.com/feed/",
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "ComingSoon",
        "feed": "https://www.comingsoon.net/feed",
        "category": "أفلام ومسلسلات"
    }

]


# =========================================================
# HEADERS
# =========================================================


HEADERS = {

    "User-Agent":

    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"

}


# =========================================================
# CLEAN TEXT
# =========================================================


def clean_text(text):

    if not text:
        return ""

    text = html.unescape(text)

    soup = BeautifulSoup(
        text,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# GET IMAGE FROM RSS
# =========================================================


def get_image(entry):

    # RSS media content

    if hasattr(
        entry,
        "media_content"
    ):

        for media in entry.media_content:

            url = media.get(
                "url"
            )

            if url:

                return url


    # RSS media thumbnail

    if hasattr(
        entry,
        "media_thumbnail"
    ):

        for media in entry.media_thumbnail:

            url = media.get(
                "url"
            )

            if url:

                return url


    # Enclosures

    if hasattr(
        entry,
        "enclosures"
    ):

        for enclosure in entry.enclosures:

            url = enclosure.get(
                "href"
            )

            media_type = enclosure.get(
                "type",
                ""
            )

            if (
                url
                and
                "image" in media_type
            ):

                return url


    # Find image inside HTML summary

    content = ""

    if hasattr(
        entry,
        "summary"
    ):

        content = entry.summary


    elif hasattr(
        entry,
        "description"
    ):

        content = entry.description


    if content:

        soup = BeautifulSoup(
            content,
            "html.parser"
        )

        image = soup.find(
            "img"
        )

        if image:

            src = image.get(
                "src"
            )

            if src:

                return src


    return ""


# =========================================================
# GET DATE
# =========================================================


def get_date(entry):

    date_struct = None


    if hasattr(
        entry,
        "published_parsed"
    ):

        date_struct = entry.published_parsed


    elif hasattr(
        entry,
        "updated_parsed"
    ):

        date_struct = entry.updated_parsed


    if date_struct:

        try:

            dt = datetime(
                *date_struct[:6],
                tzinfo=timezone.utc
            )

            return dt.strftime(
                "%Y-%m-%d"
            )

        except Exception:

            pass


    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d"
    )


# =========================================================
# GET DESCRIPTION
# =========================================================


def get_description(entry):

    text = ""


    if hasattr(
        entry,
        "summary"
    ):

        text = clean_text(
            entry.summary
        )


    elif hasattr(
        entry,
        "description"
    ):

        text = clean_text(
            entry.description
        )


    # Limit description

    if len(text) > 280:

        text = (
            text[:277]
            +
            "..."
        )


    return text


# =========================================================
# FETCH RSS
# =========================================================


def fetch_feed(source):

    print(
        f"Fetching: {source['name']}"
    )


    try:

        response = requests.get(

            source["feed"],

            headers=HEADERS,

            timeout=20

        )


        response.raise_for_status()


        feed = feedparser.parse(
            response.content
        )


        articles = []


        for entry in feed.entries:

            title = clean_text(
                entry.get(
                    "title",
                    ""
                )
            )


            url = entry.get(
                "link",
                ""
            )


            if not title or not url:

                continue


            description = (
                get_description(
                    entry
                )
            )


            image = get_image(
                entry
            )


            date = get_date(
                entry
            )


            article = {

                "title": title,

                "description":
                    description,

                "image":
                    image,

                "category":
                    source["category"],

                "date":
                    date,

                "source":
                    source["name"],

                "url":
                    url

            }


            articles.append(
                article
            )


        print(
            f"  Found {len(articles)} articles"
        )


        return articles


    except Exception as error:

        print(
            f"ERROR {source['name']}: {error}"
        )

        return []


# =========================================================
# REMOVE DUPLICATES
# =========================================================


def remove_duplicates(articles):

    unique = []

    seen = set()


    for article in articles:

        key = (

            article["title"]
            .lower()
            .strip()

        )


        if key in seen:

            continue


        seen.add(
            key
        )


        unique.append(
            article
        )


    return unique


# =========================================================
# MAIN
# =========================================================


def main():

    all_articles = []


    for source in SOURCES:

        articles = fetch_feed(
            source
        )

        all_articles.extend(
            articles
        )


    # Remove duplicate titles

    all_articles = remove_duplicates(
        all_articles
    )


    # Sort by date

    all_articles.sort(

        key=lambda item:
        item.get(
            "date",
            ""
        ),

        reverse=True

    )


    # Keep only latest articles

    all_articles = (
        all_articles[
            :MAX_ARTICLES
        ]
    )


    data = {

        "updated_at":

        datetime.now(
            timezone.utc
        ).isoformat(),


        "items":

        all_articles

    }


    with open(

        "movie-news.json",

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            data,

            file,

            ensure_ascii=False,

            indent=2

        )


    print()

    print(
        "=============================="
    )

    print(
        f"SUCCESS: {len(all_articles)} articles saved"
    )

    print(
        "movie-news.json updated"
    )

    print(
        "=============================="
    )


if __name__ == "__main__":

    main()
