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
# MOVINS — MOVIES & SERIES NEWS ENGINE
# =========================================================

print("=" * 60)
print("MOVINS MOVIES & SERIES NEWS ENGINE")
print("=" * 60)


# =========================================================
# SETTINGS
# =========================================================

OUTPUT_FILE = "movie-news.json"

MAX_ARTICLES = 30

MAX_CANDIDATES = 50

REQUEST_TIMEOUT = 20

GEMINI_MODEL = "gemini-2.5-flash"


# =========================================================
# GEMINI API KEY
# =========================================================

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY"
)

if not GEMINI_API_KEY:

    raise RuntimeError(
        "GEMINI_API_KEY is missing."
    )


genai.configure(
    api_key=GEMINI_API_KEY
)


model = genai.GenerativeModel(
    GEMINI_MODEL
)


# =========================================================
# HTTP HEADERS
# =========================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

}


# =========================================================
# NEWS SOURCES
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
# EXCLUDE KEYWORDS
# Only clearly unwanted content
# =========================================================

EXCLUDE_KEYWORDS = [

    "podcast",

    "album",

    "new song",

    "new single",

    "music video",

    "concert",

    "concert tour",

    "tour dates",

    "music festival",

    "grammy",

    "grammys",

    "singer announces",

    "spotify"

]


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(
        str(text)
    )

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

    url = str(url).strip()

    url = url.split("?")[0]

    return url.rstrip("/")


# =========================================================
# CREATE ID
# =========================================================

def create_article_id(url):

    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:24]


# =========================================================
# BASIC EXCLUSION
# =========================================================

def should_exclude(title, description):

    text = (
        title
        + " "
        + description
    ).lower()

    for keyword in EXCLUDE_KEYWORDS:

        if keyword in text:

            return True

    return False


# =========================================================
# GET IMAGE FROM RSS
# =========================================================

def get_rss_image(entry):

    # MEDIA CONTENT

    media_content = getattr(
        entry,
        "media_content",
        []
    )

    for item in media_content:

        if isinstance(item, dict):

            url = item.get("url", "")

            if url:
                return url


    # MEDIA THUMBNAIL

    media_thumbnail = getattr(
        entry,
        "media_thumbnail",
        []
    )

    for item in media_thumbnail:

        if isinstance(item, dict):

            url = item.get("url", "")

            if url:
                return url


    # ENCLOSURES

    enclosures = getattr(
        entry,
        "enclosures",
        []
    )

    for item in enclosures:

        if isinstance(item, dict):

            url = item.get("href", "")

            if url:
                return url


    # IMAGE

    image = getattr(
        entry,
        "image",
        None
    )

    if image:

        try:

            url = image.get(
                "href",
                ""
            )

            if url:
                return url

        except Exception:

            pass


    return ""


# =========================================================
# GET IMAGE FROM ARTICLE PAGE
# =========================================================

def get_article_image(article_url):

    try:

        response = requests.get(

            article_url,

            headers=HEADERS,

            timeout=REQUEST_TIMEOUT

        )

        if response.status_code != 200:

            return ""


        soup = BeautifulSoup(

            response.text,

            "html.parser"

        )


        # OG IMAGE

        meta = soup.find(

            "meta",

            attrs={

                "property": "og:image"

            }

        )

        if meta:

            image = meta.get(
                "content",
                ""
            )

            if image:

                return image.strip()


        # TWITTER IMAGE

        meta = soup.find(

            "meta",

            attrs={

                "name": "twitter:image"

            }

        )

        if meta:

            image = meta.get(
                "content",
                ""
            )

            if image:

                return image.strip()


        # SECOND TWITTER FORMAT

        meta = soup.find(

            "meta",

            attrs={

                "property": "twitter:image"

            }

        )

        if meta:

            image = meta.get(
                "content",
                ""
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


    return get_article_image(
        article_url
    )


# =========================================================
# CHECK ARABIC
# =========================================================

def contains_arabic(text):

    characters = re.findall(

        r"[\u0600-\u06FF]",

        text or ""

    )

    return len(characters) >= 10


# =========================================================
# EXTRACT JSON
# =========================================================

def extract_json(text):

    if not text:
        return None


    text = text.strip()


    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```JSON",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.strip()


    # Direct JSON

    try:

        return json.loads(
            text
        )

    except Exception:

        pass


    # Find JSON object

    match = re.search(

        r"\{.*\}",

        text,

        re.DOTALL

    )


    if match:

        try:

            return json.loads(
                match.group(0)
            )

        except Exception:

            pass


    return None


# =========================================================
# GEMINI TRANSLATION & CLASSIFICATION
# =========================================================

def process_with_gemini(
    title,
    description,
    source
):

    prompt = f"""
أنت محرر عربي محترف لموقع MOVINS.

الموقع متخصص في:

- أخبار الأفلام السينمائية
- الأفلام المنتظرة
- مواعيد إصدار الأفلام
- الإعلانات والتريلرات
- شباك التذاكر Box Office
- العروض الأولى
- المهرجانات السينمائية
- أخبار المسلسلات المهمة
- مواسم المسلسلات
- الإعلانات والتريلرات الخاصة بالمسلسلات
- أخبار الممثلين والمخرجين المرتبطة بالأفلام أو المسلسلات

المصدر:
{source}

العنوان الأصلي:
{title}

وصف الخبر:
{description}

المطلوب:

أولاً: قرر هل الخبر مناسب لموقع متخصص في الأفلام والمسلسلات.

ارفض الأخبار المتعلقة فقط بـ:
- الموسيقى
- الأغاني
- الألبومات
- الحفلات
- الجولات الغنائية
- البودكاست

إذا كان الخبر غير مناسب أعد JSON فقط:

{{
  "valid": false
}}

إذا كان الخبر مناسباً أعد JSON فقط بهذا الشكل:

{{
  "valid": true,
  "category": "فيلم",
  "title_ar": "عنوان عربي احترافي",
  "summary_ar": "ملخص عربي مسترسل وواضح من 3 إلى 5 جمل."
}}

بالنسبة للمسلسلات اجعل category:

"مسلسلات"

قواعد مهمة:

- ترجم العنوان إلى العربية ترجمة طبيعية.
- لا تترك العنوان باللغة الإنجليزية.
- اكتب ملخصاً عربياً واضحاً.
- لا تستخدم HTML.
- لا تستخدم Markdown.
- لا تضف معلومات غير موجودة في الخبر.
- لا تكتب أي نص خارج JSON.
"""

    for attempt in range(2):

        try:

            response = model.generate_content(
                prompt
            )


            text = getattr(
                response,
                "text",
                ""
            )


            data = extract_json(
                text
            )


            if not data:

                print(
                    "Invalid Gemini JSON."
                )

                continue


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


            category = clean_text(

                data.get(
                    "category",
                    "أخبار السينما"
                )

            )


            # IMPORTANT:
            # Never save untranslated English

            if not contains_arabic(
                title_ar
            ):

                print(
                    "Gemini title is not Arabic."
                )

                continue


            if not contains_arabic(
                summary_ar
            ):

                print(
                    "Gemini summary is not Arabic."
                )

                continue


            if len(title_ar) < 5:

                continue


            if len(summary_ar) < 30:

                continue


            if category not in [

                "فيلم",

                "مسلسلات"

            ]:

                category = "أخبار السينما"


            return {

                "title": title_ar,

                "summary": summary_ar,

                "category": category

            }


        except Exception as error:

            print(

                f"GEMINI ERROR "
                f"(attempt {attempt + 1}):",

                str(error)

            )


            time.sleep(2)


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

            data = json.load(file)


        return data.get(
            "items",
            []
        )


    except Exception:

        return []


# =========================================================
# COLLECT NEWS
# =========================================================

candidates = []

seen_urls = set()


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


        print(

            "ARTICLES FOUND:",

            len(feed.entries)

        )


        for entry in feed.entries:


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
            # EXCLUDE CLEARLY UNWANTED CONTENT
            # =============================================

            if should_exclude(

                title,

                description

            ):

                print(
                    "EXCLUDED:",
                    title[:80]
                )

                continue


            # =============================================
            # IMAGE
            # =============================================

            image = extract_image(

                entry,

                article_url

            )


            # NO IMAGE = NO ARTICLE

            if not image:

                print(
                    "NO IMAGE:",
                    title[:80]
                )

                continue


            candidates.append({

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


print()
print("=" * 60)

print(
    "TOTAL CANDIDATES:",
    len(candidates)
)

print("=" * 60)


# =========================================================
# LIMIT CANDIDATES
# =========================================================

candidates = candidates[
    :MAX_CANDIDATES
]


# =========================================================
# GEMINI PROCESSING
# =========================================================

final_articles = []

processed_urls = set()


for index, article in enumerate(

    candidates,

    start=1

):

    print()
    print("=" * 60)

    print(

        f"PROCESSING {index}/"
        f"{len(candidates)}"

    )

    print(

        article[
            "original_title"
        ]

    )

    print("=" * 60)


    processed = process_with_gemini(

        article[
            "original_title"
        ],

        article[
            "original_description"
        ],

        article[
            "source"
        ]

    )


    if not processed:

        print(
            "SKIPPED BY GEMINI"
        )

        continue


    article_url = article["url"]


    if article_url in processed_urls:

        continue


    processed_urls.add(
        article_url
    )


    final_articles.append({

        "id": create_article_id(
            article_url
        ),

        "title": processed[
            "title"
        ],

        "summary": processed[
            "summary"
        ],

        "image": article[
            "image"
        ],

        "source": article[
            "source"
        ],

        "url": article_url,

        "category": processed[
            "category"
        ],

        "date": datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    })


    print()

    print(
        "ARABIC:",
        processed["title"]
    )


    time.sleep(1)


    if len(final_articles) >= MAX_ARTICLES:

        break


# =========================================================
# IF NO NEWS GENERATED
# KEEP OLD NEWS INSTEAD OF EMPTY FILE
# =========================================================

old_news = load_old_news()


if not final_articles:

    print()
    print("=" * 60)

    print(
        "WARNING: No new suitable news generated."
    )

    print(
        "Keeping previous news."
    )

    print("=" * 60)


    final_articles = old_news


# =========================================================
# SAVE JSON
# =========================================================

output = {

    "updated_at": datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    ),

    "items": final_articles

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
# FINAL RESULT
# =========================================================

print()
print("=" * 60)

print(
    "SUCCESS"
)

print(
    "NEWS SAVED:",
    len(final_articles)
)

print(
    "FILE:",
    OUTPUT_FILE
)

print("=" * 60)
