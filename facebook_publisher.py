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


# One Facebook post per workflow run
MAX_POSTS_PER_RUN = 1


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


        if isinstance(
            data,
            list
        ):

            return set(
                str(x)
                for x in data
            )


    except Exception:

        pass


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
# BUILD CAPTION
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


    genres = item.get(
        "genres",
        []
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


    hashtags = (
        item.get("hashtags")
        or "#MOVINS #Movies"
    )


    if genres:

        genre_text = (
            " • ".join(
                genres[:4]
            )
        )

    else:

        genre_text = (
            "غير محدد"
        )


    return f"""🎬 {title}

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


# =========================================================
# PUBLISH
# =========================================================

def publish_to_facebook(item):

    poster = (
        item.get("poster")
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
        "--------------------------------------"
    )

    print(
        "Publishing:"
    )

    print(
        item.get("title")
    )

    print(
        "Type:"
    )

    print(
        item.get(
            "detailed_type"
        )
    )

    print(
        "--------------------------------------"
    )


    response = requests.post(
        GRAPH_URL,
        data=payload,
        timeout=60
    )


    if not response.ok:

        print(
            "Facebook API Error:"
        )

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


    print(
        f"MOVINS items: "
        f"{len(movies)}"
    )


    print(
        f"Already posted: "
        f"{len(posted)}"
    )


    # -----------------------------------------------------
    # Newest first
    # -----------------------------------------------------

    movies.sort(
        key=lambda item:
            item.get(
                "updated_at",
                ""
            ),
        reverse=True
    )


    # -----------------------------------------------------
    # Find new items
    # -----------------------------------------------------

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
        f"New items: "
        f"{len(new_items)}"
    )


    # -----------------------------------------------------
    # Nothing new
    # -----------------------------------------------------

    if not new_items:

        print(
            "Nothing new to publish."
        )

        return


    # -----------------------------------------------------
    # Publish
    # -----------------------------------------------------

    published_count = 0


    for item in new_items:

        if (
            published_count
            >= MAX_POSTS_PER_RUN
        ):

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


            published_count += 1


    print(
        f"Published this run: "
        f"{published_count}"
    )


    print(
        "MOVINS Facebook publisher finished."
    )


# =========================================================

if __name__ == "__main__":

    main()
