import json
import os
import requests


# =========================================================
# MOVINS — FACEBOOK PUBLISHER
# =========================================================

TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not TOKEN:
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing")


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

                result.add(
                    str(item).strip()
                )


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
# THIS IS THE IMPORTANT PART
#
# Example:
#
# ?movie=tv-123
#
# or
#
# ?movie=movie-456
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
# GENRES
# =========================================================

def build_genres(item):

    genres = item.get(
        "genres",
        []
    )


    if isinstance(
        genres,
        list
    ):

        clean = []


        for genre in genres:

            text = str(
                genre
            ).strip()


            if text:

                clean.append(
                    text
                )


        return " • ".join(
            clean[:5]
        )


    return str(
        genres
    ).strip()


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

        hashtags = " ".join(
            str(x)
            for x in hashtags
        )


    hashtags = str(
        hashtags
    ).strip()


    if hashtags:

        return hashtags


    return (
        "#MOVINS #Movies #Series"
    )


# =========================================================
# FACEBOOK CAPTION
# =========================================================

def build_caption(item):

    title = str(
        item.get(
            "title"
        )
        or "بدون عنوان"
    ).strip()


    overview = str(
        item.get(
            "overview"
        )
        or "اكتشف القصة والتفاصيل على MOVINS."
    ).strip()


    detailed_type = str(
        item.get(
            "detailed_type"
        )
        or item.get(
            "type"
        )
        or "عمل"
    ).strip()


    year = str(
        item.get(
            "year"
        )
        or "—"
    ).strip()


    genres = build_genres(
        item
    )


    hashtags = build_hashtags(
        item
    )


    movie_url = get_movie_url(
        item
    )


    try:

        rating = float(
            item.get(
                "rating"
            )
            or 0
        )


        rating_text = (
            f"{rating:.1f}/10"
        )


    except (
        TypeError,
        ValueError
    ):

        rating_text = "—"


    lines = [

        f"🎬 {title}",

        "",

        overview,

        "",

        f"⭐ التقييم: {rating_text}",

        f"🎭 النوع: {detailed_type}",

        f"🎞️ التصنيف: {genres or 'غير محدد'}",

        f"📅 السنة: {year}",

        "",

        "🌐 اكتشف القصة والتفاصيل:",

        movie_url,

        "",

        hashtags

    ]


    return "\n".join(
        lines
    )


# =========================================================
# PUBLISH TO FACEBOOK
# =========================================================

def publish_to_facebook(item):

    poster = str(
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


    caption = build_caption(
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
        f"Direct URL: {get_movie_url(item)}"
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
                get_movie_key(item)
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
