import json
import os
import requests
import time


# =========================================================
# MOVINS — INSTAGRAM PUBLISHER
# =========================================================

TOKEN = os.environ.get(
    "INSTAGRAM_ACCESS_TOKEN"
)

IG_USER_ID = os.environ.get(
    "INSTAGRAM_USER_ID"
)


if not TOKEN:

    raise RuntimeError(
        "INSTAGRAM_ACCESS_TOKEN is missing"
    )


if not IG_USER_ID:

    raise RuntimeError(
        "INSTAGRAM_USER_ID is missing"
    )


GRAPH_VERSION = "v26.0"

GRAPH_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}"
)


# =========================================================
# FILES
# =========================================================

MOVIES_FILE = "movies.json"

POSTED_FILE = (
    "instagram_posted_movies.json"
)

ROTATION_FILE = (
    "instagram_rotation.json"
)


# =========================================================
# MOVINS WEBSITE
# =========================================================

SITE_URL = (
    "https://nownex.github.io/movins/"
)


# =========================================================
# SETTINGS
# =========================================================

MAX_OVERVIEW_LENGTH = 300


# =========================================================
# INSTAGRAM ROTATION
# =========================================================

ROTATION_SEQUENCE = [

    {
        "type": "movie",
        "genre": "رعب"
    },

    {
        "type": "tv",
        "genre": "أكشن"
    },

    {
        "type": "movie",
        "genre": "كوميديا"
    },

    {
        "type": "tv",
        "genre": "دراما"
    },

    {
        "type": "movie",
        "genre": "خيال علمي"
    },

    {
        "type": "tv",
        "genre": "غموض"
    },

    {
        "type": "movie",
        "genre": "جريمة"
    },

    {
        "type": "tv",
        "genre": "مغامرة"
    },

    {
        "type": "movie",
        "genre": "فانتازيا"
    },

    {
        "type": "tv",
        "genre": "رومانسي"
    },

    {
        "type": "movie",
        "genre": "رسوم متحركة"
    },

    {
        "type": "tv",
        "genre": "إثارة"
    },

]


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

            data = json.load(
                file
            )


        if not isinstance(
            data,
            list
        ):

            return set()


        return set(
            str(value).strip()
            for value in data
            if str(value).strip()
        )


    except Exception as error:

        print(
            f"WARNING: could not read "
            f"{POSTED_FILE}: {error}"
        )

        return set()


# =========================================================
# SAVE POSTED
# =========================================================

def save_posted(
    posted
):

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
# LOAD ROTATION
# =========================================================

def load_rotation():

    default = {
        "index": 0
    }


    if not os.path.exists(
        ROTATION_FILE
    ):

        return default


    try:

        with open(
            ROTATION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )


        if not isinstance(
            data,
            dict
        ):

            return default


        index = int(
            data.get(
                "index",
                0
            )
        )


        return {
            "index": index
        }


    except Exception:

        return default


# =========================================================
# SAVE ROTATION
# =========================================================

def save_rotation(
    rotation
):

    with open(
        ROTATION_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(

            rotation,

            file,

            ensure_ascii=False,

            indent=2

        )


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(
    value
):

    if value is None:

        return ""


    return " ".join(
        str(value).split()
    ).strip()


# =========================================================
# MEDIA TYPE
# =========================================================

def get_media_type(
    item
):

    item_type = clean_text(
        item.get(
            "type",
            ""
        )
    ).lower()


    if item_type in (

        "movie",

        "film",

        "فيلم"

    ):

        return "movie"


    return "tv"


# =========================================================
# ARABIC TYPE
# =========================================================

def get_arabic_type(
    media_type
):

    if media_type == "movie":

        return "فيلم"


    return "مسلسل"


# =========================================================
# MOVIE ID
# =========================================================

def get_movie_id(
    item
):

    return clean_text(
        item.get(
            "id",
            ""
        )
    )


# =========================================================
# UNIQUE KEY
# =========================================================

def get_movie_key(
    item
):

    movie_id = get_movie_id(
        item
    )


    if not movie_id:

        return ""


    return (

        get_media_type(item)

        + ":"

        + movie_id

    )


# =========================================================
# DIRECT URL
# =========================================================

def get_movie_url(
    item
):

    movie_id = get_movie_id(
        item
    )


    if not movie_id:

        return SITE_URL


    return (

        SITE_URL

        + "?movie="

        + get_media_type(item)

        + "-"

        + movie_id

    )


# =========================================================
# GENRES
# =========================================================

def get_genres_list(
    item
):

    genres = item.get(
        "genres",
        []
    )


    if isinstance(
        genres,
        list
    ):

        return [

            clean_text(genre)

            for genre in genres

            if clean_text(genre)

        ]


    value = clean_text(
        genres
    )


    if value:

        return [value]


    return []


# =========================================================
# BUILD GENRES
# =========================================================

def build_genres(
    item
):

    genres = get_genres_list(
        item
    )


    return " • ".join(
        genres[:3]
    )


# =========================================================
# GENRE MATCH
# =========================================================

def genre_matches(
    item,
    wanted_genre
):

    genres = get_genres_list(
        item
    )


    if wanted_genre in genres:

        return True


    if wanted_genre == "أكشن":

        return (

            "أكشن" in genres

            or

            "أكشن ومغامرة" in genres

        )


    if wanted_genre == "مغامرة":

        return (

            "مغامرة" in genres

            or

            "أكشن ومغامرة" in genres

        )


    if wanted_genre == "خيال علمي":

        return (

            "خيال علمي" in genres

            or

            "خيال علمي وفانتازيا" in genres

        )


    if wanted_genre == "فانتازيا":

        return (

            "فانتازيا" in genres

            or

            "خيال علمي وفانتازيا" in genres

        )


    return False


# =========================================================
# RATING
# =========================================================

def get_rating(
    item
):

    try:

        rating = float(
            item.get(
                "rating",
                0
            )
        )


        if rating <= 0:

            return "—"


        return f"{rating:.1f}/10"


    except (

        ValueError,

        TypeError

    ):

        return "—"


# =========================================================
# POPULARITY
# =========================================================

def get_popularity(
    item
):

    try:

        return float(
            item.get(
                "popularity",
                0
            )
        )


    except (

        ValueError,

        TypeError

    ):

        return 0


# =========================================================
# VOTE COUNT
# =========================================================

def get_vote_count(
    item
):

    try:

        return int(
            item.get(
                "vote_count",
                0
            )
        )


    except (

        ValueError,

        TypeError

    ):

        return 0


# =========================================================
# SELECT CANDIDATES
# =========================================================

def select_candidates(

    movies,

    posted,

    wanted_media_type,

    wanted_genre

):

    candidates = []


    for item in movies:

        key = get_movie_key(
            item
        )


        if not key:

            continue


        if key in posted:

            continue


        if (

            get_media_type(item)

            != wanted_media_type

        ):

            continue


        if not genre_matches(

            item,

            wanted_genre

        ):

            continue


        candidates.append(
            item
        )


    candidates.sort(

        key=lambda item: (

            get_popularity(item),

            get_vote_count(item)

        ),

        reverse=True

    )


    return candidates


# =========================================================
# TYPE FALLBACK
# =========================================================

def select_type_fallback(

    movies,

    posted,

    wanted_media_type

):

    candidates = []


    for item in movies:

        key = get_movie_key(
            item
        )


        if not key:

            continue


        if key in posted:

            continue


        if (

            get_media_type(item)

            != wanted_media_type

        ):

            continue


        candidates.append(
            item
        )


    candidates.sort(

        key=lambda item: (

            get_popularity(item),

            get_vote_count(item)

        ),

        reverse=True

    )


    return candidates


# =========================================================
# SHORT OVERVIEW
# =========================================================

def build_short_overview(
    item
):

    overview = clean_text(
        item.get(
            "overview",
            ""
        )
    )


    if not overview:

        return (
            "اكتشف هذا العمل على MOVINS 🎬"
        )


    if len(overview) <= MAX_OVERVIEW_LENGTH:

        return overview


    shortened = overview[
        :MAX_OVERVIEW_LENGTH
    ]


    if " " in shortened:

        shortened = shortened.rsplit(
            " ",
            1
        )[0]


    return shortened + "..."


# =========================================================
# INSTAGRAM CAPTION
# =========================================================

def build_caption(
    item
):

    title = clean_text(
        item.get(
            "title",
            "بدون عنوان"
        )
    )


    year = clean_text(
        item.get(
            "year",
            "—"
        )
    )


    overview = build_short_overview(
        item
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


    lines = [

        "🎬 " + title,

        "",

        overview,

        "",

        "⭐ التقييم: " + rating,

        "🎭 التصنيف: "
        + (
            genres
            or
            "غير محدد"
        ),

        "📅 السنة: " + year,

        "",

        "👇 التفاصيل والتريلر على MOVINS",

        movie_url,

        "",

        "#MOVINS",

        "#أفلام",

        "#مسلسلات",

        "#افلام",

        "#سينما",

        "#Movie"

    ]


    return "\n".join(
        lines
    )


# =========================================================
# CREATE INSTAGRAM MEDIA
# =========================================================

def create_media(
    item
):

    poster = clean_text(
        item.get(
            "poster",
            ""
        )
    )


    if not poster:

        print(
            "SKIP: no poster"
        )

        return None


    url = (

        f"{GRAPH_URL}/"

        f"{IG_USER_ID}/media"

    )


    payload = {

        "image_url":
            poster,

        "caption":
            build_caption(item),

        "access_token":
            TOKEN

    }


    print(
        "Creating Instagram media..."
    )


    response = requests.post(

        url,

        data=payload,

        timeout=60

    )


    try:

        result = response.json()


    except ValueError:

        print(
            response.text
        )

        return None


    if not response.ok:

        print(
            "Instagram API Error:"
        )


        print(
            json.dumps(

                result,

                ensure_ascii=False,

                indent=2

            )
        )


        return None


    container_id = result.get(
        "id"
    )


    print(
        f"Instagram container: "
        f"{container_id}"
    )


    return container_id


# =========================================================
# PUBLISH INSTAGRAM MEDIA
# =========================================================

def publish_media(
    container_id
):

    url = (

        f"{GRAPH_URL}/"

        f"{IG_USER_ID}/media_publish"

    )


    payload = {

        "creation_id":
            container_id,

        "access_token":
            TOKEN

    }


    response = requests.post(

        url,

        data=payload,

        timeout=60

    )


    try:

        result = response.json()


    except ValueError:

        print(
            response.text
        )

        return False


    if not response.ok:

        print(
            "Instagram publish error:"
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
        "Instagram post successful!"
    )


    print(
        "Instagram Media ID:",
        result.get(
            "id"
        )
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
        "MOVINS INSTAGRAM PUBLISHER"
    )


    print(
        "======================================"
    )


    movies = load_movies()

    posted = load_posted()

    rotation = load_rotation()


    rotation_index = (

        rotation.get(
            "index",
            0
        )

        % len(
            ROTATION_SEQUENCE
        )

    )


    current = (

        ROTATION_SEQUENCE[
            rotation_index
        ]

    )


    wanted_media_type = (
        current["type"]
    )


    wanted_genre = (
        current["genre"]
    )


    print(
        f"Type: "
        f"{get_arabic_type(wanted_media_type)}"
    )


    print(
        f"Genre: "
        f"{wanted_genre}"
    )


    candidates = select_candidates(

        movies,

        posted,

        wanted_media_type,

        wanted_genre

    )


    if not candidates:

        print(
            "No exact match."
        )


        candidates = select_type_fallback(

            movies,

            posted,

            wanted_media_type

        )


    if not candidates:

        print(
            "No candidates available."
        )

        return


    selected = candidates[0]


    print(
        "SELECTED:"
    )


    print(
        selected.get(
            "title",
            ""
        )
    )


    # =====================================================
    # CREATE MEDIA
    # =====================================================

    container_id = create_media(
        selected
    )


    if not container_id:

        print(
            "Media creation failed."
        )

        return


    # =====================================================
    # WAIT
    # =====================================================

    print(
        "Waiting for Instagram..."
    )


    time.sleep(
        10
    )


    # =====================================================
    # PUBLISH
    # =====================================================

    success = publish_media(
        container_id
    )


    if not success:

        print(
            "Publishing failed."
        )

        return


    # =====================================================
    # SAVE POSTED
    # =====================================================

    posted.add(

        get_movie_key(
            selected
        )

    )


    save_posted(
        posted
    )


    # =====================================================
    # NEXT ROTATION
    # =====================================================

    next_index = (

        rotation_index + 1

    ) % len(
        ROTATION_SEQUENCE
    )


    save_rotation({

        "index":
            next_index

    })


    print(
        "Rotation advanced."
    )


    print(
        "======================================"
    )


    print(
        "MOVINS Instagram publisher finished."
    )


    print(
        "======================================"
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
