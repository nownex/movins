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


# One Facebook post per workflow run
MAX_POSTS_PER_RUN = 1


# =========================================================
# MOVINS WEBSITE
# =========================================================

MOVINS_URL = (
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
# BUILD MOVINS MOVIE URL
# =========================================================

def build_movie_url(item):

    item_id = item.get(
        "id"
    )


    if not item_id:

        return MOVINS_URL


    item_type = (
        item.get(
            "type"
        )
        or ""
    )


    if item_type == "فيلم":

        media_type = "movie"

    elif item_type == "مسلسل":

        media_type = "tv"

    else:

        media_type = "movie"


    return (
        MOVINS_URL
        + "?type="
        + media_type
        + "&id="
        + str(item_id)
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


    # =====================================================
    # MOVINS URL
    # =====================================================

    movie_url = build_movie_url(
        item
    )


    # =====================================================
    # FACEBOOK CAPTION
    # =====================================================

    caption = f"""🎬 {title}

{overview}

⭐ التقييم: {rating:.1f}/10
🎭 النوع: {detailed_type}
🎞️ التصنيف: {genre_text}
📅 السنة: {year}

🎬 شاهد التريلر واكتشف القصة والتفاصيل داخل MOVINS:
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
        "Publishing to Facebook:"
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
        f"MOVINS URL: "
        f"{build_movie_url(item)}"
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

    response = requests.post(
        GRAPH_URL,
        data=payload,
        timeout=60
    )


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


        response.raise_for_status()


    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    result = response.json()


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


        if str(
            item_id
        ) not in posted:

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


        try:

            success = (
                publish_to_facebook(
                    item
                )
            )


        except Exception as error:

            print(
                "Publish error:"
            )

            print(
                error
            )

            success = False


        if success:

            posted.add(
                str(
                    item["id"]
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
