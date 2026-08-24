import json
import os
import requests
from datetime import datetime, timezone


# =========================================================
# MOVINS — FACEBOOK PUBLISHER
# =========================================================

TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN")

if not TOKEN:
    raise RuntimeError("FACEBOOK_PAGE_TOKEN is missing")


GRAPH_VERSION = "v26.0"

GRAPH_URL = (
    f"https://graph.facebook.com/"
    f"{GRAPH_VERSION}/me/photos"
)

MOVIES_FILE = "movies.json"
POSTED_FILE = "posted_movies.json"

MAX_POSTS_PER_RUN = 1


# =========================================================
# LOAD MOVIES
# =========================================================

def load_movies():

    if not os.path.exists(MOVIES_FILE):
        raise RuntimeError("movies.json not found")

    with open(
        MOVIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    items = data.get("items", [])

    if not isinstance(items, list):
        raise RuntimeError(
            "Invalid movies.json format"
        )

    return items


# =========================================================
# LOAD POSTED IDS
# =========================================================

def load_posted():

    if not os.path.exists(POSTED_FILE):
        return set()

    try:

        with open(
            POSTED_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return set(str(x) for x in data)

    except Exception:
        pass

    return set()


# =========================================================
# SAVE POSTED IDS
# =========================================================

def save_posted(posted):

    with open(
        POSTED_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            sorted(list(posted)),
            file,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# HASHTAGS
# =========================================================

def make_hashtags(item):

    title = str(
        item.get("title") or ""
    ).strip()

    media_type = item.get("type")

    tags = [
        "#MOVINS",
        "#NOWNEX",
        "#Movies",
        "#Series",
        "#Film",
        "#TV",
    ]

    if media_type == "فيلم":

        tags.extend([
            "#فيلم",
            "#أفلام",
            "#سينما",
        ])

    elif media_type == "مسلسل":

        tags.extend([
            "#مسلسل",
            "#مسلسلات",
            "#دراما",
        ])

    # Add a simple title hashtag
    # only when it is reasonably safe.
    clean_title = (
        title
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )

    if clean_title:

        # Avoid excessively long hashtags
        if len(clean_title) <= 40:
            tags.append("#" + clean_title)

    return " ".join(tags)


# =========================================================
# BUILD FACEBOOK CAPTION
# =========================================================

def build_caption(item):

    title = (
        item.get("title")
        or "بدون عنوان"
    )

    media_type = (
        item.get("type")
        or "عمل"
    )

    year = (
        item.get("year")
        or "—"
    )

    overview = (
        item.get("overview")
        or "لا يوجد ملخص متوفر حاليًا."
    )

    rating = float(
        item.get("rating") or 0
    )

    hashtags = make_hashtags(item)

    caption = f"""🎬 {title}

📌 النوع: {media_type}
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
# POST PHOTO
# =========================================================

def publish_to_facebook(item):

    poster = (
        item.get("poster")
        or ""
    )

    if not poster:
        print(
            f"SKIP: {item.get('title')} "
            "has no poster."
        )
        return False

    caption = build_caption(item)

    payload = {
        "url": poster,
        "caption": caption,
        "published": "true",
        "access_token": TOKEN,
    }

    print(
        f"Publishing: "
        f"{item.get('title')}"
    )

    response = requests.post(
        GRAPH_URL,
        data=payload,
        timeout=60,
    )

    if not response.ok:

        print(
            "Facebook API response:"
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
        result.get("post_id")
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
        f"MOVINS items: {len(movies)}"
    )

    print(
        f"Already posted: {len(posted)}"
    )


    # -----------------------------------------------------
    # Sort by updated_at
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
    # Find items not posted before
    # -----------------------------------------------------

    new_items = []

    for item in movies:

        item_id = item.get("id")

        if not item_id:
            continue

        item_id = str(item_id)

        if item_id not in posted:

            new_items.append(item)


    print(
        f"New items: {len(new_items)}"
    )


    # -----------------------------------------------------
    # First installation protection
    #
    # If posted_movies.json doesn't exist,
    # don't suddenly publish all 30 items.
    # Publish only the newest item.
    # -----------------------------------------------------

    if not os.path.exists(POSTED_FILE):

        if not new_items:

            print(
                "Nothing to publish."
            )

            return


        first_item = new_items[0]

        print(
            "First Facebook run."
        )

        print(
            "Publishing only the newest item."
        )

        if publish_to_facebook(
            first_item
        ):

            posted.add(
                str(first_item["id"])
            )

            save_posted(posted)

        return


    # -----------------------------------------------------
    # Normal operation
    # -----------------------------------------------------

    published_count = 0


    for item in new_items:

        if published_count >= MAX_POSTS_PER_RUN:
            break


        try:

            success = publish_to_facebook(
                item
            )

            if success:

                posted.add(
                    str(item["id"])
                )

                save_posted(
                    posted
                )

                published_count += 1


        except Exception as error:

            print(
                "ERROR publishing:"
            )

            print(error)

            # Stop here so we don't accidentally
            # mark failed posts as published.
            raise


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
