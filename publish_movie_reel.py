import json
import os
import sys
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests


# =========================================================
# MOVINS — AUTOMATIC REEL MAKER
# =========================================================

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

GRAPH_VERSION = "v26.0"
GRAPH_URL = "https://graph.facebook.com/" + GRAPH_VERSION

FACEBOOK_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

SITE_URL = "https://nownex.github.io/movins/"

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

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
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
# FACEBOOK PAGE
# =========================================================

def get_page_info():

    url = GRAPH_URL + "/me"

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
        "Facebook Page: "
        + str(data.get("name", "Unknown"))
    )

    print(
        "Facebook Page ID: "
        + str(page_id)
    )

    return str(page_id)


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


def get_movie_id(movie):

    return str(
        movie.get("tmdb_id")
        or movie.get("id")
        or ""
    ).strip()


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


def get_movie_title(movie):

    return str(
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    ).strip()


def get_movie_year(movie):

    value = movie.get("year")

    if value:

        return str(value)

    date_value = (
        movie.get("release_date")
        or movie.get("first_air_date")
        or ""
    )

    return str(date_value)[:4]


def get_movie_rating(movie):

    try:

        return float(
            movie.get(
                "rating",
                0
            ) or 0
        )

    except Exception:

        return 0.0


def get_movie_popularity(movie):

    try:

        return float(
            movie.get(
                "popularity",
                0
            ) or 0
        )

    except Exception:

        return 0.0


# =========================================================
# POSTER
# =========================================================

def get_poster_url(movie):

    poster = movie.get("poster")

    if not poster:

        return None

    poster = str(
        poster
    ).strip()

    if poster.startswith("http://"):

        return poster

    if poster.startswith("https://"):

        return poster

    if poster.startswith("/"):

        return (
            "https://image.tmdb.org/t/p/w780"
            + poster
        )

    return None


# =========================================================
# CHOOSE MOVIE
# =========================================================

def choose_movie(
    movies,
    posted
):

    posted_ids = set()

    for item in posted:

        if not isinstance(
            item,
            dict
        ):

            continue

        item_id = item.get("id")

        if item_id is not None:

            posted_ids.add(
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

        if movie_id in posted_ids:

            continue

        poster = get_poster_url(
            movie
        )

        if not poster:

            continue

        popularity = get_movie_popularity(
            movie
        )

        rating = get_movie_rating(
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
        key=lambda item: (
            item[0],
            item[1]
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
        "Poster downloaded: "
        + str(
            round(
                len(response.content) / 1024,
                1
            )
        )
        + " KB"
    )

    return temp.name


# =========================================================
# TEXT FILE
# =========================================================

def create_text_file(
    text
):

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".txt",
        mode="w",
        encoding="utf-8"
    )

    temp.write(
        str(text)
    )

    temp.close()

    return temp.name


# =========================================================
# FIND FONT
# =========================================================

def find_font():

    fonts = [

        "/usr/share/fonts/truetype/noto/"
        "NotoSansArabic-Regular.ttf",

        "/usr/share/fonts/truetype/noto/"
        "NotoSans-Regular.ttf",

        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans.ttf"
    ]

    for font in fonts:

        if os.path.exists(font):

            print(
                "Using font: "
                + font
            )

            return font

    raise RuntimeError(
        "No compatible font found."
    )


# =========================================================
# CREATE CINEMATIC REEL
# =========================================================

def create_reel(
    movie,
    poster_path
):

    title = get_movie_title(
        movie
    )

    year = get_movie_year(
        movie
    )

    rating = get_movie_rating(
        movie
    )

    media_type = get_movie_type(
        movie
    )

    if media_type == "tv":

        type_text = "SERIES"

    else:

        type_text = "MOVIE"

    font = find_font()

    title_file = create_text_file(
        title
    )

    year_file = create_text_file(
        year
    )

    rating_file = create_text_file(
        "★ " + str(round(rating, 1)) + "/10"
    )

    type_file = create_text_file(
        type_text
    )

    output_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4"
    )

    output_path = output_file.name

    output_file.close()

    # =====================================================
    # FFmpeg filter
    # =====================================================

    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0007,1.10)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=360:"
        "s=1080x1920:"
        "fps=30,"
        "setsar=1"
        "[bg];"

        "[bg]"
        "drawbox="
        "x=0:"
        "y=1260:"
        "w=1080:"
        "h=660:"
        "color=black@0.70:"
        "t=fill"
        "[panel];"

        "[panel]"
        "drawtext="
        "fontfile=" + font + ":"
        "textfile=" + type_file + ":"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1335"
        "[t1];"

        "[t1]"
        "drawtext="
        "fontfile=" + font + ":"
        "textfile=" + title_file + ":"
        "fontcolor=white:"
        "fontsize=68:"
        "x=(w-text_w)/2:"
        "y=1420"
        "[t2];"

        "[t2]"
        "drawtext="
        "fontfile=" + font + ":"
        "textfile=" + year_file + ":"
        "fontcolor=white:"
        "fontsize=40:"
        "x=(w-text_w)/2:"
        "y=1535"
        "[t3];"

        "[t3]"
        "drawtext="
        "fontfile=" + font + ":"
        "textfile=" + rating_file + ":"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1610"
        "[t4];"

        "[t4]"
        "drawtext="
        "fontfile=" + font + ":"
        "text=MOVINS:"
        "fontcolor=white:"
        "fontsize=38:"
        "x=(w-text_w)/2:"
        "y=1740"
        "[t5];"

        "[t5]"
        "drawtext="
        "fontfile=" + font + ":"
        "text=Discover more on MOVINS:"
        "fontcolor=white:"
        "fontsize=30:"
        "x=(w-text_w)/2:"
        "y=1810"
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

        output_path
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
            result.stdout[-12000:]
        )

        raise RuntimeError(
            "FFmpeg failed to create Reel."
        )

    # =====================================================
    # Remove temporary text files
    # =====================================================

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
        output_path
    )

    print(
        "Reel created successfully: "
        + str(
            round(
                size / 1024 / 1024,
                2
            )
        )
        + " MB"
    )

    return output_path


# =========================================================
# FACEBOOK START
# =========================================================

def facebook_start(
    page_id
):

    url = (
        GRAPH_URL
        + "/"
        + page_id
        + "/video_reels"
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
# FACEBOOK UPLOAD
# =========================================================

def facebook_upload(
    upload_url,
    video_path
):

    file_size = os.path.getsize(
        video_path
    )

    headers = {
        "Authorization":
            "OAuth " + FACEBOOK_PAGE_TOKEN,

        "offset":
            "0",

        "file_size":
            str(file_size),

        "Content-Type":
            "application/octet-stream"
    }

    print(
        "Uploading Reel video to Facebook..."
    )

    with open(
        video_path,
        "rb"
    ) as video_file:

        response = requests.post(
            upload_url,
            headers=headers,
            data=video_file,
            timeout=600
        )

    if not response.ok:

        raise RuntimeError(
            "Facebook Reel upload failed:\n"
            + response.text
        )

    try:

        return response.json()

    except Exception:

        return {
            "response":
                response.text
        }


# =========================================================
# FACEBOOK FINISH
# =========================================================

def facebook_finish(
    page_id,
    video_id,
    caption
):

    url = (
        GRAPH_URL
        + "/"
        + page_id
        + "/video_reels"
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
# PUBLISH REEL
# =========================================================

def publish_reel(
    page_id,
    video_path,
    caption
):

    start_data = facebook_start(
        page_id
    )

    video_id = (
        start_data.get("video_id")
        or start_data.get("id")
    )

    upload_url = start_data.get(
        "upload_url"
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

    if not upload_url:

        raise RuntimeError(
            "Facebook did not return upload_url:\n"
            + json.dumps(
                start_data,
                ensure_ascii=False,
                indent=2
            )
        )

    facebook_upload(
        upload_url,
        video_path
    )

    finish_data = facebook_finish(
        page_id,
        video_id,
        caption
    )

    return {
        "video_id":
            video_id,

        "response":
            finish_data
    }


# =========================================================
# CAPTION
# =========================================================

def build_caption(
    movie
):

    title = get_movie_title(
        movie
    )

    year = get_movie_year(
        movie
    )

    rating = get_movie_rating(
        movie
    )

    movie_id = get_movie_id(
        movie
    )

    media_type = get_movie_type(
        movie
    )

    if media_type == "tv":

        prefix = "tv"

    else:

        prefix = "movie"

    link = (
        SITE_URL
        + "?movie="
        + prefix
        + "-"
        + movie_id
    )

    caption = (
        "🎬 "
        + title
        + "\n"
        + "📅 "
        + year
        + "\n"
        + "⭐ "
        + str(round(rating, 1))
        + "/10"
        + "\n\n"
        + "🍿 اكتشف المزيد على MOVINS:"
        + "\n"
        + link
        + "\n\n"
        + "#MOVINS #Movies #Series #Film"
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
        "Movies available: "
        + str(len(movies))
    )

    print(
        "Already posted Reels: "
        + str(len(posted))
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

    title = get_movie_title(
        movie
    )

    movie_id = get_movie_id(
        movie
    )

    print("")

    print(
        "Selected movie: "
        + title
    )

    print(
        "TMDB ID: "
        + movie_id
    )

    # -----------------------------------------------------
    # Poster
    # -----------------------------------------------------

    poster_url = get_poster_url(
        movie
    )

    if not poster_url:

        raise RuntimeError(
            "Selected movie has no poster."
        )

    poster_path = None
    video_path = None

    try:

        # -------------------------------------------------
        # Download poster
        # -------------------------------------------------

        poster_path = download_poster(
            poster_url
        )

        # -------------------------------------------------
        # Create Reel
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
            "Facebook caption:"
        )

        print(caption)

        # -------------------------------------------------
        # Publish
        # -------------------------------------------------

        result = publish_reel(
            page_id,
            video_path,
            caption
        )

        # -------------------------------------------------
        # Save history ONLY after success
        # -------------------------------------------------

        posted.append(
            {
                "id":
                    movie_id,

                "type":
                    get_movie_type(
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

    except Exception as error:

        print("")

        print("=" * 60)

        print(
            "MOVINS REEL FAILED"
        )

        print("=" * 60)

        print(
            "Error: "
            + str(error)
        )

        return 1

    finally:

        # -------------------------------------------------
        # Cleanup
        # -------------------------------------------------

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
