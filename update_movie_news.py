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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

OUTPUT_FILE = "movie-news.json"

MAX_NEWS = 12
MAX_OLD_NEWS = 36

REQUEST_TIMEOUT = 20
GEMINI_TIMEOUT = 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
}


# ============================================================
# RSS SOURCES
# ============================================================

RSS_FEEDS = [

    # ========================================================
    # ARABIC SOURCES FIRST
    # ========================================================

    {
        "name": "Google News Arabic - Movies",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D8%A3%D9%81%D9%84%D8%A7%D9%85+OR+%D9%81%D9%8A%D9%84%D9%85+"
            "OR+%D8%B3%D9%8A%D9%86%D9%85%D8%A7+OR+%D8%B4%D8%A8%D8%A7%D9%83+%D8%A7%D9%84%D8%AA%D8%B0%D8%A7%D9%83%D8%B1"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "أفلام"
    },

    {
        "name": "Google News Arabic - Upcoming Movies",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D8%A3%D9%81%D9%84%D8%A7%D9%85+%D9%85%D9%86%D8%AA%D8%B8%D8%B1%D8%A9+"
            "OR+%D8%A3%D9%81%D9%84%D8%A7%D9%85+%D9%82%D8%A7%D8%AF%D9%85%D8%A9+"
            "OR+%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1+%D9%81%D9%8A%D9%84%D9%85"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "أفلام منتظرة"
    },

    {
        "name": "Google News Arabic - Series",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D9%85%D8%B3%D9%84%D8%B3%D9%84+OR+%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA+"
            "OR+%D9%85%D9%88%D8%B3%D9%85+%D8%AC%D8%AF%D9%8A%D8%AF+"
            "OR+%D9%86%D8%AA%D9%81%D9%84%D9%8A%D9%83%D8%B3+%D9%85%D8%B3%D9%84%D8%B3%D9%84"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "مسلسلات"
    },

    {
        "name": "Google News Arabic - Netflix",
        "url": (
            "https://news.google.com/rss/search?"
            "q=%D9%86%D8%AA%D9%81%D9%84%D9%8A%D9%83%D8%B3+%D9%81%D9%8A%D9%84%D9%85+"
            "OR+Netflix+movie+OR+Netflix+series"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "منصات"
    },


    # ========================================================
    # INTERNATIONAL SOURCES
    # ========================================================

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
        "name": "The Hollywood Reporter",
        "url": "https://www.hollywoodreporter.com/feed/",
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "Collider",
        "url": "https://collider.com/feed/",
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "Google News - Upcoming Movies",
        "url": (
            "https://news.google.com/rss/search?"
            "q=upcoming+movies+OR+most+anticipated+movies+"
            "OR+movie+release+OR+film+trailer"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "category": "أفلام منتظرة"
    },

    {
        "name": "Google News - Box Office",
        "url": (
            "https://news.google.com/rss/search?"
            "q=box+office+movie+film"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "category": "بوكس أوفيس"
    },

    {
        "name": "Google News - TV Series",
        "url": (
            "https://news.google.com/rss/search?"
            "q=TV+series+OR+Netflix+series+OR+new+season+"
            "OR+series+trailer"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "category": "مسلسلات"
    }
]


# ============================================================
# IMPORTANT MOVIE / SERIES KEYWORDS
# ============================================================

MOVIE_KEYWORDS = [

    # Movies
    "movie",
    "movies",
    "film",
    "films",
    "cinema",
    "box office",
    "trailer",
    "teaser",
    "premiere",
    "movie release",
    "film release",
    "upcoming movie",
    "anticipated movie",

    # Series
    "series",
    "tv series",
    "television",
    "season",
    "episode",
    "show",
    "streaming",

    # Studios / Platforms
    "netflix",
    "disney",
    "disney+",
    "marvel",
    "dc studios",
    "warner bros",
    "paramount",
    "universal",

    # Arabic
    "فيلم",
    "أفلام",
    "السينما",
    "سينما",
    "شباك التذاكر",
    "بوكس أوفيس",
    "إيرادات",
    "إصدار",
    "تريلر",
    "إعلان تشويقي",
    "عرض أول",
    "فيلم منتظر",

    "مسلسل",
    "مسلسلات",
    "الموسم",
    "موسم جديد",
    "حلقة",
    "نتفليكس",
    "ديزني",
    "مارفل"
]


# ============================================================
# BAD KEYWORDS
# ============================================================

BAD_KEYWORDS = [

    "politics",
    "election",
    "president",
    "government",
    "war",
    "military",
    "football",
    "soccer",
    "basketball",
    "stock market",
    "bitcoin",
    "crypto",

    "سياسة",
    "انتخابات",
    "رئيس الجمهورية",
    "الحكومة",
    "حرب",
    "الجيش",
    "كرة القدم",
    "مباراة",
    "بورصة",
    "بيتكوين"
]


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(str(text))

    # معالجة HTML entities غير الطبيعية
    for _ in range(3):
        text = html.unescape(text)

    text = text.replace("&#8217;", "'")
    text = text.replace("&8217;", "'")
    text = text.replace("&#8216;", "'")
    text = text.replace("&8216;", "'")

    text = text.replace("&#8220;", '"')
    text = text.replace("&8220;", '"')

    text = text.replace("&#8221;", '"')
    text = text.replace("&8221;", '"')

    text = text.replace("&#8211;", "-")
    text = text.replace("&8211;", "-")

    text = text.replace("&#8212;", "-")
    text = text.replace("&8212;", "-")

    soup = BeautifulSoup(text, "html.parser")

    text = soup.get_text(" ", strip=True)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# DETECT ARABIC
# ============================================================

def is_arabic_text(text):

    if not text:
        return False

    arabic_letters = re.findall(
        r"[\u0600-\u06FF]",
        text
    )

    return len(arabic_letters) >= 5


# ============================================================
# MOVIE RELEVANCE
# ============================================================

def is_movie_news(title, description):

    text = clean_text(
        f"{title} {description}"
    ).lower()

    good = any(
        keyword.lower() in text
        for keyword in MOVIE_KEYWORDS
    )

    bad = any(
        keyword.lower() in text
        for keyword in BAD_KEYWORDS
    )

    return good and not bad


# ============================================================
# CREATE UNIQUE ID
# ============================================================

def make_id(title, link):

    value = (
        clean_text(title).lower().strip()
        + "|"
        + str(link)
    )

    return hashlib.md5(
        value.encode("utf-8")
    ).hexdigest()


# ============================================================
# RSS IMAGE
# ============================================================

def get_rss_image(entry):

    try:
        media = entry.get("media_content", [])

        for item in media:

            url = item.get("url", "")

            if url:
                return url

    except Exception:
        pass


    try:
        thumbnails = entry.get("media_thumbnail", [])

        for item in thumbnails:

            url = item.get("url", "")

            if url:
                return url

    except Exception:
        pass


    try:
        enclosures = entry.get("enclosures", [])

        for item in enclosures:

            url = (
                item.get("href")
                or item.get("url")
                or ""
            )

            if url:
                return url

    except Exception:
        pass


    return ""


# ============================================================
# VALIDATE IMAGE
# ============================================================

def is_valid_image(url):

    if not url:
        return False

    url = str(url).strip()

    if not url.startswith(("http://", "https://")):
        return False

    lower = url.lower()

    bad_words = [

        "logo",
        "icon",
        "avatar",
        "placeholder",
        "default-image",
        "default_image",
        "favicon",
        "sprite",
        "data:image"
    ]

    if any(word in lower for word in bad_words):
        return False

    return True


# ============================================================
# GET ARTICLE PAGE + IMAGE + TEXT
# ============================================================

def get_article_data(url):

    result = {
        "image": "",
        "text": "",
        "final_url": url
    }

    if not url:
        return result

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        if response.status_code != 200:
            return result

        result["final_url"] = response.url

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        meta_candidates = [

            ("property", "og:image"),
            ("property", "og:image:url"),
            ("name", "twitter:image"),
            ("property", "twitter:image"),
            ("name", "twitter:image:src")
        ]


        for attribute, value in meta_candidates:

            tag = soup.find(
                "meta",
                attrs={attribute: value}
            )

            if tag:

                image = (
                    tag.get("content", "")
                    .strip()
                )

                if image:

                    image = urljoin(
                        response.url,
                        image
                    )

                    if is_valid_image(image):

                        result["image"] = image
                        break


        # ----------------------------------------------------
        # ARTICLE TEXT
        # ----------------------------------------------------

        for unwanted in soup([
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside"
        ]):
            unwanted.decompose()


        paragraphs = []

        for paragraph in soup.find_all("p"):

            text = clean_text(
                paragraph.get_text(
                    " ",
                    strip=True
                )
            )

            if len(text) >= 40:

                paragraphs.append(text)


        article_text = " ".join(
            paragraphs[:20]
        )

        article_text = clean_text(
            article_text
        )

        # لا نحتاج نصاً ضخماً
        if len(article_text) > 7000:
            article_text = article_text[:7000]

        result["text"] = article_text


        # ----------------------------------------------------
        # FALLBACK IMAGE
        # ----------------------------------------------------

        if not result["image"]:

            for image_tag in soup.find_all("img"):

                image = (
                    image_tag.get("src")
                    or image_tag.get("data-src")
                    or image_tag.get("data-lazy-src")
                    or ""
                )

                if not image:
                    continue

                image = urljoin(
                    response.url,
                    image
                )

                if not is_valid_image(image):
                    continue

                width = image_tag.get("width", "")

                try:
                    if width and int(width) < 350:
                        continue
                except Exception:
                    pass

                result["image"] = image
                break


    except Exception as error:

        print(
            "ARTICLE ERROR:",
            error
        )


    return result


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
# GEMINI MODEL DISCOVERY
# ============================================================

GEMINI_MODEL = None


def find_gemini_model():

    global GEMINI_MODEL

    if GEMINI_MODEL:
        return GEMINI_MODEL

    if not GEMINI_API_KEY:
        print(
            "GEMINI KEY NOT FOUND"
        )
        return ""


    print(
        "SEARCHING FOR AVAILABLE GEMINI MODEL..."
    )


    try:

        response = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={
                "key": GEMINI_API_KEY
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        models = data.get(
            "models",
            []
        )


        available = []


        for model in models:

            name = model.get(
                "name",
                ""
            )

            methods = model.get(
                "supportedGenerationMethods",
                []
            )

            if (
                name
                and "generateContent" in methods
            ):

                available.append(
                    name
                )


        preferred = [

            "models/gemini-2.5-flash",
            "models/gemini-2.0-flash",
            "models/gemini-2.0-flash-lite",
            "models/gemini-1.5-flash"
        ]


        for preferred_model in preferred:

            if preferred_model in available:

                GEMINI_MODEL = preferred_model

                print(
                    "GEMINI MODEL:",
                    GEMINI_MODEL
                )

                return GEMINI_MODEL


        if available:

            GEMINI_MODEL = available[0]

            print(
                "GEMINI MODEL:",
                GEMINI_MODEL
            )

            return GEMINI_MODEL


        print(
            "NO GEMINI MODEL SUPPORTS generateContent"
        )


    except Exception as error:

        print(
            "MODEL DISCOVERY ERROR:",
            error
        )


    return ""


# ============================================================
# CALL GEMINI
# ============================================================

def call_gemini(prompt):

    model = find_gemini_model()

    if not model:
        return ""


    endpoint = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/{model}:generateContent"
    )


    payload = {

        "contents": [

            {
                "role": "user",

                "parts": [

                    {
                        "text": prompt
                    }

                ]
            }
        ],

        "generationConfig": {

            "temperature": 0.3,

            "maxOutputTokens": 1400
        }
    }


    try:

        response = requests.post(
            endpoint,
            params={
                "key": GEMINI_API_KEY
            },
            json=payload,
            timeout=GEMINI_TIMEOUT
        )


        if response.status_code == 404:

            global GEMINI_MODEL

            print(
                "MODEL 404 — RESEARCHING MODEL..."
            )

            GEMINI_MODEL = None

            model = find_gemini_model()

            if not model:
                return ""


            endpoint = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/{model}:generateContent"
            )


            response = requests.post(
                endpoint,
                params={
                    "key": GEMINI_API_KEY
                },
                json=payload,
                timeout=GEMINI_TIMEOUT
            )


        response.raise_for_status()

        data = response.json()


        candidates = data.get(
            "candidates",
            []
        )

        if not candidates:
            print(
                "GEMINI NO CANDIDATES:",
                data
            )
            return ""


        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )


        texts = []

        for part in parts:

            text = part.get(
                "text",
                ""
            )

            if text:
                texts.append(text)


        return "\n".join(
            texts
        ).strip()


    except Exception as error:

        print(
            "GEMINI ERROR:",
            error
        )

        return ""


# ============================================================
# JSON PARSER
# ============================================================

def extract_json(text):

    if not text:
        return {}

    text = text.strip()

    text = re.sub(
        r"^```json",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"^```",
        "",
        text
    )

    text = re.sub(
        r"```$",
        "",
        text
    )

    text = text.strip()


    try:
        return json.loads(text)
    except Exception:
        pass


    match = re.search(
        r"\{.*\}",
        text,
        re.S
    )

    if match:

        try:
            return json.loads(
                match.group(0)
            )
        except Exception:
            pass


    return {}


# ============================================================
# TRANSLATE + LONG SUMMARY
# ============================================================

def translate_and_summarize(
    title,
    description,
    article_text=""
):

    title = clean_text(title)
    description = clean_text(description)
    article_text = clean_text(article_text)


    # إذا لم يكن لدينا Gemini
    # نسمح للأخبار العربية بالمرور
    if not GEMINI_API_KEY:

        if is_arabic_text(title):

            summary = (
                article_text
                or description
            )

            return (
                title,
                summary
            )

        return "", ""


    context = article_text

    if not context:
        context = description

    if len(context) > 6000:
        context = context[:6000]


    prompt = f"""
أنت محرر عربي محترف لموقع MOVINS المتخصص حصرياً في أخبار الأفلام والمسلسلات.

المهمة:

اقرأ عنوان الخبر والمعلومات المتاحة، ثم أعد النتيجة باللغة العربية.

القواعد المهمة جداً:

1. ترجم العنوان بالكامل إلى العربية ترجمة طبيعية واحترافية.
2. أسماء الأفلام والمسلسلات والأشخاص يمكن إبقاؤها بلغتها الأصلية عند الحاجة.
3. اكتب ملخصاً عربياً طويلاً ومفصلاً.
4. الملخص يجب أن يحتوي تقريباً على 130 إلى 220 كلمة.
5. اجعل الملخص من عدة جمل مترابطة، وليس سطراً واحداً.
6. اشرح تفاصيل الخبر وأهميته وما الذي يعنيه للمشاهدين.
7. لا تخترع معلومات غير موجودة في النص.
8. إذا كانت المعلومات قليلة، اكتب ملخصاً محافظاً دون اختراع تفاصيل.
9. لا تكتب أي مقدمات مثل "إليك الترجمة".
10. أعد JSON صالحاً فقط.

الصيغة المطلوبة:

{{
  "title": "العنوان العربي",
  "summary": "ملخص عربي طويل ومتعدد الجمل"
}}

العنوان الأصلي:

{title}

الوصف:

{description}

نص المقال المتاح:

{context}
"""


    result = call_gemini(
        prompt
    )


    if not result:

        # Fallback للأخبار العربية
        if is_arabic_text(title):

            fallback_summary = (
                article_text
                or description
            )

            return (
                title,
                fallback_summary
            )

        return "", ""


    data = extract_json(
        result
    )


    arabic_title = clean_text(
        data.get(
            "title",
            ""
        )
    )

    summary = clean_text(
        data.get(
            "summary",
            ""
        )
    )


    # fallback parsing
    if not arabic_title or not summary:

        title_match = re.search(
            r'(?:TITLE|العنوان)\s*[:：]\s*(.+?)(?=\n|$)',
            result,
            re.I
        )

        if title_match:

            arabic_title = clean_text(
                title_match.group(1)
            )


        summary_match = re.search(
            r'(?:SUMMARY|الملخص)\s*[:：]\s*(.+)',
            result,
            re.I | re.S
        )

        if summary_match:

            summary = clean_text(
                summary_match.group(1)
            )


    # fallback عربي
    if not arabic_title and is_arabic_text(title):

        arabic_title = title


    if not summary and is_arabic_text(title):

        summary = (
            article_text
            or description
        )


    return (
        arabic_title,
        summary
    )


# ============================================================
# LOAD OLD NEWS
# ============================================================

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


    except Exception as error:

        print(
            "OLD NEWS ERROR:",
            error
        )

        return []


# ============================================================
# SOURCE NAME
# ============================================================

def get_source_name(entry, fallback):

    source = entry.get(
        "source",
        None
    )


    try:

        if source:

            title = source.get(
                "title",
                ""
            )

            if title:
                return clean_text(title)

    except Exception:
        pass


    return fallback


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n================================="
    )

    print(
        "MOVINS MOVIE NEWS ENGINE STARTED"
    )

    print(
        "=================================\n"
    )


    # محاولة معرفة النموذج في البداية
    if GEMINI_API_KEY:

        find_gemini_model()

    else:

        print(
            "WARNING: GEMINI_API_KEY MISSING"
        )

        print(
            "ARABIC NEWS MAY STILL BE USED AS FALLBACK"
        )


    old_items = load_old_news()


    old_ids = {

        item.get("id")

        for item in old_items

        if item.get("id")
    }


    new_articles = []

    seen_titles = set()


    # عناوين الأخبار القديمة
    for item in old_items:

        title = clean_text(
            item.get(
                "originalTitle",
                ""
            )
        )

        if title:

            seen_titles.add(
                title.lower()
            )


    # ========================================================
    # FETCH SOURCES
    # ========================================================

    for source in RSS_FEEDS:

        if len(new_articles) >= MAX_NEWS:
            break


        print(
            "\nFETCHING:",
            source["name"]
        )


        try:

            response = requests.get(
                source["url"],
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()


            feed = feedparser.parse(
                response.content
            )


            entries = feed.entries


            print(
                "ENTRIES:",
                len(entries)
            )


            for entry in entries:

                if len(new_articles) >= MAX_NEWS:
                    break


                # ------------------------------------------------
                # BASIC DATA
                # ------------------------------------------------

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


                # ------------------------------------------------
                # MOVIE FILTER
                # ------------------------------------------------

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


                # ------------------------------------------------
                # ARTICLE DATA
                # ------------------------------------------------

                print(
                    "GETTING ARTICLE:",
                    original_title[:80]
                )


                image = get_rss_image(
                    entry
                )


                article_data = {

                    "image": "",
                    "text": "",
                    "final_url": link
                }


                # نجلب المقال دائماً لتحسين الملخص
                article_data = get_article_data(
                    link
                )


                if not is_valid_image(image):

                    image = article_data.get(
                        "image",
                        ""
                    )


                # ------------------------------------------------
                # EXCLUDE NEWS WITHOUT IMAGE
                # ------------------------------------------------

                if not is_valid_image(image):

                    print(
                        "SKIPPED — NO VALID IMAGE"
                    )

                    continue


                # ------------------------------------------------
                # TRANSLATION + SUMMARY
                # ------------------------------------------------

                print(
                    "TRANSLATING:",
                    original_title
                )


                arabic_title, arabic_summary = (
                    translate_and_summarize(

                        original_title,

                        original_description,

                        article_data.get(
                            "text",
                            ""
                        )
                    )
                )


                if not arabic_title:

                    print(
                        "SKIPPED — NO ARABIC TITLE"
                    )

                    continue


                # الملخص يجب ألا يكون قصيراً
                if len(arabic_summary) < 180:

                    # للأخبار العربية يمكن استخدام النص الأصلي
                    if is_arabic_text(original_title):

                        extra_text = clean_text(
                            article_data.get(
                                "text",
                                ""
                            )
                        )

                        if len(extra_text) > len(arabic_summary):

                            arabic_summary = extra_text


                if len(arabic_summary) < 180:

                    print(
                        "SKIPPED — SUMMARY TOO SHORT"
                    )

                    continue


                # ------------------------------------------------
                # SOURCE
                # ------------------------------------------------

                source_name = get_source_name(
                    entry,
                    source["name"]
                )


                # ------------------------------------------------
                # CREATE ITEM
                # ------------------------------------------------

                item = {

                    "id": article_id,

                    "title": arabic_title,

                    "summary": arabic_summary,

                    "image": image,

                    "link": article_data.get(
                        "final_url"
                    ) or link,

                    "source": source_name,

                    "category": source[
                        "category"
                    ],

                    "date": get_date(
                        entry
                    ),

                    "originalTitle": original_title
                }


                new_articles.append(
                    item
                )


                seen_titles.add(
                    normalized_title
                )


                print(
                    "ADDED:",
                    arabic_title
                )


                # حماية من كثرة طلبات Gemini
                time.sleep(1)


        except Exception as error:

            print(
                "SOURCE ERROR:",
                source["name"],
                error
            )


    # ========================================================
    # COMBINE NEW + OLD
    # ========================================================

    combined = new_articles + old_items


    # إزالة التكرار
    unique_items = []

    unique_ids = set()


    for item in combined:

        item_id = item.get(
            "id"
        )

        if not item_id:
            continue

        if item_id in unique_ids:
            continue


        unique_ids.add(
            item_id
        )

        unique_items.append(
            item
        )


    # ترتيب حسب التاريخ
    unique_items.sort(
        key=lambda item: item.get(
            "date",
            ""
        ),
        reverse=True
    )


    # الاحتفاظ بعدد محدود
    unique_items = unique_items[
        :MAX_OLD_NEWS
    ]


    # ========================================================
    # SAVE
    # ========================================================

    data = {

        "updated": datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),

        "items": unique_items
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
        "NEW MOVIE NEWS:",
        len(new_articles)
    )

    print(
        "TOTAL NEWS:",
        len(unique_items)
    )

    print(
        "================================="
    )


    # لا نفشل إذا كانت هناك أخبار قديمة
    if not unique_items:

        raise RuntimeError(
            "No movie or series news generated"
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
