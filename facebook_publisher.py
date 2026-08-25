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


# =========================================================
# FACEBOOK GRAPH API
# =========================================================

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
# SETTINGS
# =========================================================

# One Facebook post per workflow run.
MAX_POSTS_PER_RUN = 1


# Your MOVINS website.
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

        data = json.load(
            file
        )


    items = data.get(
        "items",
        []
    )


    if not isinstance(
        items,
        list
    ):

        raise RuntimeError(
            "Invalid movies.json format"
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

            data = json.load(
                file
            )


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
            "WARNING: Could not read posted_movies.json:",
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
    Create a unique identifier.

    Example:

    movie-123
    tv-123

    This prevents a movie and a TV show
    with the same TMDB ID from colliding.
    """

    item_id = item.get(
        "id"
    )


    if not item_id:
        return ""


    item_type = (
        item.get("type")
        or ""
    ).strip()


    if item_type == "مسلسل":

        return (
            f"tv-{item_id}"
        )


    return (
        f"movie-{item_id}"
    )


# =========================================================
# GET URL TYPE
# =========================================================

def get_url_type(item):

    item_type = (
        item.get("type")
        or ""
    ).strip()


    if item_type == "مسلسل":

        return "tv"


    return "movie"


# =========================================================
# BUILD DIRECT MOVIE URL
# =========================================================

def build_movie_url(item):

    item_id = item.get(
        "id"
    )


    if not item_id:

        return SITE_URL


    media_type =
        get_url_type(item)


    return (
        f"{SITE_URL}"
        f"?movie={item_id}"
        f"&type={media_type}"
    )


# =========================================================
# BUILD FACEBOOK CAPTION
# =========================================================

def build_caption(item):

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    title = (
        item.get(
            "title"
        )
        or "بدون عنوان"
    )


    # -----------------------------------------------------
    # OVERVIEW
    # -----------------------------------------------------

    overview = (
        item.get(
            "overview"
        )
        or "لا يوجد ملخص متوفر حاليًا."
    )


    overview = str(
        overview
    ).strip()


    # -----------------------------------------------------
    # TYPE
    # -----------------------------------------------------

    detailed_type = (
        item.get(
            "detailed_type"
        )
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
        item.get(
            "year"
        )
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
    # HASHTAGS
    # -----------------------------------------------------

    hashtags = (
        item.get(
            "hashtags"
        )
        or "#MOVINS #Movies"
    )


    hashtags = str(
        hashtags
    ).strip()


    # -----------------------------------------------------
    # DIRECT MOVIE PAGE
    # -----------------------------------------------------

    movie_url =
        build_movie_url(item)


    # =====================================================
    # FACEBOOK POST
    # =====================================================

    caption = f"""🎬 {title}

{overview}

⭐ التقييم: {rating:.1f}/10
🎭 النوع: {detailed_type}
🎞️ التصنيف: {genre_text}
📅 السنة: {year}

🌐 شاهد القصة والتفاصيل والتريلر:
{movie_url}

{hashtags}
"""


    return caption


# =========================================================
# PUBLISH TO FACEBOOK
# =========================================================

def publish_to_facebook(item):

    # -----------------------------------------------------
    # POSTER
    # -----------------------------------------------------

    poster = (
        item.get(
            "poster"
        )
        or ""
    ).strip()


    if not poster:

        print(
            "SKIP: no poster"
        )

        return False


    # -----------------------------------------------------
    # DIRECT MOVIE URL
    # -----------------------------------------------------

    movie_url =
        build_movie_url(item)


    # -----------------------------------------------------
    # CAPTION
    # -----------------------------------------------------

    caption =
        build_caption(item)


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
        "======================================"
    )

    print(
        "MOVINS — FACEBOOK PUBLISH"
    )

    print(
        "======================================"
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
        f"TMDB ID: "
        f"{item.get('id')}"
    )


    print(
        f"Website URL: "
        f"{movie_url}"
    )


    print(
        f"Rating: "
        f"{item.get('rating')}"
    )


    print(
        "--------------------------------------"
    )


    print(
        "Facebook Caption:"
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

        result =
            response.json()

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
        "======================================"
    )

    print(
        "Facebook post successful."
    )


    print(
        f"Post ID: "
        f"{post_id}"
    )


    print(
        f"Movie URL: "
        f"{movie_url}"
    )


    print(
        "======================================"
    )


    return True


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "======================================"
    )

    print(
        "MOVINS FACEBOOK PUBLISHER STARTED"
    )

    print(
        "======================================"
    )


    # -----------------------------------------------------
    # LOAD DATA
    # -----------------------------------------------------

    movies =
        load_movies()


    posted =
        load_posted()


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

        item_id =
            item.get("id")


        if not item_id:

            continue


        item_key =
            get_item_key(item)


        if not item_key:

            continue


        # -------------------------------------------------
        # NEW FORMAT
        # -------------------------------------------------

        if item_key in posted:

            continue


        # -------------------------------------------------
        # BACKWARD COMPATIBILITY
        #
        # Your old posted_movies.json may contain:
        #
        # 123
        #
        # instead of:
        #
        # movie-123
        #
        # So we also check the old format.
        # -------------------------------------------------

        if str(item_id) in posted:

            continue


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

        print(
            "MOVINS Facebook publisher finished."
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


        success =
            publish_to_facebook(
                item
            )


        if success:

            item_key =
                get_item_key(
                    item
                )


            posted.add(
                item_key
            )


            save_posted(
                posted
            )


            published_count += 1


            print(
                f"Saved as posted: "
                f"{item_key}"
            )


    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    print(
        "======================================"
    )


    print(
        f"Published this run: "
        f"{published_count}"
    )


    print(
        "MOVINS Facebook publisher finished."
    )


    print(
        "======================================"
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
