import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests


# =========================================================
# MOVINS — REEL QUEUE UPDATER
# =========================================================

MOVIES_FILE = "movies.json"
QUEUE_FILE = "reel_queue.json"
POSTED_FILE = "posted_movie_reels.json"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

TMDB_BASE_URL = "https://api.themoviedb.org/3"

MAX_QUEUE = 20
REQUEST_TIMEOUT = 30


# =========================================================
# CHECK TMDB KEY
# =========================================================

if not TMDB_API_KEY:
    raise RuntimeError(
        "TMDB_API_KEY is missing."
    )


# =========================================================
# JSON HELPERS
# =========================================================

def load_json(filename, default):

    path = Path(filename)

    if not path.exists():
        return default

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            "WARNING: Could not read "
            + filename
            + ": "
            + str(error)
        )

        return default


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# MOVIES
# =========================================================

def load_movies():

    data = load_json(
        MOVIES_FILE,
        {}
    )

    if isinstance(data, dict):

        items = data.get(
            "items",
            []
        )

    elif isinstance(data, list):

        items = data

    else:

        items = []

    if not isinstance(
        items,
        list
    ):

        return []

    return items


# =========================================================
# POSTED REELS
# =========================================================

def load_posted():

    data = load_json(
        POSTED_FILE,
        []
    )

    if isinstance(data, dict):

        data = data.get(
            "items",
            []
        )

    if not isinstance(
        data,
        list
    ):

        return []

    return data


def get_posted_ids(posted):

    result = set()

    for item in posted:

        if not isinstance(
            item,
            dict
        ):

            continue

        item_id = item.get(
            "id"
        )

        if item_id is not None:

            result.add(
                str(item_id)
            )

    return result


# =========================================================
# MOVIE HELPERS
# =========================================================

def get_movie_id(movie):

    value = (
        movie.get("tmdb_id")
        or movie.get("id")
    )

    if value is None:
        return ""

    return str(value).strip()


def get_movie_type(movie):

    value = str(
        movie.get("media_type")
        or movie.get("type")
        or ""
    ).lower()

    if value in (
        "tv",
        "series",
        "مسلسل"
    ):

        return "tv"

    return "movie"


def get_title(movie):

    return str(
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    ).strip()


def get_year(movie):

    value = movie.get(
        "year"
    )

    if value:

        return str(value)

    date_value = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    return str(
        date_value
    )[:4]


def get_rating(movie):

    try:

        return float(
            movie.get(
                "rating",
                0
            ) or 0
        )

    except Exception:

        return 0.0


def get_popularity(movie):

    try:

        return float(
            movie.get(
                "popularity",
                0
            ) or 0
        )

    except Exception:

        return 0.0


def get_poster(movie):

    poster = movie.get(
        "poster"
    )

    if not poster:

        return ""

    poster = str(
        poster
    ).strip()

    if poster.startswith(
        "http://"
    ):

        return poster

    if poster.startswith(
        "https://"
    ):

        return poster

    if poster.startswith("/"):

        return (
            "https://image.tmdb.org/t/p/w780"
            + poster
        )

    return ""


# =========================================================
# TMDB
# =========================================================

def tmdb_request(
    endpoint,
    params=None
):

    if params is None:

        params = {}

    params = dict(
        params
    )

    params["api_key"] = TMDB_API_KEY

    params.setdefault(
        "language",
        "en-US"
    )

    url = (
        TMDB_BASE_URL
        + endpoint
    )

    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT
    )

    if not response.ok:

        print(
            "TMDB request failed: "
            + str(response.status_code)
        )

        return {}

    try:

        return response.json()

    except Exception:

        return {}


# =========================================================
# GET TMDB VIDEOS
# =========================================================

def get_tmdb_videos(
    movie_id,
    media_type
):

    if media_type == "tv":

        endpoint = (
            "/tv/"
            + str(movie_id)
            + "/videos"
        )

    else:

        endpoint = (
            "/movie/"
            + str(movie_id)
            + "/videos"
        )

    return tmdb_request(
        endpoint,
        {
            "language": "en-US"
        }
    )


# =========================================================
# FIND TRAILER
# =========================================================

def find_trailer(
    movie_id,
    media_type
):

    data = get_tmdb_videos(
        movie_id,
        media_type
    )

    results = data.get(
        "results",
        []
    )

    if not isinstance(
        results,
        list
    ):

        return None

    trailers = []

    for video in results:

        if not isinstance(
            video,
            dict
        ):

            continue

        site = str(
            video.get(
                "site",
                ""
            )
        ).lower()

        video_type = str(
            video.get(
                "type",
                ""
            )
        ).lower()

        key = str(
            video.get(
                "key",
                ""
            )
        ).strip()

        if not key:

            continue

        if site != "youtube":

            continue

        if video_type not in (
            "trailer",
            "teaser"
        ):

            continue

        trailers.append(
            video
        )

    if not trailers:

        return None

    # Prefer official videos
    official = [
        item
        for item in trailers
        if item.get("official") is True
    ]

    if official:

        trailers = official

    # Prefer trailers over teasers
    trailers.sort(
        key=lambda item:
            0
            if str(
                item.get(
                    "type",
                    ""
                )
            ).lower()
            == "trailer"
            else 1
    )

    return trailers[0]


# =========================================================
# BUILD QUEUE ITEM
# =========================================================

def build_queue_item(
    movie,
    trailer
):

    movie_id = get_movie_id(
        movie
    )

    media_type = get_movie_type(
        movie
    )

    title = get_title(
        movie
    )

    year = get_year(
        movie
    )

    rating = get_rating(
        movie
    )

    popularity = get_popularity(
        movie
    )

    trailer_key = ""

    trailer_url = ""

    if trailer:

        trailer_key = str(
            trailer.get(
                "key",
                ""
            )
        )

        if trailer_key:

            trailer_url = (
                "https://www.youtube.com/watch?v="
                + trailer_key
            )

    if media_type == "tv":

        site_link = (
            "https://nownex.github.io/movins/"
            "?movie=tv-"
            + movie_id
        )

    else:

        site_link = (
            "https://nownex.github.io/movins/"
            "?movie=movie-"
            + movie_id
        )

    return {

        "id":
            movie_id,

        "type":
            media_type,

        "title":
            title,

        "year":
            year,

        "rating":
            rating,

        "popularity":
            popularity,

        "poster":
            get_poster(movie),

        "trailer_key":
            trailer_key,

        "trailer_url":
            trailer_url,

        "movins_url":
            site_link,

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


# =========================================================
# UPDATE QUEUE
# =========================================================

def update_queue(
    movies,
    posted,
    old_queue
):

    posted_ids = get_posted_ids(
        posted
    )

    old_ids = set()

    for item in old_queue:

        if not isinstance(
            item,
            dict
        ):

            continue

        item_id = item.get(
            "id"
        )

        if item_id:

            old_ids.add(
                str(item_id)
            )

    candidates = []

    for movie in movies:

        if not isinstance(
            movie,
            dict
        ):

            continue

        movie_id = get_movie_id(
            movie
        )

        if not movie_id:

            continue

        # Already published
        if movie_id in posted_ids:

            continue

        # Already waiting in queue
        if movie_id in old_ids:

            continue

        poster = get_poster(
            movie
        )

        if not poster:

            continue

        media_type = get_movie_type(
            movie
        )

        trailer = find_trailer(
            movie_id,
            media_type
        )

        if not trailer:

            continue

        item = build_queue_item(
            movie,
            trailer
        )

        candidates.append(
            item
        )

    # Sort by popularity
    candidates.sort(
        key=lambda item: (
            float(
                item.get(
                    "popularity",
                    0
                ) or 0
            ),
            float(
                item.get(
                    "rating",
                    0
                ) or 0
            )
        ),
        reverse=True
    )

    # Keep existing queue
    result = list(
        old_queue
    )

    # Add new items
    for item in candidates:

        if len(result) >= MAX_QUEUE:

            break

        result.append(
            item
        )

    return result


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)

    print(
        "MOVINS — REEL QUEUE UPDATER"
    )

    print("=" * 60)

    movies = load_movies()

    posted = load_posted()

    old_queue = load_json(
        QUEUE_FILE,
        []
    )

    if not isinstance(
        old_queue,
        list
    ):

        old_queue = []

    print(
        "Movies available: "
        + str(len(movies))
    )

    print(
        "Already posted Reels: "
        + str(len(posted))
    )

    print(
        "Current Reel queue: "
        + str(len(old_queue))
    )

    new_queue = update_queue(
        movies,
        posted,
        old_queue
    )

    save_json(
        QUEUE_FILE,
        new_queue
    )

    added = (
        len(new_queue)
        - len(old_queue)
    )

    print("")

    print(
        "New Reel items added: "
        + str(max(added, 0))
    )

    print(
        "Total Reel queue: "
        + str(len(new_queue))
    )

    print("")

    if new_queue:

        print(
            "Next Reel:"
        )

        print(
            "Title: "
            + str(
                new_queue[0].get(
                    "title",
                    ""
                )
            )
        )

        print(
            "TMDB ID: "
            + str(
                new_queue[0].get(
                    "id",
                    ""
                )
            )
        )

        print(
            "Trailer: "
            + str(
                new_queue[0].get(
                    "trailer_url",
                    ""
                )
            )
        )

    else:

        print(
            "No eligible Reel found."
        )

    print("")

    print("=" * 60)

    print(
        "REEL QUEUE UPDATED"
    )

    print("=" * 60)

    return 0


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    sys.exit(
        main()
  )
