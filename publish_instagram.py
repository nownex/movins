import json
import os
import requests


# =========================================================
# MOVINS — INSTAGRAM PUBLISHER
# =========================================================

TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not TOKEN:
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing")


GRAPH_VERSION = "v26.0"


# =========================================================
# FILES
# =========================================================

MOVIES_FILE = "movies.json"

POSTED_FILE = "posted_instagram.json"


# =========================================================
# MOVINS WEBSITE
# =========================================================

SITE_URL = "https://nownex.github.io/movins/"


# =========================================================
# SETTINGS
# =========================================================

MAX_OVERVIEW_LENGTH = 500


# =========================================================
# GET INSTAGRAM ACCOUNT
# =========================================================

def get_instagram_account():

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/me"
    )

    params = {
        "fields":
            "instagram_business_account{id,username}",
        "access_token":
            TOKEN
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    account = data.get(
        "instagram_business_account"
    )

    if not account:

        raise RuntimeError(
            "No Instagram Business account found"
        )

    account_id = account.get("id")

    if not account_id:

        raise RuntimeError(
            "Instagram account ID not found"
        )

    print(
        f"Instagram ID: {account_id}"
    )

    print(
        f"Instagram username: "
        f"{account.get('username', '')}"
    )

    return account_id


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

        return set(
            str(item)
            for item in data
        )

    except Exception:

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
            sorted(list(posted)),
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(value):

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


# =========================================================
# MEDIA TYPE
# =========================================================

def get_media_type(item):

    item_type = clean_text(
        item.get("type", "")
    ).lower()

    if item_type in (
        "movie",
        "film",
        "فيلم"
    ):

        return "movie"

    return "tv"


# =========================================================
# UNIQUE KEY
# =========================================================

def get_movie_key(item):

    movie_id = clean_text(
        item.get("id", "")
    )

    if not movie_id:
        return ""

    media_type = get_media_type(item)

    return (
        f"{media_type}:{movie_id}"
    )


# =========================================================
# DIRECT MOVIE URL
# =========================================================

def get_movie_url(item):

    movie_id = clean_text(
        item.get("id", "")
    )

    if not movie_id:
        return SITE_URL

    media_type = get_media_type(item)

    return (
        SITE_URL
        + "?movie="
        + media_type
        + "-"
        + movie_id
    )


# =========================================================
# SHORT OVERVIEW
# =========================================================

def build_overview(item):

    overview = clean_text(
        item.get("overview", "")
    )

    if not overview:

        return (
            "اكتشف تفاصيل هذا العمل "
            "على MOVINS."
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
# GENRES
# =========================================================

def build_genres(item):

    genres = item.get(
        "genres",
        []
    )

    if isinstance(genres, list):

        genres = [
            clean_text(genre)
            for genre in genres
            if clean_text(genre)
        ]

        return " • ".join(
            genres[:4]
        )

    return clean_text(genres)


# =========================================================
# RATING
# =========================================================

def get_rating(item):

    try:

        rating = float(
            item.get("rating")
            or 0
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

def get_popularity(item):

    try:

        return float(
            item.get("popularity")
            or 0
        )

    except (
        ValueError,
        TypeError
    ):

        return 0


# =========================================================
# BUILD INSTAGRAM CAPTION
# =========================================================

def build_caption(item):

    title = clean_text(
        item.get("title")
        or "بدون عنوان"
    )

    overview = build_overview(item)

    year = clean_text(
        item.get("year")
        or "—"
    )

    genres = build_genres(item)

    rating = get_rating(item)

    movie_url = get_movie_url(item)

    return f"""🎬 {title}

{overview}

⭐ التقييم: {rating}
🎭 التصنيف: {genres or 'غير محدد'}
📅 السنة: {year}

👇 اكتشف التفاصيل والتريلر على MOVINS:

{movie_url}

#MOVINS #أفلام #مسلسلات #Movies #Series #Cinema #Entertainment
"""


# =========================================================
# SELECT MOVIE
# =========================================================

def select_movie(movies, posted):

    candidates = []

    for item in movies:

        key = get_movie_key(item)

        if not key:
            continue

        if key in posted:
            continue

        poster = clean_text(
            item.get("poster", "")
        )

        if not poster:
            continue

        candidates.append(item)

    candidates.sort(

        key=lambda item:
            get_popularity(item),

        reverse=True
    )

    if not candidates:
        return None

    return candidates[0]


# =========================================================
# CREATE INSTAGRAM MEDIA
# =========================================================

def create_media_container(
    instagram_id,
    image_url,
    caption
):

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/"
        f"{instagram_id}/media"
    )

    payload = {

        "image_url":
            image_url,

        "caption":
            caption,

        "access_token":
            TOKEN
    }

    response = requests.post(

        url,

        data=payload,

        timeout=60
    )

    data = response.json()

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )
    )

    response.raise_for_status()

    container_id = data.get("id")

    if not container_id:

        raise RuntimeError(
            "Instagram container ID not received"
        )

    return container_id


# =========================================================
# PUBLISH INSTAGRAM MEDIA
# =========================================================

def publish_media(
    instagram_id,
    container_id
):

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/"
        f"{instagram_id}/media_publish"
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

    data = response.json()

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )
    )

    response.raise_for_status()

    return data


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "================================"
    )

    print(
        "MOVINS INSTAGRAM PUBLISHER"
    )

    print(
        "================================"
    )

    instagram_id = get_instagram_account()

    movies = load_movies()

    posted = load_posted()

    print(
        f"Available items: {len(movies)}"
    )

    print(
        f"Already posted: {len(posted)}"
    )

    selected = select_movie(
        movies,
        posted
    )

    if not selected:

        print(
            "No new movie available."
        )

        return

    title = clean_text(
        selected.get("title", "")
    )

    poster = clean_text(
        selected.get("poster", "")
    )

    caption = build_caption(
        selected
    )

    print(
        "================================"
    )

    print(
        f"SELECTED: {title}"
    )

    print(
        f"POSTER: {poster}"
    )

    print(
        "================================"
    )

    try:

        # 1. Create container
        print(
            "Creating Instagram media..."
        )

        container_id = create_media_container(

            instagram_id,

            poster,

            caption
        )

        print(
            f"Container ID: {container_id}"
        )


        # 2. Publish
        print(
            "Publishing to Instagram..."
        )

        result = publish_media(

            instagram_id,

            container_id
        )

        print(
            "================================"
        )

        print(
            "INSTAGRAM POST SUCCESSFUL!"
        )

        print(
            f"Post ID: "
            f"{result.get('id')}"
        )


        # 3. Save posted item
        movie_key = get_movie_key(
            selected
        )

        posted.add(
            movie_key
        )

        save_posted(
            posted
        )


    except requests.RequestException as error:

        print(
            "INSTAGRAM API ERROR:"
        )

        print(error)

        raise


if __name__ == "__main__":

    main()
