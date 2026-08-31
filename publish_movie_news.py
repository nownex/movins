import json
import os
import re
import requests


# ============================================================
# MOVINS — FACEBOOK MOVIE NEWS PUBLISHER
# ============================================================


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


# ============================================================
# FILES
# ============================================================


NEWS_FILE = "movie-news.json"

POSTED_FILE = "posted_movie_news.json"


# ============================================================
# WEBSITE
# ============================================================


SITE_URL = (
    "https://nownex.github.io/movins/"
)


# ============================================================
# SETTINGS
# ============================================================


MAX_POSTS_PER_RUN = 1

MAX_SUMMARY_LENGTH = 900


# ============================================================
# LOAD NEWS
# ============================================================


def load_news():

    if not os.path.exists(
        NEWS_FILE
    ):

        raise RuntimeError(
            "movie-news.json not found"
        )


    try:

        with open(
            NEWS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )


    except Exception as error:

        raise RuntimeError(
            f"Could not read movie-news.json: {error}"
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


# ============================================================
# LOAD POSTED NEWS
# ============================================================


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


        return {

            str(item).strip()

            for item in data

            if str(item).strip()

        }


    except Exception as error:

        print(
            "WARNING: Could not read posted news:",
            error
        )

        return set()


# ============================================================
# SAVE POSTED NEWS
# ============================================================


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


# ============================================================
# CLEAN TEXT
# ============================================================


def clean_text(
    value
):

    if value is None:

        return ""


    text = str(
        value
    )


    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


# ============================================================
# GET NEWS ID
# ============================================================


def get_news_id(
    item
):

    return clean_text(
        item.get(
            "id",
            ""
        )
    )


# ============================================================
# SHORT SUMMARY
# ============================================================


def build_short_summary(
    item
):

    summary = clean_text(
        item.get(
            "summary",
            ""
        )
    )


    if not summary:

        return (
            "تعرف على أحدث التفاصيل "
            "والتطورات المتعلقة بهذا الخبر."
        )


    if len(
        summary
    ) <= MAX_SUMMARY_LENGTH:

        return summary


    shortened = summary[
        :MAX_SUMMARY_LENGTH
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


# ============================================================
# GET NEWS URL
#
# الموقع يفتح صفحة MOVINS
# ويمكن للقارئ متابعة المصدر الأصلي من البطاقة.
# ============================================================


def get_news_url(
    item
):

    news_id = get_news_id(
        item
    )


    if not news_id:

        return SITE_URL


    return (
        SITE_URL
        + "?news="
        + news_id
    )


# ============================================================
# BUILD HASHTAGS
# ============================================================


def build_hashtags(
    item
):

    title = clean_text(
        item.get(
            "title",
            ""
        )
    ).lower()


    source = clean_text(
        item.get(
            "source",
            ""
        )
    )


    hashtags = [

        "#MOVINS",
        "#أخبار_الأفلام"

    ]


    keyword_map = {

        "فيلم": "#أفلام",

        "أفلام": "#أفلام",

        "مسلسل": "#مسلسلات",

        "مسلسلات": "#مسلسلات",

        "نتفليكس": "#Netflix",

        "netflix": "#Netflix",

        "مارفل": "#Marvel",

        "marvel": "#Marvel",

        "ديزني": "#Disney",

        "disney": "#Disney",

        "هوليوود": "#هوليوود",

        "hollywood": "#Hollywood",

        "سينما": "#سينما",

        "تريلر": "#تريلر",

        "إيرادات": "#شباك_التذاكر",

        "شباك التذاكر": "#BoxOffice",

        "مهرجان": "#مهرجان_سينمائي",

        "ممثل": "#نجوم",

        "ممثلة": "#نجوم",

        "مخرج": "#سينما"

    }


    for keyword, hashtag in keyword_map.items():

        if keyword.lower() in title:

            if hashtag not in hashtags:

                hashtags.append(
                    hashtag
                )


    if source:

        source_tag = re.sub(
            r"[^\w\u0600-\u06FF]",
            "",
            source
        )


        if source_tag:

            source_hashtag = (
                "#"
                + source_tag
            )


            if source_hashtag not in hashtags:

                hashtags.append(
                    source_hashtag
                )


    return " ".join(
        hashtags[:7]
    )


# ============================================================
# FACEBOOK CAPTION
# ============================================================


def build_caption(
    item
):

    title = clean_text(
        item.get(
            "title",
            ""
        )
        or "خبر جديد"
    )


    summary = build_short_summary(
        item
    )


    source = clean_text(
        item.get(
            "source",
            ""
        )
        or "MOVINS"
    )


    news_url = get_news_url(
        item
    )


    hashtags = build_hashtags(
        item
    )


    lines = [

        "🎬 عاجل من عالم السينما والترفيه",

        "",

        f"📰 {title}",

        "",

        summary,

        "",

        f"📌 المصدر: {source}",

        "",

        "👇 تابع الخبر وتفاصيله على MOVINS:",

        "",

        news_url,

        "",

        hashtags

    ]


    return "\n".join(
        lines
    )


# ============================================================
# VALID IMAGE
# ============================================================


def valid_image(
    image
):

    image = clean_text(
        image
    )


    if not image:

        return False


    return image.startswith(
        (
            "http://",
            "https://"
        )
    )


# ============================================================
# SELECT NEWS
# ============================================================


def select_news(
    news_items,
    posted
):

    candidates = []


    for item in news_items:

        news_id = get_news_id(
            item
        )


        if not news_id:

            continue


        if news_id in posted:

            continue


        title = clean_text(
            item.get(
                "title",
                ""
            )
        )


        summary = clean_text(
            item.get(
                "summary",
                ""
            )
        )


        if not title:

            continue


        if not summary:

            continue


        candidates.append(
            item
        )


    return candidates


# ============================================================
# PUBLISH TO FACEBOOK
# ============================================================


def publish_to_facebook(
    item
):

    image = clean_text(
        item.get(
            "image",
            ""
        )
    )


    if not valid_image(
        image
    ):

        print(
            "SKIP: News has no valid image"
        )

        return False


    caption = build_caption(
        item
    )


    payload = {

        "url":
            image,

        "caption":
            caption,

        "published":
            "true",

        "access_token":
            TOKEN

    }


    print()
    print(
        "=" * 60
    )

    print(
        "PUBLISHING MOVIE NEWS TO FACEBOOK"
    )

    print(
        "=" * 60
    )

    print(
        "TITLE:"
    )

    print(
        item.get(
            "title",
            ""
        )
    )

    print()

    print(
        "IMAGE:"
    )

    print(
        image
    )

    print()

    print(
        "CAPTION:"
    )

    print(
        caption
    )

    print(
        "=" * 60
    )

    try:

        response = requests.post(

            GRAPH_URL,

            data=payload,

            timeout=60

        )


    except requests.RequestException as error:

        print(
            "FACEBOOK REQUEST ERROR:",
            error
        )

        return False


    try:

        result = response.json()


    except ValueError:

        print(
            "FACEBOOK INVALID RESPONSE:"
        )

        print(
            response.text
        )

        return False


    if not response.ok:

        print(
            "FACEBOOK API ERROR:"
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )
        )

        return False


    print()

    print(
        "FACEBOOK NEWS POST SUCCESSFUL"
    )

    print(
        "POST ID:",
        result.get(
            "post_id"
        )
        or result.get(
            "id"
        )
    )

    return True


# ============================================================
# MAIN
# ============================================================


def main():

    print()
    print(
        "=" * 60
    )

    print(
        "MOVINS FACEBOOK MOVIE NEWS PUBLISHER"
    )

    print(
        "=" * 60
    )

    print()


    news_items = load_news()

    posted = load_posted()


    print(
        "AVAILABLE NEWS:",
        len(news_items)
    )


    print(
        "ALREADY POSTED:",
        len(posted)
    )


    candidates = select_news(

        news_items,

        posted

    )


    print(
        "NEW NEWS CANDIDATES:",
        len(candidates)
    )


    if not candidates:

        print()

        print(
            "NO NEW MOVIE NEWS AVAILABLE FOR FACEBOOK."
        )

        return


    published_count = 0


    for item in candidates:

        if published_count >= MAX_POSTS_PER_RUN:

            break


        success = publish_to_facebook(
            item
        )


        if success:

            news_id = get_news_id(
                item
            )


            posted.add(
                news_id
            )


            save_posted(
                posted
            )


            published_count += 1


        else:

            print(
                "FAILED TO PUBLISH THIS NEWS."
            )


    print()

    print(
        "=" * 60
    )

    print(
        f"PUBLISHED THIS RUN: "
        f"{published_count}"
    )

    print(
        "MOVINS FACEBOOK NEWS PUBLISHER FINISHED."
    )

    print(
        "=" * 60
    )


# ============================================================
# RUN
# ============================================================


if __name__ == "__main__":

    main()
