import httpx
import pytest
from conftest import FIXTURES, fixture

pytestmark = pytest.mark.anyio

A = "/api2/app"
POST_PATH = httpx.URL(fixture("post_meta.json")["data"]["url"]).path
TOOLS = {
    "vg_search",
    "vg_post",
    "vg_comments",
    "vg_user",
    "vg_user_posts",
    "vg_feed",
    "vg_topics",
    "vg_topic_posts",
    "vg_tag_posts",
    "vg_publications",
    "vg_publication_posts",
}


async def test_all_tools_are_read_only_and_described(client):
    tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == TOOLS
    for t in tools:
        assert t.annotations.read_only_hint is True, t.name
        assert t.title and t.description.splitlines()[0].endswith("."), t.name
        assert "title" not in str(t.input_schema.get("properties", {}).values()), t.name


async def test_search_posts_and_params(client, api):
    api[f"{A}/search/posts"] = fixture("search_posts.json")
    r = (await client.call_tool("vg_search", {"query": "هوش", "page": 2})).structured_content
    assert r["type"] == "posts" and r["total"] == 1000 and r["page"] == 1
    p = r["results"][0]
    assert p["hash"] and p["title"] and p["author"] and p["url"].startswith("https://")
    assert api.calls[0].url.params["q"] == "هوش" and api.calls[0].url.params["page"] == "2"


async def test_search_publications(client, api):
    api[f"{A}/search/publications"] = fixture("pub_search.json")
    r = (await client.call_tool("vg_search", {"query": "map", "type": "publications"})).structured_content
    assert r["results"][0]["name"] == "mappub" and r["results"][0]["followers"] is not None


async def test_post_reads_story_text(client, api):
    api[f"{A}/posts/ukw56zemsayo"] = fixture("post_meta.json")
    html = (FIXTURES / "post_page.html").read_text(encoding="utf-8")
    api[POST_PATH] = lambda request: httpx.Response(200, text=html)
    r = (await client.call_tool("vg_post", {"hash": "ukw56zemsayo", "max_chars": 500})).structured_content
    assert r["title"] == "به من ربطی نداره ولی..." and r["author"] == "habib.karimi1966"
    assert r["tags"][:2] == ["داستان کوتاه", "خاطره"] and r["topics"] == ["داستان"]
    assert r["text"].startswith("ماشین رو پارک کردم") and "<" not in r["text"] and "truncated" in r


async def test_post_redirect_followed_inside_host(client, api):
    api[f"{A}/posts/abc"] = fixture("post_meta.json")
    api[POST_PATH] = lambda request: httpx.Response(308, headers={"location": "https://evil.example/x"})
    r = await client.call_tool("vg_post", {"hash": "abc"})
    assert r.is_error is True


async def test_comments(client, api):
    api[f"{A}/posts/ukw56zemsayo/comments"] = fixture("comments.json")
    r = (await client.call_tool("vg_comments", {"hash": "ukw56zemsayo"})).structured_content
    assert r["comments"] and r["comments"][0]["author"] and r["comments"][0]["text"]


async def test_user_profile_and_posts(client, api):
    api[f"{A}/users/virgool/profile"] = fixture("profile.json")
    api[f"{A}/users/virgool/publications"] = fixture("user_pubs.json")
    api[f"{A}/users/virgool/posts"] = fixture("user_posts.json")
    r = (await client.call_tool("vg_user", {"username": "@virgool"})).structured_content
    assert r["username"] == "virgool" and r["followers"] > 1000 and r["posts"] and r["publications"]
    r = (await client.call_tool("vg_user_posts", {"username": "virgool"})).structured_content
    assert r["posts"][0]["hash"] and r["total"] > 3


async def test_feed(client, api):
    api[f"{A}/posts/selections"] = fixture("posts_selections.json")
    r = (await client.call_tool("vg_feed", {})).structured_content
    assert r["kind"] == "selections" and r["posts"][0]["topics"] is not None and r["last_page"] >= 1


async def test_topics_and_topic_posts_by_english_name(client, api):
    api[f"{A}/topics"] = fixture("topics.json")
    topics = fixture("topics.json")["data"]
    book = next(t for t in topics if t["name"] == "book")
    api[f"{A}/topics/{httpx.URL('/' + book['faName']).path[1:]}/posts"] = fixture("user_posts.json")
    r = (await client.call_tool("vg_topics", {})).structured_content
    assert {"name": "book", "fa_name": book["faName"], "followers": book["followersCount"]} in r["topics"]
    r = (await client.call_tool("vg_topic_posts", {"topic": "book"})).structured_content
    assert r["topic"] == book["faName"] and r["posts"]


async def test_unknown_topic_is_an_error(client, api):
    api[f"{A}/topics"] = fixture("topics.json")
    r = await client.call_tool("vg_topic_posts", {"topic": "nonexistent-xyz"})
    assert r.is_error is True


async def test_tag_publications_and_publication_posts(client, api):
    api[f"{A}/tags/ai/posts"] = fixture("tag_posts.json")
    api[f"{A}/publications/suggests"] = fixture("pub_posts.json") | {"data": []}
    api[f"{A}/publications/neshan/posts"] = fixture("pub_posts.json")
    assert (await client.call_tool("vg_tag_posts", {"tag": "ai"})).structured_content["posts"]
    assert (await client.call_tool("vg_publications", {})).structured_content["publications"] == []
    r = (await client.call_tool("vg_publication_posts", {"name": "neshan"})).structured_content
    assert r["publication"] == "neshan" and r["posts"][0]["publication"]


async def test_http_errors_are_tool_errors(client, api):
    r = await client.call_tool("vg_user", {"username": "nobody"})
    assert r.is_error is True and "404" in r.content[0].text


async def test_cache_and_host_allowlist(api):
    from virgool_mcp import http

    api[f"{A}/topics"] = fixture("topics.json")
    await http.fetch("/topics")
    await http.fetch("/topics")
    assert len(api.calls) == 1
    with pytest.raises(http.ApiError):
        await http._get("https://virgool.io/x", {}, {}, "empty")


def _de(body):
    """A reduced-deployment answer: the foreign host tags every response with x-vrgl-upstream: de."""
    return lambda request: httpx.Response(200, json=body, headers={"x-vrgl-upstream": "de"})


async def test_reduced_deployment_comments_is_an_error(client, api):
    api[f"{A}/posts/ukw56zemsayo/comments"] = _de({"data": [], "pagination": {"total": 0}})
    r = await client.call_tool("vg_comments", {"hash": "ukw56zemsayo"})
    assert r.is_error is True and "reduced foreign deployment" in r.content[0].text


async def test_reduced_deployment_404_explains_cause(client, api):
    api[f"{A}/topics"] = lambda request: httpx.Response(404, json={}, headers={"x-vrgl-upstream": "de"})
    r = await client.call_tool("vg_topics", {})
    assert r.is_error is True and "Iranian IP" in r.content[0].text


async def test_plain_404_does_not_blame_the_network(client, api):
    r = await client.call_tool("vg_user", {"username": "nobody"})
    assert r.is_error is True and "Iranian" not in r.content[0].text


async def test_user_without_publications_endpoint_still_returns_profile(client, api):
    api[f"{A}/users/virgool/profile"] = fixture("profile.json")
    r = (await client.call_tool("vg_user", {"username": "virgool"})).structured_content
    assert r["username"] == "virgool" and r["publications"] is None and r["note"]


async def test_feed_notes_reduced_deployment(client, api):
    api[f"{A}/posts/latest"] = _de(fixture("posts_selections.json"))
    r = (await client.call_tool("vg_feed", {"kind": "latest"})).structured_content
    assert "reduced foreign deployment" in r["note"] and r["posts"]


async def test_comment_replies(client, api):
    c = fixture("comments.json")["data"][0]
    api[f"{A}/comments/abc"] = {"data": [{**c, "parentId": "abc"}]}
    r = (await client.call_tool("vg_comments", {"hash": "x", "replies_to": "abc"})).structured_content
    assert r["parent_id"] == "abc" and r["comments"][0]["parent_id"] == "abc" and "author_name" in r["comments"][0]


async def test_empty_search_is_a_clear_error(client, api):
    r = await client.call_tool("vg_search", {"query": "  "})
    assert r.is_error is True and "search text" in r.content[0].text and not api.calls
