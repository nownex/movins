import json
import os
import requests


# =========================================================
# MOVINS — FACEBOOK PUBLISHER
# =========================================================

TOKEN = os.environ.get(
    "FACEBOOK_PAGE_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        "FACEBOOK_PAGE_TOKEN is missing"
    )


GRAPH_VERSION = "v26.0"

GRAPH_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}/me/photos"
)


# =========================================================
# FILES
# =========================================================

MOVIES_FILE = "movies.json"

POSTED_FILE = "posted_movies.json"

ROTATION_FILE = "facebook_rotation.json"


# =========================================================
# MOVINS WEBSITE
# =========================================================

SITE_URL = (
    "https://nownex.github.io/movins/"
)


# =========================================================
# SETTINGS
# =========================================================

# مهم:
# منشور واحد فقط في كل تشغيل.
MAX_POSTS_PER_RUN = 1

MAX_OVERVIEW_LENGTH = 420


# =========================================================
# ROTATION
#
# فيلم ثم مسلسل ثم فيلم ثم مسلسل...
#
# والفئات تتغير:
#
# رعب
# أكشن
# كوميديا
# دراما
# خيال علمي
# غموض
# جريمة
# مغامرة
# فانتازيا
# رومانسي
# رسوم متحركة
# إثارة
# =========================================================

GENRE_ROTATION = [

    "رعب",

    "أكشن",

    "كوميديا",

    "دراما",

    "خيال علمي",

    "غموض",

    "جريمة",

    "مغامرة",

    "فانتازيا",

    "رومانسي",

    "رسوم متحركة",

    "إثارة",

]


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

        data = json.load(
            file
        )


    items = data.get(
        "items",
        []
    )


    if not isinstance(
        items,
        list
    ):

        raise RuntimeError(
            "movies.json items must be a list"
        )


    return items


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

            data = json.load(
                file
            )


        if not isinstance(
            data,
            list
        ):

            return set()


        result = set()


        for item in data:

            if isinstance(
                item,
                dict
            ):

                item_id = str(
                    item.get(
                        "id",
                        ""
                    )
                ).strip()


                item_type = str(
                    item.get(
                        "type",
                        ""
                    )
                ).strip()


                if item_id:

                    result.add(
                        f"{item_type}:{item_id}"
                    )


            else:

                value = str(
                    item
                ).strip()


                if value:

                    result.add(
                        value
                    )


        return result


    except Exception as error:

        print(
            f"WARNING: could not read "
            f"{POSTED_FILE}: {error}"
        )


        return set()


# =========================================================
# SAVE POSTED
# =========================================================

def save_posted(
    posted
):

    with open(
        POSTED_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            sorted(
                list(posted)
            ),
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# LOAD ROTATION
# =========================================================

def load_rotation():

    default = {

        "type_index":
            0,

        "genre_index":
            0,

    }


    if not os.path.exists(
        ROTATION_FILE
    ):

        return default


    try:

        with open(
            ROTATION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )


        if not isinstance(
            data,
            dict
        ):

            return default


        try:

            type_index = int(
                data.get(
                    "type_index",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            type_index = 0


        try:

            genre_index = int(
                data.get(
                    "genre_index",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            genre_index = 0


        return {

            "type_index":
                type_index,

            "genre_index":
                genre_index,

        }


    except Exception as error:

        print(
            f"WARNING: could not read "
            f"{ROTATION_FILE}: {error}"
        )


        return default


# =========================================================
# SAVE ROTATION
# =========================================================

def save_rotation(
    rotation
):

    with open(
        ROTATION_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            rotation,
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# MEDIA TYPE
# =========================================================

def get_media_type(
    item
):

    item_type = str(
        item.get(
            "type",
            ""
        )
    ).strip().lower()


    if item_type in (
        "فيلم",
        "movie",
        "film"
    ):

        return "movie"


    return "tv"


# =========================================================
# ARABIC MEDIA TYPE
# =========================================================

def get_arabic_type(
    media_type
):

    if media_type == "movie":

        return "فيلم"

    return "مسلسل"


# =========================================================
# MOVIE ID
# =========================================================

def get_movie_id(
    item
):

    return str(
        item.get(
            "id",
            ""
        )
    ).strip()


# =========================================================
# UNIQUE MOVIE KEY
# =========================================================

def get_movie_key(
    item
):

    movie_id = get_movie_id(
        item
    )


    if not movie_id:

        return ""


    media_type = get_media_type(
        item
    )


    return (
        f"{media_type}:{movie_id}"
    )


# =========================================================
# DIRECT MOVIE URL
# =========================================================

def get_movie_url(
    item
):

    movie_id = get_movie_id(
        item
    )


    if not movie_id:

        return SITE_URL


    media_type = get_media_type(
        item
    )


    return (
        SITE_URL
        + "?movie="
        + media_type
        + "-"
        + movie_id
    )


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(
    value
):

    if value is None:

        return ""


    text = str(
        value
    )


    text = " ".join(
        text.split()
    )


    return text.strip()


# =========================================================
# SHORT OVERVIEW
# =========================================================

def build_short_overview(
    item
):

    overview = clean_text(
        item.get(
            "overview",
            ""
        )
    )


    if not overview:

        return (
            "اكتشف القصة والتفاصيل "
            "على MOVINS."
        )


    if len(
        overview
    ) <= MAX_OVERVIEW_LENGTH:

        return overview


    shortened = overview[
        :MAX_OVERVIEW_LENGTH
    ]


    if " " in shortened:

        shortened = shortened.rsplit(
            " ",
            1
        )[0]


    return (
        shortened
        + "..."
    )


# =========================================================
# GET GENRES LIST
# =========================================================

def get_genres_list(
    item
):

    genres = item.get(
        "genres",
        []
    )


    if isinstance(
        genres,
        list
    ):

        result = []


        for genre in genres:

            value = clean_text(
                genre
            )


            if value:

                result.append(
                    value
                )


        return result


    value = clean_text(
        genres
    )


    if value:

        return [value]


    return []


# =========================================================
# BUILD GENRES
# =========================================================

def build_genres(
    item
):

    genres = get_genres_list(
        item
    )


    if not genres:

        return ""


    return " • ".join(
        genres[:5]
    )


# =========================================================
# HASHTAGS
# =========================================================

def build_hashtags(
    item
):

    hashtags = item.get(
        "hashtags",
        ""
    )


    if isinstance(
        hashtags,
        list
    ):

        cleaned = []


        for value in hashtags:

            value = clean_text(
                value
            )


            if value:

                cleaned.append(
                    value
                )


        hashtags = " ".join(
            cleaned
        )


    hashtags = clean_text(
        hashtags
    )


    if hashtags:

        parts = hashtags.split()

        result = []


        for part in parts:

            part = part.strip()


            if not part:

                continue


            if not part.startswith(
                "#"
            ):

                part = "#" + part


            result.append(
                part
            )


        if result:

            return " ".join(
                result[:6]
            )


    media_type = get_media_type(
        item
    )


    if media_type == "movie":

        return (
            "#MOVINS "
            "#أفلام"
        )


    return (
        "#MOVINS "
        "#مسلسلات"
    )


# =========================================================
# RATING
# =========================================================

def get_rating(
    item
):

    try:

        rating = float(
            item.get(
                "rating"
            )
            or 0
        )


        if rating <= 0:

            return "—"


        return (
            f"{rating:.1f}/10"
        )


    except (
        TypeError,
        ValueError
    ):

        return "—"


# =========================================================
# POPULARITY
# =========================================================

def get_popularity(
    item
):

    try:

        return float(
            item.get(
                "popularity"
            )
            or 0
        )


    except (
        TypeError,
        ValueError
    ):

        return 0.0


# =========================================================
# VOTE COUNT
# =========================================================

def get_vote_count(
    item
):

    try:

        return int(
            item.get(
                "vote_count"
            )
            or 0
        )


    except (
        TypeError,
        ValueError
    ):

        return 0


# =========================================================
# ENGAGING ENDINGS
# =========================================================

ENDINGS = [

    "👇 اكتشف بقية القصة والتفاصيل والتريلر على MOVINS:",

    "👇 هل تريد معرفة ما ينتظرك؟ اكتشف القصة كاملة والتريلر على MOVINS:",

    "👇 لمعرفة القصة كاملة والتفاصيل والتريلر، تابعها على MOVINS:",

    "👇 التفاصيل الكاملة والتريلر في MOVINS — اكتشف القصة قبل المشاهدة:",

    "👇 إذا أثارت القصة فضولك، اكتشف التفاصيل والتريلر على MOVINS:",

    "👇 أكمل اكتشاف القصة وشاهد التريلر والتفاصيل على MOVINS:"

]


# =========================================================
# GET ROTATING ENDING
# =========================================================

def get_ending(
    item
):

    movie_id = get_movie_id(
        item
    )


    try:

        number = int(
            movie_id
        )


        index = (
            number
            % len(ENDINGS)
        )


    except (
        ValueError,
        TypeError
    ):

        title = clean_text(
            item.get(
                "title",
                ""
            )
        )


        index = (
            len(title)
            % len(ENDINGS)
        )


    return ENDINGS[
        index
    ]


# =========================================================
# GENRE MATCH
# =========================================================

def genre_matches(
    item,
    wanted_genre
):

    genres = get_genres_list(
        item
    )


    if wanted_genre in genres:

        return True


    # -----------------------------------------------------
    # Special cases
    # -----------------------------------------------------

    if wanted_genre == "أكشن":

        return (
            "أكشن" in genres
            or
            "أكشن ومغامرة" in genres
        )


    if wanted_genre == "خيال علمي":

        return (
            "خيال علمي" in genres
            or
            "خيال علمي وفانتازيا" in genres
        )


    if wanted_genre == "رسوم متحركة":

        return (
            "رسوم متحركة" in genres
        )


    return False


# =========================================================
# FACEBOOK CAPTION
# =========================================================

def build_caption(
    item
):

    title = clean_text(
        item.get(
            "title"
        )
        or "بدون عنوان"
    )


    overview = build_short_overview(
        item
    )


    detailed_type = clean_text(
        item.get(
            "detailed_type"
        )
        or item.get(
            "type"
        )
        or "عمل"
    )


    year = clean_text(
        item.get(
            "year"
        )
        or "—"
    )


    genres = build_genres(
        item
    )


    rating_text = get_rating(
        item
    )


    movie_url = get_movie_url(
        item
    )


    hashtags = build_hashtags(
        item
    )


    ending = get_ending(
        item
    )


    lines = [

        f"🎬 {title}",

        "",

        overview,

        "",

        f"⭐ التقييم: {rating_text}",

        f"🎭 النوع: {detailed_type}",

        f"🎞️ التصنيف: "
        f"{genres or 'غير محدد'}",

        f"📅 السنة: {year}",

        "",

        ending,

        "",

        movie_url,

        "",

        hashtags

    ]


    return "\n".join(
        lines
    )


# =========================================================
# SELECT CANDIDATES
#
# أهم جزء في النظام.
#
# الأولوية:
#
# 1. نوع المحتوى المطلوب
# 2. الفئة المطلوبة
# 3. الشعبية Popularity
# 4. Vote Count
#
# التقييم ليس العامل الأساسي.
# =========================================================

def select_candidates(
    movies,
    posted,
    wanted_media_type,
    wanted_genre
):

    candidates = []


    for item in movies:

        movie_key = get_movie_key(
            item
        )


        if not movie_key:

            continue


        # لا تعيد نشر العمل
        if movie_key in posted:

            continue


        media_type = get_media_type(
            item
        )


        # نوع العمل
        if media_type != wanted_media_type:

            continue


        # الفئة المطلوبة
        if not genre_matches(
            item,
            wanted_genre
        ):

            continue


        popularity = get_popularity(
            item
        )


        vote_count = get_vote_count(
            item
        )


        # -------------------------------------------------
        # Ignore completely empty TMDB entries
        # -------------------------------------------------

        if (
            popularity <= 0
            and vote_count <= 0
        ):

            continue


        candidates.append(
            item
        )


    # =====================================================
    # SORT
    #
    # Popularity أولاً
    # Vote count ثانيًا
    #
    # لا نعطي Rating أولوية.
    # =====================================================

    candidates.sort(

        key=lambda item: (

            get_popularity(
                item
            ),

            get_vote_count(
                item
            ),

        ),

        reverse=True

    )


    return candidates


# =========================================================
# FALLBACK BY TYPE
#
# إذا لم نجد الفئة المطلوبة،
# نبحث عن أفضل عمل من نفس النوع.
#
# =========================================================

def select_type_fallback(
    movies,
    posted,
    wanted_media_type
):

    candidates = []


    for item in movies:

        movie_key = get_movie_key(
            item
        )


        if not movie_key:

            continue


        if movie_key in posted:

            continue


        if (
            get_media_type(
                item
            )
            != wanted_media_type
        ):

            continue


        popularity = get_popularity(
            item
        )


        vote_count = get_vote_count(
            item
        )


        if (
            popularity <= 0
            and vote_count <= 0
        ):

            continue


        candidates.append(
            item
        )


    candidates.sort(

        key=lambda item: (

            get_popularity(
                item
            ),

            get_vote_count(
                item
            ),

        ),

        reverse=True

    )


    return candidates


# =========================================================
# PUBLISH TO FACEBOOK
# =========================================================

def publish_to_facebook(
    item
):

    poster = clean_text(
        item.get(
            "poster"
        )
        or ""
    )


    if not poster:

        print(
            "SKIP: no poster"
        )

        return False


    caption = build_caption(
        item
    )


    movie_url = get_movie_url(
        item
    )


    payload = {

        "url":
            poster,

        "caption":
            caption,

        "published":
            "true",

        "access_token":
            TOKEN

    }


    print(
        "--------------------------------------"
    )


    print(
        "Publishing to Facebook"
    )


    print(
        f"Page ID: "
        f"1269050452957956"
    )


    print(
        f"Title: "
        f"{item.get('title', '')}"
    )


    print(
        f"ID: "
        f"{item.get('id', '')}"
    )


    print(
        f"Popularity: "
        f"{get_popularity(item):.2f}"
    )


    print(
        f"Rating: "
        f"{get_rating(item)}"
    )


    print(
        f"Vote Count: "
        f"{get_vote_count(item)}"
    )


    print(
        f"Direct Movie URL: "
        f"{movie_url}"
    )


    print(
        "--------------------------------------"
    )


    print(
        "Caption:"
    )


    print(
        caption
    )


    print(
        "--------------------------------------"
    )


    try:

        response = requests.post(

            GRAPH_URL,

            data=payload,

            timeout=60

        )


    except requests.RequestException as error:

        print(
            f"Facebook request error: "
            f"{error}"
        )

        return False


    try:

        result = response.json()


    except ValueError:

        print(
            "Facebook returned invalid JSON:"
        )


        print(
            response.text
        )


        return False


    if not response.ok:

        print(
            "Facebook API Error:"
        )


        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )


        return False


    print(
        "Facebook post successful."
    )


    print(
        "Post ID:",
        result.get(
            "post_id"
        )
        or result.get(
            "id"
        )
    )


    return True


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "======================================"
    )


    print(
        "MOVINS FACEBOOK PUBLISHER"
    )


    print(
        "======================================"
    )


    movies = load_movies()

    posted = load_posted()

    rotation = load_rotation()


    print(
        f"MOVINS items: "
        f"{len(movies)}"
    )


    print(
        f"Already posted: "
        f"{len(posted)}"
    )


    # =====================================================
    # CURRENT ROTATION
    # =====================================================

    type_index = (
        rotation.get(
            "type_index",
            0
        )
        % 2
    )


    genre_index = (
        rotation.get(
            "genre_index",
            0
        )
        % len(
            GENRE_ROTATION
        )
    )


    # 0 = movie
    # 1 = tv

    wanted_media_type = (
        "movie"
        if type_index == 0
        else "tv"
    )


    wanted_genre = (
        GENRE_ROTATION[
            genre_index
        ]
    )


    print(
        "======================================"
    )


    print(
        "CURRENT ROTATION:"
    )


    print(
        f"Type: "
        f"{get_arabic_type(wanted_media_type)}"
    )


    print(
        f"Genre: "
        f"{wanted_genre}"
    )


    print(
        "======================================"
    )


    # =====================================================
    # PRIMARY SELECTION
    # =====================================================

    candidates = select_candidates(

        movies,

        posted,

        wanted_media_type,

        wanted_genre

    )


    print(
        f"Candidates for "
        f"{get_arabic_type(wanted_media_type)} "
        f"+ {wanted_genre}: "
        f"{len(candidates)}"
    )


    # =====================================================
    # FALLBACK
    #
    # إذا لم توجد فئة محددة،
    # لا نكسر التناوب.
    #
    # نبحث عن أشهر عمل من نفس النوع.
    # =====================================================

    if not candidates:

        print(
            "No exact genre match."
        )


        print(
            "Using same-type popularity fallback."
        )


        candidates = select_type_fallback(

            movies,

            posted,

            wanted_media_type

        )


    # =====================================================
    # FINAL FALLBACK
    #
    # إذا لم نجد أي فيلم/مسلسل من النوع المطلوب،
    # نبحث عن أي عمل جديد.
    # =====================================================

    if not candidates:

        print(
            "No candidates for requested type."
        )


        print(
            "Using global popularity fallback."
        )


        global_candidates = []


        for item in movies:

            movie_key = get_movie_key(
                item
            )


            if not movie_key:

                continue


            if movie_key in posted:

                continue


            popularity = get_popularity(
                item
            )


            vote_count = get_vote_count(
                item
            )


            if (
                popularity <= 0
                and vote_count <= 0
            ):

                continue


            global_candidates.append(
                item
            )


        global_candidates.sort(

            key=lambda item: (

                get_popularity(
                    item
                ),

                get_vote_count(
                    item
                ),

            ),

            reverse=True

        )


        candidates = global_candidates


    # =====================================================
    # NOTHING
    # =====================================================

    if not candidates:

        print(
            "No new items available."
        )


        return


    # =====================================================
    # SHOW TOP CANDIDATES
    # =====================================================

    print(
        "TOP FACEBOOK CANDIDATES:"
    )


    for index, item in enumerate(
        candidates[:10],
        start=1
    ):

        print(

            f"{index}. "
            f"{item.get('title', '')} | "

            f"Type: "
            f"{item.get('type', '')} | "

            f"Genre: "
            f"{build_genres(item)} | "

            f"Popularity: "
            f"{get_popularity(item):.2f} | "

            f"Rating: "
            f"{get_rating(item)} | "

            f"Votes: "
            f"{get_vote_count(item)}"

        )


    # =====================================================
    # SELECT ONE
    # =====================================================

    selected = candidates[0]


    print(
        "======================================"
    )


    print(
        "SELECTED FOR FACEBOOK:"
    )


    print(
        f"Title: "
        f"{selected.get('title', '')}"
    )


    print(
        f"Type: "
        f"{selected.get('type', '')}"
    )


    print(
        f"Genre: "
        f"{build_genres(selected)}"
    )


    print(
        f"Popularity: "
        f"{get_popularity(selected):.2f}"
    )


    print(
        f"Rating: "
        f"{get_rating(selected)}"
    )


    print(
        "======================================"
    )


    # =====================================================
    # PUBLISH ONLY ONE
    # =====================================================

    published_count = 0


    success = publish_to_facebook(
        selected
    )


    if success:

        movie_key = get_movie_key(
            selected
        )


        posted.add(
            movie_key
        )


        save_posted(
            posted
        )


        published_count += 1


        # =================================================
        # ADVANCE ROTATION ONLY AFTER SUCCESS
        # =================================================

        rotation = {

            "type_index":
                (
                    type_index + 1
                ) % 2,

            "genre_index":
                (
                    genre_index + 1
                )
                % len(
                    GENRE_ROTATION
                ),

        }


        save_rotation(
            rotation
        )


        print(
            "Rotation advanced successfully."
        )


        print(
            f"Next type: "
            f"{'فيلم' if rotation['type_index'] == 0 else 'مسلسل'}"
        )


        print(
            f"Next genre: "
            f"{GENRE_ROTATION[rotation['genre_index']]}"
        )


    else:

        print(
            "Facebook publishing failed."
        )


        print(
            "Rotation was NOT advanced."
        )


    # =====================================================
    # RESULT
    # =====================================================

    print(
        "======================================"
    )


    print(
        f"Published this run: "
        f"{published_count}"
    )


    print(
        "MOVINS Facebook publisher finished."
    )


    print(
        "======================================"
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
