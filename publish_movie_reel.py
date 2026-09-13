import json
import os
import requests
from datetime import datetime, timezone


# =========================================================
# MOVINS — FACEBOOK REEL PUBLISHER
# =========================================================

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

FACEBOOK_PAGE_TOKEN = os.environ.get(
    "FACEBOOK_PAGE_TOKEN"
)

FACEBOOK_PAGE_ID = os.environ.get(
    "FACEBOOK_PAGE_ID"
)

GRAPH_VERSION = "v26.0"

GRAPH_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}"
)


# =========================================================
# SETTINGS
# =========================================================

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing."
    )

if not FACEBOOK_PAGE_ID:
    raise RuntimeError(
        "FACEBOOK_PAGE_ID is missing."
    )


# =========================================================
# FILE HELPERS
# =========================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:
        print(
            f"[LOAD ERROR] {filename}: {e}"
        )

        return default


def save_json(filename, data):
    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# MOVIES
# =========================================================

def load_movies():
    data = load_json(
        MOVIES_FILE,
        []
    )

    if isinstance(data, dict):
        return data.get(
            "movies",
            data.get("items", [])
        )

    if isinstance(data, list):
        return data

    return []


# =========================================================
# POSTED REELS
# =========================================================

def load_posted():
    data = load_json(
        POSTED_FILE,
        []
    )

    if isinstance(data, dict):
        return data.get(
            "items",
            []
        )

    if isinstance(data, list):
        return data

    return []


def save_posted(items):
    save_json(
        POSTED_FILE,
        {
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "items": items
        }
    )


# =========================================================
# MOVIE ID
# =========================================================

def get_movie_id(movie):
    return str(
        movie.get("id")
        or movie.get("tmdb_id")
        or ""
    ).strip()


def get_movie_type(movie):
    media_type = (
        movie.get("media_type")
        or movie.get("type")
        or "movie"
    )

    media_type = str(
        media_type
    ).lower()

    if media_type in [
        "tv",
        "series",
        "show"
    ]:
        return "tv"

    return "movie"


# =========================================================
# TITLE
# =========================================================

def get_title(movie):
    return (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    ).strip()


# =========================================================
# OFFICIAL / LICENSED REEL VIDEO
# =========================================================

def get_reel_video(movie):
    """
    IMPORTANT:

    This system does NOT download trailers from YouTube.

    It expects a direct video URL that you are legally
    allowed to upload to Facebook.

    Supported fields:
      reel_video_url
      licensed_video_url
      facebook_reel_video_url

    You can later add your own authorized video source.
    """

    for key in [
        "reel_video_url",
        "licensed_video_url",
        "facebook_reel_video_url",
    ]:
        value = movie.get(key)

        if value:
            return str(value).strip()

    return ""


# =========================================================
# DESCRIPTION
# =========================================================

def build_caption(movie):
    title = get_title(movie)

    overview = (
        movie.get("overview")
        or movie.get("description")
        or movie.get("summary")
        or ""
    )

    overview = str(
        overview
    ).strip()

    if len(overview) > 500:
        overview = overview[:500].rsplit(
            " ",
            1
        )[0] + "..."

    movie_id = get_movie_id(movie)

    if overview:
        caption = (
            f"🎬 التريلر الرسمي لـ {title}\n\n"
            f"{overview}\n\n"
            f"🔥 شاهد التريلر واكتشف ما ينتظر "
            f"هذا العمل.\n\n"
            f"#MOVINS "
            f"#Trailer "
            f"#Movies "
            f"#{title.replace(' ', '')}"
        )
    else:
        caption = (
            f"🎬 التريلر الرسمي لـ {title}\n\n"
            f"🔥 شاهد التريلر واكتشف المزيد "
            f"عن العمل.\n\n"
            f"#MOVINS #Trailer #Movies "
            f"#{title.replace(' ', '')}"
        )

    if movie_id:
        caption += (
            f"\n\n"
            f"🎬 المزيد على MOVINS:"
            f"\nhttps://nownex.github.io/"
            f"movins/?movie="
            f"{get_movie_type(movie)}-{movie_id}"
        )

    return caption


# =========================================================
# FIND CANDIDATE
# =========================================================

def choose_movie(movies, posted):
    posted_ids = set()

    for item in posted:
        if isinstance(item, dict):
            movie_id = str(
                item.get("movie_id", "")
            )

            if movie_id:
                posted_ids.add(
                    movie_id
                )

        else:
            posted_ids.add(
                str(item)
            )

    candidates = []

    for movie in movies:

        if not isinstance(movie, dict):
            continue

        movie_id = get_movie_id(movie)

        if not movie_id:
            continue

        if movie_id in posted_ids:
            continue

        video_url = get_reel_video(
            movie
        )

        if not video_url:
            continue

        candidates.append(
            movie
        )

    if not candidates:
        return None

    # Prefer popularity when available
    candidates.sort(
        key=lambda x: float(
            x.get("popularity", 0) or 0
        ),
        reverse=True
    )

    return candidates[0]


# =========================================================
# FACEBOOK REEL UPLOAD
# =========================================================

def publish_reel(video_url, caption):
    """
    Facebook's video/reel publishing flow can require
    Page permissions and may change with Graph API versions.

    This function starts the upload using the Page endpoint.
    """

    url = (
        f"{GRAPH_URL}/"
        f"{FACEBOOK_PAGE_ID}/"
        f"video_reels"
    )

    payload = {
        "upload_phase": "start",
        "access_token": FACEBOOK_PAGE_TOKEN,
    }

    response = requests.post(
        url,
        data=payload,
        timeout=60
    )

    print(
        "START RESPONSE:",
        response.text
    )

    response.raise_for_status()

    data = response.json()

    return data


# =========================================================
# MAIN
# =========================================================

def main():

    movies = load_movies()

    posted = load_posted()

    print(
        f"MOVIES: {len(movies)}"
    )

    print(
        f"POSTED REELS: {len(posted)}"
    )

    movie = choose_movie(
        movies,
        posted
    )

    if not movie:
        print(
            "No authorized reel video "
            "is available for a new movie."
        )

        return

    movie_id = get_movie_id(
        movie
    )

    title = get_title(
        movie
    )

    video_url = get_reel_video(
        movie
    )

    caption = build_caption(
        movie
    )

    print(
        f"\nSELECTED: {title}"
    )

    print(
        f"MOVIE ID: {movie_id}"
    )

    print(
        "AUTHORIZED VIDEO: YES"
    )

    print(
        "\nCAPTION:"
    )

    print(
        caption
    )

    # -----------------------------------------------------
    # Facebook upload
    # -----------------------------------------------------

    result = publish_reel(
        video_url,
        caption
    )

    # -----------------------------------------------------
    # Record only after Facebook accepts upload
    # -----------------------------------------------------

    posted.append(
        {
            "movie_id": movie_id,
            "title": title,
            "published_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "facebook_response": result,
        }
    )

    save_posted(
        posted
    )

    print(
        "\nREEL PUBLISHED/STARTED"
    )


if __name__ == "__main__":
    main()
