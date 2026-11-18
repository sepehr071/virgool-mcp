import pytest

pytestmark = [pytest.mark.live, pytest.mark.anyio]

POST = "ukw56zemsayo"  # 2026-11-11, "به من ربطی نداره ولی..." by habib.karimi1966


async def test_live_search_and_post(client):
    r = (await client.call_tool("vg_search", {"query": "هوش مصنوعی"})).structured_content
    assert r["results"] and r["total"] > 100
    r = (await client.call_tool("vg_post", {"hash": POST})).structured_content
    assert r["title"] == "به من ربطی نداره ولی..." and r["author"] == "habib.karimi1966"
    assert r["text"].startswith("ماشین رو پارک کردم") and "نارفیق" in r["text"]
    assert "داستان کوتاه" in r["tags"]


async def test_live_search_other_types(client):
    for kind in ("users", "publications", "tags"):
        r = (await client.call_tool("vg_search", {"query": "map", "type": kind})).structured_content
        assert r["results"], kind


async def test_live_comments(client):
    r = (await client.call_tool("vg_comments", {"hash": POST})).structured_content
    assert r["comments"] and r["comments"][0]["text"]


async def test_live_user(client):
    r = (await client.call_tool("vg_user", {"username": "virgool"})).structured_content
    assert r["name"] == "ویرگول" and r["followers"] > 5000 and r["publications"]
    r = (await client.call_tool("vg_user_posts", {"username": "virgool"})).structured_content
    assert r["posts"] and r["total"] >= 50


async def test_live_feeds(client):
    for kind in ("selections", "latest"):
        r = (await client.call_tool("vg_feed", {"kind": kind})).structured_content
        assert r["posts"] and r["posts"][0]["hash"], kind


async def test_live_topics_and_tags(client):
    r = (await client.call_tool("vg_topics", {})).structured_content
    assert len(r["topics"]) >= 40
    r = (await client.call_tool("vg_topic_posts", {"topic": "book"})).structured_content
    assert r["topic"] == "کتاب" and r["total"] > 1000 and r["posts"]
    r = (await client.call_tool("vg_topic_posts", {"topic": "کتاب"})).structured_content
    assert r["posts"]
    r = (await client.call_tool("vg_tag_posts", {"tag": "ai"})).structured_content
    assert r["posts"] and r["total"] > 100


async def test_live_publications(client):
    r = (await client.call_tool("vg_publications", {})).structured_content
    assert r["publications"]
    r = (await client.call_tool("vg_publications", {"query": "نقشه"})).structured_content
    assert r["publications"][0]["name"] == "neshan"
    r = (await client.call_tool("vg_publication_posts", {"name": "BaladMaps"})).structured_content
    assert r["posts"] and r["total"] >= 10
