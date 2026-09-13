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
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import arabic_reshaper
from bidi.algorithm import get_display


# =========================================================
# MOVINS — CINEMATIC REEL PUBLISHER
# =========================================================

GRAPH_VERSION = "v26.0"

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movie_reels.json"

WORK_DIR = Path("reel_work")
WORK_DIR.mkdir(exist_ok=True)

POSTER_FILE = WORK_DIR / "poster.jpg"
DESIGN_FILE = WORK_DIR / "design.png"
AUDIO_FILE = WORK_DIR / "cinematic_music.wav"
VIDEO_FILE = WORK_DIR / "movins_reel.mp4"

WIDTH = 1080
HEIGHT = 1920
DURATION = 12
FPS = 30

FACEBOOK_PAGE_TOKEN = os.environ.get(
    "FACEBOOK_PAGE_TOKEN"
)

if not FACEBOOK_PAGE_TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing."
    )


# =========================================================
# LOG
# =========================================================

def log(text):
    print(text, flush=True)


# =========================================================
# COMMAND
# =========================================================

def run_command(command):

    log("")
    log("Running:")
    log(" ".join(str(x) for x in command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

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
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return default


def save_json(path, data):

    with open(
        path,
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
# CLEAN
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
        exist_ok=True
    )


# =========================================================
# MOVIES
# =========================================================

def load_movies():

    data = load_json(
        MOVIES_FILE,
        {"items": []}
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

    return items


# =========================================================
# POSTED
# =========================================================

def load_posted():

    data = load_json(
        POSTED_FILE,
        []
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data.get(
            "items",
            []
        )

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
            result.add(
                str(value)
            )

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


def movie_title(movie):

    value = (
        movie.get("title")
        or movie.get("name")
        or movie.get("original_title")
        or movie.get("original_name")
        or "MOVINS"
    )

    return str(value).strip()


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


def movie_rating(movie):

    value = (
        movie.get("rating")
        or movie.get("vote_average")
    )

    if value is None:
        return ""

    try:
        return "{:.1f}".format(
            float(value)
        )

    except Exception:
        return str(value)


def movie_type(movie):

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
        return "مسلسل"

    return "فيلم"


def movie_prefix(movie):

    if movie_type(movie) == "مسلسل":
        return "tv"

    return "movie"


# =========================================================
# SELECT MOVIE
# =========================================================

def choose_movie(
    movies,
    already_posted
):

    candidates = []

    for movie in movies:

        if not isinstance(movie, dict):
            continue

        mid = movie_id(movie)

        if not mid:
            continue

        if mid in already_posted:
            continue

        poster = (
            movie.get("poster")
            or movie.get("poster_url")
            or movie.get("image")
        )

        if not poster:
            continue

        try:
            popularity = float(
                movie.get(
                    "popularity",
                    0
                ) or 0
            )
        except Exception:
            popularity = 0

        try:
            rating = float(
                movie.get(
                    "rating",
                    0
                ) or 0
            )
        except Exception:
            rating = 0

        try:
            votes = float(
                movie.get(
                    "vote_count",
                    0
                ) or 0
            )
        except Exception:
            votes = 0

        score = (
            popularity
            + rating * 2
            + math.log10(
                votes + 1
            )
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
# FIND ARABIC FONT
# =========================================================

def find_arabic_font():

    preferred_names = [
        "NotoNaskhArabic-Regular.ttf",
        "NotoNaskhArabicUI-Regular.ttf",
        "NotoSansArabic-Regular.ttf",
        "NotoSansArabicUI-Regular.ttf",
    ]

    search_roots = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
    ]

    for root in search_roots:

        if not os.path.exists(root):
            continue

        for current, dirs, files in os.walk(root):

            for filename in files:

                if filename in preferred_names:

                    path = os.path.join(
                        current,
                        filename
                    )

                    log(
                        "Arabic font: "
                        + path
                    )

                    return path

    # Second search
    for root in search_roots:

        if not os.path.exists(root):
            continue

        for current, dirs, files in os.walk(root):

            for filename in files:

                lower = filename.lower()

                if (
                    lower.endswith(".ttf")
                    and (
                        "naskh" in lower
                        or "arabic" in lower
                    )
                ):

                    path = os.path.join(
                        current,
                        filename
                    )

                    log(
                        "Arabic font found: "
                        + path
                    )

                    return path

    raise RuntimeError(
        "Arabic font not found. "
        "Noto Arabic fonts must be installed."
    )


# =========================================================
# ARABIC SHAPING
# =========================================================

def arabic_text(text):

    reshaped = arabic_reshaper.reshape(
        str(text)
    )

    return get_display(
        reshaped
    )


# =========================================================
# DOWNLOAD POSTER
# =========================================================

def download_poster(movie):

    url = (
        movie.get("poster")
        or movie.get("poster_url")
        or movie.get("image")
    )

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
# COVER POSTER
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
# DRAW CENTERED TEXT
# =========================================================

def centered_text(
    draw,
    text,
    font,
    y,
    fill,
    stroke_width=0
):

    shaped = arabic_text(
        text
    )

    box = draw.textbbox(
        (0, 0),
        shaped,
        font=font,
        stroke_width=stroke_width
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
        shaped,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=(0, 0, 0, 230)
    )


# =========================================================
# CREATE DESIGN
# =========================================================

def create_design(movie):

    font_path = find_arabic_font()

    image = prepare_poster().convert(
        "RGBA"
    )

    # Slight cinematic darkening
    dark = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 55)
    )

    image = Image.alpha_composite(
        image,
        dark
    )

    # Bottom dark panel
    panel = Image.new(
        "RGBA",
        (
            WIDTH,
            760
        ),
        (0, 0, 0, 0)
    )

    panel_draw = ImageDraw.Draw(
        panel
    )

    panel_draw.rounded_rectangle(
        (
            35,
            35,
            WIDTH - 35,
            725
        ),
        radius=45,
        fill=(8, 10, 17, 232),
        outline=(255, 255, 255, 35),
        width=2
    )

    image.alpha_composite(
        panel,
        (
            0,
            1110
        )
    )

    draw = ImageDraw.Draw(
        image
    )

    # Fonts
    brand_font = ImageFont.truetype(
        font_path,
        62
    )

    category_font = ImageFont.truetype(
        font_path,
        40
    )

    title_size = 70

    title = movie_title(
        movie
    )

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
        43
    )

    cta_font = ImageFont.truetype(
        font_path,
        43
    )

    site_font = ImageFont.truetype(
        font_path,
        35
    )

    # -----------------------------------------------------
    # BRAND
    # -----------------------------------------------------

    centered_text(
        draw,
        "MOVINS",
        brand_font,
        80,
        (255, 255, 255, 255),
        2
    )

    centered_text(
        draw,
        "أفلام ومسلسلات",
        category_font,
        160,
        (235, 235, 235, 255),
        1
    )

    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    centered_text(
        draw,
        movie_type(movie),
        category_font,
        1190,
        (210, 210, 215, 255),
        1
    )

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    centered_text(
        draw,
        title,
        title_font,
        1280,
        (255, 255, 255, 255),
        2
    )

    # -----------------------------------------------------
    # INFO
    # -----------------------------------------------------

    year = movie_year(
        movie
    )

    rating = movie_rating(
        movie
    )

    info = []

    if year:
        info.append(
            year
        )

    if rating:
        info.append(
            "⭐ " + rating + " / 10"
        )

    if info:

        centered_text(
            draw,
            "   •   ".join(info),
            info_font,
            1420,
            (225, 225, 230, 255),
            1
        )

    # -----------------------------------------------------
    # CTA
    # -----------------------------------------------------

    centered_text(
        draw,
        "شاهد التفاصيل على MOVINS",
        cta_font,
        1535,
        (245, 190, 65, 255),
        1
    )

    # -----------------------------------------------------
    # WEBSITE
    # -----------------------------------------------------

    centered_text(
        draw,
        "nownex.github.io/movins",
        site_font,
        1640,
        (220, 220, 225, 255),
        1
    )

    # -----------------------------------------------------
    # SMALL DECORATION
    # -----------------------------------------------------

    draw.line(
        (
            260,
            1735,
            820,
            1735
        ),
        fill=(245, 190, 65, 180),
        width=3
    )

    image.convert(
        "RGB"
    ).save(
        DESIGN_FILE,
        "PNG",
        optimize=True
    )

    log(
        "Professional Arabic design created."
    )


# =========================================================
# SYNTHESIZED CINEMATIC MUSIC
# =========================================================

def piano_note(
    frequency,
    t,
    duration
):

    if t < 0 or t > duration:
        return 0.0

    attack = min(
        1.0,
        t / 0.025
    )

    release = min(
        1.0,
        (
            duration - t
        ) / 0.35
    )

    envelope = (
        attack
        * release
    )

    # Piano-like harmonics
    value = 0.0

    value += (
        math.sin(
            2
            * math.pi
            * frequency
            * t
        )
        * 0.50
    )

    value += (
        math.sin(
            2
            * math.pi
            * frequency
            * 2
            * t
        )
        * 0.20
    )

    value += (
        math.sin(
            2
            * math.pi
            * frequency
            * 3
            * t
        )
        * 0.08
    )

    value += (
        math.sin(
            2
            * math.pi
            * frequency
            * 4
            * t
        )
        * 0.035
    )

    # Natural decay
    decay = math.exp(
        -2.7 * t
    )

    return (
        value
        * envelope
        * decay
    )


def create_music():

    log(
        "Creating cinematic original music..."
    )

    sample_rate = 44100

    total = int(
        sample_rate
        * DURATION
    )

    # Cinematic progression
    progression = [
        [261.63, 329.63, 392.00],
        [220.00, 277.18, 329.63],
        [174.61, 220.00, 261.63],
        [196.00, 246.94, 293.66],
    ]

    melody = [
        523.25,
        493.88,
        440.00,
        392.00,
        440.00,
        493.88,
        523.25,
        587.33,
    ]

    frames = []

    for i in range(total):

        t = (
            i
            / sample_rate
        )

        # -------------------------------------------------
        # FADE
        # -------------------------------------------------

        fade_in = min(
            1.0,
            t / 1.2
        )

        fade_out = min(
            1.0,
            (
                DURATION - t
            ) / 1.4
        )

        master = min(
            fade_in,
            fade_out
        )

        # -------------------------------------------------
        # CHORD PAD
        # -------------------------------------------------

        chord_index = int(
            t / 3.0
        ) % len(progression)

        chord = progression[
            chord_index
        ]

        pad = 0.0

        for freq in chord:

            pad += (
                math.sin(
                    2
                    * math.pi
                    * freq
                    * t
                )
                * 0.055
            )

            pad += (
                math.sin(
                    2
                    * math.pi
                    * freq
                    * 0.5
                    * t
                )
                * 0.025
            )

        # -------------------------------------------------
        # PIANO MELODY
        # -------------------------------------------------

        beat = 0.75

        note_index = int(
            t / beat
        )

        note_start = (
            note_index
            * beat
        )

        local_t = (
            t
            - note_start
        )

        note = melody[
            note_index
            % len(melody)
        ]

        piano = piano_note(
            note,
            local_t,
            0.68
        )

        piano *= 0.22

        # -------------------------------------------------
        # BASS
        # -------------------------------------------------

        bass_freq = (
            chord[0]
            / 2
        )

        bass = (
            math.sin(
                2
                * math.pi
                * bass_freq
                * t
            )
            * 0.045
        )

        bass *= (
            0.7
            + 0.3
            * math.sin(
                2
                * math.pi
                * 0.5
                * t
            )
        )

        # -------------------------------------------------
        # SOFT PERCUSSION
        # -------------------------------------------------

        beat_position = (
            t % 1.5
        )

        kick_distance = min(
            beat_position,
            1.5 - beat_position
        )

        kick = 0.0

        if kick_distance < 0.08:

            kt = kick_distance

            kick = (
                math.sin(
                    2
                    * math.pi
                    * (
                        70
                        - 35 * kt
                    )
                    * kt
                )
                * math.exp(
                    -35 * kt
                )
                * 0.10
            )

        # -------------------------------------------------
        # AIR / ATMOSPHERE
        # -------------------------------------------------

        air = (
            math.sin(
                2
                * math.pi
                * 880
                * t
            )
            * 0.006
        )

        value = (
            pad
            + piano
            + bass
            + kick
            + air
        )

        value *= master

        # Gentle stereo
        left = value

        right = (
            value
            * (
                0.94
                + 0.06
                * math.sin(
                    2
                    * math.pi
                    * 0.18
                    * t
                )
            )
        )

        left_i = int(
            max(
                -1,
                min(
                    1,
                    left
                )
            )
            * 32767
        )

        right_i = int(
            max(
                -1,
                min(
                    1,
                    right
                )
            )
            * 32767
        )

        frames.append(
            struct.pack(
                "<hh",
                left_i,
                right_i
            )
        )

    with wave.open(
        str(AUDIO_FILE),
        "wb"
    ) as wav:

        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(
            sample_rate
        )

        wav.writeframes(
            b"".join(frames)
        )

    log(
        "Cinematic music created."
    )


# =========================================================
# CREATE VIDEO
# =========================================================

def create_video():

    log(
        "Creating MOVINS Reel..."
    )

    filter_complex = (
        "[0:v]"
        "scale="
        + str(WIDTH)
        + ":"
        + str(HEIGHT)
        + ","
        "zoompan="
        "z='min(zoom+0.0007,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=1:"
        "s="
        + str(WIDTH)
        + "x"
        + str(HEIGHT)
        + ":"
        "fps="
        + str(FPS)
        + ","
        "format=yuv420p"
        "[v]"
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
        "veryfast",

        "-crf",
        "21",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "44100",

        "-shortest",

        "-movflags",
        "+faststart",

        str(VIDEO_FILE)
    ]

    run_command(
        command
    )

    if not VIDEO_FILE.exists():
        raise RuntimeError(
            "Reel video was not created."
        )

    log(
        "Video created: "
        + str(
            VIDEO_FILE.stat().st_size
        )
        + " bytes"
    )


# =========================================================
# FACEBOOK
# =========================================================

def get_page():

    url = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/me"
    )

    response = requests.get(
        url,
        params={
            "fields": "id,name",
            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=30
    )

    if not response.ok:

        raise RuntimeError(
            "Facebook page lookup failed:\n"
            + response.text
        )

    data = response.json()

    page_id = data.get("id")
    page_name = data.get("name")

    if not page_id:

        raise RuntimeError(
            "Facebook Page ID not found."
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
# CAPTION
# =========================================================

def create_caption(movie):

    title = movie_title(
        movie
    )

    year = movie_year(
        movie
    )

    rating = movie_rating(
        movie
    )

    prefix = movie_prefix(
        movie
    )

    mid = movie_id(
        movie
    )

    url = (
        "https://nownex.github.io/movins/"
        "?movie="
        + prefix
        + "-"
        + str(mid)
    )

    lines = [
        "🎬 " + title
    ]

    if year:
        lines.append(
            "📅 " + year
        )

    if rating:
        lines.append(
            "⭐ " + rating + " / 10"
        )

    lines.extend(
        [
            "",
            "🍿 شاهد التفاصيل على MOVINS",
            url,
            "",
            "#MOVINS #Movies #Film #Series"
        ]
    )

    return "\n".join(
        lines
    )


# =========================================================
# FACEBOOK REEL
# =========================================================

def publish_reel(
    page_id,
    caption
):

    size = VIDEO_FILE.stat().st_size

    endpoint = (
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/"
        + str(page_id)
        + "/video_reels"
    )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    log(
        "Starting Facebook Reel upload..."
    )

    start = requests.post(
        endpoint,
        data={
            "upload_phase": "start",
            "access_token":
                FACEBOOK_PAGE_TOKEN
        },
        timeout=60
    )

    if not start.ok:

        raise RuntimeError(
            "Facebook upload start failed:\n"
            + start.text
        )

    start_data = start.json()

    upload_url = start_data.get(
        "upload_url"
    )

    video_id = (
        start_data.get("video_id")
        or start_data.get("id")
    )

    if not upload_url:

        raise RuntimeError(
            "Facebook did not return upload_url."
        )

    # -----------------------------------------------------
    # UPLOAD FILE
    # -----------------------------------------------------

    log(
        "Uploading video file..."
    )

    with open(
        VIDEO_FILE,
        "rb"
    ) as video:

        upload = requests.post(
            upload_url,
            headers={
                "Authorization":
                    "OAuth "
                    + FACEBOOK_PAGE_TOKEN,

                "offset": "0",

                "file_size":
                    str(size)
            },
            data=video,
            timeout=300
        )

    if not upload.ok:

        raise RuntimeError(
            "Facebook video upload failed:\n"
            + upload.text
        )

    log(
        "Video uploaded."
    )

    # -----------------------------------------------------
    # FINISH
    # -----------------------------------------------------

    finish_data = {
        "upload_phase": "finish",
        "video_state": "PUBLISHED",
        "description": caption,
        "access_token":
            FACEBOOK_PAGE_TOKEN
    }

    if video_id:
        finish_data[
            "video_id"
        ] = video_id

    finish = requests.post(
        endpoint,
        data=finish_data,
        timeout=120
    )

    if not finish.ok:

        raise RuntimeError(
            "Facebook Reel publish failed:\n"
            + finish.text
        )

    result = finish.json()

    log(
        "Facebook Reel published successfully."
    )

    return result


# =========================================================
# HISTORY
# =========================================================

def save_history(
    posted,
    movie,
    facebook_result
):

    entry = {
        "id": movie_id(movie),
        "tmdb_id": movie_id(movie),
        "title": movie_title(movie),
        "year": movie_year(movie),
        "type": movie_type(movie),
        "rating": movie_rating(movie),
        "posted_at": int(time.time()),
        "facebook_result": facebook_result
    }

    posted.append(
        entry
    )

    save_json(
        POSTED_FILE,
        posted
    )

    log(
        "Reel history saved."
    )


# =========================================================
# MAIN
# =========================================================

def main():

    log("")
    log("======================================")
    log("MOVINS CINEMATIC REEL")
    log("======================================")

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
        "Already posted: "
        + str(len(already_posted))
    )

    movie = choose_movie(
        movies,
        already_posted
    )

    if not movie:

        log(
            "No new movie available."
        )

        return

    log("")
    log(
        "Selected movie: "
        + movie_title(movie)
    )

    log(
        "TMDB ID: "
        + str(movie_id(movie))
    )

    # Poster
    download_poster(
        movie
    )

    # Arabic design
    create_design(
        movie
    )

    # Original music
    create_music()

    # Video
    create_video()

    # Facebook
    page_id = get_page()

    caption = create_caption(
        movie
    )

    result = publish_reel(
        page_id,
        caption
    )

    # Save only after successful publishing
    save_history(
        posted,
        movie,
        result
    )

    log("")
    log("======================================")
    log("MOVINS REEL SUCCESS")
    log("======================================")


if __name__ == "__main__":
    main()
