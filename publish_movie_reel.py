import os
import json
import time
import math
import wave
import struct
import shutil
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


# =========================================================
# MOVINS — CINEMATIC REEL PUBLISHER
# =========================================================

GRAPH_VERSION = "v26.0"

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

WORK_DIR = Path("reel_work")

POSTER_FILE = WORK_DIR / "poster.jpg"
DESIGN_FILE = WORK_DIR / "design.jpg"
AUDIO_FILE = WORK_DIR / "cinematic_music.wav"
VIDEO_FILE = WORK_DIR / "movins_reel.mp4"

WIDTH = 1080
HEIGHT = 1920

DURATION = 12
FPS = 30
SAMPLE_RATE = 44100


FACEBOOK_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")


# =========================================================
# BASIC CHECKS
# =========================================================

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing.")


# =========================================================
# LOGGING
# =========================================================

def log(text):
    print(str(text), flush=True)


# =========================================================
# COMMAND
# =========================================================

def run_command(command):

    log("")
    log("RUNNING:")
    log(" ".join(str(x) for x in command))
    log("")

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    if result.stdout:
        print(result.stdout, flush=True)

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed with exit code "
            + str(result.returncode)
        )


# =========================================================
# JSON
# =========================================================

def load_json(path, default):

    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        log("JSON load warning: " + str(e))
        return default


def save_json(path, data):

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# CLEAN WORK DIRECTORY
# =========================================================

def clean_work():

    if WORK_DIR.exists():

        for item in WORK_DIR.iterdir():

            try:

                if item.is_file():
                    item.unlink()

                elif item.is_dir():
                    shutil.rmtree(item)

            except Exception:
                pass

    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# =========================================================
# LOAD MOVIES
# =========================================================

def load_movies():

    data = load_json(
        MOVIES_FILE,
        {"items": []}
    )

    if isinstance(data, dict):
        items = data.get("items", [])

    elif isinstance(data, list):
        items = data

    else:
        items = []

    if not isinstance(items, list):
        items = []

    return items


# =========================================================
# POSTED HISTORY
# =========================================================

def load_posted():

    data = load_json(
        POSTED_FILE,
        []
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data.get("items", [])

    return []


def posted_ids(posted):

    result = set()

    for item in posted:

        if isinstance(item, dict):

            value = (
                item.get("id")
                or item.get("tmdb_id")
                or item.get("movie_id")
            )

        else:
            value = item

        if value is not None:
            result.add(str(value))

    return result


# =========================================================
# MOVIE HELPERS
# =========================================================

def movie_id(movie):

    value = (
        movie.get("id")
        or movie.get("tmdb_id")
    )

    if value is None:
        return None

    return str(value)


def movie_prefix(movie):

    value = (
        movie.get("detailed_type")
        or movie.get("type")
        or ""
    )

    text = str(value).lower()

    if (
        "مسلسل" in text
        or "tv" in text
        or "series" in text
    ):
        return "tv"

    return "movie"


def movie_type(movie):

    if movie_prefix(movie) == "tv":
        return "TV SERIES"

    return "MOVIE"


def contains_arabic(text):

    if not text:
        return False

    for char in str(text):

        if (
            "\u0600" <= char <= "\u06ff"
            or "\u0750" <= char <= "\u077f"
            or "\u08a0" <= char <= "\u08ff"
        ):
            return True

    return False


# =========================================================
# TMDB ENGLISH TITLE
# =========================================================

def get_english_tmdb_title(mid, media_type):

    if not TMDB_API_KEY:
        return None

    if media_type == "tv":
        endpoint = (
            "https://api.themoviedb.org/3/tv/"
            + str(mid)
        )
    else:
        endpoint = (
            "https://api.themoviedb.org/3/movie/"
            + str(mid)
        )

    try:

        response = requests.get(
            endpoint,
            params={
                "api_key": TMDB_API_KEY,
                "language": "en-US"
            },
            timeout=20
        )

        if not response.ok:
            return None

        data = response.json()

        title = (
            data.get("title")
            or data.get("name")
            or data.get("original_title")
            or data.get("original_name")
        )

        if not title:
            return None

        title = str(title).strip()

        if contains_arabic(title):
            return None

        return title

    except Exception as e:

        log(
            "TMDB title lookup failed: "
            + str(e)
        )

        return None


def movie_title(movie):

    mid = movie_id(movie)
    media_type = movie_prefix(movie)

    candidates = [
        movie.get("original_title"),
        movie.get("original_name")
    ]

    for value in candidates:

        if value:

            value = str(value).strip()

            if value and not contains_arabic(value):
                return value

    if mid:

        title = get_english_tmdb_title(
            mid,
            media_type
        )

        if title:
            return title

    local_title = (
        movie.get("title")
        or movie.get("name")
        or ""
    )

    local_title = str(
        local_title
    ).strip()

    if local_title and not contains_arabic(local_title):
        return local_title

    return "MOVINS FEATURE"


# =========================================================
# YEAR
# =========================================================

def movie_year(movie):

    value = movie.get("year")

    if value:
        return str(value)

    date = (
        movie.get("release_date")
        or movie.get("first_air_date")
    )

    if date:
        return str(date)[:4]

    return ""


# =========================================================
# RATING
# =========================================================

def movie_rating(movie):

    value = (
        movie.get("rating")
        or movie.get("vote_average")
    )

    if value is None:
        return ""

    try:
        return "{:.1f}".format(float(value))

    except Exception:
        return str(value)


# =========================================================
# POSTER URL
# =========================================================

def poster_url(movie):

    return (
        movie.get("poster")
        or movie.get("poster_url")
        or movie.get("image")
    )


# =========================================================
# SELECT MOVIE
# =========================================================

def choose_movie(movies, already_posted):

    candidates = []

    for movie in movies:

        if not isinstance(movie, dict):
            continue

        mid = movie_id(movie)

        if not mid:
            continue

        if mid in already_posted:
            continue

        if not poster_url(movie):
            continue

        try:
            popularity = float(
                movie.get("popularity", 0) or 0
            )
        except Exception:
            popularity = 0

        try:
            rating = float(
                movie.get("rating", 0) or 0
            )
        except Exception:
            rating = 0

        try:
            votes = float(
                movie.get("vote_count", 0) or 0
            )
        except Exception:
            votes = 0

        score = (
            popularity
            + rating * 2
            + math.log10(votes + 1)
        )

        candidates.append(
            (
                score,
                movie
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return candidates[0][1]


# =========================================================
# FONT
# =========================================================

def find_font():

    fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]

    for font in fonts:

        if os.path.exists(font):
            return font

    raise RuntimeError(
        "No suitable font found."
    )


# =========================================================
# DOWNLOAD POSTER
# =========================================================

def download_poster(movie):

    url = poster_url(movie)

    if not url:
        raise RuntimeError(
            "Poster URL missing."
        )

    log(
        "Downloading poster..."
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    with open(
        POSTER_FILE,
        "wb"
    ) as f:

        f.write(
            response.content
        )

    log(
        "Poster downloaded: "
        + str(
            POSTER_FILE.stat().st_size
        )
        + " bytes"
    )


# =========================================================
# PREPARE POSTER
# =========================================================

def prepare_poster():

    image = Image.open(
        POSTER_FILE
    ).convert("RGB")

    source_ratio = (
        image.width
        / image.height
    )

    target_ratio = (
        WIDTH
        / HEIGHT
    )

    if source_ratio > target_ratio:

        new_height = HEIGHT

        new_width = int(
            new_height
            * source_ratio
        )

    else:

        new_width = WIDTH

        new_height = int(
            new_width
            / source_ratio
        )

    image = image.resize(
        (
            new_width,
            new_height
        ),
        Image.Resampling.LANCZOS
    )

    left = (
        new_width
        - WIDTH
    ) // 2

    top = (
        new_height
        - HEIGHT
    ) // 2

    image = image.crop(
        (
            left,
            top,
            left + WIDTH,
            top + HEIGHT
        )
    )

    return image


# =========================================================
# CENTER TEXT
# =========================================================

def centered_text(
    draw,
    text,
    font,
    y,
    fill,
    stroke=0
):

    text = str(text)

    box = draw.textbbox(
        (0, 0),
        text,
        font=font,
        stroke_width=stroke
    )

    text_width = (
        box[2]
        - box[0]
    )

    x = (
        WIDTH
        - text_width
    ) / 2

    draw.text(
        (
            x,
            y
        ),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke,
        stroke_fill=(0, 0, 0)
    )


# =========================================================
# CREATE DESIGN
# =========================================================

def create_design(movie):

    font_path = find_font()

    image = prepare_poster().convert(
        "RGBA"
    )

    # Dark cinematic overlay
    overlay = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 55)
    )

    image = Image.alpha_composite(
        image,
        overlay
    )

    # Bottom panel
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (
            35,
            1140,
            WIDTH - 35,
            1810
        ),
        radius=42,
        fill=(5, 8, 14, 235),
        outline=(255, 255, 255, 50),
        width=2
    )

    brand_font = ImageFont.truetype(
        font_path,
        64
    )

    category_font = ImageFont.truetype(
        font_path,
        38
    )

    title = movie_title(movie)

    title_size = 70

    if len(title) > 28:
        title_size = 58

    if len(title) > 40:
        title_size = 48

    title_font = ImageFont.truetype(
        font_path,
        title_size
    )

    info_font = ImageFont.truetype(
        font_path,
        42
    )

    cta_font = ImageFont.truetype(
        font_path,
        40
    )

    site_font = ImageFont.truetype(
        font_path,
        32
    )

    # Brand
    centered_text(
        draw,
        "MOVINS",
        brand_font,
        75,
        (255, 255, 255),
        2
    )

    centered_text(
        draw,
        "MOVIES & SERIES",
        category_font,
        155,
        (235, 235, 235),
        1
    )

    # Type
    centered_text(
        draw,
        movie_type(movie),
        category_font,
        1205,
        (205, 205, 215),
        1
    )

    # Title
    centered_text(
        draw,
        title,
        title_font,
        1295,
        (255, 255, 255),
        2
    )

    year = movie_year(movie)
    rating = movie_rating(movie)

    info = []

    if year:
        info.append(year)

    if rating:
        info.append(
            "RATING "
            + rating
            + " / 10"
        )

    if info:

        centered_text(
            draw,
            "  •  ".join(info),
            info_font,
            1415,
            (225, 225, 230),
            1
        )

    centered_text(
        draw,
        "WATCH DETAILS ON MOVINS",
        cta_font,
        1535,
        (245, 190, 65),
        1
    )

    centered_text(
        draw,
        "nownex.github.io/movins",
        site_font,
        1625,
        (220, 220, 225),
        1
    )

    draw.line(
        (
            270,
            1710,
            810,
            1710
        ),
        fill=(245, 190, 65),
        width=3
    )

    image.convert(
        "RGB"
    ).save(
        DESIGN_FILE,
        "JPEG",
        quality=95
    )

    log(
        "Design created: "
        + str(DESIGN_FILE)
    )


# =========================================================
# CINEMATIC AUDIO
# =========================================================

def create_music():

    log(
        "Creating cinematic music..."
    )

    sample_rate = SAMPLE_RATE

    total = int(
        sample_rate
        * DURATION
    )

    # Simple cinematic progression
    progression = [
        [261.63, 329.63, 392.00],
        [220.00, 277.18, 329.63],
        [174.61, 220.00, 261.63],
        [196.00, 246.94, 293.66]
    ]

    melody = [
        523.25,
        493.88,
        440.00,
        392.00,
        440.00,
        493.88,
        523.25,
        587.33
    ]

    frames = []

    for i in range(total):

        t = i / sample_rate

        fade_in = min(
            1.0,
            t / 1.0
        )

        fade_out = min(
            1.0,
            (DURATION - t) / 1.5
        )

        envelope = (
            fade_in
            * fade_out
        )

        chord_index = int(
            t / 3
        )

        if chord_index >= len(progression):
            chord_index = len(progression) - 1

        chord = progression[chord_index]

        value = 0.0

        # Pad
        for frequency in chord:

            value += (
                math.sin(
                    2
                    * math.pi
                    * frequency
                    * t
                )
                * 0.055
            )

        # Melody
        note_index = int(
            t * 2
        ) % len(melody)

        note_frequency = melody[
            note_index
        ]

        note_time = (
            t * 2
        ) % 1.0

        note_env = math.exp(
            -3.5 * note_time
        )

        value += (
            math.sin(
                2
                * math.pi
                * note_frequency
                * t
            )
            * 0.16
            * note_env
        )

        # Low cinematic pulse
        bass_frequency = chord[0] / 2

        value += (
            math.sin(
                2
                * math.pi
                * bass_frequency
                * t
            )
            * 0.08
        )

        value *= envelope

        value = max(
            -0.95,
            min(
                0.95,
                value
            )
        )

        sample = int(
            value
            * 32767
        )

        frames.append(
            struct.pack(
                "<h",
                sample
            )
        )

    with wave.open(
        str(AUDIO_FILE),
        "wb"
    ) as wav:

        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(
            sample_rate
        )

        wav.writeframes(
            b"".join(frames)
        )

    log(
        "Music created: "
        + str(AUDIO_FILE)
    )


# =========================================================
# CREATE VIDEO
# =========================================================

def create_video():

    log(
        "Creating cinematic Reel..."
    )

    # Slight zoom effect
    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0008,1.10)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d="
        + str(DURATION * FPS)
        + ":"
        "s=1080x1920:"
        "fps="
        + str(FPS)
        + "[v]"
    )

    command = [
        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        str(DESIGN_FILE),

        "-i",
        str(AUDIO_FILE),

        "-filter_complex",
        filter_complex,

        "-map",
        "[v]",

        "-map",
        "1:a",

        "-t",
        str(DURATION),

        "-r",
        str(FPS),

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "21",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-ar",
        "44100",

        "-movflags",
        "+faststart",

        str(VIDEO_FILE)
    ]

    run_command(command)

    if not VIDEO_FILE.exists():
        raise RuntimeError(
            "Video file was not created."
        )

    size = VIDEO_FILE.stat().st_size

    log(
        "Reel video created: "
        + str(size)
        + " bytes"
    )


# =========================================================
# FACEBOOK PAGE
# =========================================================

def get_page_info():

    log(
        "Checking Facebook Page..."
    )

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/me"
    )

    response = requests.get(
        url,
        params={
            "fields": "id,name",
            "access_token": FACEBOOK_PAGE_TOKEN
        },
        timeout=30
    )

    data = response.json()

    log(
        "Facebook /me response:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook Page check failed: "
            + json.dumps(
                data,
                ensure_ascii=False
            )
        )

    page_id = data.get("id")
    page_name = data.get("name")

    if not page_id:
        raise RuntimeError(
            "Facebook Page ID was not returned."
        )

    log(
        "Facebook Page: "
        + str(page_name)
    )

    log(
        "Facebook Page ID: "
        + str(page_id)
    )

    return page_id


# =========================================================
# FACEBOOK START UPLOAD
# =========================================================

def facebook_start(page_id):

    log(
        "Starting Facebook Reel upload..."
    )

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/"
        + page_id
        + "/video_reels"
    )

    response = requests.post(
        url,
        params={
            "upload_phase": "start",
            "access_token": FACEBOOK_PAGE_TOKEN
        },
        timeout=30
    )

    data = response.json()

    log(
        "Facebook START response:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook START failed: "
            + json.dumps(
                data,
                ensure_ascii=False
            )
        )

    video_id = data.get("video_id")

    upload_url = data.get(
        "upload_url"
    )

    if not video_id:
        raise RuntimeError(
            "Facebook did not return video_id."
        )

    if not upload_url:
        upload_url = (
            "https://rupload.facebook.com/"
            "video-upload/"
            + GRAPH_VERSION
            + "/"
            + str(video_id)
        )

    return (
        str(video_id),
        upload_url
    )


# =========================================================
# FACEBOOK UPLOAD BINARY
# =========================================================

def facebook_upload(
    video_id,
    upload_url
):

    log(
        "Uploading video binary..."
    )

    file_size = VIDEO_FILE.stat().st_size

    log(
        "Video size: "
        + str(file_size)
        + " bytes"
    )

    with open(
        VIDEO_FILE,
        "rb"
    ) as video_file:

        response = requests.post(
            upload_url,
            headers={
                "Authorization":
                    "OAuth "
                    + FACEBOOK_PAGE_TOKEN,

                "offset":
                    "0",

                "file_size":
                    str(file_size),

                "Content-Type":
                    "application/octet-stream"
            },
            data=video_file,
            timeout=180
        )

    try:
        data = response.json()
    except Exception:
        data = {
            "raw": response.text
        }

    log(
        "Facebook UPLOAD response:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook binary upload failed: "
            + json.dumps(
                data,
                ensure_ascii=False
            )
        )

    return data


# =========================================================
# FACEBOOK STATUS
# =========================================================

def facebook_status(video_id):

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/"
        + str(video_id)
    )

    response = requests.get(
        url,
        params={
            "fields": "status",
            "access_token": FACEBOOK_PAGE_TOKEN
        },
        timeout=30
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "raw": response.text
        }

    if not response.ok:

        log(
            "Facebook STATUS error:"
        )

        log(
            json.dumps(
                data,
                ensure_ascii=False
            )
        )

        return None

    log(
        "Facebook STATUS:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    return data


# =========================================================
# WAIT FOR FACEBOOK PROCESSING
# =========================================================

def wait_for_processing(video_id):

    log(
        "Waiting for Facebook processing..."
    )

    for attempt in range(1, 31):

        time.sleep(3)

        log(
            "Processing check "
            + str(attempt)
            + "/30"
        )

        data = facebook_status(
            video_id
        )

        if not data:
            continue

        status = data.get(
            "status",
            {}
        )

        if isinstance(status, dict):

            video_status = str(
                status.get(
                    "video_status",
                    ""
                )
            ).lower()

            processing_phase = str(
                status.get(
                    "processing_phase",
                    ""
                )
            ).lower()

            log(
                "video_status="
                + video_status
                + " processing_phase="
                + processing_phase
            )

            if video_status in (
                "ready",
                "published",
                "complete",
                "completed"
            ):
                log(
                    "Facebook video is ready."
                )
                return True

            if video_status in (
                "error",
                "failed"
            ):
                raise RuntimeError(
                    "Facebook reported video processing failure."
                )

            if processing_phase in (
                "complete",
                "completed"
            ):
                return True

        # Some API responses may not expose
        # a detailed status. Continue polling.

    log(
        "Facebook did not return a final ready state "
        "within the polling window."
    )

    return False


# =========================================================
# FACEBOOK PUBLISH
# =========================================================

def facebook_publish(
    page_id,
    video_id,
    movie
):

    title = movie_title(movie)

    movins_url = (
        "https://nownex.github.io/movins/"
        + "?movie="
        + movie_prefix(movie)
        + "-"
        + movie_id(movie)
    )

    description = (
        "🎬 "
        + title
        + "\n\n"
        + "Discover the movie or series on MOVINS.\n"
        + movins_url
        + "\n\n"
        + "#MOVINS #Movies #Series #Film"
    )

    log(
        "Publishing Reel..."
    )

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/"
        + page_id
        + "/video_reels"
    )

    response = requests.post(
        url,
        params={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "title": title,
            "description": description,
            "access_token": FACEBOOK_PAGE_TOKEN
        },
        timeout=60
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "raw": response.text
        }

    log(
        "Facebook PUBLISH response:"
    )

    log(
        json.dumps(
            data,
            ensure_ascii=False
        )
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook PUBLISH failed: "
            + json.dumps(
                data,
                ensure_ascii=False
            )
        )

    if data.get("success") is False:

        raise RuntimeError(
            "Facebook returned success=false."
        )

    return data


# =========================================================
# SAVE HISTORY
# =========================================================

def save_posted(
    posted,
    movie,
    video_id,
    publish_response
):

    mid = movie_id(movie)

    record = {
        "id": mid,
        "tmdb_id": mid,
        "title": movie_title(movie),
        "type": movie_type(movie),
        "video_id": str(video_id),
        "published_at": int(time.time()),
        "movins_url": (
            "https://nownex.github.io/movins/"
            + "?movie="
            + movie_prefix(movie)
            + "-"
            + mid
        )
    }

    if isinstance(publish_response, dict):

        if publish_response.get("id"):
            record["facebook_id"] = str(
                publish_response.get("id")
            )

        if publish_response.get("success") is not None:
            record["facebook_success"] = (
                publish_response.get("success")
            )

    posted.append(record)

    save_json(
        POSTED_FILE,
        posted
    )

    log(
        "Reel history updated."
    )


# =========================================================
# MAIN
# =========================================================

def main():

    log("")
    log("======================================")
    log("MOVINS CINEMATIC REEL PUBLISHER")
    log("======================================")
    log("")

    clean_work()

    movies = load_movies()

    posted = load_posted()

    already_posted = posted_ids(
        posted
    )

    log(
        "Movies available: "
        + str(len(movies))
    )

    log(
        "Already posted Reels: "
        + str(len(already_posted))
    )

    movie = choose_movie(
        movies,
        already_posted
    )

    if not movie:

        log(
            "No eligible movie found."
        )

        return

    mid = movie_id(movie)
    title = movie_title(movie)

    log("")
    log(
        "Selected movie: "
        + title
    )

    log(
        "TMDB ID: "
        + str(mid)
    )

    log(
        "Type: "
        + movie_type(movie)
    )

    log(
        "Year: "
        + movie_year(movie)
    )

    log(
        "Rating: "
        + movie_rating(movie)
    )

    # ---------------------------------------------
    # CREATE REEL
    # ---------------------------------------------

    download_poster(movie)

    create_design(movie)

    create_music()

    create_video()

    # ---------------------------------------------
    # FACEBOOK
    # ---------------------------------------------

    page_id = get_page_info()

    video_id, upload_url = facebook_start(
        page_id
    )

    log(
        "Facebook video_id: "
        + str(video_id)
    )

    log(
        "Facebook upload URL received."
    )

    facebook_upload(
        video_id,
        upload_url
    )

    # ---------------------------------------------
    # WAIT
    # ---------------------------------------------

    ready = wait_for_processing(
        video_id
    )

    if not ready:

        raise RuntimeError(
            "Facebook upload was acknowledged, "
            "but processing was not confirmed. "
            "Reel was NOT marked as posted."
        )

    # ---------------------------------------------
    # PUBLISH
    # ---------------------------------------------

    publish_response = facebook_publish(
        page_id,
        video_id,
        movie
    )

    # ---------------------------------------------
    # SAVE ONLY AFTER SUCCESS
    # ---------------------------------------------

    save_posted(
        posted,
        movie,
        video_id,
        publish_response
    )

    log("")
    log("======================================")
    log("MOVINS REEL PUBLISHED SUCCESSFULLY")
    log("======================================")
    log(
        "Movie: "
        + title
    )
    log(
        "Facebook video_id: "
        + str(video_id)
    )
    log("======================================")


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
