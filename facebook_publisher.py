import json
import os
import requests


# =========================================================
# MOVINS — FACEBOOK PUBLISHER
# =========================================================

TOKEN = os.environ.get(
    "FACEBOOK_PAGE_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing"
    )


GRAPH_VERSION = "v26.0"

GRAPH_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}/me/photos"
)


MOVIES_FILE = "movies.json"

POSTED_FILE = "posted_movies.json"


# =========================================================
# SETTINGS
# =========================================================

# منشور واحد فقط في كل تشغيل
MAX_POSTS_PER_RUN = 1


# رابط موقع MOVINS
SITE_URL = (
    "https://nownex.github.io/movins/"
)


# =========================================================
# LOAD MOVIES
# =========================================================

def load_movies():

    if not os.path.exists(
        MOVIES_FILE
    ):
        raise RuntimeError(
            "movies.json not found"
        )

    with open(
        MOVIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return data.get(
        "items",
        []
    )


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

        if isinstance(
            data,
            list
        ):
            return set(
                str(x)
                for x in data
            )

    except Exception as error:

        print(
            "Posted file warning:",
            error
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
# GET ITEM KEY
# =========================================================

def get_item_key(item):

    """
    Use media type + TMDB ID.

    Example:

    فيلم 123
    مسلسل 123

    are treated as two different items.
    """

    item_id = item.get(
        "id"
    )

    item_type = (
        item.get("type")
        or ""
    )

    return (
        f"{item_type}:"
        f"{item_id}"
    )


# =========================================================
# BUILD FACEBOOK CAPTION
# =========================================================

def build_caption(item):

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    title = (
        item.get("title")
        or "بدون عنوان"
    )


    # -----------------------------------------------------
    # OVERVIEW
    # -----------------------------------------------------

    overview = (
        item.get("overview")
        or "لا يوجد ملخص متوفر حاليًا."
    )

    overview = str(
        overview
    ).strip()


    # -----------------------------------------------------
    # TYPE
    # -----------------------------------------------------

    detailed_type = (
        item.get("detailed_type")
        or item.get(
            "type",
            "عمل"
        )
    )

    detailed_type = str(
        detailed_type
    ).strip()


    # -----------------------------------------------------
    # GENRES
    # -----------------------------------------------------

    genres = item.get(
        "genres",
        []
    )


    if isinstance(
        genres,
        list
    ):

        clean_genres = [
            str(g).strip()
            for g in genres
            if str(g).strip()
        ]

        genre_text = (
            " • ".join(
                clean_genres[:5]
            )
            if clean_genres
            else "غير محدد"
        )

    else:

        genre_text = str(
            genres
        ).strip()

        if not genre_text:

            genre_text = (
                "غير محدد"
            )


    # -----------------------------------------------------
    # YEAR
    # -----------------------------------------------------

    year = (
        item.get("year")
        or "—"
    )


    # -----------------------------------------------------
    # RATING
    # -----------------------------------------------------

    try:

        rating = float(
            item.get(
                "rating"
            )
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        rating = 0


    # -----------------------------------------------------
    # TRAILER
    # -----------------------------------------------------

    trailer_url = str(
        item.get(
            "trailer_url"
        )
        or ""
    ).strip()


    # -----------------------------------------------------
    # HASHTAGS
    # -----------------------------------------------------

    hashtags = (
        item.get("hashtags")
        or "#MOVINS #Movies"
    )

    hashtags = str(
        hashtags
    ).strip()


    # =====================================================
    # BUILD POST
    # =====================================================

    caption_parts = [

        f"🎬 {title}",

        "",

        overview,

        "",

        f"⭐ التقييم: {rating:.1f}/10",

        f"🎭 النوع: {detailed_type}",

        f"🎞️ التصنيف: {genre_text}",

        f"📅 السنة: {year}",

        "",

        "🌐 اكتشف القصة والتفاصيل:",

        SITE_URL,

    ]


    # -----------------------------------------------------
    # TRAILER
    # -----------------------------------------------------

    if trailer_url:

        caption_parts.extend([

            "",

            "▶️ شاهد التريلر:",

            trailer_url,

        ])


    # -----------------------------------------------------
    # HASHTAGS
    # -----------------------------------------------------

    caption_parts.extend([

        "",

        hashtags,

    ])


    return "\n".join(
        caption_parts
    )


# =========================================================
# PUBLISH TO FACEBOOK
# =========================================================

def publish_to_facebook(item):

    # -----------------------------------------------------
    # POSTER
    # -----------------------------------------------------

    poster = (
        item.get("poster")
        or ""
    )


    if not poster:

        print(
            "SKIP: no poster"
        )

        return False


    # -----------------------------------------------------
    # CAPTION
    # -----------------------------------------------------

    caption = build_caption(
        item
    )


    # -----------------------------------------------------
    # PAYLOAD
    # -----------------------------------------------------

    payload = {

        "url":
            poster,

        "caption":
            caption,

        "published":
            "true",

        "access_token":
            TOKEN,
    }


    # -----------------------------------------------------
    # LOG
    # -----------------------------------------------------

    print(
        "--------------------------------------"
    )

    print(
        "Publishing to Facebook"
    )

    print(
        f"Title: "
        f"{item.get('title')}"
    )

    print(
        f"Type: "
        f"{item.get('detailed_type', item.get('type'))}"
    )

    print(
        f"Rating: "
        f"{item.get('rating')}"
    )

    print(
        f"Trailer: "
        f"{'YES' if item.get('trailer_url') else 'NO'}"
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


    # -----------------------------------------------------
    # FACEBOOK REQUEST
    # -----------------------------------------------------

    try:

        response = requests.post(
            GRAPH_URL,
            data=payload,
            timeout=60
        )

    except requests.RequestException as error:

        print(
            "Facebook connection error:"
        )

        print(
            error
        )

        return False


    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    if not response.ok:

        print(
            "Facebook API Error:"
        )

        print(
            response.text
        )

        return False


    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

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


    post_id = (
        result.get(
            "post_id"
        )
        or result.get(
            "id"
        )
    )


    print(
        "Facebook post successful."
    )

    print(
        "Post ID:",
        post_id
    )


    return True


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # LOAD
    # -----------------------------------------------------

    movies = load_movies()

    posted = load_posted()


    print(
        f"MOVINS items: "
        f"{len(movies)}"
    )


    print(
        f"Already posted: "
        f"{len(posted)}"
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

        item_id = item.get(
            "id"
        )


        if not item_id:

            continue


        item_key = get_item_key(
            item
        )


        if item_key not in posted:

            new_items.append(
                item
            )


    print(
        f"New items: "
        f"{len(new_items)}"
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

            item_key = get_item_key(
                item
            )


            posted.add(
                item_key
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
