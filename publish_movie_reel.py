import json
import os
import sys
import tempfile
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
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

SITE_URL = "https://nownex.github.io/movins/"


# =========================================================
# VALIDATE SECRETS
# =========================================================

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing.")

if not FACEBOOK_PAGE_ID:
    raise RuntimeError("FACEBOOK_PAGE_ID is missing.")

if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is missing.")


# =========================================================
# FILE HELPERS
# =========================================================

def load_json(filename, default):
    path = Path(filename)

    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"WARNING: Could not read {filename}: {e}")
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# MOVIE DATA
# =========================================================

def load_movies():
    data = load_json(MOVIES_FILE, {})

    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        items = []

    if not isinstance(items, list):
        return []

    return items


def load_posted():
    data = load_json(POSTED_FILE, [])

    if isinstance(data, dict):
        data = data.get("items", [])

    if not isinstance(data, list):
        return []

    return data


def normalize_id(value):
    if value is None:
        return ""

    return str(value).strip()


# =========================================================
# MOVIE INFORMATION
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

    if value in ("tv", "series", "مسلسل", "series_tv"):
        return "tv"

    return "movie"


def get_title(movie):
    title = (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    )

    return str(title).strip()


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
    overview = movie.get("overview") or ""

    return str(overview).strip()


# =========================================================
# TMDB
# =========================================================

def tmdb_headers():
    return {
        "Authorization": f"Bearer {TMDB_API_KEY}",
        "Accept": "application/json"
    }


def get_tmdb_videos(movie_id, media_type):
    endpoint_type = "tv" if media_type == "tv" else "movie"

    url = (
        f"https://api.themoviedb.org/3/"
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

        return data.get("results", [])

    except Exception as e:
        print(
            f"TMDB video lookup failed "
            f"for {media_type}/{movie_id}: {e}"
        )

        return []


def find_official_trailer(movie_id, media_type):
    videos = get_tmdb_videos(
        movie_id,
        media_type
    )

    if not videos:
        return None

    # Prefer official trailers
    official_trailers = [
        video
        for video in videos
        if video.get("site") == "YouTube"
        and str(video.get("type", "")).lower() == "trailer"
        and video.get("key")
        and video.get("official") is True
    ]

    if official_trailers:
        return official_trailers[0]

    # Then any YouTube trailer
    youtube_trailers = [
        video
        for video in videos
        if video.get("site") == "YouTube"
        and str(video.get("type", "")).lower() == "trailer"
        and video.get("key")
    ]

    if youtube_trailers:
        return youtube_trailers[0]

    return None


# =========================================================
# AUTHORIZED DIRECT VIDEO
# =========================================================

def get_authorized_video_url(movie):
    """
    MOVINS will only upload a direct video URL that the owner
    has permission to publish.

    Supported fields:
      reel_video_url
      licensed_video_url
      authorized_video_url
      facebook_reel_video_url
    """

    fields = [
        "reel_video_url",
        "licensed_video_url",
        "authorized_video_url",
        "facebook_reel_video_url"
    ]

    for field in fields:
        value = movie.get(field)

        if value:
            value = str(value).strip()

            if value.startswith("http://") or value.startswith("https://"):
                return value

    return None


# =========================================================
# CAPTION
# =========================================================

def build_caption(movie, trailer):
    title = get_title(movie)
    year = get_year(movie)
    overview = get_overview(movie)

    movie_id = get_movie_id(movie)
    media_type = get_movie_type(movie)

    type_label = "مسلسل" if media_type == "tv" else "فيلم"

    if year:
        headline = f"🎬 {title} ({year})"
    else:
        headline = f"🎬 {title}"

    lines = [
        headline,
        "",
        f"📺 النوع: {type_label}"
    ]

    if overview:
        clean_overview = overview.replace("\n", " ").strip()

        if len(clean_overview) > 500:
            clean_overview = clean_overview[:497] + "..."

        lines.extend([
            "",
            "📝 القصة:",
            clean_overview
        ])

    lines.extend([
        "",
        "🍿 شاهد التفاصيل على MOVINS:",
        f"{SITE_URL}?movie={'tv' if media_type == 'tv' else 'movie'}-{movie_id}",
        "",
        "#MOVINS #Movies #Series #Trailer"
    ])

    return "\n".join(lines)


# =========================================================
# CHOOSE MOVIE
# =========================================================

def choose_movie(movies, posted):
    posted_ids = {
        normalize_id(item.get("id"))
        for item in posted
        if isinstance(item, dict)
    }

    candidates = []

    for movie in movies:
        if not isinstance(movie, dict):
            continue

        movie_id = get_movie_id(movie)

        if not movie_id:
            continue

        if movie_id in posted_ids:
            continue

        # We need an authorized direct video file.
        video_url = get_authorized_video_url(movie)

        if not video_url:
            continue

        media_type = get_movie_type(movie)

        trailer = find_official_trailer(
            movie_id,
            media_type
        )

        # Trailer metadata is useful for validation/caption,
        # but the uploaded video itself must be authorized.
        if not trailer:
            print(
                f"Skipping {get_title(movie)}: "
                "no TMDB trailer metadata found."
            )
            continue

        popularity = float(
            movie.get("popularity") or 0
        )

        vote_count = int(
            movie.get("vote_count") or 0
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

def download_video(video_url):
    print("Downloading authorized video...")

    response = requests.get(
        video_url,
        stream=True,
        timeout=60,
        allow_redirects=True
    )

    response.raise_for_status()

    content_type = (
        response.headers.get(
            "content-type",
            ""
        ).lower()
    )

    if (
        "video/" not in content_type
        and "application/octet-stream" not in content_type
    ):
        raise RuntimeError(
            f"URL does not appear to be a video file. "
            f"Content-Type: {content_type}"
        )

    suffix = ".mp4"

    filename = response.url.split("?")[0].split("/")[-1]

    if "." in filename:
        possible_suffix = "." + filename.split(".")[-1]

        if len(possible_suffix) <= 6:
            suffix = possible_suffix

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
            f"Video downloaded: "
            f"{total_size / 1024 / 1024:.2f} MB"
        )

        if total_size < 10000:
            os.unlink(temp.name)

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
# FACEBOOK START
# =========================================================

def facebook_start_upload():
    url = (
        f"{GRAPH_URL}/"
        f"{FACEBOOK_PAGE_ID}/video_reels"
    )

    params = {
        "access_token": FACEBOOK_PAGE_TOKEN,
        "upload_phase": "start"
    }

    response = requests.post(
        url,
        params=params,
        timeout=60
    )

    if not response.ok:
        raise RuntimeError(
            "Facebook start upload failed:\n"
            + response.text
        )

    data = response.json()

    print("Facebook upload started.")

    return data


# =========================================================
# FACEBOOK TRANSFER
# =========================================================

def facebook_transfer_video(
    upload_session_id,
    video_path,
    start_offset=0
):
    url = (
        f"{GRAPH_URL}/"
        f"{FACEBOOK_PAGE_ID}/video_reels"
    )

    file_size = os.path.getsize(video_path)

    headers = {
        "Authorization": (
            f"OAuth {FACEBOOK_PAGE_TOKEN}"
        ),
        "offset": str(start_offset),
        "file_size": str(file_size)
    }

    params = {
        "upload_phase": "transfer",
        "upload_session_id": upload_session_id,
        "start_offset": str(start_offset)
    }

    with open(video_path, "rb") as video_file:

        if start_offset:
            video_file.seek(start_offset)

        response = requests.post(
            url,
            params=params,
            headers=headers,
            files={
                "video_file": video_file
            },
            timeout=300
        )

    if not response.ok:
        raise RuntimeError(
            "Facebook video transfer failed:\n"
            + response.text
        )

    return response.json()


# =========================================================
# FACEBOOK FINISH
# =========================================================

def facebook_finish_upload(
    video_id,
    caption
):
    url = (
        f"{GRAPH_URL}/"
        f"{FACEBOOK_PAGE_ID}/video_reels"
    )

    params = {
        "access_token": FACEBOOK_PAGE_TOKEN,
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": caption
    }

    response = requests.post(
        url,
        params=params,
        timeout=120
    )

    if not response.ok:
        raise RuntimeError(
            "Facebook finish upload failed:\n"
            + response.text
        )

    return response.json()


# =========================================================
# PUBLISH REEL
# =========================================================

def publish_reel(video_path, caption):
    print("Starting Facebook Reel upload...")

    start_data = facebook_start_upload()

    video_id = (
        start_data.get("video_id")
        or start_data.get("id")
    )

    upload_session_id = (
        start_data.get("upload_session_id")
        or start_data.get("upload_session")
    )

    if not video_id:
        raise RuntimeError(
            "Facebook did not return video_id:\n"
            + json.dumps(
                start_data,
                ensure_ascii=False,
                indent=2
            )
        )

    if not upload_session_id:
        raise RuntimeError(
            "Facebook did not return upload_session_id:\n"
            + json.dumps(
                start_data,
                ensure_ascii=False,
                indent=2
            )
        )

    print(f"Facebook video_id: {video_id}")
    print(
        f"Facebook upload_session_id: "
        f"{upload_session_id}"
    )

    file_size = os.path.getsize(video_path)

    # Start with offset 0.
    transfer_data = facebook_transfer_video(
        upload_session_id,
        video_path,
        start_offset=0
    )

    print(
        "Facebook transfer response:",
        json.dumps(
            transfer_data,
            ensure_ascii=False
        )
    )

    # Finish/publish
    finish_data = facebook_finish_upload(
        video_id,
        caption
    )

    print(
        "Facebook finish response:",
        json.dumps(
            finish_data,
            ensure_ascii=False
        )
    )

    return {
        "video_id": video_id,
        "upload_session_id": upload_session_id,
        "finish_response": finish_data
    }


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)
    print("MOVINS — FACEBOOK REEL PUBLISHER")
    print("=" * 60)

    movies = load_movies()
    posted = load_posted()

    print(f"Movies available: {len(movies)}")
    print(f"Already posted Reels: {len(posted)}")

    if not movies:
        print("No movies found.")
        return 0

    selected = choose_movie(
        movies,
        posted
    )

    if not selected:
        print("")
        print(
            "No eligible Reel found."
        )
        print(
            "MOVINS requires an authorized "
            "direct video URL in one of:"
        )
        print(
            "reel_video_url / "
            "licensed_video_url / "
            "authorized_video_url / "
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

    movie_id = get_movie_id(movie)
    media_type = get_movie_type(movie)
    title = get_title(movie)

    print("")
    print(f"Selected: {title}")
    print(f"TMDB ID: {movie_id}")
    print(f"Type: {media_type}")
    print(f"Popularity: {popularity}")
    print(f"Vote count: {vote_count}")
    print(
        f"TMDB trailer: "
        f"https://www.youtube.com/watch?v={trailer.get('key')}"
    )

    print("")
    print(
        "Authorized video URL found."
    )

    caption = build_caption(
        movie,
        trailer
    )

    print("")
    print("Caption:")
    print(caption)
    print("")

    video_path = None

    try:

        video_path = download_video(
            video_url
        )

        result = publish_reel(
            video_path,
            caption
        )

        # IMPORTANT:
        # Save history only AFTER Facebook confirms publishing.
        posted.append(
            {
                "id": movie_id,
                "type": media_type,
                "title": title,
                "video_id": result["video_id"],
                "trailer_key": trailer.get("key"),
                "posted_at": __import__(
                    "datetime"
                ).datetime.now(
                    __import__(
                        "datetime"
                    ).timezone.utc
                ).isoformat()
            }
        )

        save_json(
            POSTED_FILE,
            posted
        )

        print("")
        print("=" * 60)
        print("REEL PUBLISHED SUCCESSFULLY")
        print("=" * 60)

        return 0

    except Exception as e:

        print("")
        print("=" * 60)
        print("REEL PUBLISH FAILED")
        print("=" * 60)
        print(str(e))

        return 1

    finally:

        if video_path:

            try:
                os.remove(video_path)

                print(
                    "Temporary video deleted."
                )

            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
