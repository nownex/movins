import os
import re
import json
import time
import html
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
import feedparser
from bs4 import BeautifulSoup


# ============================================================
# MOVINS — MOVIES & SERIES NEWS ENGINE
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add it to GitHub Secrets."
    )


# ============================================================
# SETTINGS
# ============================================================

OUTPUT_FILE = "movie-news.json"

MAX_NEWS = 12

REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


# ============================================================
# RSS SOURCES
# ============================================================

RSS_FEEDS = [

    # --------------------------------------------------------
    # ARABIC MOVIE NEWS
    # --------------------------------------------------------

    {
        "name": "Google News Arabic - Movies",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D8%A3%D9%81%D9%84%D8%A7%D9%85+OR+%D8%B3%D9%8A%D9%86%D9%85%D8%A7+"
            "OR+%D8%B4%D8%A8%D8%A7%D9%83+%D8%A7%D9%84%D8%AA%D8%B0%D8%A7%D9%83%D8%B1+"
            "OR+%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA+"
            "OR+%D9%86%D8%AA%D9%81%D9%84%D9%8A%D9%83%D8%B3"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "Google News Arabic - Cinema",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D8%A3%D9%81%D9%84%D8%A7%D9%85+%D9%82%D8%A7%D8%AF%D9%85%D8%A9+"
            "OR+%D8%A3%D9%81%D9%84%D8%A7%D9%85+%D9%85%D9%86%D8%AA%D8%B8%D8%B1%D8%A9+"
            "OR+%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1+%D9%81%D9%8A%D9%84%D9%85"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "أفلام"
    },


    # --------------------------------------------------------
    # INTERNATIONAL MOVIE NEWS
    # --------------------------------------------------------

    {
        "name": "Variety",
        "url": "https://variety.com/feed/",
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "Deadline",
        "url": "https://deadline.com/feed/",
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "Collider",
        "url": "https://collider.com/feed/",
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "Google News Movies",
        "url": (
            "https://news.google.com/rss/search?"
            "q=upcoming+movies+OR+box+office+OR+movie+release+"
            "OR+Netflix+series+OR+TV+series+OR+film+trailer"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "category": "أفلام ومسلسلات"
    }
]


# ============================================================
# KEYWORDS
# ============================================================

MOVIE_KEYWORDS = [

    # ENGLISH
    "movie",
    "film",
    "cinema",
    "box office",
    "trailer",
    "premiere",
    "release",
    "netflix",
    "disney",
    "marvel",
    "warner",
    "hollywood",
    "actor",
    "actress",
    "director",
    "tv series",
    "television series",
    "season",
    "episode",
    "streaming",

    # ARABIC
    "فيلم",
    "أفلام",
    "سينما",
    "شباك التذاكر",
    "مسلسل",
    "مسلسلات",
    "موسم",
    "حلقة",
    "نتفليكس",
    "ديزني",
    "مارفل",
    "هوليوود",
    "ممثل",
    "ممثلة",
    "مخرج"
]


# كلمات تشير إلى أخبار غير مناسبة
BAD_KEYWORDS = [

    "politics",
    "election",
    "president",
    "war",
    "football",
    "soccer",
    "basketball",
    "stock market",

    "سياسة",
    "انتخابات",
    "حرب",
    "كرة القدم"
]


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(str(text))

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

    text = re.sub(
        r"&8217;",
        "'",
        text
    )

    text = re.sub(
        r"&8220;",
        '"',
        text
    )

    text = re.sub(
        r"&8221;",
        '"',
        text
    )

    return text.strip()


# ============================================================
# MOVIE RELEVANCE
# ============================================================

def is_movie_news(title, description):

    text = (
        f"{title} {description}"
    ).lower()

    good = any(
        word.lower() in text
        for word in MOVIE_KEYWORDS
    )

    bad = any(
        word.lower() in text
        for word in BAD_KEYWORDS
    )

    return good and not bad


# ============================================================
# IMAGE FROM RSS
# ============================================================

def get_rss_image(entry):

    # media_content
    try:

        media = entry.get(
            "media_content",
            []
        )

        if media:

            for item in media:

                url = item.get(
                    "url"
                )

                if url and url.startswith("http"):

                    return url

    except Exception:
        pass


    # media_thumbnail
    try:

        media = entry.get(
            "media_thumbnail",
            []
        )

        if media:

            for item in media:

                url = item.get(
                    "url"
                )

                if url and url.startswith("http"):

                    return url

    except Exception:
        pass


    # enclosures
    try:

        enclosures = entry.get(
            "enclosures",
            []
        )

        for item in enclosures:

            url = item.get(
                "href"
            )

            if url and url.startswith("http"):

                return url

    except Exception:
        pass


    return ""


# ============================================================
# IMAGE FROM ARTICLE PAGE
# ============================================================

def get_article_image(url):

    if not url:
        return ""

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # Open Graph image
        for prop in [
            "og:image",
            "twitter:image",
            "twitter:image:src"
        ]:

            tag = soup.find(
                "meta",
                attrs={
                    "property": prop
                }
            )

            if not tag:

                tag = soup.find(
                    "meta",
                    attrs={
                        "name": prop
                    }
                )

            if tag:

                image = tag.get(
                    "content",
                    ""
                )

                if image and image.startswith("http"):

                    return image


        # Try large image
        images = soup.find_all(
            "img"
        )

        for image_tag in images:

            image = (
                image_tag.get("src")
                or image_tag.get("data-src")
                or image_tag.get("data-lazy-src")
            )

            if not image:
                continue

            if not image.startswith("http"):
                continue

            width = image_tag.get(
                "width",
                ""
            )

            try:

                if width and int(width) < 300:
                    continue

            except Exception:
                pass

            return image


    except Exception as error:

        print(
            "IMAGE ERROR:",
            error
        )

    return ""


# ============================================================
# VALIDATE IMAGE
# ============================================================

def is_valid_image(url):

    if not url:
        return False

    if not url.startswith("http"):
        return False

    bad_words = [
        "logo",
        "icon",
        "avatar",
        "placeholder",
        "default"
    ]

    lower = url.lower()

    if any(
        word in lower
        for word in bad_words
    ):
        return False

    return True


# ============================================================
# DATE
# ============================================================

def get_date(entry):

    published = (
        entry.get("published")
        or entry.get("updated")
        or ""
    )

    if published:

        try:

            date = parsedate_to_datetime(
                published
            )

            return date.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        except Exception:
            pass

    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ============================================================
# GEMINI REQUEST
# ============================================================

def call_gemini(prompt):

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.5-flash:generateContent"
    )

    params = {
        "key": GEMINI_API_KEY
    }

    payload = {

        "contents": [

            {
                "parts": [

                    {
                        "text": prompt
                    }

                ]
            }

        ],

        "generationConfig": {

            "temperature": 0.4,

            "maxOutputTokens": 900
        }
    }


    response = requests.post(
        url,
        params=params,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()


    try:

        return data[
            "candidates"
        ][0][
            "content"
        ][
            "parts"
        ][0][
            "text"
        ].strip()

    except Exception:

        print(
            "GEMINI RESPONSE:",
            data
        )

        return ""


# ============================================================
# TRANSLATE + LONG SUMMARY
# ============================================================

def translate_and_summarize(
    title,
    description
):

    prompt = f"""
أنت محرر عربي محترف لموقع أخبار الأفلام والمسلسلات اسمه MOVINS.

المطلوب:

1. ترجمة العنوان بالكامل إلى العربية ترجمة طبيعية واحترافية.
2. كتابة ملخص عربي طويل وواضح للخبر.

قواعد مهمة جداً:

- لا تترك كلمات أو جمل إنجليزية إلا أسماء الأفلام أو المسلسلات أو الأشخاص عند الضرورة.
- الملخص يجب أن يكون بين 100 و180 كلمة تقريباً.
- اكتب من 5 إلى 8 جمل مفيدة.
- اجعل الملخص يبدو كمقالة قصيرة وليس كسطر واحد.
- اشرح ما الذي حدث ولماذا هو مهم وما الذي يمكن أن يعنيه للجمهور.
- لا تخترع معلومات غير موجودة.
- الخبر يجب أن يكون متعلقاً بالأفلام أو المسلسلات أو السينما أو البوكس أوفيس أو الإصدارات أو المنصات.

أعد النتيجة بهذا الشكل فقط:

TITLE: العنوان العربي

SUMMARY: الملخص العربي الطويل

العنوان الأصلي:
{title}

وصف الخبر:
{description}
"""

    try:

        result = call_gemini(
            prompt
        )

        if not result:
            return "", ""

        translated_title = ""
        summary = ""

        title_match = re.search(
            r"TITLE:\s*(.+?)(?=\n\s*SUMMARY:|$)",
            result,
            re.S
        )

        summary_match = re.search(
            r"SUMMARY:\s*(.+)",
            result,
            re.S
        )


        if title_match:

            translated_title = clean_text(
                title_match.group(1)
            )


        if summary_match:

            summary = clean_text(
                summary_match.group(1)
            )


        # إذا لم يلتزم Gemini بالتنسيق
        if not translated_title:

            lines = result.split(
                "\n"
            )

            if lines:

                translated_title = clean_text(
                    lines[0]
                )


        if not summary:

            summary = clean_text(
                result
            )


        return (
            translated_title,
            summary
        )


    except Exception as error:

        print(
            "GEMINI ERROR:",
            error
        )

        return "", ""


# ============================================================
# CREATE UNIQUE ID
# ============================================================

def make_id(title, link):

    text = (
        title + link
    ).encode(
        "utf-8"
    )

    return hashlib.md5(
        text
    ).hexdigest()


# ============================================================
# LOAD OLD NEWS
# ============================================================

def load_old_ids():

    if not os.path.exists(
        OUTPUT_FILE
    ):
        return set()

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

        return {

            item.get("id")

            for item in items

            if item.get("id")

        }

    except Exception:

        return set()


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "MOVINS MOVIE NEWS ENGINE STARTED"
    )


    old_ids = load_old_ids()

    articles = []

    seen_titles = set()


    for source in RSS_FEEDS:

        print(
            "\nFETCHING:",
            source["name"]
        )

        try:

            feed = feedparser.parse(
                source["url"]
            )

            entries = feed.entries

            print(
                "ENTRIES:",
                len(entries)
            )


            for entry in entries:

                if len(articles) >= MAX_NEWS:
                    break


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
                    or
                    entry.get(
                        "description",
                        ""
                    )
                )

                link = entry.get(
                    "link",
                    ""
                )


                if not original_title:
                    continue


                # Movie filter
                if not is_movie_news(
                    original_title,
                    original_description
                ):

                    continue


                # Duplicate title
                normalized_title = (
                    original_title.lower()
                    .strip()
                )

                if normalized_title in seen_titles:
                    continue


                article_id = make_id(
                    original_title,
                    link
                )


                if article_id in old_ids:

                    continue


                # ------------------------------------------------
                # IMAGE
                # ------------------------------------------------

                image = get_rss_image(
                    entry
                )


                if not is_valid_image(
                    image
                ):

                    print(
                        "SEARCHING ARTICLE IMAGE..."
                    )

                    image = get_article_image(
                        link
                    )


                # IMPORTANT:
                # EXCLUDE NEWS WITHOUT IMAGE
                if not is_valid_image(
                    image
                ):

                    print(
                        "SKIPPED — NO IMAGE:",
                        original_title
                    )

                    continue


                # ------------------------------------------------
                # SOURCE
                # ------------------------------------------------

                source_name = (
                    entry.get(
                        "source",
                        {}
                    ).get(
                        "title",
                        source["name"]
                    )
                    if isinstance(
                        entry.get(
                            "source",
                            {}
                        ),
                        dict
                    )
                    else source["name"]
                )


                # ------------------------------------------------
                # TRANSLATION + LONG SUMMARY
                # ------------------------------------------------

                print(
                    "TRANSLATING:",
                    original_title
                )


                arabic_title, arabic_summary = (
                    translate_and_summarize(
                        original_title,
                        original_description
                    )
                )


                # Skip if Gemini failed
                if not arabic_title:

                    print(
                        "SKIPPED — TRANSLATION FAILED"
                    )

                    continue


                if len(arabic_summary) < 120:

                    print(
                        "SKIPPED — SUMMARY TOO SHORT"
                    )

                    continue


                item = {

                    "id": article_id,

                    "title": arabic_title,

                    "summary": arabic_summary,

                    "image": image,

                    "link": link,

                    "source": source_name,

                    "category": source[
                        "category"
                    ],

                    "date": get_date(
                        entry
                    ),

                    "originalTitle": original_title
                }


                articles.append(
                    item
                )

                seen_titles.add(
                    normalized_title
                )


                print(
                    "ADDED:",
                    arabic_title
                )


                # Gemini rate protection
                time.sleep(2)


        except Exception as error:

            print(
                "SOURCE ERROR:",
                source["name"],
                error
            )


    # ========================================================
    # SAVE
    # ========================================================

    data = {

        "updated": datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),

        "items": articles
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


    print(
        "\n================================="
    )

    print(
        "MOVIE NEWS:",
        len(articles)
    )

    print(
        "================================="
    )


    if not articles:

        raise RuntimeError(
            "No movie or series news generated"
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
