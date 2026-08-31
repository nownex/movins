import os
import json
import html
import re
import time
import hashlib
from datetime import datetime, timezone

import requests
import feedparser
from bs4 import BeautifulSoup
from google import genai


# ============================================================
# MOVINS — MOVIE & SERIES NEWS ENGINE
# Arabic Sources + Gemini Translation
# ============================================================


OUTPUT_FILE = "movie-news.json"


# ============================================================
# GEMINI
# ============================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add it to GitHub Secrets."
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# NEWS SOURCES
# ============================================================

RSS_FEEDS = [

    # --------------------------------------------------------
    # ARABIC MOVIE / ENTERTAINMENT SOURCES
    # --------------------------------------------------------

    {
        "name": "الفن",
        "url": "https://www.google.com/alerts/feeds/00000000000000000000/00000000000000000000",
        "lang": "ar"
    },

    # --------------------------------------------------------
    # GOOGLE NEWS ARABIC — MOVIES
    # --------------------------------------------------------

    {
        "name": "أخبار الأفلام",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D8%A3%D9%81%D9%84%D8%A7%D9%85+%D8%B3%D9%8A%D9%86%D9%85%D8%A7"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "lang": "ar"
    },

    {
        "name": "شباك التذاكر",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D8%B4%D8%A8%D8%A7%D9%83+%D8%A7%D9%84%D8%AA%D8%B0%D8%A7%D9%83%D8%B1+%D8%A3%D9%81%D9%84%D8%A7%D9%85"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "lang": "ar"
    },

    {
        "name": "مسلسلات",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA+%D8%A7%D9%84%D8%AA%D9%84%D9%81%D8%B2%D9%8A%D9%88%D9%86"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "lang": "ar"
    },


    # --------------------------------------------------------
    # INTERNATIONAL SOURCES
    # Gemini will translate these
    # --------------------------------------------------------

    {
        "name": "Variety",
        "url": "https://variety.com/v/film/feed/",
        "lang": "en"
    },

    {
        "name": "Deadline",
        "url": "https://deadline.com/v/film/feed/",
        "lang": "en"
    },

    {
        "name": "The Hollywood Reporter",
        "url": "https://www.hollywoodreporter.com/c/movies/movie-news/feed/",
        "lang": "en"
    },

]


# ============================================================
# MOVIE / SERIES KEYWORDS
# ============================================================

KEYWORDS = [

    # Movies
    "movie",
    "film",
    "cinema",
    "box office",
    "trailer",
    "premiere",
    "release date",
    "theatrical",
    "hollywood",

    # Series
    "series",
    "tv series",
    "television",
    "episode",
    "season",
    "netflix",
    "hbo",
    "disney+",
    "amazon prime",

    # Arabic
    "فيلم",
    "أفلام",
    "سينما",
    "شباك التذاكر",
    "بوكس أوفيس",
    "مسلسل",
    "مسلسلات",
    "موسم",
    "حلقة",
    "نتفليكس",
    "نيتفليكس",
    "تريلر",
    "إعلان",
]


# ============================================================
# EXCLUDED KEYWORDS
# ============================================================

EXCLUDED_KEYWORDS = [

    "music",
    "album",
    "concert",
    "singer",

    "رياضة",
    "كرة القدم",
    "football",
    "soccer",

    "politics",
    "political",
    "election",

]


# ============================================================
# CLEAN TEXT
# ============================================================

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


# ============================================================
# CHECK RELEVANCE
# ============================================================

def is_relevant(title, description):

    text = (
        title + " " + description
    ).lower()

    keyword_found = any(
        keyword.lower() in text
        for keyword in KEYWORDS
    )

    excluded_found = any(
        keyword.lower() in text
        for keyword in EXCLUDED_KEYWORDS
    )

    return (
        keyword_found
        and not excluded_found
    )


# ============================================================
# GET IMAGE FROM RSS
# ============================================================

def get_rss_image(entry):

    # Media content

    media_content = getattr(
        entry,
        "media_content",
        []
    )

    if media_content:

        for media in media_content:

            url = media.get("url")

            if url:
                return url


    # Media thumbnail

    media_thumbnail = getattr(
        entry,
        "media_thumbnail",
        []
    )

    if media_thumbnail:

        for media in media_thumbnail:

            url = media.get("url")

            if url:
                return url


    # Enclosures

    enclosures = getattr(
        entry,
        "enclosures",
        []
    )

    if enclosures:

        for enclosure in enclosures:

            url = enclosure.get("href")

            if url:
                return url


    # Image inside HTML summary

    content = (
        getattr(
            entry,
            "summary",
            ""
        )
        or
        getattr(
            entry,
            "description",
            ""
        )
    )

    if content:

        soup = BeautifulSoup(
            content,
            "html.parser"
        )

        image = soup.find("img")

        if image:

            src = image.get("src")

            if src:
                return src


    return None


# ============================================================
# EXTRACT IMAGE FROM ARTICLE
# ============================================================

def extract_article_image(url):

    try:

        headers = {
            "User-Agent":
                "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # OpenGraph image

        og_image = soup.find(
            "meta",
            property="og:image"
        )

        if og_image:

            image = og_image.get(
                "content"
            )

            if image:
                return image


        # Twitter image

        twitter_image = soup.find(
            "meta",
            attrs={
                "name":
                "twitter:image"
            }
        )

        if twitter_image:

            image = twitter_image.get(
                "content"
            )

            if image:
                return image


        # First article image

        article = soup.find(
            "article"
        )

        if article:

            image = article.find(
                "img"
            )

            if image:

                src = image.get(
                    "src"
                )

                if src:
                    return src


    except Exception as error:

        print(
            "IMAGE ERROR:",
            error
        )


    return None


# ============================================================
# CHECK IMAGE
# ============================================================

def has_valid_image(url):

    if not url:
        return False

    if not url.startswith(
        "http"
    ):
        return False

    return True


# ============================================================
# GEMINI TRANSLATION
# ============================================================

def translate_with_gemini(
    title,
    description
):

    prompt = f"""
أنت محرر محترف لموقع عربي متخصص في الأفلام والمسلسلات اسمه MOVINS.

ترجم الخبر التالي إلى اللغة العربية ترجمة طبيعية واحترافية.

مهم جداً:

- اكتب العربية فقط.
- لا تترك أي جملة إنجليزية.
- لا تترجم أسماء الأفلام والمسلسلات ترجمة خاطئة.
- حافظ على أسماء الأشخاص.
- لا تضف معلومات غير موجودة.
- اجعل العنوان جذاباً وقصيراً.
- اجعل الملخص واضحاً ومفيداً.
- أصلح أي رموز HTML مثل &#8217;.
- أعد النتيجة بصيغة JSON فقط.

الشكل المطلوب:

{{
  "title": "العنوان بالعربية",
  "description": "ملخص الخبر بالعربية"
}}

العنوان الأصلي:

{title}

وصف الخبر:

{description}
"""

    try:

        response = (
            client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "temperature": 0.2
                }
            )
        )

        text = response.text.strip()

        # Remove markdown if Gemini returns it

        text = re.sub(
            r"^```json",
            "",
            text
        )

        text = re.sub(
            r"^```",
            "",
            text
        )

        text = text.replace(
            "```",
            ""
        ).strip()


        data = json.loads(
            text
        )


        translated_title = clean_text(
            data.get(
                "title",
                ""
            )
        )

        translated_description = clean_text(
            data.get(
                "description",
                ""
            )
        )


        if not translated_title:

            translated_title = title


        if not translated_description:

            translated_description = description


        return (
            translated_title,
            translated_description
        )


    except Exception as error:

        print(
            "GEMINI TRANSLATION ERROR:",
            error
        )

        return (
            title,
            description
        )


# ============================================================
# GENERATE UNIQUE ID
# ============================================================

def generate_id(url):

    return hashlib.md5(
        url.encode(
            "utf-8"
        )
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
# FETCH NEWS
# ============================================================

def fetch_news():

    old_ids = load_old_ids()

    items = []


    for source in RSS_FEEDS:

        print(
            "\nSOURCE:",
            source["name"]
        )


        try:

            feed = feedparser.parse(
                source["url"]
            )


            for entry in feed.entries[:15]:

                title = clean_text(
                    getattr(
                        entry,
                        "title",
                        ""
                    )
                )


                description = clean_text(

                    getattr(
                        entry,
                        "summary",
                        ""
                    )
                    or
                    getattr(
                        entry,
                        "description",
                        ""
                    )
                )


                link = getattr(
                    entry,
                    "link",
                    ""
                )


                if not title:

                    continue


                if not link:

                    continue


                # --------------------------------------------
                # MOVIE / SERIES FILTER
                # --------------------------------------------

                if not is_relevant(
                    title,
                    description
                ):

                    continue


                news_id = generate_id(
                    link
                )


                if news_id in old_ids:

                    print(
                        "SKIP DUPLICATE:",
                        title[:60]
                    )

                    continue


                # --------------------------------------------
                # IMAGE
                # --------------------------------------------

                image = get_rss_image(
                    entry
                )


                if not image:

                    image = extract_article_image(
                        link
                    )


                # Reject news without image

                if not has_valid_image(
                    image
                ):

                    print(
                        "SKIP NO IMAGE:",
                        title[:60]
                    )

                    continue


                # --------------------------------------------
                # TRANSLATE
                # --------------------------------------------

                if source["lang"] != "ar":

                    print(
                        "TRANSLATING:",
                        title[:60]
                    )


                    arabic_title, arabic_description = (
                        translate_with_gemini(
                            title,
                            description
                        )
                    )


                else:

                    arabic_title = title

                    arabic_description = description


                # --------------------------------------------
                # FINAL CHECK
                # --------------------------------------------

                arabic_title = clean_text(
                    arabic_title
                )

                arabic_description = clean_text(
                    arabic_description
                )


                # Reject if translation failed
                # and title is still mostly English

                if source["lang"] != "ar":

                    arabic_letters = len(
                        re.findall(
                            r"[\u0600-\u06FF]",
                            arabic_title
                        )
                    )


                    if arabic_letters < 3:

                        print(
                            "SKIP TRANSLATION FAILED:",
                            title[:60]
                        )

                        continue


                item = {

                    "id": news_id,

                    "title": arabic_title,

                    "description": arabic_description,

                    "image": image,

                    "url": link,

                    "source": source["name"],

                    "date": datetime.now(
                        timezone.utc
                    ).isoformat(),

                    "category":
                        "أفلام ومسلسلات"

                }


                items.append(
                    item
                )


                print(
                    "ADDED:",
                    arabic_title[:60]
                )


                time.sleep(
                    1
                )


        except Exception as error:

            print(
                "SOURCE ERROR:",
                source["name"],
                error
            )


    return items


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "================================="
    )

    print(
        "MOVINS MOVIE NEWS ENGINE"
    )

    print(
        "================================="
    )


    items = fetch_news()


    # Remove duplicates

    unique_items = []

    seen_urls = set()


    for item in items:

        url = item.get(
            "url"
        )


        if url in seen_urls:

            continue


        seen_urls.add(
            url
        )


        unique_items.append(
            item
        )


    # Maximum news

    unique_items = unique_items[:20]


    output = {

        "updated": datetime.now(
            timezone.utc
        ).isoformat(),

        "items": unique_items

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

    print(
        "================================="
    )

    print(
        "MOVIE NEWS:",
        len(unique_items)
    )

    print(
        "================================="
    )


if __name__ == "__main__":

    main()
