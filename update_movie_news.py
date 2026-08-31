import os
import json
import time
import hashlib
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
import feedparser


# =========================================================
# MOVINS — MOVIE NEWS ENGINE
# RSS + GEMINI ARABIC TRANSLATION + SUMMARY
# =========================================================


# =========================================================
# CONFIG
# =========================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Add it to GitHub Secrets."
    )


GEMINI_MODEL = "gemini-2.5-flash"


MAX_ARTICLES = 30


OUTPUT_FILE = "movie-news.json"


# صورة افتراضية خاصة بموقع MOVINS
# ضع ملف الصورة بهذا الاسم داخل المشروع
DEFAULT_IMAGE = "movins-news.jpg"


SOURCES = [

    {
        "name": "Variety",
        "url": "https://variety.com/feed/"
    },

    {
        "name": "The Hollywood Reporter",
        "url": "https://www.hollywoodreporter.com/feed/"
    },

    {
        "name": "IndieWire",
        "url": "https://www.indiewire.com/feed/"
    },

    {
        "name": "Collider",
        "url": "https://collider.com/feed/"
    }

]


# =========================================================
# HTTP SESSION
# =========================================================

session = requests.Session()

session.headers.update({

    "User-Agent":
    (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )

})


# =========================================================
# CLEAN HTML
# =========================================================

def clean_html(text):

    if not text:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        str(text)
    )

    text = text.replace(
        "&nbsp;",
        " "
    )

    text = text.replace(
        "&amp;",
        "&"
    )

    text = text.replace(
        "&quot;",
        '"'
    )

    text = text.replace(
        "&#39;",
        "'"
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# DATE FORMAT
# =========================================================

def format_date(value):

    if not value:
        return datetime.now().strftime(
            "%Y-%m-%d"
        )

    try:

        date = parsedate_to_datetime(
            value
        )

        if date.tzinfo is None:

            date = date.replace(
                tzinfo=timezone.utc
            )

        return date.astimezone(
            timezone.utc
        ).strftime(
            "%Y-%m-%d"
        )

    except Exception:

        return datetime.now().strftime(
            "%Y-%m-%d"
        )


# =========================================================
# EXTRACT IMAGE
# =========================================================

def get_image(entry):

    # media_content
    if hasattr(entry, "media_content"):

        try:

            for media in entry.media_content:

                url = media.get(
                    "url"
                )

                if url:
                    return url

        except Exception:
            pass


    # media_thumbnail
    if hasattr(entry, "media_thumbnail"):

        try:

            for media in entry.media_thumbnail:

                url = media.get(
                    "url"
                )

                if url:
                    return url

        except Exception:
            pass


    # enclosures
    if hasattr(entry, "enclosures"):

        try:

            for enclosure in entry.enclosures:

                url = enclosure.get(
                    "href"
                )

                if url:
                    return url

        except Exception:
            pass


    # image
    if "image" in entry:

        try:

            image = entry.image

            if isinstance(
                image,
                dict
            ):

                url = image.get(
                    "href"
                )

                if url:
                    return url

        except Exception:
            pass


    return DEFAULT_IMAGE


# =========================================================
# GEMINI
# =========================================================

def gemini_translate_and_summarize(
    title,
    description,
    source
):

    prompt = f"""
أنت محرر محترف لموقع عربي متخصص في أخبار السينما اسمه MOVINS.

لدي خبر من موقع:
{source}

عنوان الخبر بالإنجليزية:
{title}

وصف الخبر:
{description}

المطلوب:

1. ترجم عنوان الخبر إلى العربية ترجمة طبيعية واحترافية.
2. اكتب وصفًا عربيًا قصيرًا مناسبًا لبطاقة خبر.
3. اكتب ملخصًا عربيًا مسترسلًا وواضحًا للخبر في فقرة أو فقرتين.
4. لا تخترع أي معلومات غير موجودة في النص.
5. لا تذكر أنك ذكاء اصطناعي.
6. اجعل اللغة عربية فصحى سهلة.
7. لا تستخدم Markdown.
8. أعد JSON فقط بدون أي كلام خارجه.

استخدم هذا الشكل بالضبط:

{{
  "title_ar": "العنوان بالعربية",
  "description_ar": "وصف قصير بالعربية",
  "summary_ar": "ملخص عربي مسترسل للخبر"
}}
"""


    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )


    headers = {

        "Content-Type":
        "application/json"

    }


    payload = {

        "contents": [

            {

                "parts": [

                    {

                        "text":
                        prompt

                    }

                ]

            }

        ],

        "generationConfig": {

            "temperature":
            0.3,

            "responseMimeType":
            "application/json"

        }

    }


    try:

        response = session.post(

            url,

            params={

                "key":
                GEMINI_API_KEY

            },

            headers=headers,

            json=payload,

            timeout=60

        )


        if not response.ok:

            print(
                "GEMINI ERROR:",
                response.status_code
            )

            print(
                response.text[:500]
            )

            return {

                "title_ar":
                title,

                "description_ar":
                description,

                "summary_ar":
                description

            }


        data = response.json()


        text = (

            data["candidates"][0]
            ["content"]["parts"][0]
            ["text"]

        )


        result = json.loads(
            text
        )


        return {

            "title_ar":

            str(
                result.get(
                    "title_ar",
                    title
                )
            ).strip(),


            "description_ar":

            str(
                result.get(
                    "description_ar",
                    description
                )
            ).strip(),


            "summary_ar":

            str(
                result.get(
                    "summary_ar",
                    description
                )
            ).strip()

        }


    except Exception as error:

        print(
            "GEMINI EXCEPTION:",
            error
        )

        return {

            "title_ar":
            title,

            "description_ar":
            description,

            "summary_ar":
            description

        }


# =========================================================
# CREATE ARTICLE ID
# =========================================================

def create_article_id(url):

    return hashlib.sha256(

        url.encode(
            "utf-8"
        )

    ).hexdigest()[:20]


# =========================================================
# LOAD RSS
# =========================================================

def load_source(source):

    print()
    print("=" * 60)
    print(
        f"SOURCE: {source['name']}"
    )
    print(
        source["url"]
    )
    print("=" * 60)


    try:

        response = session.get(

            source["url"],

            timeout=30

        )


        print(
            "STATUS:",
            response.status_code
        )


        response.raise_for_status()


        feed = feedparser.parse(

            response.content

        )


        print(
            "ARTICLES FOUND:",
            len(
                feed.entries
            )
        )


        articles = []


        for entry in feed.entries:

            title = clean_html(

                entry.get(
                    "title",
                    ""
                )

            )


            url = entry.get(

                "link",
                ""

            )


            description = clean_html(

                entry.get(
                    "summary",
                    entry.get(
                        "description",
                        ""
                    )
                )

            )


            date = format_date(

                entry.get(
                    "published",
                    entry.get(
                        "updated",
                        ""
                    )
                )

            )


            image = get_image(
                entry
            )


            if not title:

                continue


            if not url:

                continue


            # =================================================
            # GEMINI TRANSLATION
            # =================================================

            print()
            print(
                "Translating:"
            )

            print(
                title[:100]
            )


            arabic = (
                gemini_translate_and_summarize(

                    title=title,

                    description=description,

                    source=source["name"]

                )
            )


            article = {

                "id":
                create_article_id(
                    url
                ),


                # Arabic content
                "title":
                arabic[
                    "title_ar"
                ],


                "description":
                arabic[
                    "description_ar"
                ],


                "summary":
                arabic[
                    "summary_ar"
                ],


                # Original content
                "original_title":
                title,


                "original_description":
                description,


                # Other information
                "image":
                image,


                "url":
                url,


                "source":
                source["name"],


                "category":
                "أخبار السينما",


                "date":
                date


            }


            articles.append(
                article
            )


            # انتظار بسيط
            # لتجنب إرسال الطلبات بسرعة كبيرة

            time.sleep(
                0.5
            )


        return articles


    except Exception as error:

        print()

        print(
            "SOURCE ERROR:",
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

        article_id = item.get(
            "id"
        )


        if not article_id:

            continue


        if article_id in seen:

            continue


        seen.add(
            article_id
        )


        unique.append(
            item
        )


    return unique


# =========================================================
# SORT ARTICLES
# =========================================================

def sort_articles(items):

    return sorted(

        items,

        key=lambda item:

        item.get(
            "date",
            ""
        ),

        reverse=True

    )


# =========================================================
# SAVE NEWS
# =========================================================

def save_news(items):

    output = {

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

            output,

            file,

            ensure_ascii=False,

            indent=2

        )


    print()
    print("=" * 60)
    print("SUCCESS")
    print(
        "NEWS SAVED:",
        len(items)
    )
    print(
        f"FILE: {OUTPUT_FILE}"
    )
    print("=" * 60)


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 60)
    print(
        "MOVINS MOVIE NEWS ENGINE"
    )
    print(
        "RSS + GEMINI ARABIC TRANSLATION"
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


    print()
    print(
        "TOTAL ARTICLES:",
        len(
            all_articles
        )
    )


    unique_articles = (

        remove_duplicates(
            all_articles
        )

    )


    print(
        "AFTER DUPLICATES:",
        len(
            unique_articles
        )
    )


    sorted_articles = (

        sort_articles(
            unique_articles
        )

    )


    final_articles = (

        sorted_articles[
            :MAX_ARTICLES
        ]

    )


    save_news(
        final_articles
    )


if __name__ == "__main__":

    main()
