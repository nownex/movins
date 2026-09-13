import json
import os
import sys
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests


# =========================================================
# MOVINS — AUTOMATIC MOVIE REEL MAKER
# =========================================================

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

GRAPH_VERSION = "v26.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

FACEBOOK_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

SITE_URL = "https://nownex.github.io/movins/"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_DURATION = 12


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
# JSON
# =========================================================

def load_json(filename, default):

    path = Path(filename)

    if not path.exists():
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
            f"WARNING: Could not read {filename}: {e}"
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
# FACEBOOK PAGE
# =========================================================

def get_page_info():

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

    if not page_id:

        raise RuntimeError(
            "Facebook did not return Page ID:\n"
            + json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            )
        )

    print(
        f"Facebook Page: "
        f"{data.get('name', 'Unknown')}"
    )

    print(
        f"Facebook Page ID: {page_id}"
    )

    return page_id


# =========================================================
# MOVIES
# =========================================================

def load_movies():

    data = load_json(
        MOVIES_FILE,
        {}
    )

    if isinstance(data, dict):
        return data.get(
            "items",
            []
        )

    if isinstance(data, list):
        return data

    return []


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


def movie_id(movie):

    return str(
        movie.get("tmdb_id")
        or movie.get("id")
        or ""
    ).strip()


def movie_type(movie):

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


def movie_title(movie):

    return str(
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    ).strip()


def movie_year(movie):

    if movie.get("year"):
        return str(
            movie.get("year")
        )

    date_value = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    return str(date_value)[:4]


def movie_rating(movie):

    try:

        return float(
            movie.get(
                "rating",
                0
            ) or 0
        )

    except Exception:

        return 0


def movie_popularity(movie):

    try:

        return float(
            movie.get(
                "popularity",
                0
            ) or 0
        )

    except Exception:

        return 0


# =========================================================
# POSTER
# =========================================================

def get_poster_url(movie):

    poster = movie.get(
        "poster"
    )

    if not poster:
        return None

    poster = str(
        poster
    ).strip()

    if poster.startswith(
        "http://"
    ) or poster.startswith(
        "https://"
    ):

        return poster

    if poster.startswith("/"):
        return (
            "https://image.tmdb.org/t/p/w780"
            + poster
        )

    return None


# =========================================================
# SELECT MOVIE
# =========================================================

def choose_movie(
    movies,
    posted
):

    posted_ids = {
        str(
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

        mid = movie_id(
            movie
        )

        if not mid:
            continue

        if mid in posted_ids:
            continue

        poster = get_poster_url(
            movie
        )

        if not poster:
            continue

        popularity = movie_popularity(
            movie
        )

        rating = movie_rating(
            movie
        )

        candidates.append(
            (
                popularity,
                rating,
                movie
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            x[0],
            x[1]
        ),
        reverse=True
    )

    return candidates[0][2]


# =========================================================
# DOWNLOAD POSTER
# =========================================================

def download_poster(
    poster_url
):

    print(
        "Downloading movie poster..."
    )

    response = requests.get(
        poster_url,
        timeout=60
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

    if "image" not in content_type:

        raise RuntimeError(
            "Poster URL is not an image."
        )

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".jpg"
    )

    temp.write(
        response.content
    )

    temp.close()

    print(
        f"Poster downloaded: "
        f"{len(response.content) / 1024:.1f} KB"
    )

    return temp.name


# =========================================================
# TEXT FILES
# =========================================================

def write_text_file(
    text
):

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".txt",
        mode="w",
        encoding="utf-8"
    )

    temp.write(
        text
    )

    temp.close()

    return temp.name


# =========================================================
# CREATE REEL
# =========================================================

def create_reel(
    movie,
    poster_path
):

    title = movie_title(
        movie
    )

    year = movie_year(
        movie
    )

    rating = movie_rating(
        movie
    )

    media = movie_type(
        movie
    )

    if media == "tv":
        media_label = "SERIES"
    else:
        media_label = "MOVIE"

    output = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4"
    )

    output.close()

    title_file = write_text_file(
        title
    )

    year_file = write_text_file(
        str(year)
    )

    rating_file = write_text_file(
        f"{rating:.1f}/10"
    )

    type_file = write_text_file(
        media_label
    )

    # -----------------------------------------------------
    # 12-second cinematic vertical Reel
    # -----------------------------------------------------

    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0008,1.12)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=360:"
        "s=1080x1920:"
        "fps=30,"
        "setsar=1,"
        "eq=brightness=-0.08:"
        "contrast=1.08,"
        "boxblur=1:1"
        "[bg];"

        # Dark cinematic overlay
        "color=c=black@0.25:"
        "s=1080x1920:"
        "d=12"
        "[shade];"

        "[bg][shade]"
        "overlay=0:0"
        "[v1];"

        # Bottom gradient-like dark box
        "[v1]"
        "drawbox="
        "x=0:"
        "y=1320:"
        "w=1080:"
        "h=600:"
        "color=black@0.68:"
        "t=fill"
        "[v2];"

        # MOVINS
        "[v2]"
        "drawtext="
        f"textfile='{type_file}':"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1380:"
        "alpha='if(lt(t,1),t,1)':"
        "enable='between(t,0,12)'"
        "[v3];"

        # Title
        "[v3]"
        "drawtext="
        f"textfile='{title_file}':"
        "fontcolor=white:"
        "fontsize=70:"
        "fontweight=bold:"
        "x=(w-text_w)/2:"
        "y=1450:"
        "alpha='if(lt(t,1),t,1)'"
        "[v4];"

        # Year
        "[v4]"
        "drawtext="
        f"textfile='{year_file}':"
        "fontcolor=white:"
        "fontsize=40:"
        "x=(w-text_w)/2:"
        "y=1545:"
        "alpha='if(lt(t,1.5),(t/1.5),1)'"
        "[v5];"

        # Rating
        "[v5]"
        "drawtext="
        f"textfile='{rating_file}':"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1620:"
        "alpha='if(lt(t,2),(t/2),1)'"
        "[v6];"

        # MOVINS branding
        "[v6]"
        "drawtext="
        "text='MOVINS':"
        "fontcolor=white:"
        "fontsize=36:"
        "x=(w-text_w)/2:"
        "y=1760:"
        "alpha='if(lt(t,2),(t/2),1)'"
        "[v7];"

        # Call to action
        "[v7]"
        "drawtext="
        "text='Watch more on MOVINS':"
        "fontcolor=white:"
        "fontsize=32:"
        "x=(w-text_w)/2:"
        "y=1815:"
        "alpha='if(gt(t,3),1,0)'"
        "[vout]"
    )

    command = [
        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        poster_path,

        "-filter_complex",
        filter_complex,

        "-map",
        "[vout]",

        "-t",
        str(VIDEO_DURATION),

        "-r",
        "30",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        output.name
    ]

    print(
        "Creating cinematic Reel..."
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    if result.returncode != 0:

        print(
            result.stdout[-5000:]
        )

        raise RuntimeError(
            "FFmpeg failed to create Reel."
        )

    # Cleanup text files
    for path in (
        title_file,
        year_file,
        rating_file,
        type_file
    ):

        try:
            os.remove(path)
        except Exception:
            pass

    size = os.path.getsize(
        output.name
    )

    print(
        f"Reel created: "
        f"{size / 1024 / 1024:.2f} MB"
    )

    return output.name


# =========================================================
# FACEBOOK START
# =========================================================

def facebook_start(
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

    return data


# =========================================================
# FACEBOOK TRANSFER
# =========================================================

def facebook_transfer(
    upload_url,
    video_path
):

    file_size = os.path.getsize(
        video_path
    )

    headers = {
        "Authorization":
            f"OAuth {FACEBOOK_PAGE_TOKEN}",

        "offset":
            "0",

        "file_size":
            str(file_size)
    }

    print(
        "Uploading Reel video..."
    )

    with open(
        video_path,
        "rb"
    ) as video:

        response = requests.post(
            upload_url,
            headers=headers,
            files={
                "video_file":
                    video
            },
            timeout=600
        )

    if not response.ok:

        raise RuntimeError(
            "Facebook video upload failed:\n"
            + response.text
        )

    return response.json()


# =========================================================
# FACEBOOK FINISH
# =========================================================

def facebook_finish(
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

    return response.json()


# =========================================================
# PUBLISH FACEBOOK REEL
# =========================================================

def publish_reel(
    page_id,
    video_path,
    caption
):

    start = facebook_start(
        page_id
    )

    video_id = (
        start.get("video_id")
        or start.get("id")
    )

    upload_url = start.get(
        "upload_url"
    )

    if not video_id:

        raise RuntimeError(
            "Facebook did not return video_id:\n"
            + json.dumps(
                start,
                ensure_ascii=False,
                indent=2
            )
        )

    if not upload_url:

        raise RuntimeError(
            "Facebook did not return upload_url:\n"
            + json.dumps(
                start,
                ensure_ascii=False,
                indent=2
            )
        )

    facebook_transfer(
        upload_url,
        video_path
    )

    finish = facebook_finish(
        page_id,
        video_id,
        caption
    )

    return {
        "video_id": video_id,
        "response": finish
    }


# =========================================================
# CAPTION
# =========================================================

def build_caption(
    movie
):

    title = movie_title(
        movie
    )

    year = movie_year(
        movie
    )

    rating = movie_rating(
        movie
    )

    mid = movie_id(
        movie
    )

    media = movie_type(
        movie
    )

    prefix = (
        "tv"
        if media == "tv"
        else "movie"
    )

    link = (
        f"{SITE_URL}"
        f"?movie={prefix}-{mid}"
    )

    caption = (
        f"🎬 {title}\n"
        f"📅 {year}\n"
        f"⭐ {rating:.1f}/10\n\n"
        f"🍿 اكتشف الفيلم على MOVINS:\n"
        f"{link}\n\n"
        f"#MOVINS #Movies #Series #Film"
    )

    return caption


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)
    print(
        "MOVINS — AUTOMATIC REEL MAKER"
    )
    print("=" * 60)

    # -----------------------------------------------------
    # Facebook
    # -----------------------------------------------------

    page_id = get_page_info()

    # -----------------------------------------------------
    # Movies
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
            "No movies available."
        )

        return 0

    # -----------------------------------------------------
    # Choose
    # -----------------------------------------------------

    movie = choose_movie(
        movies,
        posted
    )

    if not movie:

        print(
            "No new movie available for Reel."
        )

        return 0

    title = movie_title(
        movie
    )

    mid = movie_id(
        movie
    )

    print("")
    print(
        f"Selected movie: {title}"
    )

    print(
        f"TMDB ID: {mid}"
    )

    # -----------------------------------------------------
    # Poster
    # -----------------------------------------------------

    poster_url = get_poster_url(
        movie
    )

    poster_path = None
    video_path = None

    try:

        poster_path = download_poster(
            poster_url
        )

        # -------------------------------------------------
        # Create video
        # -------------------------------------------------

        video_path = create_reel(
            movie,
            poster_path
        )

        # -------------------------------------------------
        # Caption
        # -------------------------------------------------

        caption = build_caption(
            movie
        )

        print("")
        print(
            "Caption:"
        )
        print(caption)

        # -------------------------------------------------
        # Facebook
        # -------------------------------------------------

        result = publish_reel(
            page_id,
            video_path,
            caption
        )

        # -------------------------------------------------
        # Save history
        # -------------------------------------------------

        posted.append(
            {
                "id":
                    mid,

                "type":
                    movie_type(
                        movie
                    ),

                "title":
                    title,

                "video_id":
                    result[
                        "video_id"
                    ],

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
            "MOVINS REEL FAILED"
        )
        print("=" * 60)

        print(
            str(e)
        )

        return 1

    finally:

        for path in (
            poster_path,
            video_path
        ):

            if path:

                try:
                    os.remove(path)
                except Exception:
                    pass


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    sys.exit(
        main()
    )
