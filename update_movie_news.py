import os
import re
import json
import time
import html
import hashlib
from datetime import datetime, timezone

import requests
import feedparser
from bs4 import BeautifulSoup
import google.generativeai as genai


# =========================================================
# MOVINS — MOVIE NEWS ENGINE
# STRICT MOVIE FILTER + GEMINI ARABIC TRANSLATION
# =========================================================


print("=" * 60)
print("MOVINS MOVIE NEWS ENGINE")
print("=" * 60)


# =========================================================
# SETTINGS
# =========================================================


MAX_ARTICLES = 30

OUTPUT_FILE = "movie-news.json"

REQUEST_TIMEOUT = 15

GEMINI_MODEL = "gemini-2.5-flash"


# =========================================================
# GEMINI API KEY
# =========================================================


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


if not GEMINI_API_KEY:

    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Add it to GitHub Secrets."
    )


genai.configure(
    api_key=GEMINI_API_KEY
)


model = genai.GenerativeModel(
    GEMINI_MODEL
)


# =========================================================
# HEADERS
# =========================================================


HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/124.0 Safari/537.36"
    )

}


# =========================================================
# RSS SOURCES
# =========================================================


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
# MOVIE KEYWORDS
# =========================================================


MOVIE_KEYWORDS = [

    "movie",
    "film",
    "cinema",
    "box office",
    "theater",
    "theatre",
    "ticket sales",

    "trailer",
    "teaser",

    "release date",
    "release",

    "upcoming film",
    "upcoming movie",

    "world premiere",
    "premiere",

    "feature film",

    "filmmaker",
    "director",

    "movie star",

    "academy awards",
    "oscars",

    "cannes",
    "venice film festival",
    "sundance",
    "toronto film festival",

    "tiff",

    "animated film",

    "sequel",

    "reboot",

    "franchise",

    "casting",

    "screenplay"

]


# =========================================================
# WORDS TO EXCLUDE
# =========================================================


EXCLUDE_KEYWORDS = [

    "tv series",
    "television series",
    "television show",

    "season finale",

    "episode",

    "streaming series",

    "miniseries",

    "podcast",

    "album",

    "singer",

    "song",

    "concert",

    "tour dates",

    "music festival",

    "siriusxm",

    "grammy",

    "grammys",

    "broadway"

]


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
# NORMALIZE URL
# =========================================================


def normalize_url(url):

    if not url:
        return ""

    url = url.strip()

    url = url.split("?")[0]

    return url.rstrip("/")


# =========================================================
# CREATE ARTICLE ID
# =========================================================


def create_article_id(url):

    value = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()

    return value[:24]


# =========================================================
# CHECK MOVIE RELEVANCE
# =========================================================


def is_movie_related(title, description):

    text = (
        title
        + " "
        + description
    ).lower()


    # Exclude obvious non-movie content

    for word in EXCLUDE_KEYWORDS:

        if word in text:

            return False


    # Must contain movie-related keyword

    for word in MOVIE_KEYWORDS:

        if word in text:

            return True


    return False


# =========================================================
# GET IMAGE FROM RSS
# =========================================================


def get_rss_image(entry):


    # media:content

    media_content = getattr(
        entry,
        "media_content",
        []
    )

    if media_content:

        for item in media_content:

            url = item.get(
                "url"
            )

            if url:

                return url


    # media:thumbnail

    media_thumbnail = getattr(
        entry,
        "media_thumbnail",
        []
    )

    if media_thumbnail:

        for item in media_thumbnail:

            url = item.get(
                "url"
            )

            if url:

                return url


    # enclosure

    enclosures = getattr(
        entry,
        "enclosures",
        []
    )

    if enclosures:

        for item in enclosures:

            url = item.get(
                "href"
            )

            if url:

                return url


    # image

    image = getattr(
        entry,
        "image",
        None
    )

    if image:

        url = image.get(
            "href"
        )

        if url:

            return url


    return ""


# =========================================================
# GET IMAGE FROM ARTICLE PAGE
# =========================================================


def get_article_image(url):

    try:

        response = requests.get(

            url,

            headers=HEADERS,

            timeout=REQUEST_TIMEOUT

        )


        if response.status_code != 200:

            return ""


        soup = BeautifulSoup(

            response.text,

            "html.parser"

        )


        # Open Graph image

        meta = soup.find(

            "meta",

            property="og:image"

        )


        if meta:

            image = meta.get(
                "content"
            )

            if image:

                return image.strip()


        # Twitter image

        meta = soup.find(

            "meta",

            attrs={

                "name": "twitter:image"

            }

        )


        if meta:

            image = meta.get(
                "content"
            )

            if image:

                return image.strip()


    except Exception as error:

        print(
            "IMAGE ERROR:",
            str(error)
        )


    return ""


# =========================================================
# EXTRACT IMAGE
# =========================================================


def extract_image(entry, article_url):

    image = get_rss_image(
        entry
    )


    if image:

        return image


    print(
        "Checking article image..."
    )


    image = get_article_image(
        article_url
    )


    return image


# =========================================================
# GEMINI PROCESSING
# =========================================================


def process_with_gemini(
    title,
    description,
    source
):


    prompt = f"""
أنت محرر محترف لموقع عربي متخصص حصرياً في أخبار السينما والأفلام.

المصدر: {source}

العنوان الأصلي:
{title}

وصف الخبر الأصلي:
{description}

المهمة:

1. تحقق أولاً هل الخبر متعلق فعلاً بالأفلام السينمائية.
2. يجب رفض أخبار الموسيقى والأغاني والحفلات والبودكاست.
3. يجب رفض أخبار المسلسلات والتلفزيون والبرامج إذا لم تكن مرتبطة بشكل واضح بفيلم سينمائي.
4. يجب التركيز على:
   - الأفلام الجديدة
   - الأفلام المنتظرة
   - مواعيد الإصدار
   - الإعلانات والتريلرات
   - شباك التذاكر Box Office
   - العروض الأولى
   - المهرجانات السينمائية
   - أخبار مهمة عن ممثلين أو مخرجين مرتبطة بالأفلام

إذا كان الخبر غير متعلق بالأفلام السينمائية أعد فقط:

{{
  "valid": false
}}

أما إذا كان متعلقاً بالأفلام أعد JSON فقط بهذا الشكل:

{{
  "valid": true,
  "title_ar": "عنوان عربي احترافي وواضح",
  "summary_ar": "ملخص عربي مسترسل من 3 إلى 5 جمل يشرح الخبر بشكل واضح ومفيد."
}}

قواعد مهمة جداً:

- ترجم إلى العربية ولا تترك العنوان باللغة الإنجليزية.
- لا تكتب أي HTML.
- لا تكتب Markdown.
- لا تضف معلومات غير موجودة في النص.
- اجعل العنوان جذاباً وطبيعياً لموقع أخبار سينمائية.
- اجعل الملخص مفهوماً للقارئ العربي.
- أعد JSON فقط بدون أي كلام إضافي.
"""


    try:

        response = model.generate_content(
            prompt
        )


        text = response.text.strip()


        # Remove markdown JSON markers if Gemini adds them

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )

        text = text.strip()


        data = json.loads(
            text
        )


        if not data.get(
            "valid",
            False
        ):

            return None


        title_ar = clean_text(

            data.get(
                "title_ar",
                ""
            )

        )


        summary_ar = clean_text(

            data.get(
                "summary_ar",
                ""
            )

        )


        # Do not save untranslated articles

        if not title_ar:

            return None


        if not summary_ar:

            return None


        # Basic Arabic character check

        arabic_characters = len(

            re.findall(

                r"[\u0600-\u06FF]",


                title_ar + summary_ar

            )

        )


        if arabic_characters < 15:

            print(
                "Gemini did not return Arabic."
            )

            return None


        return {

            "title": title_ar,

            "summary": summary_ar

        }


    except Exception as error:

        print(
            "GEMINI ERROR:",
            str(error)
        )

        # IMPORTANT:
        # Do NOT save English fallback

        return None


# =========================================================
# LOAD OLD NEWS
# =========================================================


def load_old_news():

    if not os.path.exists(
        OUTPUT_FILE
    ):

        return []


    try:

        with open(

            OUTPUT_FILE,

            "r",

            encoding="utf-8"

        ) as file:

            data = json.load(
                file
            )


        return data.get(
            "items",
            []
        )


    except Exception:

        return []


# =========================================================
# MAIN
# =========================================================


all_articles = []

seen_urls = set()

old_news = load_old_news()


# =========================================================
# COLLECT RSS NEWS
# =========================================================


for source in SOURCES:


    print()

    print("=" * 60)

    print(
        "SOURCE:",
        source["name"]
    )

    print(
        source["url"]
    )

    print("=" * 60)


    try:

        response = requests.get(

            source["url"],

            headers=HEADERS,

            timeout=REQUEST_TIMEOUT

        )


        print(
            "STATUS:",
            response.status_code
        )


        if response.status_code != 200:

            continue


        feed = feedparser.parse(

            response.content
        )


        entries = feed.entries


        print(
            "ARTICLES FOUND:",
            len(entries)
        )


        for entry in entries:


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

            )


            article_url = normalize_url(

                getattr(
                    entry,
                    "link",
                    ""
                )

            )


            if not title:

                continue


            if not article_url:

                continue


            if article_url in seen_urls:

                continue


            seen_urls.add(
                article_url
            )


            # =============================================
            # STRICT MOVIE FILTER
            # =============================================


            if not is_movie_related(

                title,

                description

            ):

                print(
                    "SKIPPED NON-MOVIE:",
                    title[:70]
                )

                continue


            # =============================================
            # IMAGE
            # =============================================


            image = extract_image(

                entry,

                article_url

            )


            # EXCLUDE NEWS WITHOUT IMAGE

            if not image:

                print(
                    "SKIPPED NO IMAGE:",
                    title[:70]
                )

                continue


            # =============================================
            # SAVE CANDIDATE
            # =============================================


            all_articles.append({

                "original_title": title,

                "original_description": description,

                "url": article_url,

                "image": image,

                "source": source["name"]

            })


    except Exception as error:

        print(
            "SOURCE ERROR:",
            str(error)
        )


# =========================================================
# LIMIT BEFORE GEMINI
# =========================================================


print()

print(
    "MOVIE CANDIDATES:",
    len(all_articles)
)


all_articles = all_articles[:40]


# =========================================================
# PROCESS WITH GEMINI
# =========================================================


final_articles = []


for index, article in enumerate(

    all_articles,

    start=1

):


    print()

    print(
        f"[{index}/{len(all_articles)}]"
    )

    print(
        "PROCESSING:",
        article["original_title"]
    )


    processed = process_with_gemini(

        article["original_title"],

        article["original_description"],

        article["source"]

    )


    if not processed:

        print(
            "SKIPPED BY GEMINI"
        )

        continue


    article_id = create_article_id(

        article["url"]
    )


    final_articles.append({

        "id": article_id,

        "title": processed["title"],

        "summary": processed["summary"],

        "image": article["image"],

        "source": article["source"],

        "url": article["url"],

        "date": datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),

        "category": "movie"

    })


    print(
        "ARABIC TITLE:",
        processed["title"]
    )


    # Small pause

    time.sleep(
        1
    )


    if len(final_articles) >= MAX_ARTICLES:

        break


# =========================================================
# REMOVE DUPLICATES
# =========================================================


unique_articles = []

used_urls = set()


for article in final_articles:


    url = article["url"]


    if url in used_urls:

        continue


    used_urls.add(
        url
    )


    unique_articles.append(
        article
    )


# =========================================================
# OUTPUT
# =========================================================


output = {

    "updated_at": datetime.now(

        timezone.utc

    ).strftime(

        "%Y-%m-%dT%H:%M:%SZ"

    ),

    "items": unique_articles

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


# =========================================================
# SUCCESS
# =========================================================


print()

print("=" * 60)

print("SUCCESS")

print(
    "MOVIE NEWS SAVED:",
    len(unique_articles)
)

print(
    "FILE:",
    OUTPUT_FILE
)

print("=" * 60)
