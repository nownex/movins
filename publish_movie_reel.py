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

TMDB_TOKEN = os.environ.get(
    "TMDB_TOKEN"
)

GRAPH_VERSION = "v26.0"

GRAPH_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}"
)

TMDB_URL = "https://api.themoviedb.org/3"


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

if not TMDB_TOKEN:
    raise RuntimeError(
        "TMDB_TOKEN is missing."
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
            data.get(
                "items",
                []
            )
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
            "updated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "items": items
        }
    )


# =========================================================
# MOVIE INFORMATION
# =========================================================

def get_movie_id(movie):

    value = (
        movie.get("tmdb_id")
        or movie.get("id")
        or ""
    )

    return str(value).strip()


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


def get_title(movie):

    return (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    ).strip()


def get_overview(movie):

    return (
        movie.get("overview")
        or movie.get("description")
        or movie.get("summary")
        or ""
    ).strip()


# =========================================================
# TMDB
# =========================================================

def tmdb_request(
    endpoint,
    params=None
):

    headers = {
        "Authorization":
            f"Bearer {TMDB_TOKEN}",

        "accept":
            "application/json"
    }

    try:

        response = requests.get(
            f"{TMDB_URL}{endpoint}",
            headers=headers,
            params=params or {},
            timeout=30
        )

        print(
            "TMDB:",
            response.status_code,
            endpoint
        )

        if not response.ok:

            print(
                "TMDB ERROR:",
                response.text[:1000]
            )

            return None

        return response.json()

    except Exception as e:

        print(
            "TMDB REQUEST ERROR:",
            e
        )

        return None


# =========================================================
# FIND OFFICIAL TRAILER
# =========================================================

def find_trailer(movie):

    movie_id = get_movie_id(
        movie
    )

    if not movie_id:
        return None

    media_type = get_movie_type(
        movie
    )

    if media_type == "tv":

        endpoint = (
            f"/tv/{movie_id}/videos"
        )

    else:

        endpoint = (
            f"/movie/{movie_id}/videos"
        )

    data = tmdb_request(
        endpoint,
        {
            "language": "en-US"
        }
    )

    if not data:
        return None

    videos = data.get(
        "results",
        []
    )

    if not isinstance(
        videos,
        list
    ):
        return None

    # -----------------------------------------------------
    # First priority:
    # Official + Trailer + YouTube
    # -----------------------------------------------------

    official = []

    for video in videos:

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

        kind = str(
            video.get(
                "type",
                ""
            )
        ).lower()

        is_official = bool(
            video.get(
                "official",
                False
            )
        )

        if (
            site == "youtube"
            and kind == "trailer"
        ):

            score = 0

            if is_official:
                score += 100

            name = str(
                video.get(
                    "name",
                    ""
                )
            ).lower()

            if "official" in name:
                score += 30

            if "teaser" not in name:
                score += 10

            official.append(
                (
                    score,
                    video
                )
            )

    if not official:
        return None

    official.sort(
        key=lambda x: x[0],
        reverse=True
    )

    video = official[0][1]

    key = video.get(
        "key"
    )

    if not key:
        return None

    return {
        "key": key,
        "name": video.get(
            "name",
            ""
        ),
        "site": video.get(
            "site",
            ""
        ),
        "type": video.get(
            "type",
            ""
        ),
        "official": video.get(
            "official",
            False
        ),
        "youtube_url":
            f"https://www.youtube.com/watch?v={key}"
    }


# =========================================================
# AUTHORIZED DIRECT VIDEO
# =========================================================

def get_authorized_video_url(
    movie
):

    for field in [
        "reel_video_url",
        "licensed_video_url",
        "authorized_video_url",
        "facebook_reel_video_url"
    ]:

        value = movie.get(
            field
        )

        if value:

            return str(
                value
            ).strip()

    return ""


# =========================================================
# CAPTION
# =========================================================

def build_caption(
    movie,
    trailer
):

    title = get_title(
        movie
    )

    overview = get_overview(
        movie
    )

    if len(overview) > 500:

        overview = (
            overview[:500]
            .rsplit(" ", 1)[0]
            + "..."
        )

    movie_id = get_movie_id(
        movie
    )

    media_type = get_movie_type(
        movie
    )

    if media_type == "tv":

        intro = (
            f"🎬 التريلر الرسمي "
            f"لمسلسل {title}"
        )

        hashtag_type = "#Series"

    else:

        intro = (
            f"🎬 التريلر الرسمي "
            f"لفيلم {title}"
        )

        hashtag_type = "#Movies"

    parts = [
        intro,
        ""
    ]

    if overview:

        parts.extend([
            overview,
            ""
        ])

    parts.extend([
        "🔥 شاهد التريلر واكتشف "
        "ما ينتظر هذا العمل.",
        "",
        "#MOVINS",
        "#Trailer",
        hashtag_type
    ])

    # Safe hashtag
    safe_title = (
        title
        .replace(" ", "")
        .replace("#", "")
        .replace("/", "")
        .replace(":", "")
    )

    if safe_title:

        parts.append(
            f"#{safe_title}"
        )

    # MOVINS page link
    if movie_id:

        parts.extend([
            "",
            "🎬 المزيد على MOVINS:",
            (
                "https://nownex.github.io/"
                "movins/?movie="
                f"{media_type}-{movie_id}"
            )
        ])

    return "\n".join(
        parts
    )


# =========================================================
# ALREADY POSTED
# =========================================================

def posted_ids(posted):

    result = set()

    for item in posted:

        if isinstance(
            item,
            dict
        ):

            value = item.get(
                "movie_id"
            )

            if value:
                result.add(
                    str(value)
                )

        else:

            result.add(
                str(item)
            )

    return result


# =========================================================
# CHOOSE MOVIE
# =========================================================

def choose_movie(
    movies,
    posted
):

    already_posted = posted_ids(
        posted
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

        if movie_id in already_posted:
            continue

        # -------------------------------------------------
        # Find official trailer metadata
        # -------------------------------------------------

        trailer = find_trailer(
            movie
        )

        if not trailer:

            print(
                "NO TRAILER:",
                get_title(movie)
            )

            continue

        # -------------------------------------------------
        # We still need an authorized
        # direct video file.
        # -------------------------------------------------

        video_url = (
            get_authorized_video_url(
                movie
            )
        )

        if not video_url:

            print(
                "TRAILER FOUND BUT "
                "NO AUTHORIZED VIDEO FILE:",
                get_title(movie)
            )

            print(
                "TRAILER:",
                trailer[
                    "youtube_url"
                ]
            )

            continue

        candidates.append(
            {
                "movie": movie,
                "trailer": trailer,
                "video_url": video_url
            }
        )

    if not candidates:

        return None

    # -----------------------------------------------------
    # Popularity
    # -----------------------------------------------------

    candidates.sort(
        key=lambda item: float(
            item["movie"].get(
                "popularity",
                0
            ) or 0
        ),
        reverse=True
    )

    return candidates[0]


# =========================================================
# FACEBOOK — START REEL UPLOAD
# =========================================================

def facebook_start():

    url = (
        f"{GRAPH_URL}/"
        f"{FACEBOOK_PAGE_ID}/"
        f"video_reels"
    )

    response = requests.post(
        url,
        data={
            "upload_phase":
                "start",

            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=60
    )

    print(
        "FACEBOOK START:",
        response.text
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# DOWNLOAD AUTHORIZED VIDEO
# =========================================================

def download_video(
    video_url,
    output_file
):

    print(
        "Downloading authorized video..."
    )

    response = requests.get(
        video_url,
        stream=True,
        timeout=120
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get(
            "content-type",
            ""
        )
        .lower()
    )

    if not content_type.startswith(
        "video/"
    ):

        raise RuntimeError(
            "The supplied video URL "
            "did not return a video file."
        )

    with open(
        output_file,
        "wb"
    ) as f:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:
                f.write(chunk)

    return output_file


# =========================================================
# FACEBOOK — UPLOAD FILE
# =========================================================

def upload_video_file(
    upload_url,
    video_file
):

    file_size = os.path.getsize(
        video_file
    )

    headers = {
        "Authorization":
            f"OAuth {FACEBOOK_PAGE_TOKEN}",

        "offset": "0",

        "file_size": str(
            file_size
        )
    }

    with open(
        video_file,
        "rb"
    ) as f:

        response = requests.post(
            upload_url,
            headers=headers,
            data=f,
            timeout=600
        )

    print(
        "FACEBOOK UPLOAD:",
        response.text
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# FACEBOOK — FINISH
# =========================================================

def facebook_finish(
    video_id,
    caption
):

    url = (
        f"{GRAPH_URL}/"
        f"{FACEBOOK_PAGE_ID}/"
        f"video_reels"
    )

    response = requests.post(
        url,
        data={
            "upload_phase":
                "finish",

            "video_id":
                video_id,

            "video_state":
                "PUBLISHED",

            "description":
                caption,

            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=120
    )

    print(
        "FACEBOOK FINISH:",
        response.text
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# PUBLISH REEL
# =========================================================

def publish_reel(
    video_url,
    caption
):

    start = facebook_start()

    video_id = start.get(
        "video_id"
    )

    upload_url = start.get(
        "upload_url"
    )

    if not video_id:
        raise RuntimeError(
            "Facebook did not return "
            "video_id."
        )

    if not upload_url:
        raise RuntimeError(
            "Facebook did not return "
            "upload_url."
        )

    video_file = (
        "movins_reel_video.mp4"
    )

    try:

        download_video(
            video_url,
            video_file
        )

        upload_video_file(
            upload_url,
            video_file
        )

        result = facebook_finish(
            video_id,
            caption
        )

        return result

    finally:

        if os.path.exists(
            video_file
        ):

            os.remove(
                video_file
            )


# =========================================================
# MAIN
# =========================================================

def main():

    movies = load_movies()

    posted = load_posted()

    print(
        "================================"
    )

    print(
        "MOVINS REEL PUBLISHER"
    )

    print(
        "================================"
    )

    print(
        f"MOVIES: {len(movies)}"
    )

    print(
        f"POSTED REELS: {len(posted)}"
    )

    selected = choose_movie(
        movies,
        posted
    )

    if not selected:

        print(
            "\nNo suitable authorized "
            "Reel is available."
        )

        print(
            "Nothing was published."
        )

        return

    movie = selected[
        "movie"
    ]

    trailer = selected[
        "trailer"
    ]

    video_url = selected[
        "video_url"
    ]

    movie_id = get_movie_id(
        movie
    )

    title = get_title(
        movie
    )

    caption = build_caption(
        movie,
        trailer
    )

    print(
        f"\nSELECTED: {title}"
    )

    print(
        f"TMDB ID: {movie_id}"
    )

    print(
        f"TRAILER: "
        f"{trailer['youtube_url']}"
    )

    print(
        "\nCAPTION:"
    )

    print(
        caption
    )

    # -----------------------------------------------------
    # Publish
    # -----------------------------------------------------

    result = publish_reel(
        video_url,
        caption
    )

    # -----------------------------------------------------
    # Save history ONLY after success
    # -----------------------------------------------------

    posted.append(
        {
            "movie_id":
                movie_id,

            "title":
                title,

            "tmdb_trailer":
                trailer,

            "published_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "facebook_response":
                result
        }
    )

    save_posted(
        posted
    )

    print(
        "\n================================"
    )

    print(
        "REEL PUBLISHED SUCCESSFULLY"
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()
