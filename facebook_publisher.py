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


MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movies.json"


# Publish one new item per run
MAX_POSTS_PER_RUN = 1


# =========================================================
# LOAD MOVIES
# =========================================================

def load_movies():

    with open(
        MOVIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return data.get(
        "items",
        []
    )


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

            data = json.load(file)

        return set(
            str(x)
            for x in data
        )

    except Exception:

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
# HASHTAGS
# =========================================================

def make_hashtags(item):

    hashtags = [
        "#MOVINS",
        "#NOWNEX",
    ]


    media_type = item.get(
        "type"
    )


    genres = item.get(
        "genres",
        []
    )


    if media_type == "فيلم":

        hashtags.extend([
            "#فيلم",
            "#أفلام",
            "#سينما",
        ])

    elif media_type == "مسلسل":

        hashtags.extend([
            "#مسلسل",
            "#مسلسلات",
            "#دراما",
        ])


    # Genre hashtags
    genre_hashtags = {

        "أكشن": "#أكشن",

        "مغامرة": "#مغامرة",

        "رسوم متحركة":
            "#رسوم_متحركة",

        "كوميدي":
            "#كوميدي",

        "جريمة":
            "#جريمة",

        "وثائقي":
            "#وثائقي",

        "دراما":
            "#دراما",

        "عائلي":
            "#عائلي",

        "فانتازيا":
            "#فانتازيا",

        "تاريخي":
            "#تاريخي",

        "رعب":
            "#رعب",

        "موسيقى":
            "#موسيقى",

        "غموض":
            "#غموض",

        "رومانسي":
            "#رومانسي",

        "خيال علمي":
            "#خيال_علمي",

        "إثارة":
            "#إثارة",

        "حربي":
            "#حربي",

        "غربي":
            "#غربي",
    }


    for genre in genres:

        hashtag = genre_hashtags.get(
            genre
        )

        if hashtag:

            hashtags.append(
                hashtag
            )


    # Remove duplicates
    return " ".join(
        dict.fromkeys(
            hashtags
        )
    )


# =========================================================
# CAPTION
# =========================================================

def build_caption(item):

    title = (
        item.get("title")
        or "بدون عنوان"
    )


    detailed_type = (
        item.get(
            "detailed_type"
        )
        or item.get(
            "type",
            "عمل"
        )
    )


    year = (
        item.get("year")
        or "—"
    )


    rating = float(
        item.get(
            "rating"
        )
        or 0
    )


    overview = (
        item.get("overview")
        or "لا يوجد ملخص متوفر حاليًا."
    )


    genres = item.get(
        "genres",
        []
    )


    hashtags = make_hashtags(
        item
    )


    genre_text = (
        " • ".join(genres[:4])
        if genres
        else "غير محدد"
    )


    caption = f"""🎬 {title}

📌 النوع: {detailed_type}

🎭 التصنيف:
{genre_text}

📅 السنة: {year}

⭐ التقييم: {rating:.1f}/10

📝 القصة:

{overview}

━━━━━━━━━━━━━━

🍿 اكتشف المزيد من الأفلام والمسلسلات على MOVINS

🌐 https://nownex.github.io/movins/

{hashtags}
"""


    return caption


# =========================================================
# FACEBOOK POST
# =========================================================

def publish_to_facebook(item):

    poster = item.get(
        "poster"
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

        "url":
            poster,

        "caption":
            caption,

        "published":
            "true",

        "access_token":
            TOKEN,
    }


    print(
        "Publishing:",
        item.get("title")
    )


    response = requests.post(
        GRAPH_URL,
        data=payload,
        timeout=60
    )


    if not response.ok:

        print(
            response.text
        )

        response.raise_for_status()


    result = response.json()


    print(
        "Facebook post successful."
    )


    print(
        "Post ID:",
        result.get(
            "post_id"
        )
        or result.get("id")
    )


    return True


# =========================================================
# MAIN
# =========================================================

def main():

    movies = load_movies()

    posted = load_posted()


    movies.sort(
        key=lambda item:
            item.get(
                "updated_at",
                ""
            ),
        reverse=True
    )


    new_items = []


    for item in movies:

        item_id = item.get(
            "id"
        )

        if not item_id:
            continue


        if str(item_id) not in posted:

            new_items.append(
                item
            )


    print(
        "New items:",
        len(new_items)
    )


    if not new_items:

        print(
            "Nothing new to publish."
        )

        return


    published = 0


    for item in new_items:

        if published >= MAX_POSTS_PER_RUN:
            break


        success = publish_to_facebook(
            item
        )


        if success:

            posted.add(
                str(
                    item["id"]
                )
            )


            save_posted(
                posted
            )


            published += 1


    print(
        "Published:",
        published
    )


# =========================================================

if __name__ == "__main__":
    main()
