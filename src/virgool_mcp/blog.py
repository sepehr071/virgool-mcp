"""Virgool tools: search, post text, comments, authors, feeds, topics, tags, publications."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Annotated, Any, Literal
from urllib.parse import quote

from pydantic import Field

from .http import REDUCED_NOTE, ApiError, fetch, fetch_html, reduced
from .registry import tool

Page = Annotated[int, Field(ge=1, le=100, description="Page number, 10 items per page (publications 7).")]
BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "figcaption", "tr"}
BODY_END = '<div class="mt-7 no-print">'  # the tag list follows the story text in the page HTML


def _seg(value: str) -> str:
    """One URL path segment: percent-encoded, so user input cannot add path parts."""
    return quote(value.strip().lstrip("@"), safe="")


def _page(r: dict[str, Any]) -> dict[str, Any]:
    p = r.get("pagination") or {}
    return {"page": p.get("currentPage"), "last_page": p.get("lastPage"), "total": p.get("total")}


def _user(u: dict[str, Any] | None) -> dict[str, Any] | None:
    if not u:
        return None
    return {
        "username": u.get("username"),
        "name": u.get("name"),
        "bio": u.get("bio"),
        "followers": u.get("followersCount"),
        "following": u.get("followingCount"),
        "joined": (u.get("registeredAt") or "")[:10] or None,
        "url": u.get("url"),
    }


def _post(p: dict[str, Any]) -> dict[str, Any]:
    pub = p.get("publication") or {}
    return {
        "hash": p.get("hash"),
        "title": p.get("title"),
        "summary": p.get("description"),
        "author": (p.get("user") or {}).get("username"),
        "author_name": (p.get("user") or {}).get("name"),
        "publication": pub.get("name"),
        "published": p.get("publishedAt"),
        "likes": p.get("likesCount"),
        "comments": p.get("commentsCount"),
        "reading_minutes": p.get("readingTime"),
        "words": p.get("wordsCount"),
        "views": p.get("impressions"),
        "topics": [t.get("faName") or t.get("name") for t in p.get("topics") or []],
        "url": p.get("shortUrl") or p.get("url"),
    }


def _publication(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": p.get("name"),
        "title": p.get("title"),
        "description": p.get("description"),
        "followers": p.get("followers"),
        "url": p.get("url"),
    }


def _topic(t: dict[str, Any]) -> dict[str, Any]:
    return {"name": t.get("name"), "fa_name": t.get("faName"), "followers": t.get("followersCount")}


def _tag(t: dict[str, Any]) -> dict[str, Any]:
    return {"name": t.get("name"), "slug": t.get("slug"), "description": t.get("description")}


def _posts(r: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {**_page(r), **extra, "posts": [_post(p) for p in r.get("data") or []]}


class _Text(HTMLParser):
    """Story HTML to plain text: one line per block, list items prefixed with "- "."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "figcaption"):
            self.skip += 1
        elif tag in BLOCKS or tag == "br":
            self.out.append("\n- " if tag == "li" else "\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "figcaption"):
            self.skip -= 1
        elif tag in BLOCKS:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def _story_text(page: str) -> str:
    start = page.find("</h1>")
    if start < 0:
        raise ApiError("Could not find the story text in the post page.")
    end = page.find(BODY_END, start)
    parser = _Text()
    parser.feed(page[start + 5 : end if end > 0 else None])
    lines = (re.sub(r"[ \t]+", " ", ln).strip() for ln in "".join(parser.out).split("\n"))
    return "\n".join(ln for ln in lines if ln and ln != "-")


@tool("Search Virgool")
async def vg_search(
    query: Annotated[str, Field(description="Persian or English search text.")],
    type: Annotated[
        Literal["posts", "users", "publications", "tags"], Field(description="What to search; default posts.")
    ] = "posts",
    page: Page = 1,
) -> dict[str, Any]:
    """Search Virgool posts, authors, publications or tags. Post results carry the `hash` that vg_post reads."""
    if not query.strip():
        raise ApiError("Give some search text.")
    r = await fetch(f"/search/{type}", {"q": query.strip(), "page": page})
    rows = r.get("data") or []
    out = {"posts": _post, "users": _user, "publications": _publication, "tags": _tag}[type]
    # users/publications/tags answer one page without pagination info; posts cap at 1000 hits
    return {**_page(r), "type": type, "results": [out(x) for x in rows]}


@tool("Read a post")
async def vg_post(
    hash: Annotated[str, Field(description="Post hash (12 letters/digits) from any list, e.g. 'ukw56zemsayo'.")],
    max_chars: Annotated[int, Field(ge=500, le=50000, description="Cut the text after this many characters.")] = 8000,
) -> dict[str, Any]:
    """Read one Virgool post: title, author, topics, tags, counts and the full story text (images are skipped)."""
    meta = (await fetch(f"/posts/{_seg(hash)}")).get("data") or {}
    text = _story_text(await fetch_html(meta["url"]))
    row = _post(meta)
    row["tags"] = [t.get("name") for t in meta.get("tags") or []]
    row["canonical_url"] = meta.get("canonicalUrl")
    row["text"] = text[:max_chars]
    if len(text) > max_chars:
        row["truncated"] = f"text cut at {max_chars} of {len(text)} characters; raise max_chars"
    return row


def _comment(c: dict[str, Any]) -> dict[str, Any]:
    u = c.get("user") or {}
    return {
        "id": c.get("hash"),
        "parent_id": c.get("parentId"),
        "author": u.get("username"),
        "author_name": u.get("name"),
        "text": c.get("body"),
        "likes": c.get("likes"),
        "replies": c.get("replies"),
        "published": c.get("publishedAt"),
    }


@tool("Post comments")
async def vg_comments(
    hash: Annotated[str, Field(description="Post hash.")],
    page: Page = 1,
    replies_to: Annotated[
        str | None, Field(description="Comment id: list its replies instead (page is ignored).")
    ] = None,
) -> dict[str, Any]:
    """List the public top-level comments of a post, or the replies of one comment (`replies` counts them)."""
    if replies_to:
        r = await fetch(f"/comments/{_seg(replies_to)}")
        rows = r.get("data") or []
        return {"parent_id": replies_to, "comments": [_comment(c) for c in rows if not c.get("deleted")]}
    r = await fetch(f"/posts/{_seg(hash)}/comments", {"page": page})
    if reduced():  # the foreign deployment answers every post with an empty comment list
        raise ApiError(f"Comments are unavailable. {REDUCED_NOTE}")
    return {**_page(r), "comments": [_comment(c) for c in r.get("data") or [] if not c.get("deleted")]}


@tool("Author profile")
async def vg_user(username: Annotated[str, Field(description="Username without @, e.g. 'virgool'.")]) -> dict[str, Any]:
    """Get an author's public profile (bio, followers, post count, links) and the publications they belong to."""
    u = _seg(username)
    prof = (await fetch(f"/users/{u}/profile")).get("data") or {}
    out = {**(_user(prof) or {}), "posts": prof.get("postsCount"), "socials": prof.get("socials") or None}
    try:
        pubs = await fetch(f"/users/{u}/publications")
    except ApiError as e:
        if e.status != 404:
            raise
        return {**out, "publications": None, "note": REDUCED_NOTE if reduced() else "Publications are unavailable."}
    return {**out, "publications": [_publication(p) for p in pubs.get("data") or []]}


@tool("Author posts")
async def vg_user_posts(
    username: Annotated[str, Field(description="Username without @.")], page: Page = 1
) -> dict[str, Any]:
    """List an author's published posts, newest first."""
    return _posts(await fetch(f"/users/{_seg(username)}/posts", {"page": page}), username=username)


@tool("Popular and latest posts")
async def vg_feed(
    kind: Annotated[
        Literal["selections", "latest"],
        Field(description="selections = editors' picks shown on the home page; latest = newest posts."),
    ] = "selections",
    page: Page = 1,
) -> dict[str, Any]:
    """List Virgool's front-page posts: editors' picks or the newest posts. The site has no view-count ranking."""
    r = _posts(await fetch(f"/posts/{kind}", {"page": page}), kind=kind)
    return {**r, "note": REDUCED_NOTE} if reduced() else r


@tool("Topics")
async def vg_topics() -> dict[str, Any]:
    """List all Virgool topics (broad categories) with follower counts. vg_topic_posts takes `name` or `fa_name`."""
    return {"topics": [_topic(t) for t in (await fetch("/topics")).get("data") or []]}


async def _topic_fa_name(topic: str) -> str:
    """The posts endpoint wants the Persian name; map an English name ('book') through the topic list."""
    if not topic.isascii():
        return topic
    for t in (await fetch("/topics")).get("data") or []:
        if t.get("name") == topic.lower():
            return t.get("faName") or topic
    raise ApiError(f"No topic named {topic!r}. Use vg_topics for the list.", 404)


@tool("Topic posts")
async def vg_topic_posts(
    topic: Annotated[str, Field(description="Topic, Persian ('کتاب') or English slug ('book') from vg_topics.")],
    page: Page = 1,
) -> dict[str, Any]:
    """List the latest posts of a topic (category) such as book, economy or psychology."""
    fa = await _topic_fa_name(topic)
    return _posts(await fetch(f"/topics/{_seg(fa)}/posts", {"page": page}), topic=fa)


@tool("Tag posts")
async def vg_tag_posts(
    tag: Annotated[
        str,
        Field(description="Tag slug, Persian or English, e.g. 'ai' or 'هوش-مصنوعی'. vg_search type=tags finds slugs."),
    ],
    page: Page = 1,
) -> dict[str, Any]:
    """List the latest posts carrying a tag."""
    return _posts(await fetch(f"/tags/{_seg(tag)}/posts", {"page": page}), tag=tag)


@tool("Publications")
async def vg_publications(
    query: Annotated[str | None, Field(description="Search text; omit to list suggested publications.")] = None,
    page: Page = 1,
) -> dict[str, Any]:
    """Search or list Virgool publications (group blogs). vg_publication_posts reads one by its `name`.

    Without a query the list is a random suggestion per call; some entries have no posts.
    """
    r = (
        await fetch("/search/publications", {"q": query, "page": page})
        if query
        else await fetch("/publications/suggests", {"page": page})
    )
    return {**_page(r), "publications": [_publication(p) for p in r.get("data") or []]}


@tool("Publication posts")
async def vg_publication_posts(
    name: Annotated[str, Field(description="Publication name from vg_publications, e.g. 'neshan'.")], page: Page = 1
) -> dict[str, Any]:
    """List the latest posts of a publication, newest first."""
    return _posts(await fetch(f"/publications/{_seg(name)}/posts", {"page": page}), publication=name)
