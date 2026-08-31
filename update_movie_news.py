import os
import re
import json
import time
import html
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

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


OUTPUT_FILE = "movie-news.json"

MAX_NEWS = 12

REQUEST_TIMEOUT = 25

MIN_ARTICLE_TEXT = 120

session = requests.Session()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
}


# ============================================================
# RSS SOURCES
# ============================================================

RSS_FEEDS = [

    {
        "name": "Google News Arabic Movies",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D8%A3%D9%81%D9%84%D8%A7%D9%85+OR+"
            "%D8%B3%D9%8A%D9%86%D9%85%D8%A7+OR+"
            "%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA+OR+"
            "%D9%86%D8%AA%D9%81%D9%84%D9%8A%D9%83%D8%B3"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "Google News Arabic Cinema",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1+%D9%81%D9%8A%D9%84%D9%85+"
            "OR+%D8%B4%D8%A8%D8%A7%D9%83+%D8%A7%D9%84%D8%AA%D8%B0%D8%A7%D9%83%D8%B1+"
            "OR+%D9%85%D8%B3%D9%84%D8%B3%D9%84"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "أفلام ومسلسلات"
    },

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
            "q=movie+OR+film+OR+Netflix+series+OR+"
            "TV+series+OR+film+trailer+OR+box+office"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "category": "أفلام ومسلسلات"
    }
]


# ============================================================
# KEYWORDS
# ============================================================

MOVIE_KEYWORDS = [

    "movie",
    "movies",
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
    "television",
    "season",
    "episode",
    "streaming",

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
    "مخرج",
    "عرض"
]


BAD_KEYWORDS = [

    "football",
    "soccer",
    "basketball",
    "election",
    "president",
    "stock market",

    "كرة القدم",
    "انتخابات"
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

    text = html.unescape(text)

    replacements = {
        "&8217;": "'",
        "&#8217;": "'",
        "&8220;": '"',
        "&#8220;": '"',
        "&8221;": '"',
        "&#8221;": '"'
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# MOVIE FILTER
# ============================================================

def is_movie_news(title, description):

    text = f"{title} {description}".lower()

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
# IMAGE VALIDATION
# ============================================================

def is_valid_image(url):

    if not url:
        return False

    if not isinstance(url, str):
        return False

    if not url.startswith("http"):
        return False

    lower = url.lower()

    bad_words = [
        "logo",
        "favicon",
        "icon.",
        "/icon",
        "avatar",
        "placeholder",
        "default-image",
        "sprite"
    ]

    if any(word in lower for word in bad_words):
        return False

    return True


# ============================================================
# RESOLVE FINAL URL
# ============================================================

def resolve_url(url):

    if not url:
        return ""

    try:

        response = session.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        return response.url or url

    except Exception as error:

        print(
            "URL RESOLVE ERROR:",
            error
        )

        return url


# ============================================================
# RSS IMAGE
# ============================================================

def get_rss_image(entry):

    # media_content
    try:

        for item in entry.get(
            "media_content",
            []
        ):

            image = item.get(
                "url",
                ""
            )

            if is_valid_image(image):
                return image

    except Exception:
        pass


    # media_thumbnail
    try:

        for item in entry.get(
            "media_thumbnail",
            []
        ):

            image = item.get(
                "url",
                ""
            )

            if is_valid_image(image):
                return image

    except Exception:
        pass


    # enclosures
    try:

        for item in entry.get(
            "enclosures",
            []
        ):

            image = (
                item.get("href")
                or item.get("url")
                or ""
            )

            if is_valid_image(image):
                return image

    except Exception:
        pass


    # HTML inside RSS
    try:

        content = (
            entry.get("summary", "")
            or entry.get("description", "")
            or ""
        )

        soup = BeautifulSoup(
            content,
            "html.parser"
        )

        image_tag = soup.find("img")

        if image_tag:

            image = (
                image_tag.get("src")
                or image_tag.get("data-src")
                or image_tag.get("data-lazy-src")
                or ""
            )

            if is_valid_image(image):
                return image

    except Exception:
        pass


    return ""


# ============================================================
# GET IMAGE FROM ARTICLE HTML
# ============================================================

def extract_article_image(soup, base_url):

    # OpenGraph
    meta_selectors = [

        ("property", "og:image"),
        ("property", "og:image:url"),
        ("property", "og:image:secure_url"),

        ("name", "twitter:image"),
        ("name", "twitter:image:src"),

        ("itemprop", "image")
    ]


    for attribute, value in meta_selectors:

        tag = soup.find(
            "meta",
            attrs={
                attribute: value
            }
        )

        if tag:

            image = tag.get(
                "content",
                ""
            ).strip()

            image = urljoin(
                base_url,
                image
            )

            if is_valid_image(image):
                return image


    # JSON-LD
    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):

        try:

            raw = script.string

            if not raw:
                continue

            data = json.loads(raw)

            objects = (
                data
                if isinstance(data, list)
                else [data]
            )

            for obj in objects:

                if not isinstance(obj, dict):
                    continue

                image = obj.get("image")

                if isinstance(image, list) and image:
                    image = image[0]

                if isinstance(image, dict):
                    image = (
                        image.get("url")
                        or image.get("contentUrl")
                    )

                if isinstance(image, str):

                    image = urljoin(
                        base_url,
                        image
                    )

                    if is_valid_image(image):
                        return image

        except Exception:
            pass


    # Article images
    images = soup.find_all("img")

    for tag in images:

        image = (

            tag.get("data-src")
            or tag.get("data-lazy-src")
            or tag.get("data-original")
            or tag.get("src")
            or ""
        )

        if not image:
            continue

        image = urljoin(
            base_url,
            image
        )

        if not is_valid_image(image):
            continue

        return image


    return ""


# ============================================================
# GET ARTICLE DATA
# ============================================================

def get_article_data(url):

    result = {
        "url": url,
        "image": "",
        "text": ""
    }

    if not url:
        return result


    try:

        print("RESOLVING ARTICLE...")

        final_url = resolve_url(url)

        result["url"] = final_url

        print("FETCHING ARTICLE...")

        response = session.get(
            final_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        if response.status_code != 200:

            print(
                "ARTICLE STATUS:",
                response.status_code
            )

            return result


        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # REMOVE USELESS TAGS
        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "noscript"
        ]):

            tag.decompose()


        # IMAGE
        image = extract_article_image(
            soup,
            response.url
        )

        result["image"] = image


        # ARTICLE TEXT
        article = soup.find("article")

        if article:

            text = article.get_text(
                " ",
                strip=True
            )

        else:

            paragraphs = soup.find_all("p")

            text = " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for p in paragraphs
            )


        text = clean_text(text)

        result["text"] = text[:10000]

        print(
            "ARTICLE TEXT LENGTH:",
            len(result["text"])
        )


    except Exception as error:

        print(
            "ARTICLE ERROR:",
            error
        )


    return result


# ============================================================
# FIND AVAILABLE GEMINI MODEL
# ============================================================

GEMINI_MODEL = None


def get_gemini_model():

    global GEMINI_MODEL

    if GEMINI_MODEL:
        return GEMINI_MODEL


    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models"
    )

    try:

        response = session.get(
            url,
            params={
                "key": GEMINI_API_KEY
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        models = data.get(
            "models",
            []
        )


        preferred = [

            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash"
        ]


        available = []

        for model in models:

            name = model.get(
                "name",
                ""
            ).replace(
                "models/",
                ""
            )

            methods = model.get(
                "supportedGenerationMethods",
                []
            )

            if (
                "generateContent" in methods
                and name
            ):

                available.append(name)


        for preferred_name in preferred:

            if preferred_name in available:

                GEMINI_MODEL = preferred_name

                print(
                    "USING GEMINI MODEL:",
                    GEMINI_MODEL
                )

                return GEMINI_MODEL


        if available:

            GEMINI_MODEL = available[0]

            print(
                "USING GEMINI MODEL:",
                GEMINI_MODEL
            )

            return GEMINI_MODEL


    except Exception as error:

        print(
            "MODEL LIST ERROR:",
            error
        )


    # fallback
    GEMINI_MODEL = "gemini-2.0-flash"

    return GEMINI_MODEL


# ============================================================
# GEMINI REQUEST
# ============================================================

def call_gemini(prompt):

    model = get_gemini_model()

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

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

            "temperature": 0.5,

            "maxOutputTokens": 1400
        }
    }


    response = session.post(
        url,
        params={
            "key": GEMINI_API_KEY
        },
        json=payload,
        timeout=90
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
            "GEMINI BAD RESPONSE:",
            data
        )

        return ""


# ============================================================
# TRANSLATE + LONG SUMMARY
# ============================================================

def translate_and_summarize(
    title,
    description,
    article_text
):

    article_text = (
        article_text[:7000]
        if article_text
        else ""
    )


    prompt = f"""
أنت محرر عربي محترف متخصص في أخبار الأفلام والمسلسلات لموقع MOVINS.

حوّل الخبر التالي إلى محتوى عربي احترافي.

المطلوب:

1. ترجمة العنوان إلى العربية ترجمة طبيعية.
2. كتابة ملخص عربي طويل ومفصل.

شروط الملخص:

- بين 140 و220 كلمة تقريباً.
- من 7 إلى 10 جمل.
- يجب أن يكون عدة أسطر وليس فقرة قصيرة جداً.
- اشرح الخبر بوضوح.
- اذكر أهم المعلومات المتوفرة.
- وضح أهمية الخبر للجمهور إذا كانت المعلومات تسمح بذلك.
- لا تخترع أي معلومات غير موجودة.
- لا تكرر نفس الجملة.
- استخدم العربية الفصحى.
- أسماء الأفلام والمسلسلات والأشخاص يمكن إبقاؤها بلغتها الأصلية عند الحاجة.

أعد النتيجة بهذا الشكل فقط:

TITLE: عنوان عربي هنا

SUMMARY:
ملخص عربي طويل هنا.

ORIGINAL TITLE:
{title}

RSS DESCRIPTION:
{description}

ARTICLE TEXT:
{article_text}
"""

    try:

        result = call_gemini(prompt)

        if not result:
            return "", ""


        title_match = re.search(
            r"TITLE:\s*(.*?)(?=\s*SUMMARY:)",
            result,
            re.S | re.I
        )


        summary_match = re.search(
            r"SUMMARY:\s*(.*)",
            result,
            re.S | re.I
        )


        arabic_title = ""

        arabic_summary = ""


        if title_match:

            arabic_title = clean_text(
                title_match.group(1)
            )


        if summary_match:

            arabic_summary = clean_text(
                summary_match.group(1)
            )


        if not arabic_title:

            arabic_title = clean_text(
                title
            )


        if len(arabic_summary) < 150:

            # لا نفشل الخبر بالكامل
            # نستعمل الوصف والنص المتاح
            fallback = clean_text(
                f"{description} {article_text}"
            )

            if len(fallback) > len(arabic_summary):

                arabic_summary = fallback[:1800]


        return (
            arabic_title,
            arabic_summary
        )


    except Exception as error:

        print(
            "GEMINI ERROR:",
            error
        )

        return "", ""


# ============================================================
# ID
# ============================================================

def make_id(title, link):

    text = (
        title + link
    ).encode("utf-8")

    return hashlib.md5(
        text
    ).hexdigest()


# ============================================================
# LOAD OLD IDS
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

            data = json.load(file)


        return {

            item.get("id")

            for item in data.get(
                "items",
                []
            )

            if item.get("id")

        }


    except Exception:

        return set()


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

            if date.tzinfo is None:

                date = date.replace(
                    tzinfo=timezone.utc
                )

            return date.astimezone(
                timezone.utc
            ).strftime(
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

        if len(articles) >= MAX_NEWS:
            break


        print(
            "\n================================"
        )

        print(
            "FETCHING:",
            source["name"]
        )


        try:

            feed = feedparser.parse(
                source["url"],
                request_headers=HEADERS
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


                if not is_movie_news(
                    original_title,
                    original_description
                ):
                    continue


                normalized_title = (
                    original_title
                    .lower()
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


                print(
                    "\nPROCESSING:",
                    original_title
                )


                # --------------------------------------------
                # RSS IMAGE
                # --------------------------------------------

                image = get_rss_image(
                    entry
                )


                # --------------------------------------------
                # ARTICLE
                # --------------------------------------------

                article_data = get_article_data(
                    link
                )


                final_link = (
                    article_data["url"]
                    or link
                )


                article_text = article_data[
                    "text"
                ]


                # Prefer real article image
                if is_valid_image(
                    article_data["image"]
                ):

                    image = article_data[
                        "image"
                    ]


                # --------------------------------------------
                # SOURCE NAME
                # --------------------------------------------

                entry_source = entry.get(
                    "source",
                    {}
                )


                if isinstance(
                    entry_source,
                    dict
                ):

                    source_name = (
                        entry_source.get(
                            "title"
                        )
                        or source["name"]
                    )

                else:

                    source_name = source["name"]


                # --------------------------------------------
                # GEMINI
                # --------------------------------------------

                print(
                    "TRANSLATING AND SUMMARIZING..."
                )


                arabic_title, arabic_summary = (
                    translate_and_summarize(
                        original_title,
                        original_description,
                        article_text
                    )
                )


                if not arabic_title:

                    print(
                        "SKIPPED — NO TITLE"
                    )

                    continue


                if not arabic_summary:

                    arabic_summary = (
                        original_description
                        or article_text
                        or "لم تتوفر تفاصيل إضافية عن هذا الخبر."
                    )


                # --------------------------------------------
                # IMPORTANT:
                # DO NOT DELETE NEWS BECAUSE IMAGE FAILED
                # --------------------------------------------

                if not is_valid_image(image):

                    print(
                        "WARNING — NO ARTICLE IMAGE, KEEPING NEWS"
                    )

                    image = ""


                item = {

                    "id": article_id,

                    "title": arabic_title,

                    "summary": arabic_summary,

                    "image": image,

                    "link": final_link,

                    "source": source_name,

                    "category": source[
                        "category"
                    ],

                    "date": get_date(
                        entry
                    ),

                    "originalTitle": original_title
                }


                articles.append(item)

                seen_titles.add(
                    normalized_title
                )


                print(
                    "ADDED:",
                    arabic_title
                )

                print(
                    "IMAGE:",
                    "YES"
                    if image
                    else "NO"
                )

                print(
                    "SUMMARY LENGTH:",
                    len(arabic_summary)
                )


                time.sleep(1)


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


    # لا نجعل GitHub Action يفشل
    # حتى لو كانت المصادر مؤقتاً فارغة

    if not articles:

        print(
            "WARNING: No news generated this run."
        )

        print(
            "Keeping workflow successful."
        )

        return


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
