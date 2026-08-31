import json
import re
import html
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator


# =========================================================
# MOVINS — MOVIE NEWS ENGINE
# =========================================================

MAX_ARTICLES = 30

TIMEOUT = 20

OUTPUT_FILE = "movie-news.json"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


SOURCES = [

    {
        "name": "Variety",
        "feed": "https://variety.com/feed/",
        "category": "أخبار السينما",
        "domain": "variety.com"
    },

    {
        "name": "The Hollywood Reporter",
        "feed": "https://www.hollywoodreporter.com/feed/",
        "category": "أخبار السينما",
        "domain": "hollywoodreporter.com"
    },

    {
        "name": "IndieWire",
        "feed": "https://www.indiewire.com/feed/",
        "category": "أفلام ومسلسلات",
        "domain": "indiewire.com"
    },

    {
        "name": "Collider",
        "feed": "https://collider.com/feed/",
        "category": "أفلام ومسلسلات",
        "domain": "collider.com"
    }

]


# =========================================================
# TRANSLATOR
# =========================================================

translator = GoogleTranslator(
    source="auto",
    target="ar"
)


# =========================================================
# CLEAN HTML
# =========================================================

def clean_text(value):

    if not value:
        return ""

    soup = BeautifulSoup(
        str(value),
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = html.unescape(text)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# TRANSLATE
# =========================================================

def translate_text(text):

    if not text:
        return ""

    text = clean_text(text)

    if not text:
        return ""

    try:

        translated = translator.translate(
            text[:4500]
        )

        return translated or text

    except Exception as error:

        print(
            "TRANSLATION ERROR:",
            error
        )

        return text


# =========================================================
# CREATE ARABIC SUMMARY
# =========================================================

def create_summary(title, description):

    if not description:

        return (
            "لا تتوفر تفاصيل إضافية حول هذا الخبر حالياً. "
            "يمكنك قراءة الخبر الأصلي من المصدر لمعرفة جميع التفاصيل."
        )

    description = clean_text(
        description
    )

    if len(description) < 120:

        return description

    sentences = re.split(
        r"(?<=[.!؟])\s+",
        description
    )

    summary = []

    length = 0

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        summary.append(
            sentence
        )

        length += len(sentence)

        if length >= 450:
            break

    result = " ".join(
        summary
    )

    if len(result) < 80:
        result = description[:600]

    return result.strip()


# =========================================================
# EXTRACT IMAGE
# =========================================================

def get_entry_image(entry):

    # media_content

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


    # media_thumbnail

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


    # enclosure

    enclosures = entry.get(
        "enclosures",
        []
    )

    for enclosure in enclosures:

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


    # HTML content

    html_content = ""

    if entry.get("content"):

        try:

            html_content = entry.content[0].value

        except Exception:
            pass


    if not html_content:

        html_content = entry.get(
            "summary",
            ""
        )


    if html_content:

        soup = BeautifulSoup(
            html_content,
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
# FORMAT DATE
# =========================================================

def format_date(entry):

    published = entry.get(
        "published_parsed"
    )

    if published:

        try:

            dt = datetime(
                *published[:6],
                tzinfo=timezone.utc
            )

            months = [

                "يناير",
                "فبراير",
                "مارس",
                "أبريل",
                "مايو",
                "يونيو",
                "يوليو",
                "أغسطس",
                "سبتمبر",
                "أكتوبر",
                "نوفمبر",
                "ديسمبر"

            ]

            return (
                f"{dt.day} "
                f"{months[dt.month - 1]} "
                f"{dt.year}"
            )

        except Exception:
            pass


    return datetime.now().strftime(
        "%Y-%m-%d"
    )


# =========================================================
# SOURCE LOGO
# =========================================================

def get_source_logo(domain):

    return (
        "https://www.google.com/s2/favicons"
        f"?domain={domain}&sz=256"
    )


# =========================================================
# ARTICLE ID
# =========================================================

def make_article_id(url):

    return hashlib.md5(
        url.encode(
            "utf-8"
        )
    ).hexdigest()


# =========================================================
# LOAD SOURCE
# =========================================================

def load_source(source):

    print("\n" + "=" * 60)

    print(
        "SOURCE:",
        source["name"]
    )

    print(
        source["feed"]
    )

    print("=" * 60)


    try:

        response = requests.get(

            source["feed"],

            headers=HEADERS,

            timeout=TIMEOUT

        )


        print(
            "STATUS:",
            response.status_code
        )


        response.raise_for_status()


        feed = feedparser.parse(
            response.content
        )


        entries = feed.entries[:15]


        print(
            "ARTICLES FOUND:",
            len(entries)
        )


        articles = []


        for entry in entries:

            original_title = clean_text(
                entry.get(
                    "title",
                    ""
                )
            )


            original_description = clean_text(
                entry.get(
                    "summary",
                    ""
                )
            )


            url = entry.get(
                "link",
                ""
            )


            if not original_title or not url:
                continue


            print(
                "\nTRANSLATING:",
                original_title[:70]
            )


            arabic_title = translate_text(
                original_title
            )


            arabic_description = translate_text(
                original_description
            )


            summary = create_summary(
                arabic_title,
                arabic_description
            )


            image = get_entry_image(
                entry
            )


            article = {

                "id": make_article_id(
                    url
                ),

                "title": arabic_title,

                "description": arabic_description,

                "summary": summary,

                "originalTitle":
                    original_title,

                "image": image,

                "category":
                    source["category"],

                "date":
                    format_date(entry),

                "source":
                    source["name"],

                "sourceDomain":
                    source["domain"],

                "sourceLogo":
                    get_source_logo(
                        source["domain"]
                    ),

                "url": url

            }


            articles.append(
                article
            )


        return articles


    except Exception as error:

        print(
            "SOURCE ERROR:",
            error
        )

        return []


# =========================================================
# MAIN
# =========================================================

def main():

    print("\n" + "=" * 60)

    print(
        "MOVINS MOVIE NEWS ENGINE"
    )

    print("=" * 60)


    all_articles = []


    for source in SOURCES:

        articles = load_source(
            source
        )

        all_articles.extend(
            articles
        )


    print("\nTOTAL NEW ARTICLES:")

    print(
        len(all_articles)
    )


    # Remove duplicates

    unique_articles = []

    seen = set()


    for article in all_articles:

        article_id = article[
            "id"
        ]

        if article_id in seen:
            continue

        seen.add(
            article_id
        )

        unique_articles.append(
            article
        )


    print(
        "AFTER DUPLICATES:",
        len(unique_articles)
    )


    unique_articles = unique_articles[
        :MAX_ARTICLES
    ]


    data = {

        "updatedAt":

            datetime.now(
                timezone.utc
            ).isoformat(),

        "items":

            unique_articles

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


    print("\n" + "=" * 60)

    print("SUCCESS")

    print(
        "NEWS SAVED:",
        len(unique_articles)
    )

    print(
        "FILE:",
        OUTPUT_FILE
    )

    print("=" * 60)


if __name__ == "__main__":

    main()
