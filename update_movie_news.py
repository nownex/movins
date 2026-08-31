import os
import re
import json
import html
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import requests
import feedparser
from bs4 import BeautifulSoup


# ============================================================
# MOVINS — ARABIC MOVIE & SERIES NEWS ENGINE
# ============================================================

OUTPUT_FILE = "movie-news.json"

MAX_NEWS = 20
MAX_PER_SOURCE = 10
REQUEST_TIMEOUT = 25


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
}


# ============================================================
# ARABIC SOURCES
# ============================================================

RSS_FEEDS = [

    {
        "name": "في الفن",
        "url": "https://www.filfan.com/rss",
        "category": "أفلام ومسلسلات",
        "type": "general"
    },

    {
        "name": "الشرق الأوسط - سينما",
        "url": "https://aawsat.com/feed/cinema",
        "category": "أفلام ومسلسلات",
        "type": "cinema"
    },

    {
        "name": "الشرق الأوسط - أنغام وفنون",
        "url": "https://aawsat.com/feed/arts",
        "category": "أفلام ومسلسلات",
        "type": "arts"
    }

]


# ============================================================
# MOVIE / SERIES KEYWORDS
# ============================================================

MOVIE_KEYWORDS = [

    "فيلم",
    "فيلما",
    "فيلماً",
    "أفلام",
    "سينما",
    "سينمائي",
    "سينمائية",
    "شباك التذاكر",
    "إيرادات",

    "مسلسل",
    "مسلسلات",
    "دراما",
    "موسم",
    "الحلقة",
    "حلقة",

    "نتفليكس",
    "Netflix",

    "ديزني",
    "Disney",

    "مارفل",
    "Marvel",

    "هوليوود",
    "Hollywood",

    "ممثل",
    "ممثلة",
    "بطولة",
    "مخرج",
    "إخراج",

    "عرض",
    "يعرض",
    "الإعلان",
    "برومو",
    "تريلر",

    "مهرجان سينمائي",
    "مهرجان الفيلم"
]


BAD_KEYWORDS = [

    "كرة القدم",
    "مباراة",
    "الدوري",
    "منتخب",

    "سياسة",
    "انتخابات",
    "رئيس",
    "حكومة",

    "اقتصاد",
    "بورصة",

    "طقس",
    "زلزال"
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

    text = re.sub(
        r"&(?:#\d+|#x[0-9a-fA-F]+|\w+);",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# CHECK IF ARTICLE IS MOVIE NEWS
# ============================================================

def is_movie_news(title, description):

    text = (
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
        title.strip() + "|" + link.strip()
    ).encode("utf-8")

    return hashlib.md5(
        value
    ).hexdigest()


# ============================================================
# NORMALIZE TITLE
# ============================================================

def normalize_title(title):

    title = clean_text(title).lower()

    title = re.sub(
        r"[^\w\s]",
        "",
        title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


# ============================================================
# GET DATE
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
# GET RSS IMAGE
# ============================================================

def get_rss_image(entry):

    # media:content
    try:

        media_content = entry.get(
            "media_content",
            []
        )

        for item in media_content:

            url = item.get(
                "url",
                ""
            )

            if url.startswith("http"):

                return url

    except Exception:
        pass


    # media:thumbnail
    try:

        media_thumbnail = entry.get(
            "media_thumbnail",
            []
        )

        for item in media_thumbnail:

            url = item.get(
                "url",
                ""
            )

            if url.startswith("http"):

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

            url = (
                item.get("href")
                or item.get("url")
                or ""
            )

            if url.startswith("http"):

                return url

    except Exception:
        pass


    # image field
    try:

        image = entry.get(
            "image",
            {}
        )

        if isinstance(image, dict):

            url = image.get(
                "href",
                ""
            )

            if url.startswith("http"):

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

    if not url.startswith("http"):
        return False

    lower = url.lower()

    bad_words = [

        "logo",
        "icon",
        "avatar",
        "favicon",

        "placeholder",

        "default-image",

        "blank",

        "sprite"

    ]

    if any(
        word in lower
        for word in bad_words
    ):
        return False

    return True


# ============================================================
# GET ARTICLE PAGE
# ============================================================

def get_article_page(url):

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

            print(
                "ARTICLE HTTP:",
                response.status_code
            )

            return None, ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        return soup, response.url

    except Exception as error:

        print(
            "ARTICLE ERROR:",
            error
        )

        return None, ""


# ============================================================
# EXTRACT ARTICLE IMAGE
# ============================================================

def get_article_image(soup, base_url):

    if not soup:
        return ""


    # Open Graph
    meta_selectors = [

        ("property", "og:image"),

        ("property", "og:image:url"),

        ("name", "twitter:image"),

        ("property", "twitter:image"),

        ("name", "twitter:image:src")

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

            if image:

                image = urljoin(
                    base_url,
                    image
                )

                if is_valid_image(image):

                    return image


    # Images in article
    for img in soup.find_all("img"):

        image = (

            img.get("data-src")

            or img.get("data-lazy-src")

            or img.get("data-original")

            or img.get("src")

            or ""

        ).strip()


        if not image:

            continue


        image = urljoin(
            base_url,
            image
        )


        if not is_valid_image(image):

            continue


        width = img.get("width")

        try:

            if width and int(width) < 250:

                continue

        except Exception:
            pass


        return image


    return ""


# ============================================================
# EXTRACT ARTICLE TEXT
# ============================================================

def get_article_text(soup):

    if not soup:
        return ""


    # Remove unwanted elements
    for element in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
        "button"
    ]):

        try:

            element.decompose()

        except Exception:
            pass


    # Priority selectors
    selectors = [

        "article",

        ".article-content",

        ".article-body",

        ".article__content",

        ".entry-content",

        ".post-content",

        ".content-body",

        ".news-content",

        "main"

    ]


    for selector in selectors:

        try:

            container = soup.select_one(
                selector
            )

            if not container:

                continue


            paragraphs = []

            for p in container.find_all(
                ["p", "h2", "h3"]
            ):

                text = clean_text(
                    p.get_text(
                        " ",
                        strip=True
                    )
                )

                if len(text) >= 35:

                    paragraphs.append(
                        text
                    )


            if paragraphs:

                text = "\n\n".join(
                    paragraphs
                )

                if len(text) >= 250:

                    return text[:8000]

        except Exception:
            pass


    # Fallback
    paragraphs = []

    for p in soup.find_all("p"):

        text = clean_text(
            p.get_text(
                " ",
                strip=True
            )
        )

        if len(text) >= 40:

            paragraphs.append(
                text
            )


    return "\n\n".join(
        paragraphs
    )[:8000]


# ============================================================
# CREATE LONG SUMMARY WITHOUT AI
# ============================================================

def create_summary(
    title,
    rss_description,
    article_text
):

    rss_description = clean_text(
        rss_description
    )

    article_text = clean_text(
        article_text
    )


    # Use article content first
    source_text = article_text

    if len(source_text) < 300:

        source_text = rss_description


    if not source_text:

        return (
            f"يتناول الخبر موضوع {title}. "
            "ويقدم أحدث المعلومات المتاحة حول هذا العمل أو الحدث الفني. "
            "وسيتم تحديث التفاصيل عند توفر معلومات إضافية من المصدر الأصلي."
        )


    # Split sentences
    sentences = re.split(
        r"(?<=[.!؟])\s+",
        source_text
    )


    selected = []

    total_length = 0


    for sentence in sentences:

        sentence = clean_text(
            sentence
        )

        if len(sentence) < 25:

            continue


        # Prevent duplicates
        if sentence in selected:

            continue


        selected.append(
            sentence
        )

        total_length += len(sentence)


        # Long summary
        if len(selected) >= 8:

            break

        if total_length >= 1400:

            break


    summary = " ".join(
        selected
    )


    # If text does not contain enough sentence separators
    if len(summary) < 500:

        words = source_text.split()

        summary = " ".join(
            words[:260]
        )


    # Add context only when necessary
    if len(summary) < 350:

        summary = (
            f"يتناول الخبر {title}. "
            f"{summary} "
            "وتبرز أهمية هذه التفاصيل بالنسبة لمتابعي الأفلام والمسلسلات، "
            "خصوصاً مع استمرار الإعلان عن أعمال جديدة وتطورات مرتبطة "
            "بالإنتاج أو العرض أو نجوم العمل. "
            "ولمعرفة التفاصيل الكاملة يمكن الرجوع إلى المصدر الأصلي للخبر."
        )


    return summary.strip()


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


        items = data.get(
            "items",
            []
        )


        if isinstance(
            items,
            list
        ):

            return items


    except Exception as error:

        print(
            "OLD NEWS ERROR:",
            error
        )


    return []


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "================================="
    )
    print(
        "MOVINS ARABIC MOVIE NEWS ENGINE"
    )
    print(
        "================================="
    )
    print()


    old_items = load_old_news()


    old_ids = {

        item.get("id")

        for item in old_items

        if item.get("id")

    }


    seen_titles = {

        normalize_title(
            item.get("title", "")
        )

        for item in old_items

        if item.get("title")

    }


    new_articles = []


    for source in RSS_FEEDS:

        print()
        print(
            "================================="
        )

        print(
            "FETCHING:",
            source["name"]
        )

        print(
            source["url"]
        )

        print(
            "================================="
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


            source_count = 0


            for entry in entries:

                if len(new_articles) >= MAX_NEWS:

                    break


                if source_count >= MAX_PER_SOURCE:

                    break


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


                link = entry.get(
                    "link",
                    ""
                ).strip()


                if not title or not link:

                    continue


                # Movie relevance
                if not is_movie_news(
                    title,
                    description
                ):

                    continue


                normalized = normalize_title(
                    title
                )


                if normalized in seen_titles:

                    print(
                        "SKIPPED DUPLICATE TITLE:",
                        title
                    )

                    continue


                article_id = make_id(
                    title,
                    link
                )


                if article_id in old_ids:

                    print(
                        "SKIPPED OLD ARTICLE:",
                        title
                    )

                    continue


                print()
                print(
                    "PROCESSING:",
                    title
                )


                # ----------------------------------------------
                # IMAGE FROM RSS
                # ----------------------------------------------

                image = get_rss_image(
                    entry
                )


                # ----------------------------------------------
                # ARTICLE PAGE
                # ----------------------------------------------

                soup, final_url = get_article_page(
                    link
                )


                article_text = ""

                if soup:

                    article_text = get_article_text(
                        soup
                    )


                    # Prefer article image if RSS image missing
                    if not is_valid_image(image):

                        article_image = get_article_image(
                            soup,
                            final_url or link
                        )


                        if is_valid_image(
                            article_image
                        ):

                            image = article_image


                # ----------------------------------------------
                # FALLBACK IMAGE
                # ----------------------------------------------

                if not is_valid_image(image):

                    print(
                        "NO IMAGE FOUND — USING MOVINS FALLBACK"
                    )


                    image = (
                        "https://images.unsplash.com/"
                        "photo-1489599849927-2ee91cede3ba"
                        "?auto=format&fit=crop&w=1400&q=85"
                    )


                # ----------------------------------------------
                # LONG SUMMARY
                # ----------------------------------------------

                summary = create_summary(
                    title,
                    description,
                    article_text
                )


                print(
                    "SUMMARY LENGTH:",
                    len(summary)
                )

                print(
                    "ARTICLE TEXT LENGTH:",
                    len(article_text)
                )

                print(
                    "IMAGE:",
                    image[:100]
                )


                # Minimum validation
                if len(summary) < 150:

                    print(
                        "SKIPPED — SUMMARY TOO SHORT"
                    )

                    continue


                item = {

                    "id": article_id,

                    "title": title,

                    "summary": summary,

                    "image": image,

                    "link": link,

                    "source": source["name"],

                    "category": source[
                        "category"
                    ],

                    "date": get_date(
                        entry
                    )

                }


                new_articles.append(
                    item
                )


                seen_titles.add(
                    normalized
                )

                old_ids.add(
                    article_id
                )


                source_count += 1


                print(
                    "ADDED SUCCESSFULLY"
                )


        except Exception as error:

            print(
                "SOURCE ERROR:",
                source["name"]
            )

            print(
                error
            )


    # ========================================================
    # MERGE OLD + NEW
    # ========================================================

    all_items = (

        new_articles

        +

        old_items

    )


    # Remove duplicates
    unique_items = []

    unique_ids = set()


    for item in all_items:

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


    # Keep only latest news
    unique_items = unique_items[
        :MAX_NEWS
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


    print()
    print(
        "================================="
    )

    print(
        "NEW MOVIE NEWS:",
        len(new_articles)
    )

    print(
        "TOTAL MOVIE NEWS:",
        len(unique_items)
    )

    print(
        "================================="
    )

    print()

    print(
        "MOVINS UPDATE FINISHED SUCCESSFULLY"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
