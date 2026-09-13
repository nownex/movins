import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests


# =========================================================
# MOVINS — FACEBOOK REEL PUBLISHER
# =========================================================

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

GRAPH_VERSION = "v26.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

FACEBOOK_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

SITE_URL = "https://nownex.github.io/movins/"


# =========================================================
# CHECK SECRETS
# =========================================================

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing."
    )

if not TMDB_API_KEY:
    raise RuntimeError(
        "TMDB_API_KEY is missing."
    )


# =========================================================
# FACEBOOK PAGE ID
# =========================================================

def get_page_info():
    """
    Automatically gets the Page ID using the Page Access Token.
    No FACEBOOK_PAGE_ID secret is required.
    """

    url = f"{GRAPH_URL}/me"

    params = {
        "fields": "id,name",
        "access_token": FACEBOOK_PAGE_TOKEN
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    if not response.ok:
        raise RuntimeError(
            "Could not get Facebook Page information:\n"
            + response.text
        )

    data = response.json()

    page_id = data.get("id")
    page_name = data.get("name")

    if not page_id:
        raise RuntimeError(
            "Facebook did not return a Page ID:\n"
            + json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            )
        )

    print(f"Facebook Page: {page_name or 'Unknown'}")
    print(f"Facebook Page ID: {page_id}")

    return page_id


# =========================================================
# JSON HELPERS
# =========================================================

def load_json(filename, default):
    path = Path(filename)

    if not path.exists():
        return default

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception as e:
        print(
            f"WARNING: Could not read {filename}: {e}"
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

    if not isinstance(items, list):
        return []

    return items


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

    if not isinstance(data, list):
        return []

    return data


def normalize_id(value):

    if value is None:
        return ""

    return str(value).strip()


# =========================================================
# MOVIE DATA
# =========================================================

def get_movie_id(movie):

    return normalize_id(
        movie.get("tmdb_id")
        or movie.get("id")
    )


def get_movie_type(movie):

    value = str(
        movie.get("media_type")
        or movie.get("type")
        or ""
    ).lower()

    if value in (
        "tv",
        "series",
        "مسلسل",
        "series_tv"
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

    year = movie.get("year")

    if year:
        return str(year)

    date_value = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    if len(str(date_value)) >= 4:
        return str(date_value)[:4]

    return ""


def get_overview(movie):

    return str(
        movie.get("overview")
        or ""
    ).strip()


# =========================================================
# TMDB
# =========================================================

def tmdb_headers():

    return {
        "Authorization": (
            f"Bearer {TMDB_API_KEY}"
        ),
        "Accept": "application/json"
    }


def get_tmdb_videos(
    movie_id,
    media_type
):

    endpoint_type = (
        "tv"
        if media_type == "tv"
        else "movie"
    )

    url = (
        "https://api.themoviedb.org/3/"
        f"{endpoint_type}/{movie_id}/videos"
    )

    try:

        response = requests.get(
            url,
            headers=tmdb_headers(),
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        return data.get(
            "results",
            []
        )

    except Exception as e:

        print(
            f"TMDB video lookup failed "
            f"for {media_type}/{movie_id}: {e}"
        )

        return []


def find_official_trailer(
    movie_id,
    media_type
):

    videos = get_tmdb_videos(
        movie_id,
        media_type
    )

    if not videos:
        return None

    official = [
        video
        for video in videos
        if video.get("site") == "YouTube"
        and str(
            video.get("type", "")
        ).lower() == "trailer"
        and video.get("key")
        and video.get("official") is True
    ]

    if official:
        return official[0]

    trailers = [
        video
        for video in videos
        if video.get("site") == "YouTube"
        and str(
            video.get("type", "")
        ).lower() == "trailer"
        and video.get("key")
    ]

    if trailers:
        return trailers[0]

    return None


# =========================================================
# AUTHORIZED VIDEO URL
# =========================================================

def get_authorized_video_url(movie):

    fields = [
        "reel_video_url",
        "licensed_video_url",
        "authorized_video_url",
        "facebook_reel_video_url"
    ]

    for field in fields:

        value = movie.get(field)

        if not value:
            continue

        value = str(value).strip()

        if value.startswith(
            "https://"
        ) or value.startswith(
            "http://"
        ):

            return value

    return None


# =========================================================
# CAPTION
# =========================================================

def build_caption(
    movie,
    trailer
):

    title = get_title(movie)
    year = get_year(movie)
    overview = get_overview(movie)

    movie_id = get_movie_id(movie)
    media_type = get_movie_type(movie)

    type_label = (
        "مسلسل"
        if media_type == "tv"
        else "فيلم"
    )

    if year:
        headline = (
            f"🎬 {title} ({year})"
        )
    else:
        headline = (
            f"🎬 {title}"
        )

    lines = [
        headline,
        "",
        f"📺 النوع: {type_label}"
    ]

    if overview:

        clean_overview = (
            overview
            .replace("\n", " ")
            .strip()
        )

        if len(clean_overview) > 500:
            clean_overview = (
                clean_overview[:497]
                + "..."
            )

        lines.extend([
            "",
            "📝 القصة:",
            clean_overview
        ])

    prefix = (
        "tv"
        if media_type == "tv"
        else "movie"
    )

    lines.extend([
        "",
        "🍿 شاهد التفاصيل على MOVINS:",
        (
            f"{SITE_URL}"
            f"?movie={prefix}-{movie_id}"
        ),
        "",
        "#MOVINS #Movies #Series #Trailer"
    ])

    return "\n".join(lines)


# =========================================================
# SELECT MOVIE
# =========================================================

def choose_movie(
    movies,
    posted
):

    posted_ids = {
        normalize_id(
            item.get("id")
        )
        for item in posted
        if isinstance(
            item,
            dict
        )
    }

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

        if movie_id in posted_ids:
            continue

        video_url = (
            get_authorized_video_url(
                movie
            )
        )

        if not video_url:
            continue

        media_type = get_movie_type(
            movie
        )

        trailer = find_official_trailer(
            movie_id,
            media_type
        )

        if not trailer:
            continue

        popularity = float(
            movie.get(
                "popularity",
                0
            ) or 0
        )

        vote_count = int(
            movie.get(
                "vote_count",
                0
            ) or 0
        )

        candidates.append(
            (
                popularity,
                vote_count,
                movie,
                video_url,
                trailer
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )

    return candidates[0]


# =========================================================
# DOWNLOAD AUTHORIZED VIDEO
# =========================================================

def download_video(
    video_url
):

    print(
        "Downloading authorized video..."
    )

    response = requests.get(
        video_url,
        stream=True,
        timeout=60,
        allow_redirects=True
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

    if (
        "video/" not in content_type
        and
        "application/octet-stream"
        not in content_type
    ):

        raise RuntimeError(
            "The supplied URL does not "
            "appear to be a direct video file.\n"
            f"Content-Type: {content_type}"
        )

    suffix = ".mp4"

    filename = (
        response.url
        .split("?")[0]
        .split("/")[-1]
    )

    if "." in filename:

        possible = (
            "."
            + filename.split(".")[-1]
        )

        if len(possible) <= 6:
            suffix = possible

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    total_size = 0

    try:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if not chunk:
                continue

            temp.write(chunk)

            total_size += len(chunk)

        temp.close()

        print(
            "Video size: "
            f"{total_size / 1024 / 1024:.2f} MB"
        )

        if total_size < 10000:

            os.unlink(
                temp.name
            )

            raise RuntimeError(
                "Downloaded video is too small."
            )

        return temp.name

    except Exception:

        try:
            temp.close()
            os.unlink(temp.name)
        except Exception:
            pass

        raise


# =========================================================
# FACEBOOK — START
# =========================================================

def facebook_start_upload(
    page_id
):

    url = (
        f"{GRAPH_URL}/"
        f"{page_id}/video_reels"
    )

    params = {
        "access_token":
            FACEBOOK_PAGE_TOKEN,

        "upload_phase":
            "start"
    }

    response = requests.post(
        url,
        params=params,
        timeout=60
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook Reel start failed:\n"
            + response.text
        )

    data = response.json()

    print(
        "Facebook Reel upload started."
    )

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )
    )

    return data


# =========================================================
# FACEBOOK — TRANSFER
# =========================================================

def facebook_transfer_video(
    upload_url,
    video_path
):

    file_size = os.path.getsize(
        video_path
    )

    headers = {
        "Authorization":
            f"OAuth {FACEBOOK_PAGE_TOKEN}",

        "offset": "0",

        "file_size":
            str(file_size)
    }

    print(
        "Uploading video to Facebook..."
    )

    with open(
        video_path,
        "rb"
    ) as video_file:

        response = requests.post(
            upload_url,
            headers=headers,
            files={
                "video_file":
                    video_file
            },
            timeout=600
        )

    if not response.ok:

        raise RuntimeError(
            "Facebook Reel video upload failed:\n"
            + response.text
        )

    data = response.json()

    print(
        "Facebook video transfer completed."
    )

    return data


# =========================================================
# FACEBOOK — FINISH
# =========================================================

def facebook_finish_upload(
    page_id,
    video_id,
    caption
):

    url = (
        f"{GRAPH_URL}/"
        f"{page_id}/video_reels"
    )

    params = {
        "access_token":
            FACEBOOK_PAGE_TOKEN,

        "upload_phase":
            "finish",

        "video_id":
            video_id,

        "video_state":
            "PUBLISHED",

        "description":
            caption
    }

    response = requests.post(
        url,
        params=params,
        timeout=120
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook Reel publish failed:\n"
            + response.text
        )

    data = response.json()

    print(
        "Facebook Reel published."
    )

    return data


# =========================================================
# PUBLISH
# =========================================================

def publish_reel(
    page_id,
    video_path,
    caption
):

    start_data = (
        facebook_start_upload(
            page_id
        )
    )

    video_id = (
        start_data.get(
            "video_id"
        )
        or
        start_data.get(
            "id"
        )
    )

    upload_url = (
        start_data.get(
            "upload_url"
        )
    )

    if not video_id:

        raise RuntimeError(
            "Facebook did not return "
            "video_id:\n"
            + json.dumps(
                start_data,
                ensure_ascii=False,
                indent=2
            )
        )

    if not upload_url:

        raise RuntimeError(
            "Facebook did not return "
            "upload_url:\n"
            + json.dumps(
                start_data,
                ensure_ascii=False,
                indent=2
            )
        )

    facebook_transfer_video(
        upload_url,
        video_path
    )

    finish_data = (
        facebook_finish_upload(
            page_id,
            video_id,
            caption
        )
    )

    return {
        "video_id": video_id,
        "finish_response":
            finish_data
    }


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)
    print(
        "MOVINS — FACEBOOK REEL PUBLISHER"
    )
    print("=" * 60)

    # -----------------------------------------------------
    # Automatically get Page ID
    # -----------------------------------------------------

    page_id = get_page_info()

    # -----------------------------------------------------
    # Load data
    # -----------------------------------------------------

    movies = load_movies()

    posted = load_posted()

    print(
        f"Movies available: {len(movies)}"
    )

    print(
        f"Already posted Reels: {len(posted)}"
    )

    if not movies:

        print(
            "No movies found."
        )

        return 0

    # -----------------------------------------------------
    # Select
    # -----------------------------------------------------

    selected = choose_movie(
        movies,
        posted
    )

    if not selected:

        print("")
        print(
            "No eligible Reel found."
        )
        print("")
        print(
            "The movie must contain an "
            "authorized direct video URL:"
        )
        print(
            "reel_video_url"
        )
        print(
            "licensed_video_url"
        )
        print(
            "authorized_video_url"
        )
        print(
            "facebook_reel_video_url"
        )
        print("")

        return 0

    (
        popularity,
        vote_count,
        movie,
        video_url,
        trailer
    ) = selected

    movie_id = get_movie_id(
        movie
    )

    media_type = get_movie_type(
        movie
    )

    title = get_title(
        movie
    )

    print("")
    print(
        f"Selected movie: {title}"
    )

    print(
        f"TMDB ID: {movie_id}"
    )

    print(
        f"Type: {media_type}"
    )

    print(
        f"Popularity: {popularity}"
    )

    print(
        f"Vote count: {vote_count}"
    )

    print(
        "TMDB trailer key: "
        f"{trailer.get('key')}"
    )

    # -----------------------------------------------------
    # Caption
    # -----------------------------------------------------

    caption = build_caption(
        movie,
        trailer
    )

    print("")
    print(
        "Caption:"
    )

    print(caption)

    # -----------------------------------------------------
    # Download
    # -----------------------------------------------------

    video_path = None

    try:

        video_path = download_video(
            video_url
        )

        # -------------------------------------------------
        # Publish
        # -------------------------------------------------

        result = publish_reel(
            page_id,
            video_path,
            caption
        )

        # -------------------------------------------------
        # Save history ONLY after successful publish
        # -------------------------------------------------

        posted.append(
            {
                "id":
                    movie_id,

                "type":
                    media_type,

                "title":
                    title,

                "video_id":
                    result[
                        "video_id"
                    ],

                "trailer_key":
                    trailer.get(
                        "key"
                    ),

                "posted_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat()
            }
        )

        save_json(
            POSTED_FILE,
            posted
        )

        print("")
        print("=" * 60)
        print(
            "MOVINS REEL PUBLISHED SUCCESSFULLY"
        )
        print("=" * 60)

        return 0

    except Exception as e:

        print("")
        print("=" * 60)
        print(
            "MOVINS REEL PUBLISH FAILED"
        )
        print("=" * 60)

        print(str(e))

        return 1

    finally:

        if video_path:

            try:

                os.remove(
                    video_path
                )

                print(
                    "Temporary video deleted."
                )

            except Exception:
                pass


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    sys.exit(
        main()
    )
