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

NEWS_FILE = "movie-news.json"

POSTED_FILE = "posted_movies.json"

POSTED_NEWS_FILE = "posted_news.json"

ROTATION_FILE = "facebook_rotation.json"


# =========================================================
# POST TYPE
#
# movie = نشر فيلم أو مسلسل
# news  = نشر خبر
#
# يتم تحديده من GitHub Actions:
#
# POST_TYPE=movie
# أو
# POST_TYPE=news
# =========================================================

POST_TYPE = os.environ.get(
    "POST_TYPE",
    "movie"
).strip().lower()


# =========================================================
# MOVINS WEBSITE
# =========================================================

SITE_URL = (
    "https://nownex.github.io/movins/"
)


# =========================================================
# SETTINGS
# =========================================================

MAX_POSTS_PER_RUN = 1

MAX_OVERVIEW_LENGTH = 420

MAX_NEWS_SUMMARY_LENGTH = 900


# =========================================================
# FACEBOOK ROTATION
# =========================================================

ROTATION_SEQUENCE = [

    {
        "type": "movie",
        "genre": "رعب"
    },

    {
        "type": "tv",
        "genre": "أكشن"
    },

    {
        "type": "movie",
        "genre": "كوميديا"
    },

    {
        "type": "tv",
        "genre": "دراما"
    },

    {
        "type": "movie",
        "genre": "خيال علمي"
    },

    {
        "type": "tv",
        "genre": "غموض"
    },

    {
        "type": "movie",
        "genre": "جريمة"
    },

    {
        "type": "tv",
        "genre": "مغامرة"
    },

    {
        "type": "movie",
        "genre": "فانتازيا"
    },

    {
        "type": "tv",
        "genre": "رومانسي"
    },

    {
        "type": "movie",
        "genre": "رسوم متحركة"
    },

    {
        "type": "tv",
        "genre": "إثارة"
    },

]


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(value):

    if value is None:

        return ""

    text = str(value)

    text = " ".join(
        text.split()
    )

    return text.strip()


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
# LOAD NEWS
# =========================================================

def load_news():

    if not os.path.exists(
        NEWS_FILE
    ):

        raise RuntimeError(
            "movie-news.json not found"
        )


    with open(
        NEWS_FILE,
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
            "movie-news.json items must be a list"
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

def save_posted(posted):

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
# LOAD POSTED NEWS
# =========================================================

def load_posted_news():

    if not os.path.exists(
        POSTED_NEWS_FILE
    ):

        return set()


    try:

        with open(
            POSTED_NEWS_FILE,
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


        return {

            str(item).strip()

            for item in data

            if str(item).strip()

        }


    except Exception:

        return set()


# =========================================================
# SAVE POSTED NEWS
# =========================================================

def save_posted_news(posted):

    with open(
        POSTED_NEWS_FILE,
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
        "index": 0
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

            index = int(
                data.get(
                    "index",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            index = 0


        return {
            "index": index
        }


    except Exception:

        return default


# =========================================================
# SAVE ROTATION
# =========================================================

def save_rotation(rotation):

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

def get_media_type(item):

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

def get_arabic_type(media_type):

    if media_type == "movie":

        return "فيلم"

    return "مسلسل"


# =========================================================
# MOVIE ID
# =========================================================

def get_movie_id(item):

    return str(
        item.get(
            "id",
            ""
        )
    ).strip()


# =========================================================
# UNIQUE MOVIE KEY
# =========================================================

def get_movie_key(item):

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

def get_movie_url(item):

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
# SHORT OVERVIEW
# =========================================================

def build_short_overview(item):

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

def get_genres_list(item):

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

def build_genres(item):

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

def build_hashtags(item):

    hashtags = item.get(
        "hashtags",
        ""
    )


    if isinstance(
        hashtags,
        list
    ):

        hashtags = " ".join(
            clean_text(value)

            for value in hashtags

            if clean_text(value)
        )


    hashtags = clean_text(
        hashtags
    )


    if hashtags:

        parts = hashtags.split()

        result = []


        for part in parts:

            if not part.startswith("#"):

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

        return "#MOVINS #أفلام"


    return "#MOVINS #مسلسلات"


# =========================================================
# RATING
# =========================================================

def get_rating(item):

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

def get_popularity(item):

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

def get_vote_count(item):

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

def get_ending(item):

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

        return "رسوم متحركة" in genres


    if wanted_genre == "مغامرة":

        return (
            "مغامرة" in genres
            or
            "أكشن ومغامرة" in genres
        )


    if wanted_genre == "فانتازيا":

        return (
            "فانتازيا" in genres
            or
            "خيال علمي وفانتازيا" in genres
        )


    if wanted_genre == "إثارة":

        return "إثارة" in genres


    return False


# =========================================================
# FACEBOOK MOVIE CAPTION
# =========================================================

def build_caption(item):

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


        if movie_key in posted:

            continue


        media_type = get_media_type(
            item
        )


        if media_type != wanted_media_type:

            continue


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
# SAME TYPE FALLBACK
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
# GLOBAL FALLBACK
# =========================================================

def select_global_fallback(
    movies,
    posted
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
# NEWS HASHTAGS
# =========================================================

def build_news_hashtags(news):

    title = clean_text(
        news.get(
            "title",
            ""
        )
    ).lower()


    hashtags = [
        "#MOVINS",
        "#أفلام",
        "#مسلسلات",
        "#سينما"
    ]


    if (
        "نتفليكس" in title
        or
        "netflix" in title
    ):

        hashtags.append(
            "#Netflix"
        )


    if (
        "مارفل" in title
        or
        "marvel" in title
    ):

        hashtags.append(
            "#Marvel"
        )


    if (
        "هوليوود" in title
        or
        "hollywood" in title
    ):

        hashtags.append(
            "#Hollywood"
        )


    if (
        "مسلسل" in title
    ):

        hashtags.append(
            "#مسلسلات"
        )


    if (
        "فيلم" in title
    ):

        hashtags.append(
            "#فيلم"
        )


    # إزالة التكرار

    result = []


    for tag in hashtags:

        if tag not in result:

            result.append(
                tag
            )


    return " ".join(
        result[:7]
    )


# =========================================================
# SHORT NEWS SUMMARY
# =========================================================

def build_news_summary(news):

    summary = clean_text(
        news.get(
            "summary",
            ""
        )
    )


    if not summary:

        return (
            "اكتشف التفاصيل الكاملة "
            "على MOVINS."
        )


    if len(summary) <= MAX_NEWS_SUMMARY_LENGTH:

        return summary


    shortened = summary[
        :MAX_NEWS_SUMMARY_LENGTH
    ]


    if " " in shortened:

        shortened = shortened.rsplit(
            " ",
            1
        )[0]


    return shortened + "..."


# =========================================================
# BUILD NEWS CAPTION
# =========================================================

def build_news_caption(news):

    title = clean_text(
        news.get(
            "title",
            "خبر جديد"
        )
    )


    summary = build_news_summary(
        news
    )


    hashtags = build_news_hashtags(
        news
    )


    lines = [

        "📰 خبر جديد من عالم الأفلام والمسلسلات",

        "",

        f"🎬 {title}",

        "",

        summary,

        "",

        "🎥 تابع أحدث أخبار السينما والمسلسلات على MOVINS",

        "",

        SITE_URL,

        "",

        hashtags

    ]


    return "\n".join(
        lines
    )


# =========================================================
# PUBLISH MOVIE
# =========================================================

def publish_to_facebook(item):

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


    payload = {

        "url": poster,

        "caption": caption,

        "published": "true",

        "access_token": TOKEN

    }


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
            response.text
        )

        return False


    if not response.ok:

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )

        return False


    print(
        "Facebook movie post successful."
    )


    return True


# =========================================================
# PUBLISH NEWS
# =========================================================

def publish_news_to_facebook(news):

    image = clean_text(
        news.get(
            "image",
            ""
        )
    )


    if not image:

        print(
            "SKIP NEWS: no image"
        )

        return False


    caption = build_news_caption(
        news
    )


    payload = {

        "url": image,

        "caption": caption,

        "published": "true",

        "access_token": TOKEN

    }


    print(
        "--------------------------------------"
    )


    print(
        "Publishing NEWS to Facebook"
    )


    print(
        "Title:",
        news.get(
            "title",
            ""
        )
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
        "Facebook NEWS post successful."
    )


    return True


# =========================================================
# MAIN — NEWS
# =========================================================

def run_news():

    print(
        "MOVINS NEWS FACEBOOK PUBLISHER"
    )


    news_items = load_news()

    posted_news = load_posted_news()


    candidates = []


    for news in news_items:

        news_id = clean_text(
            news.get(
                "id",
                ""
            )
        )


        if not news_id:

            continue


        if news_id in posted_news:

            continue


        image = clean_text(
            news.get(
                "image",
                ""
            )
        )


        if not image:

            continue


        candidates.append(
            news
        )


    if not candidates:

        print(
            "No new news available."
        )

        return


    selected = candidates[0]


    print(
        "SELECTED NEWS:"
    )


    print(
        selected.get(
            "title",
            ""
        )
    )


    success = publish_news_to_facebook(
        selected
    )


    if success:

        news_id = clean_text(
            selected.get(
                "id",
                ""
            )
        )


        posted_news.add(
            news_id
        )


        save_posted_news(
            posted_news
        )


        print(
            "News marked as posted."
        )


# =========================================================
# MAIN — MOVIES
# =========================================================

def run_movies():

    movies = load_movies()

    posted = load_posted()

    rotation = load_rotation()


    rotation_index = (

        rotation.get(
            "index",
            0
        )

        % len(
            ROTATION_SEQUENCE
        )

    )


    current_rotation = (

        ROTATION_SEQUENCE[
            rotation_index
        ]

    )


    wanted_media_type = (
        current_rotation[
            "type"
        ]
    )


    wanted_genre = (
        current_rotation[
            "genre"
        ]
    )


    candidates = select_candidates(

        movies,

        posted,

        wanted_media_type,

        wanted_genre

    )


    if not candidates:

        candidates = select_type_fallback(

            movies,

            posted,

            wanted_media_type

        )


    if not candidates:

        candidates = select_global_fallback(

            movies,

            posted

        )


    if not candidates:

        print(
            "No new items available."
        )

        return


    selected = candidates[0]


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


        next_index = (

            rotation_index + 1

        ) % len(
            ROTATION_SEQUENCE
        )


        rotation = {

            "index":
                next_index

        }


        save_rotation(
            rotation
        )


        print(
            "Movie rotation advanced."
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print(
        "======================================"
    )

    print(
        "MOVINS FACEBOOK PUBLISHER"
    )

    print(
        "POST TYPE:",
        POST_TYPE
    )

    print(
        "======================================"
    )


    if POST_TYPE == "news":

        run_news()

    else:

        run_movies()


    print(
        "======================================"
    )

    print(
        "MOVINS FACEBOOK PUBLISHER FINISHED"
    )

    print(
        "======================================"
            )
