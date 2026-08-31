import json
import re
import html
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
import feedparser


# =========================================================
# MOVINS — MOVIE NEWS ENGINE
# =========================================================

OUTPUT_FILE = "movie-news.json"

MAX_ARTICLES = 30

TIMEOUT = 20


# =========================================================
# RSS SOURCES
# =========================================================

FEEDS = [

    {
        "name": "Variety",
        "category": "أخبار السينما",
        "url": "https://variety.com/feed/"
    },

    {
        "name": "The Hollywood Reporter",
        "category": "أخبار السينما",
        "url": "https://www.hollywoodreporter.com/feed/"
    },

    {
        "name": "IndieWire",
        "category": "أخبار الأفلام",
        "url": "https://www.indiewire.com/feed/"
    },

    {
        "name": "Collider",
        "category": "أفلام ومسلسلات",
        "url": "https://collider.com/feed/"
    },

]


# =========================================================
# SESSION
# =========================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
)


# =========================================================
# CLEAN HTML
# =========================================================

def clean_text(value):

    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# =========================================================
# EXTRACT IMAGE FROM RSS
# =========================================================

def get_entry_image(entry):

    # -----------------------------------------------------
    # media_content
    # -----------------------------------------------------

    media_content = entry.get(
        "media_content",
        []
    )

    if media_content:

        for media in media_content:

            url = media.get(
                "url"
            )

            if url:

                return url


    # -----------------------------------------------------
    # media_thumbnail
    # -----------------------------------------------------

    media_thumbnail = entry.get(
        "media_thumbnail",
        []
    )

    if media_thumbnail:

        for media in media_thumbnail:

            url = media.get(
                "url"
            )

            if url:

                return url


    # -----------------------------------------------------
    # enclosures
    # -----------------------------------------------------

    enclosures = entry.get(
        "enclosures",
        []
    )

    if enclosures:

        for enclosure in enclosures:

            enclosure_type = str(
                enclosure.get(
                    "type",
                    ""
                )
            ).lower()

            url = enclosure.get(
                "href"
            )

            if (
                url
                and
                "image" in enclosure_type
            ):

                return url


    # -----------------------------------------------------
    # LINKS
    # -----------------------------------------------------

    links = entry.get(
        "links",
        []
    )

    for link in links:

        link_type = str(
            link.get(
                "type",
                ""
            )
        ).lower()

        href = link.get(
            "href"
        )

        if (
            href
            and
            "image" in link_type
        ):

            return href


    return ""


# =========================================================
# PARSE DATE
# =========================================================

def parse_date(entry):

    published = (
        entry.get("published")
        or
        entry.get("updated")
        or
        ""
    )


    if not published:

        return datetime.now(
            timezone.utc
        ).isoformat()


    try:

        date = parsedate_to_datetime(
            published
        )

        if date.tzinfo is None:

            date = date.replace(
                tzinfo=timezone.utc
            )

        return date.isoformat()


    except Exception:

        return datetime.now(
            timezone.utc
        ).isoformat()


# =========================================================
# CREATE ARTICLE
# =========================================================

def create_article(
    entry,
    source
):

    title = clean_text(
        entry.get(
            "title",
            ""
        )
    )


    description = clean_text(

        entry.get(
            "summary",
            ""
        )

        or

        entry.get(
            "description",
            ""
        )

    )


    url = (

        entry.get(
            "link",
            ""
        )

        or

        entry.get(
            "id",
            ""
        )

    )


    image = get_entry_image(
        entry
    )


    date = parse_date(
        entry
    )


    if not title:

        return None


    # Avoid very short articles

    if len(title) < 5:

        return None


    if not description:

        description = (
            "تابع آخر التطورات والأخبار "
            "المتعلقة بعالم السينما والأفلام."
        )


    return {

        "title":
            title,

        "description":
            description[:500],

        "image":
            image,

        "category":
            source["category"],

        "date":
            date,

        "published_at":
            date,

        "source":
            source["name"],

        "url":
            url

    }


# =========================================================
# DOWNLOAD RSS
# =========================================================

def fetch_feed(source):

    print()

    print(
        "=" * 60
    )

    print(
        "SOURCE:",
        source["name"]
    )

    print(
        source["url"]
    )

    print(
        "=" * 60
    )


    try:

        response = session.get(

            source["url"],

            timeout=TIMEOUT

        )


        print(
            "STATUS:",
            response.status_code
        )


        if response.status_code != 200:

            return []


        feed = feedparser.parse(
            response.content
        )


        entries = feed.entries


        print(
            "ARTICLES FOUND:",
            len(entries)
        )


        articles = []


        for entry in entries:

            article = create_article(

                entry,
                source

            )


            if article:

                articles.append(
                    article
                )


        return articles


    except Exception as error:

        print(
            "ERROR:",
            error
        )

        return []


# =========================================================
# REMOVE DUPLICATES
# =========================================================

def remove_duplicates(items):

    unique = []

    seen = set()


    for item in items:

        title = (

            item.get(
                "title",
                ""
            )

            .lower()

            .strip()

        )


        if not title:

            continue


        key = re.sub(

            r"[^a-z0-9]+",

            "",

            title

        )


        if key in seen:

            continue


        seen.add(
            key
        )


        unique.append(
            item
        )


    return unique


# =========================================================
# SORT ARTICLES
# =========================================================

def sort_articles(items):

    def get_date(item):

        value = item.get(
            "date",
            ""
        )


        try:

            return datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00"
                )
            )


        except Exception:

            return datetime.min.replace(
                tzinfo=timezone.utc
            )


    return sorted(

        items,

        key=get_date,

        reverse=True

    )


# =========================================================
# LOAD OLD NEWS
# =========================================================

def load_old_news():

    try:

        with open(

            OUTPUT_FILE,

            "r",

            encoding="utf-8"

        ) as file:

            data = json.load(
                file
            )


        items = data.get(
            "items",
            []
        )


        if isinstance(
            items,
            list
        ):

            return items


    except Exception:

        pass


    return []


# =========================================================
# SAVE JSON
# =========================================================

def save_news(items):

    data = {

        "updated_at":

            datetime.now(
                timezone.utc
            ).isoformat(),

        "items":

            items

    }


    with open(

        OUTPUT_FILE,

        "w",

        encoding="utf-8"

    ) as file:

        json.dump(

            data,

            file,

            ensure_ascii=False,

            indent=2

        )


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 60
    )

    print(
        "MOVINS MOVIE NEWS ENGINE"
    )

    print(
        "=" * 60
    )


    all_articles = []


    # -----------------------------------------------------
    # GET NEW ARTICLES
    # -----------------------------------------------------

    for source in FEEDS:

        articles = fetch_feed(
            source
        )


        all_articles.extend(
            articles
        )


        time.sleep(
            1
        )


    print()

    print(
        "TOTAL NEW ARTICLES:",
        len(all_articles)
    )


    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    all_articles = remove_duplicates(
        all_articles
    )


    print(
        "AFTER DUPLICATES:",
        len(all_articles)
    )


    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    all_articles = sort_articles(
        all_articles
    )


    # -----------------------------------------------------
    # KEEP LATEST
    # -----------------------------------------------------

    all_articles = all_articles[
        :MAX_ARTICLES
    ]


    # -----------------------------------------------------
    # SAFETY:
    # IF ALL FEEDS FAIL,
    # KEEP OLD NEWS INSTEAD OF
    # DESTROYING movie-news.json
    # -----------------------------------------------------

    if not all_articles:

        old_items = load_old_news()


        if old_items:

            print()

            print(
                "WARNING: NO NEW ARTICLES"
            )

            print(
                "KEEPING OLD NEWS:",
                len(old_items)
            )

            all_articles = old_items


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    save_news(
        all_articles
    )


    print()

    print(
        "=" * 60
    )

    print(
        "SUCCESS"
    )

    print(
        "NEWS SAVED:",
        len(all_articles)
    )

    print(
        "FILE:",
        OUTPUT_FILE
    )

    print(
        "=" * 60
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
