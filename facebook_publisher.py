import json
import os
import requests


# =========================================================
# MOVINS — FACEBOOK PUBLISHER
# =========================================================

TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing"
    )


GRAPH_VERSION = "v26.0"

GRAPH_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}/me/photos"
)


# =========================================================
# FILES
# =========================================================

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movies.json"


# =========================================================
# MOVINS WEBSITE
# =========================================================

SITE_URL = "https://nownex.github.io/movins/"


# =========================================================
# SETTINGS
# =========================================================

MAX_POSTS_PER_RUN = 1

# أقصى طول للملخص داخل منشور فيسبوك
MAX_OVERVIEW_LENGTH = 420


# =========================================================
# LOAD MOVIES
# =========================================================

def load_movies():

    if not os.path.exists(MOVIES_FILE):
        raise RuntimeError(
            "movies.json not found"
        )

    with open(
        MOVIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    items = data.get(
        "items",
        []
    )

    if not isinstance(
        items,
        list
    ):

        raise RuntimeError(
            "movies.json items must be a list"
        )

    return items


# =========================================================
# LOAD POSTED
# =========================================================

def load_posted():

    if not os.path.exists(
        POSTED_FILE
    ):

        return set()

    try:

        with open(
            POSTED_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(
            data,
            list
        ):

            return set()

        result = set()

        for item in data:

            if isinstance(
                item,
                dict
            ):

                item_id = str(
                    item.get(
                        "id",
                        ""
                    )
                ).strip()

                item_type = str(
                    item.get(
                        "type",
                        ""
                    )
                ).strip()

                if item_id:

                    result.add(
                        f"{item_type}:{item_id}"
                    )

            else:

                value = str(
                    item
                ).strip()

                if value:
                    result.add(value)

        return result

    except Exception as e:

        print(
            f"WARNING: could not read "
            f"{POSTED_FILE}: {e}"
        )

        return set()


# =========================================================
# SAVE POSTED
# =========================================================

def save_posted(posted):

    with open(
        POSTED_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            sorted(
                list(posted)
            ),
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# MEDIA TYPE
# =========================================================

def get_media_type(item):

    item_type = str(
        item.get(
            "type",
            ""
        )
    ).strip().lower()

    if item_type in (
        "فيلم",
        "movie",
        "film"
    ):

        return "movie"

    return "tv"


# =========================================================
# MOVIE ID
# =========================================================

def get_movie_id(item):

    return str(
        item.get(
            "id",
            ""
        )
    ).strip()


# =========================================================
# UNIQUE MOVIE KEY
# =========================================================

def get_movie_key(item):

    movie_id = get_movie_id(
        item
    )

    if not movie_id:
        return ""

    media_type = get_media_type(
        item
    )

    return (
        f"{media_type}:{movie_id}"
    )


# =========================================================
# DIRECT MOVIE URL
#
# IMPORTANT:
#
# Facebook receives the exact movie URL.
#
# Example:
#
# https://nownex.github.io/movins/?movie=tv-123
#
# https://nownex.github.io/movins/?movie=movie-456
#
# =========================================================

def get_movie_url(item):

    movie_id = get_movie_id(
        item
    )

    if not movie_id:
        return SITE_URL

    media_type = get_media_type(
        item
    )

    return (
        SITE_URL
        + "?movie="
        + media_type
        + "-"
        + movie_id
    )


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(value):

    if value is None:
        return ""

    text = str(value)

    # إزالة المسافات الزائدة
    text = " ".join(
        text.split()
    )

    return text.strip()


# =========================================================
# SHORT OVERVIEW
# =========================================================

def build_short_overview(item):

    overview = clean_text(
        item.get(
            "overview",
            ""
        )
    )

    if not overview:

        return (
            "اكتشف قصة هذا العمل "
            "وتفاصيله على MOVINS."
        )

    if len(overview) <= MAX_OVERVIEW_LENGTH:

        return overview

    shortened = overview[
        :MAX_OVERVIEW_LENGTH
    ]

    # لا نقطع الكلمة الأخيرة
    if " " in shortened:

        shortened = shortened.rsplit(
            " ",
            1
        )[0]

    return shortened + "..."


# =========================================================
# GENRES
# =========================================================

def get_genres_list(item):

    genres = item.get(
        "genres",
        []
    )

    if isinstance(
        genres,
        list
    ):

        result = []

        for genre in genres:

            value = clean_text(
                genre
            )

            if value:

                result.append(
                    value
                )

        return result

    value = clean_text(
        genres
    )

    if value:
        return [value]

    return []


# =========================================================
# GENRES FOR DISPLAY
# =========================================================

def build_genres(item):

    genres = get_genres_list(
        item
    )

    if not genres:
        return ""

    return " • ".join(
        genres[:3]
    )


# =========================================================
# HASHTAGS
# =========================================================

def build_hashtags(item):

    hashtags = item.get(
        "hashtags",
        ""
    )

    if isinstance(
        hashtags,
        list
    ):

        cleaned = []

        for value in hashtags:

            value = clean_text(
                value
            )

            if value:

                cleaned.append(
                    value
                )

        hashtags = " ".join(
            cleaned
        )

    hashtags = clean_text(
        hashtags
    )

    # إذا كانت البيانات تحتوي على هاشتاغات
    if hashtags:

        # لا نريد عددًا ضخمًا من الهاشتاغات
        parts = hashtags.split()

        cleaned_parts = []

        for part in parts:

            if part.startswith("#"):

                cleaned_parts.append(
                    part
                )

        if cleaned_parts:

            return " ".join(
                cleaned_parts[:5]
            )

    # هاشتاغات افتراضية نظيفة
    return (
        "#MOVINS #أفلام #مسلسلات"
    )


# =========================================================
# RATING
# =========================================================

def get_rating(item):

    try:

        rating = float(
            item.get(
                "rating"
            ) or 0
        )

        if rating <= 0:
            return "—"

        return f"{rating:.1f}/10"

    except (
        TypeError,
        ValueError
    ):

        return "—"


# =========================================================
# FACEBOOK CAPTION
#
# الهدف:
#
# 1. عنوان واضح
# 2. Hook قصير
# 3. ملخص مشوق
# 4. التقييم
# 5. النوع
# 6. دعوة للنقر
# 7. الرابط المباشر للبطاقة
# =========================================================

def build_caption(item):

    title = clean_text(
        item.get(
            "title"
        )
        or "بدون عنوان"
    )

    overview = build_short_overview(
        item
    )

    detailed_type = clean_text(
        item.get(
            "detailed_type"
        )
        or item.get(
            "type"
        )
        or "عمل"
    )

    year = clean_text(
        item.get(
            "year"
        )
        or "—"
    )

    genres = build_genres(
        item
    )

    rating = get_rating(
        item
    )

    movie_url = get_movie_url(
        item
    )

    hashtags = build_hashtags(
        item
    )


    # -----------------------------------------------------
    # اختيار نوع افتتاحية مناسبة
    # -----------------------------------------------------

    if detailed_type:

        hook = (
            f"هل يستحق {title} المشاهدة؟ "
            "اكتشف القصة والتفاصيل قبل أن تبدأ."
        )

    else:

        hook = (
            "اكتشف القصة والتفاصيل قبل المشاهدة."
        )


    # -----------------------------------------------------
    # المنشور النهائي
    # -----------------------------------------------------

    lines = [

        f"🎬 {title}",

        "",

        hook,

        "",

        overview,

        "",

        f"⭐ التقييم: {rating}",

        f"🎭 {detailed_type}",

        (
            f"🎞️ {genres}"
            if genres
            else ""
        ),

        (
            f"📅 {year}"
            if year and year != "—"
            else ""
        ),

        "",

        "👀 تريد معرفة المزيد؟",

        "اكتشف القصة الكاملة والتفاصيل والتريلر على MOVINS 👇",

        "",

        movie_url,

        "",

        hashtags

    ]


    # إزالة الأسطر الفارغة المتكررة
    final_lines = []

    previous_empty = False

    for line in lines:

        if line == "":

            if previous_empty:
                continue

            previous_empty = True

        else:

            previous_empty = False

        final_lines.append(
            line
        )


    return "\n".join(
        final_lines
    )


# =========================================================
# PUBLISH TO FACEBOOK
# =========================================================

def publish_to_facebook(item):

    poster = clean_text(
        item.get(
            "poster"
        )
        or ""
    )

    if not poster:

        print(
            "SKIP: no poster"
        )

        return False


    caption = build_caption(
        item
    )


    movie_url = get_movie_url(
        item
    )


    payload = {

        "url":
            poster,

        "caption":
            caption,

        "published":
            "true",

        "access_token":
            TOKEN

    }


    print(
        "--------------------------------------"
    )

    print(
        "Publishing to Facebook"
    )

    print(
        f"Title: {item.get('title', '')}"
    )

    print(
        f"ID: {item.get('id', '')}"
    )

    print(
        f"Direct movie URL: {movie_url}"
    )

    print(
        "--------------------------------------"
    )

    print(
        "Caption:"
    )

    print(
        caption
    )

    print(
        "--------------------------------------"
    )


    try:

        response = requests.post(

            GRAPH_URL,

            data=payload,

            timeout=60

        )

    except requests.RequestException as e:

        print(
            f"Facebook request error: {e}"
        )

        return False


    try:

        result = response.json()

    except ValueError:

        print(
            "Facebook returned invalid JSON:"
        )

        print(
            response.text
        )

        return False


    if not response.ok:

        print(
            "Facebook API Error:"
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )

        return False


    print(
        "Facebook post successful."
    )

    print(
        "Post ID:",
        result.get(
            "post_id"
        )
        or result.get(
            "id"
        )
    )


    return True


# =========================================================
# MAIN
# =========================================================

def main():

    movies = load_movies()

    posted = load_posted()


    print(
        f"MOVINS items: {len(movies)}"
    )

    print(
        f"Already posted: {len(posted)}"
    )


    # -----------------------------------------------------
    # NEWEST FIRST
    # -----------------------------------------------------

    movies.sort(

        key=lambda item:
            item.get(
                "updated_at",
                ""
            ),

        reverse=True

    )


    # -----------------------------------------------------
    # FIND NEW ITEMS
    # -----------------------------------------------------

    new_items = []


    for item in movies:

        movie_key = get_movie_key(
            item
        )

        if not movie_key:

            continue


        if movie_key not in posted:

            new_items.append(
                item
            )


    print(
        f"New items: {len(new_items)}"
    )


    # -----------------------------------------------------
    # NOTHING NEW
    # -----------------------------------------------------

    if not new_items:

        print(
            "Nothing new to publish."
        )

        return


    # -----------------------------------------------------
    # PUBLISH
    # -----------------------------------------------------

    published_count = 0


    for item in new_items:

        if (
            published_count
            >= MAX_POSTS_PER_RUN
        ):

            break


        success = publish_to_facebook(
            item
        )


        if success:

            posted.add(
                get_movie_key(
                    item
                )
            )


            save_posted(
                posted
            )


            published_count += 1


    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    print(
        f"Published this run: "
        f"{published_count}"
    )

    print(
        "MOVINS Facebook publisher finished."
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
