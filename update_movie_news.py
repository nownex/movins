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
        "application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
}


# ============================================================
# FALLBACK IMAGE
# ============================================================

FALLBACK_IMAGE = (
    "https://images.unsplash.com/"
    "photo-1489599849927-2ee91cede3ba"
    "?auto=format&fit=crop&w=1400&q=85"
)


# ============================================================
# SOURCES
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
# MOVIE KEYWORDS
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

    "حلقة",
    "الحلقة",

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

    "التلفزيون",
    "منصة عرض"
]


# ============================================================
# BAD KEYWORDS
# ============================================================

BAD_KEYWORDS = [

    "كرة القدم",
    "كرة السلة",
    "كرة اليد",
    "كرة الطائرة",

    "مباراة",
    "مباريات",

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

    "ركلة",
    "ركلات",

    "تنس",

    "بطولة رياضية",

    "سياسة",
    "سياسي",
    "سياسية",

    "انتخابات",

    "رئيس الجمهورية",

    "حكومة",

    "وزير",
    "وزارة",

    "برلمان",

    "دبلوماسي",

    "الحرب",

    "غزة",
    "أوكرانيا",

    "إسرائيل",
    "فلسطين",

    "البيت الأبيض",

    "بورصة",

    "بنك مركزي",

    "أسعار النفط",

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
# NORMALIZE ARABIC TEXT
# ============================================================

def normalize_text(text):

    text = clean_text(text).lower()

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه"
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    text = re.sub(
        r"[ًٌٍَُِّْـ]",
        "",
        text
    )

    text = re.sub(
        r"[^\w\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# NORMALIZE TITLE
# ============================================================

def normalize_title(title):

    return normalize_text(title)


# ============================================================
# CHECK MOVIE NEWS
# ============================================================

def is_movie_news(title, description):

    title = clean_text(title).lower()
    description = clean_text(description).lower()

    text = f"{title} {description}"

    movie_count = sum(
        1
        for keyword in MOVIE_KEYWORDS
        if keyword.lower() in text
    )

    bad_count = sum(
        1
        for keyword in BAD_KEYWORDS
        if keyword.lower() in text
    )

    # إذا كان هناك محتوى سيئ واضح
    if bad_count >= 2 and movie_count == 0:

        return False

    # يجب وجود كلمة واحدة على الأقل
    if movie_count == 0:

        return False

    return True


# ============================================================
# CREATE ID
# ============================================================

def make_id(title, link):

    value = (
        normalize_title(title)
        + "|"
        + link.strip()
    ).encode("utf-8")

    return hashlib.md5(
        value
    ).hexdigest()


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
# IMAGE VALIDATION
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
# VERIFY IMAGE
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

        status = response.status_code

        response.close()

        if status != 200:

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


    for key in [

        "media_content",
        "media_thumbnail",
        "enclosures"

    ]:

        try:

            for item in entry.get(key, []):

                url = (

                    item.get("url")

                    or item.get("href")

                    or ""
                )

                if url:

                    candidates.append(url)

        except Exception:

            pass


    try:

        image = entry.get("image")

        if isinstance(image, dict):

            url = (

                image.get("href")

                or image.get("url")

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
# GET BEST SRCSET IMAGE
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
# ARTICLE IMAGE
# ============================================================

def get_article_image(soup, base_url):

    if not soup:

        return ""

    meta_rules = [

        ("property", "og:image"),

        ("property", "og:image:url"),

        ("name", "twitter:image"),

        ("property", "twitter:image"),

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

        if verify_image(image):

            return image


    return ""


# ============================================================
# REMOVE NON ARTICLE CONTENT
# ============================================================

def remove_junk(soup):

    junk_tags = [

        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
        "button",
        "noscript",
        "iframe",
        "svg"
    ]


    for tag in soup(junk_tags):

        try:

            tag.decompose()

        except Exception:

            pass


    junk_words = [

        "related",
        "recommend",
        "sidebar",
        "advert",
        "advertisement",
        "latest",
        "popular",
        "more-news",
        "most-read",

        "ذات صلة",
        "أخبار ذات صلة",
        "الأكثر قراءة",
        "اقرأ أيضا",
        "إعلانات",
        "أحدث الأخبار",
        "مواضيع ذات صلة"
    ]


    for element in soup.find_all(True):

        try:

            classes = " ".join(
                element.get(
                    "class",
                    []
                )
            ).lower()

            element_id = (
                element.get(
                    "id",
                    ""
                )
            ).lower()

            attrs = (
                classes
                + " "
                + element_id
            )

            if any(
                word.lower() in attrs
                for word in junk_words
            ):

                element.decompose()

        except Exception:

            pass


# ============================================================
# GET CLEAN PARAGRAPHS
# ============================================================

def extract_paragraphs(container):

    paragraphs = []

    seen = set()


    for element in container.find_all(
        ["p"]
    ):

        text = clean_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        if len(text) < 40:

            continue

        normalized = normalize_text(
            text
        )

        if normalized in seen:

            continue

        seen.add(normalized)

        paragraphs.append(text)


    return paragraphs


# ============================================================
# CHECK TEXT RELEVANCE TO TITLE
# ============================================================

def text_matches_title(title, text):

    title_words = [

        word

        for word in normalize_text(title).split()

        if len(word) >= 4
    ]


    if not title_words:

        return True


    text_normalized = normalize_text(
        text
    )


    matches = sum(

        1

        for word in title_words

        if word in text_normalized

    )


    # يكفي ظهور كلمة مهمة من العنوان
    if len(title_words) <= 3:

        return matches >= 1


    # العناوين الطويلة يجب أن تتطابق أكثر
    return matches >= 2


# ============================================================
# EXTRACT ARTICLE TEXT — STRICT VERSION
# ============================================================

def get_article_text(soup, title):

    if not soup:

        return ""


    # نعمل على نسخة مستقلة
    soup = BeautifulSoup(
        str(soup),
        "html.parser"
    )


    remove_junk(soup)


    # لا نستخدم main مباشرة إلا كخيار أخير
    selectors = [

        "article",

        "[itemprop='articleBody']",

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

        ".article-text",

        ".story-content",

        ".field-name-body",

        ".field--name-body"
    ]


    candidates = []


    for selector in selectors:

        try:

            containers = soup.select(
                selector
            )

            for container in containers:

                paragraphs = extract_paragraphs(
                    container
                )

                if len(paragraphs) < 2:

                    continue

                text = "\n\n".join(
                    paragraphs
                )

                if len(text) < 180:

                    continue

                score = len(text)


                if text_matches_title(
                    title,
                    text
                ):

                    score += 10000


                candidates.append(
                    (score, text)
                )

        except Exception:

            pass


    # اختيار أفضل عنصر فقط
    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

        best_text = candidates[0][1]

        return best_text[:7000]


    # FALLBACK محدود جداً
    paragraphs = []


    for p in soup.find_all("p"):

        text = clean_text(
            p.get_text(
                " ",
                strip=True
            )
        )

        if len(text) < 50:

            continue

        paragraphs.append(text)

        # نأخذ عدداً محدوداً جداً
        if len(paragraphs) >= 8:

            break


    text = "\n\n".join(
        paragraphs
    )


    # إذا لم يكن له علاقة بالعنوان نرفضه
    if text and not text_matches_title(
        title,
        text
    ):

        return ""


    return text[:5000]


# ============================================================
# CREATE SAFE SUMMARY
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


    # ==========================================
    # RSS DESCRIPTION HAS PRIORITY
    # لأنه مرتبط مباشرة بالخبر
    # ==========================================

    if len(rss_description) >= 120:

        source_text = rss_description

    elif (

        len(article_text) >= 200

        and text_matches_title(
            title,
            article_text
        )

    ):

        source_text = article_text

    else:

        source_text = rss_description


    if not source_text:

        return (
            f"يتناول الخبر {title}. "
            "ويكشف عن أحدث المعلومات والتطورات المرتبطة بهذا العمل "
            "في عالم الأفلام والمسلسلات والترفيه."
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

        if len(sentence) < 25:

            continue

        normalized = normalize_text(
            sentence
        )

        if normalized in used:

            continue

        used.add(normalized)

        selected.append(sentence)

        total += len(sentence)


        # لا نريد ملخصاً ضخماً
        if len(selected) >= 5:

            break


        if total >= 900:

            break


    summary = " ".join(
        selected
    )


    # في حالة عدم وجود علامات ترقيم جيدة
    if len(summary) < 100:

        words = source_text.split()

        summary = " ".join(
            words[:180]
        )


    if len(summary) < 80:

        summary = (
            f"يتناول الخبر {title}. "
            f"{summary}"
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


        if isinstance(items, list):

            return items


    except Exception as error:

        print(
            "OLD NEWS ERROR:",
            error
        )


    return []


# ============================================================
# SORT DATE
# ============================================================

def date_sort_key(item):

    date = item.get(
        "date",
        ""
    )

    try:

        return datetime.fromisoformat(
            date.replace(
                "Z",
                "+00:00"
            )
        )

    except Exception:

        return datetime.min.replace(
            tzinfo=timezone.utc
        )


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


            if response.status_code != 200:

                continue


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
                # MOVIE FILTER
                # ================================================

                if not is_movie_news(
                    title,
                    description
                ):

                    print(
                        "SKIPPED NON-MOVIE:",
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
                        "SKIPPED OLD:",
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

                    # استخراج النص مع العنوان للتحقق
                    article_text = get_article_text(
                        soup,
                        title
                    )


                    article_image = get_article_image(

                        soup,

                        final_url or link

                    )


                # ================================================
                # RSS IMAGE
                # ================================================

                rss_image = ""


                if not article_image:

                    rss_image = get_rss_image(
                        entry
                    )


                image = (

                    article_image

                    or rss_image

                    or FALLBACK_IMAGE

                )


                # ================================================
                # SUMMARY
                # ================================================

                summary = create_summary(

                    title,

                    description,

                    article_text

                )


                print(
                    "RSS LENGTH:",
                    len(description)
                )

                print(
                    "ARTICLE LENGTH:",
                    len(article_text)
                )

                print(
                    "SUMMARY LENGTH:",
                    len(summary)
                )


                if len(summary) < 80:

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

            print()
            print(
                "SOURCE ERROR:",
                source["name"]
            )

            print(
                error
            )


    # ========================================================
    # CLEAN OLD NEWS
    # ========================================================

    clean_old_items = [

        item

        for item in old_items

        if is_movie_news(

            item.get("title", ""),

            item.get("summary", "")

        )

    ]


    # ========================================================
    # MERGE
    # ========================================================

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

    unique_titles = set()


    for item in all_items:

        item_id = item.get(
            "id"
        )

        title = normalize_title(
            item.get(
                "title",
                ""
            )
        )


        if not item_id:

            continue


        if item_id in unique_ids:

            continue


        if title in unique_titles:

            continue


        unique_ids.add(
            item_id
        )

        unique_titles.add(
            title
        )

        unique_items.append(
            item
        )


    # ========================================================
    # SORT NEWEST FIRST
    # ========================================================

    unique_items.sort(

        key=date_sort_key,

        reverse=True

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
