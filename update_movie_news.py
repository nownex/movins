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
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
}


# ============================================================
# MOVINS FALLBACK IMAGE
# ============================================================

FALLBACK_IMAGE = (
    "https://images.unsplash.com/"
    "photo-1489599849927-2ee91cede3ba"
    "?auto=format&fit=crop&w=1400&q=85"
)


# ============================================================
# ARABIC SOURCES
# ============================================================

RSS_FEEDS = [

    {
        "name": "في الفن",
        "url": "https://www.filfan.com/rss",
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "الشرق الأوسط - سينما",
        "url": "https://aawsat.com/feed/cinema",
        "category": "أفلام ومسلسلات"
    },

    {
        "name": "الشرق الأوسط - أنغام وفنون",
        "url": "https://aawsat.com/feed/arts",
        "category": "أفلام ومسلسلات"
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
    "إيرادات فيلم",

    "مسلسل",
    "مسلسلات",
    "دراما",

    "الحلقة",
    "حلقة",

    "نتفليكس",
    "netflix",

    "ديزني",
    "disney",

    "مارفل",
    "marvel",

    "هوليوود",
    "hollywood",

    "ممثل",
    "ممثلة",

    "مخرج",
    "إخراج",

    "تريلر",
    "برومو",

    "إعلان الفيلم",
    "إعلان المسلسل",

    "مهرجان سينمائي",
    "مهرجان الفيلم",

    "صناعة السينما",
    "التلفزيون"
]


# ============================================================
# BAD KEYWORDS — SPORTS / POLITICS / OTHER
# ============================================================

BAD_KEYWORDS = [

    # ==========================================
    # SPORTS
    # ==========================================

    "كرة القدم",
    "كرة السلة",
    "كرة اليد",
    "كرة الطائرة",

    "مباراة",
    "مباريات",

    "الدوري",
    "الدوري الإنجليزي",
    "الدوري الإسباني",
    "الدوري الإيطالي",
    "الدوري الفرنسي",

    "منتخب",
    "المنتخب",

    "لاعب",
    "لاعبين",
    "لاعبة",

    "مدرب",
    "تدريب",

    "هدف",
    "أهداف",

    "ركلة",
    "ركلات",

    "تنس",

    "رياضة",
    "رياضي",
    "رياضية",

    "بطولة رياضية",
    "بطولة التنس",

    "كأس العالم",
    "كأس أفريقيا",

    "فوز",
    "خسارة",
    "هزيمة",
    "تعادل",


    # ==========================================
    # POLITICS
    # ==========================================

    "سياسة",
    "سياسي",
    "سياسية",

    "انتخابات",
    "انتخاب",

    "رئيس الجمهورية",
    "الرئيس الأميركي",
    "الرئيس الأمريكي",

    "حكومة",

    "وزير",
    "وزارة",

    "برلمان",

    "دبلوماسي",
    "دبلوماسية",

    "علاقات دولية",

    "الحرب",

    "غزة",
    "أوكرانيا",

    "إسرائيل",
    "فلسطين",

    "البيت الأبيض",


    # ==========================================
    # ECONOMY
    # ==========================================

    "اقتصاد",
    "اقتصادية",

    "بورصة",

    "أسهم",

    "بنك مركزي",

    "نفط",

    "أسعار النفط",


    # ==========================================
    # OTHER
    # ==========================================

    "طقس",

    "زلزال",

    "فيضانات"
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

    title = clean_text(title).lower()

    description = clean_text(description).lower()

    text = f"{title} {description}"


    # ==========================================
    # REJECT SPORTS / POLITICS FIRST
    # ==========================================

    if any(
        keyword.lower() in text
        for keyword in BAD_KEYWORDS
    ):

        return False


    # ==========================================
    # REQUIRE MOVIE / SERIES KEYWORD
    # ==========================================

    movie_found = any(
        keyword.lower() in text
        for keyword in MOVIE_KEYWORDS
    )


    if not movie_found:

        return False


    return True


# ============================================================
# CREATE UNIQUE ID
# ============================================================

def make_id(title, link):

    value = (
        title.strip()
        + "|"
        + link.strip()
    ).encode("utf-8")

    return hashlib.md5(
        value
    ).hexdigest()


# ============================================================
# NORMALIZE TITLE
# ============================================================

def normalize_title(title):

    title = clean_text(
        title
    ).lower()

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

        or

        entry.get("updated")

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
# CHECK IMAGE URL
# ============================================================

def is_valid_image_url(url):

    if not url:

        return False

    url = str(url).strip()

    if not url.startswith(
        ("http://", "https://")
    ):

        return False

    lower = url.lower()

    bad_words = [

        "logo",
        "favicon",
        "avatar",
        "icon",
        "sprite",
        "placeholder",
        "blank",
        "default-image",
        "default_image",
        "loading.gif"

    ]

    if any(
        word in lower
        for word in bad_words
    ):

        return False

    return True


# ============================================================
# VERIFY IMAGE EXISTS
# ============================================================

def verify_image(url):

    if not is_valid_image_url(url):

        return False

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            stream=True,
            allow_redirects=True
        )

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        response.close()

        if response.status_code != 200:

            return False

        if "image" not in content_type:

            return False

        return True

    except Exception:

        return False


# ============================================================
# GET RSS IMAGE
# ============================================================

def get_rss_image(entry):

    candidates = []


    try:

        for item in entry.get(
            "media_content",
            []
        ):

            url = item.get(
                "url",
                ""
            )

            if url:

                candidates.append(url)

    except Exception:
        pass


    try:

        for item in entry.get(
            "media_thumbnail",
            []
        ):

            url = item.get(
                "url",
                ""
            )

            if url:

                candidates.append(url)

    except Exception:
        pass


    try:

        for item in entry.get(
            "enclosures",
            []
        ):

            url = (

                item.get("href")

                or

                item.get("url")

                or ""

            )

            if url:

                candidates.append(url)

    except Exception:
        pass


    try:

        image = entry.get(
            "image"
        )

        if isinstance(
            image,
            dict
        ):

            url = (

                image.get("href")

                or

                image.get("url")

                or ""

            )

            if url:

                candidates.append(url)

    except Exception:
        pass


    for url in candidates:

        if verify_image(url):

            return url


    return ""


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

        print(
            "ARTICLE HTTP:",
            response.status_code
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
            "ARTICLE ERROR:",
            error
        )

        return None, ""


# ============================================================
# GET SRCSET BEST IMAGE
# ============================================================

def get_best_srcset(srcset):

    if not srcset:

        return ""

    items = []

    for part in srcset.split(","):

        part = part.strip()

        if not part:

            continue

        pieces = part.split()

        url = pieces[0]

        width = 0

        if len(pieces) > 1:

            match = re.search(
                r"(\d+)w",
                pieces[1]
            )

            if match:

                width = int(
                    match.group(1)
                )

        items.append(
            (width, url)
        )

    if not items:

        return ""

    items.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return items[0][1]


# ============================================================
# EXTRACT ARTICLE IMAGE
# ============================================================

def get_article_image(soup, base_url):

    if not soup:

        return ""


    print(
        "SEARCHING FOR ORIGINAL ARTICLE IMAGE..."
    )


    meta_rules = [

        ("property", "og:image"),

        ("property", "og:image:url"),

        ("property", "og:image:secure_url"),

        ("name", "twitter:image"),

        ("property", "twitter:image"),

        ("name", "twitter:image:src"),

        ("name", "twitter:image:src")

    ]


    for attribute, value in meta_rules:

        tag = soup.find(
            "meta",
            attrs={
                attribute: value
            }
        )

        if not tag:

            continue

        image = tag.get(
            "content",
            ""
        ).strip()

        if not image:

            continue

        image = urljoin(
            base_url,
            image
        )

        print(
            "META IMAGE FOUND:",
            image[:120]
        )

        if verify_image(image):

            print(
                "ORIGINAL IMAGE VERIFIED"
            )

            return image


    images = soup.find_all(
        "img"
    )


    for img in images:

        candidates = [

            img.get("data-src"),

            img.get("data-lazy-src"),

            img.get("data-original"),

            img.get("data-image"),

            img.get("data-url"),

            get_best_srcset(
                img.get("data-srcset")
            ),

            get_best_srcset(
                img.get("srcset")
            ),

            img.get("src")

        ]


        for image in candidates:

            if not image:

                continue

            image = str(
                image
            ).strip()

            if not image:

                continue

            image = urljoin(
                base_url,
                image
            )

            if not is_valid_image_url(
                image
            ):

                continue


            width = img.get(
                "width"
            )

            height = img.get(
                "height"
            )

            try:

                if width and int(width) < 250:

                    continue

            except Exception:
                pass

            try:

                if height and int(height) < 150:

                    continue

            except Exception:
                pass


            if verify_image(image):

                print(
                    "ARTICLE IMAGE VERIFIED:",
                    image[:120]
                )

                return image


    return ""


# ============================================================
# EXTRACT ARTICLE TEXT
# ============================================================

def get_article_text(soup):

    if not soup:

        return ""


    for element in soup([

        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
        "button",
        "noscript"

    ]):

        try:

            element.decompose()

        except Exception:
            pass


    selectors = [

        "article",

        ".article-content",

        ".article-body",

        ".article__content",

        ".entry-content",

        ".post-content",

        ".content-body",

        ".news-content",

        ".post-body",

        ".single-content",

        ".article-details",

        "main"

    ]


    best_text = ""


    for selector in selectors:

        try:

            container = soup.select_one(
                selector
            )

            if not container:

                continue


            paragraphs = []


            for element in container.find_all([

                "p",
                "h2",
                "h3",
                "li"

            ]):

                text = clean_text(
                    element.get_text(
                        " ",
                        strip=True
                    )
                )

                if len(text) >= 30:

                    paragraphs.append(
                        text
                    )


            text = "\n\n".join(
                paragraphs
            )


            if len(text) > len(best_text):

                best_text = text


        except Exception:
            pass


    if len(best_text) >= 200:

        return best_text[:10000]


    paragraphs = []

    for p in soup.find_all("p"):

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


    return "\n\n".join(
        paragraphs
    )[:10000]


# ============================================================
# CREATE SUMMARY
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


    source_text = article_text

    if len(source_text) < 250:

        source_text = rss_description


    if not source_text:

        return (
            f"يتناول هذا الخبر {title}. "
            "ويعرض آخر المعلومات والتطورات المتعلقة بالأفلام أو المسلسلات "
            "أو صناعة الترفيه. ويمكن متابعة المصدر الأصلي للاطلاع على "
            "التفاصيل الكاملة والمعلومات الجديدة عند نشرها."
        )


    sentences = re.split(
        r"(?<=[.!؟])\s+",
        source_text
    )


    selected = []

    used = set()

    total = 0


    for sentence in sentences:

        sentence = clean_text(
            sentence
        )

        normalized = normalize_title(
            sentence
        )


        if len(sentence) < 25:

            continue


        if normalized in used:

            continue


        used.add(
            normalized
        )

        selected.append(
            sentence
        )

        total += len(
            sentence
        )


        if len(selected) >= 10:

            break


        if total >= 1600:

            break


    summary = " ".join(
        selected
    )


    if len(summary) < 450:

        words = source_text.split()

        summary = " ".join(
            words[:300]
        )


    if len(summary) < 250:

        summary = (
            f"يتناول الخبر موضوع {title}. "
            f"{summary} "
            "وتوضح المعلومات المنشورة أحدث التفاصيل المرتبطة بهذا الموضوع، "
            "سواء تعلق الأمر بعمل جديد أو موعد عرض أو تطورات تخص نجوم العمل "
            "أو الإنتاج أو صناعة السينما والتلفزيون."
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
    print("=" * 55)
    print("MOVINS ARABIC MOVIE NEWS ENGINE")
    print("=" * 55)
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
        print("=" * 55)

        print(
            "FETCHING:",
            source["name"]
        )

        print(
            source["url"]
        )

        print("=" * 55)


        try:

            response = requests.get(
                source["url"],
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            print(
                "RSS HTTP:",
                response.status_code
            )

            feed = feedparser.parse(
                response.content
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


                # ================================================
                # STRICT MOVIE / SERIES FILTER
                # ================================================

                if not is_movie_news(
                    title,
                    description
                ):

                    print(
                        "SKIPPED NON-MOVIE NEWS:",
                        title
                    )

                    continue


                normalized = normalize_title(
                    title
                )


                if normalized in seen_titles:

                    print(
                        "SKIPPED DUPLICATE:",
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
                print("-" * 55)
                print(
                    "PROCESSING:",
                    title
                )
                print("-" * 55)


                soup, final_url = get_article_page(
                    link
                )


                article_text = ""

                article_image = ""


                if soup:

                    article_text = get_article_text(
                        soup
                    )


                    article_image = get_article_image(

                        soup,

                        final_url or link

                    )


                rss_image = ""


                if not article_image:

                    print(
                        "NO ARTICLE IMAGE — TRYING RSS IMAGE"
                    )

                    rss_image = get_rss_image(
                        entry
                    )


                image = (

                    article_image

                    or

                    rss_image

                    or

                    FALLBACK_IMAGE

                )


                print()
                print(
                    "ARTICLE TEXT LENGTH:",
                    len(article_text)
                )

                print(
                    "SUMMARY SOURCE:",
                    "ARTICLE"
                    if len(article_text) >= 250
                    else "RSS"
                )

                print(
                    "FINAL IMAGE:",
                    image[:150]
                )


                summary = create_summary(

                    title,

                    description,

                    article_text

                )


                print(
                    "SUMMARY LENGTH:",
                    len(summary)
                )


                if len(summary) < 120:

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
    # MERGE NEW + OLD
    # ========================================================

    # يتم هنا أيضاً حذف الأخبار الرياضية والسياسية القديمة
    # الموجودة مسبقاً في movie-news.json

    clean_old_items = [

        item

        for item in old_items

        if is_movie_news(

            item.get("title", ""),

            item.get("summary", "")

        )

    ]


    all_items = (

        new_articles

        +

        clean_old_items

    )


    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

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


    # ========================================================
    # KEEP MAX NEWS
    # ========================================================

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
    print("=" * 55)

    print(
        "NEW MOVIE NEWS:",
        len(new_articles)
    )

    print(
        "TOTAL MOVIE NEWS:",
        len(unique_items)
    )

    print("=" * 55)

    print()


    if len(unique_items) == 0:

        print(
            "WARNING: NO NEWS AVAILABLE"
        )

    else:

        print(
            "MOVINS UPDATE FINISHED SUCCESSFULLY"
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
