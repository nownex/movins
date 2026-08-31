import os
import re
import json
import time
import html
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

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

    # ================= ARABIC =================

    {
        "name": "Google News Arabic Movies",
        "url": (
            "https://news.google.com/rss/search?"
            "q=(%D8%A3%D9%81%D9%84%D8%A7%D9%85+OR+%D9%81%D9%8A%D9%84%D9%85+"
            "OR+%D8%B3%D9%8A%D9%86%D9%85%D8%A7+OR+%D9%85%D8%B3%D9%84%D8%B3%D9%84+"
            "OR+%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA+OR+%D8%B4%D8%A8%D8%A7%D9%83+%D8%A7%D9%84%D8%AA%D8%B0%D8%A7%D9%83%D8%B1)"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "Google News Arabic Cinema",
        "url": (
            "https://news.google.com/rss/search?"
            "q=(%D8%A3%D9%81%D9%84%D8%A7%D9%85+%D9%85%D9%86%D8%AA%D8%B8%D8%B1%D8%A9+"
            "OR+%D9%81%D9%8A%D9%84%D9%85+%D8%AC%D8%AF%D9%8A%D8%AF+"
            "OR+%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1+%D9%81%D9%8A%D9%84%D9%85+"
            "OR+%D8%A5%D9%8A%D8%B1%D8%A7%D8%AF%D8%A7%D8%AA+%D8%A7%D9%84%D8%A3%D9%81%D9%84%D8%A7%D9%85)"
            "&hl=ar&gl=SA&ceid=SA:ar"
        ),
        "category": "أفلام"
    },


    # ================= INTERNATIONAL =================

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
        "name": "Google News Movies",
        "url": (
            "https://news.google.com/rss/search?"
            "q=(movie+OR+film+OR+box+office+OR+movie+release+"
            "OR+movie+trailer+OR+Netflix+series+OR+TV+series)"
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
    "films",
    "cinema",
    "box office",
    "trailer",
    "premiere",
    "release",
    "netflix",
    "disney",
    "marvel",
    "hollywood",
    "series",
    "tv",
    "season",
    "episode",
    "streaming",

    "فيلم",
    "أفلام",
    "سينما",
    "شباك التذاكر",
    "إيرادات",
    "مسلسل",
    "مسلسلات",
    "موسم",
    "حلقة",
    "نتفليكس",
    "ديزني",
    "مارفل",
    "هوليوود",
    "منصة"
]


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
    "كرة القدم",
    "برشلونة",
    "ريال مدريد"
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

    # إصلاح HTML entities الرقمية
    text = html.unescape(text)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = text.replace(
        "&8217;",
        "'"
    )

    text = text.replace(
        "&8220;",
        '"'
    )

    text = text.replace(
        "&8221;",
        '"'
    )

    return text.strip()


# ============================================================
# MOVIE FILTER
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
# RESOLVE GOOGLE NEWS LINK
# ============================================================

def resolve_article_url(url):

    if not url:
        return ""

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        final_url = response.url

        # إذا خرجنا من Google News
        if (
            "news.google.com" not in urlparse(
                final_url
            ).netloc.lower()
        ):
            return final_url

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # canonical
        canonical = soup.find(
            "link",
            attrs={
                "rel": "canonical"
            }
        )

        if canonical:

            href = canonical.get(
                "href",
                ""
            )

            if (
                href
                and "news.google.com" not in href
            ):
                return href

        # ابحث عن رابط خارجي
        for tag in soup.find_all(
            "a",
            href=True
        ):

            href = tag.get("href")

            if not href:
                continue

            absolute = urljoin(
                final_url,
                href
            )

            domain = urlparse(
                absolute
            ).netloc.lower()

            if (
                domain
                and "google.com" not in domain
                and "googleusercontent.com" not in domain
            ):
                return absolute

        return final_url

    except Exception as error:

        print(
            "URL RESOLVE ERROR:",
            error
        )

        return url


# ============================================================
# FETCH ARTICLE PAGE
# ============================================================

def fetch_article(url):

    if not url:
        return None, ""

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        if response.status_code != 200:
            return None, ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        return soup, response.url

    except Exception as error:

        print(
            "ARTICLE FETCH ERROR:",
            error
        )

        return None, ""


# ============================================================
# EXTRACT ARTICLE TEXT
# ============================================================

def get_article_text(soup):

    if not soup:
        return ""

    # حذف العناصر غير المهمة
    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form"
        ]
    ):
        tag.decompose()

    article = soup.find("article")

    if article:

        paragraphs = article.find_all("p")

    else:

        paragraphs = soup.find_all("p")

    texts = []

    for p in paragraphs:

        text = clean_text(
            p.get_text(
                " ",
                strip=True
            )
        )

        if len(text) < 40:
            continue

        texts.append(text)

    text = "\n".join(texts)

    # نحتاج كمية كافية ولكن لا نرسل مقالاً ضخماً
    return text[:9000]


# ============================================================
# GET RSS IMAGE
# ============================================================

def get_rss_image(entry):

    try:

        media = entry.get(
            "media_content",
            []
        )

        for item in media:

            url = item.get(
                "url",
                ""
            )

            if url.startswith("http"):
                return url

    except Exception:
        pass

    try:

        media = entry.get(
            "media_thumbnail",
            []
        )

        for item in media:

            url = item.get(
                "url",
                ""
            )

            if url.startswith("http"):
                return url

    except Exception:
        pass

    return ""


# ============================================================
# GET ARTICLE IMAGE
# ============================================================

def get_article_image(soup, page_url):

    if not soup:
        return ""

    # الأولوية للصورة الرئيسية للمقال

    meta_types = [

        ("property", "og:image"),
        ("name", "twitter:image"),
        ("property", "twitter:image"),
        ("name", "twitter:image:src")
    ]

    for attr_name, attr_value in meta_types:

        tag = soup.find(
            "meta",
            attrs={
                attr_name: attr_value
            }
        )

        if tag:

            image = tag.get(
                "content",
                ""
            ).strip()

            if image:

                image = urljoin(
                    page_url,
                    image
                )

                if is_valid_image(image):
                    return image

    # صور article
    article = soup.find("article")

    if article:

        images = article.find_all("img")

    else:

        images = soup.find_all("img")

    for img in images:

        image = (
            img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("src")
            or ""
        )

        if not image:
            continue

        image = urljoin(
            page_url,
            image
        )

        if is_valid_image(image):
            return image

    return ""


# ============================================================
# VALIDATE IMAGE
# ============================================================

def is_valid_image(url):

    if not url:
        return False

    if not url.startswith("http"):
        return False

    lower = url.lower()

    bad_words = [

        "logo",
        "favicon",
        "icon",
        "avatar",
        "placeholder",
        "default",

        # منع صور Google News
        "news.google.com",
        "gstatic.com",
        "google.com/images",
        "googleusercontent.com"
    ]

    if any(
        word in lower
        for word in bad_words
    ):
        return False

    # امتدادات أو خدمات صور معروفة
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

    # نحاول أكثر من نموذج لتجنب مشكلة 404
    models = [

        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]

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

            "temperature": 0.35,

            "maxOutputTokens": 1800
        }
    }

    for model in models:

        try:

            url = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{model}:generateContent"
            )

            response = requests.post(
                url,
                params={
                    "key": GEMINI_API_KEY
                },
                json=payload,
                timeout=90
            )

            if response.status_code != 200:

                print(
                    f"GEMINI MODEL FAILED {model}:",
                    response.status_code
                )

                continue

            data = response.json()

            candidates = data.get(
                "candidates",
                []
            )

            if not candidates:
                continue

            content = candidates[0].get(
                "content",
                {}
            )

            parts = content.get(
                "parts",
                []
            )

            if not parts:
                continue

            result = parts[0].get(
                "text",
                ""
            ).strip()

            if result:
                print(
                    "GEMINI MODEL:",
                    model
                )

                return result

        except Exception as error:

            print(
                f"GEMINI ERROR {model}:",
                error
            )

    return ""


# ============================================================
# TRANSLATE + REAL LONG SUMMARY
# ============================================================

def translate_and_summarize(
    title,
    rss_description,
    article_text
):

    prompt = f"""
أنت محرر محترف لموقع عربي متخصص في أخبار الأفلام والمسلسلات اسمه MOVINS.

أمامك عنوان الخبر ووصفه ونص من المقال الأصلي.

المهمة:

أولاً:
ترجم العنوان إلى العربية ترجمة طبيعية واحترافية.

ثانياً:
اكتب ملخصاً عربياً طويلاً ومفصلاً.

قواعد إلزامية:

- الملخص يجب أن يحتوي بين 180 و300 كلمة.
- يجب أن يتكون من عدة فقرات أو على الأقل 8 إلى 12 جملة.
- لا تكتب ملخصاً قصيراً.
- اشرح تفاصيل الخبر المهمة.
- وضح ما الذي حدث.
- وضح الأشخاص أو الأفلام أو المسلسلات المعنية.
- وضح سبب أهمية الخبر للجمهور.
- استخدم فقط المعلومات الموجودة في النص.
- لا تخترع معلومات.
- ترجم النص كاملاً إلى العربية بأسلوب صحفي ممتاز.
- يمكن إبقاء أسماء الأفلام والمسلسلات والأشخاص الأجنبية كما هي عند الحاجة.
- لا تستخدم اللغة الإنجليزية في الجمل العربية إلا للأسماء والعناوين.
- لا تضع مقدمة مثل: "إليك الملخص".
- لا تضع نقاطاً أو تعداداً.

أعد النتيجة فقط بهذا الشكل:

TITLE:
العنوان العربي

SUMMARY:
ملخص عربي طويل ومفصل من 180 إلى 300 كلمة.

========================

العنوان الأصلي:

{title}

========================

وصف RSS:

{rss_description}

========================

نص المقال:

{article_text}
"""

    result = call_gemini(prompt)

    if not result:
        return "", ""

    title_match = re.search(
        r"TITLE:\s*(.*?)(?=\s*SUMMARY:|$)",
        result,
        re.S | re.I
    )

    summary_match = re.search(
        r"SUMMARY:\s*(.+)",
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

    return (
        arabic_title,
        arabic_summary
    )


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
# MAIN
# ============================================================

def main():

    print(
        "================================="
    )

    print(
        "MOVINS NEWS ENGINE STARTED"
    )

    print(
        "================================="
    )

    old_ids = load_old_ids()

    articles = []

    seen_titles = set()


    for source in RSS_FEEDS:

        if len(articles) >= MAX_NEWS:
            break

        print()
        print(
            "FETCHING:",
            source["name"]
        )

        try:

            feed = feedparser.parse(
                source["url"]
            )

            print(
                "ENTRIES:",
                len(feed.entries)
            )

            for entry in feed.entries:

                if len(articles) >= MAX_NEWS:
                    break

                original_title = clean_text(
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
                    or entry.get(
                        "description",
                        ""
                    )
                )

                rss_link = entry.get(
                    "link",
                    ""
                )

                if not original_title:
                    continue

                if not is_movie_news(
                    original_title,
                    description
                ):
                    continue

                normalized_title = (
                    original_title
                    .lower()
                    .strip()
                )

                if normalized_title in seen_titles:
                    continue


                # ==========================================
                # RESOLVE REAL ARTICLE URL
                # ==========================================

                print(
                    "RESOLVING ARTICLE..."
                )

                article_url = resolve_article_url(
                    rss_link
                )

                article_id = make_id(
                    original_title,
                    article_url
                )

                if article_id in old_ids:
                    continue


                # ==========================================
                # FETCH REAL ARTICLE
                # ==========================================

                print(
                    "FETCHING ARTICLE..."
                )

                soup, final_url = fetch_article(
                    article_url
                )

                if not soup:

                    print(
                        "SKIPPED — ARTICLE NOT ACCESSIBLE"
                    )

                    continue


                # ==========================================
                # GET REAL ARTICLE TEXT
                # ==========================================

                article_text = get_article_text(
                    soup
                )

                # إذا كان المقال قصيراً نستخدم RSS أيضاً
                if len(article_text) < 300:

                    article_text = (
                        description
                        + "\n\n"
                        + original_title
                    )

                print(
                    "ARTICLE TEXT LENGTH:",
                    len(article_text)
                )


                # ==========================================
                # GET REAL IMAGE
                # ==========================================

                image = get_article_image(
                    soup,
                    final_url
                )

                if not is_valid_image(image):

                    rss_image = get_rss_image(
                        entry
                    )

                    if is_valid_image(
                        rss_image
                    ):
                        image = rss_image


                # لا ننشر بدون صورة حقيقية
                if not is_valid_image(image):

                    print(
                        "SKIPPED — NO REAL ARTICLE IMAGE"
                    )

                    continue


                # ==========================================
                # SOURCE NAME
                # ==========================================

                domain = urlparse(
                    final_url
                ).netloc.replace(
                    "www.",
                    ""
                )

                source_name = domain

                try:

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
                                "title",
                                source_name
                            )
                        )

                except Exception:
                    pass


                # ==========================================
                # TRANSLATE + LONG SUMMARY
                # ==========================================

                print()
                print(
                    "TRANSLATING AND SUMMARIZING:"
                )

                print(
                    original_title
                )

                arabic_title, arabic_summary = (
                    translate_and_summarize(
                        original_title,
                        description,
                        article_text
                    )
                )

                if not arabic_title:

                    print(
                        "SKIPPED — TRANSLATION FAILED"
                    )

                    continue


                # نرفض الملخص القصير فعلاً
                if len(arabic_summary) < 600:

                    print(
                        "SKIPPED — SUMMARY TOO SHORT:",
                        len(arabic_summary)
                    )

                    continue


                item = {

                    "id": article_id,

                    "title": arabic_title,

                    "summary": arabic_summary,

                    "image": image,

                    "link": final_url,

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

                print()
                print(
                    "✓ ADDED:",
                    arabic_title
                )

                print(
                    "✓ SUMMARY:",
                    len(arabic_summary),
                    "characters"
                )

                print(
                    "✓ IMAGE:",
                    image[:100]
                )

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


    print()
    print(
        "================================="
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


if __name__ == "__main__":

    main()
