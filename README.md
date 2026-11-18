<!-- mcp-name: io.github.sepehr071/virgool-mcp -->

<div align="center">

<img src="https://raw.githubusercontent.com/sepehr071/virgool-mcp/main/.github/banner.png" alt="virgool-mcp: unofficial Virgool (ویرگول) MCP server that searches Persian blog posts, authors and publications and reads full post text and comments for Claude, Cursor and Copilot" width="100%">

# virgool-mcp: Virgool (ویرگول) Persian blog MCP server for AI agents

**virgool-mcp is an unofficial, read-only MCP server that lets an AI agent search posts, authors, publications and tags, and read full post text and comments on Virgool (ویرگول, virgool.ir), the biggest Persian blogging platform.**<br>
Its 11 tools search Virgool, read a post (metadata, tags and the story text) and its comments, show an author's profile and posts, list the editors' picks and the newest posts, and browse topics, tags and publications.<br>
No API key or account is needed; it works in Claude, Cursor, Copilot and any other MCP client.

[![PyPI](https://img.shields.io/pypi/v/virgool-mcp?color=2563eb)](https://pypi.org/project/virgool-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/virgool-mcp)](https://pypi.org/project/virgool-mcp/)
[![CI](https://github.com/sepehr071/virgool-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sepehr071/virgool-mcp/actions/workflows/ci.yml)
[![License: PolyForm Noncommercial](https://img.shields.io/badge/license-PolyForm%20Noncommercial-c2410c)](https://github.com/sepehr071/virgool-mcp/blob/main/LICENSE)

[For AI agents](#for-ai-agents) · [Quick start](#quick-start) · [Tools](#tools) · [Limits](#limits) · [فارسی](#فارسی)

</div>

---

## For AI agents

- **What:** unofficial MCP server (model context protocol) for virgool.ir: post, author, publication and tag search, full post text, comments and replies, author pages, editors' picks, newest posts, topics.
- **Install:** `uvx virgool-mcp` or `claude mcp add virgool -- uvx virgool-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none. Optional `VIRGOOL_MCP_PROXY` (HTTP proxy URL, or a comma-separated list); system proxy settings are ignored.
- **Access:** read-only. It cannot log in, write, like, comment or follow. Needs an Iranian IP for full results (see [Limits](#limits)); the server uses the direct line by default.
- **Tools:** 11, all prefixed `vg_`. Typical sequences: `vg_search` -> `vg_post` / `vg_comments`; `vg_user` -> `vg_user_posts`; `vg_feed`; `vg_topics` -> `vg_topic_posts`; `vg_tag_posts`; `vg_publications` -> `vg_publication_posts`.
- **Use when:** the user wants to find Persian blog posts on a subject, read an article, see what readers wrote under it, look at an author or a group blog, or see what Virgool's editors picked.
- **Output:** compact JSON. Dates are ISO UTC, counts are numbers, titles, text and comments are Persian. Lists are 10 per page (`page`).
- **Domain:** the site is virgool.ir. The old virgool.io domain is dead.

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). No API key or account.

Claude Code:

```bash
claude mcp add virgool -- uvx virgool-mcp
```

Claude Desktop, Cursor, VS Code and other clients:

```json
{
  "mcpServers": {
    "virgool": { "command": "uvx", "args": ["virgool-mcp"] }
  }
}
```

Example prompts:

- "Search Virgool for posts about artificial intelligence."
- "Read this Virgool post and summarize it."
- "What did the editors pick on Virgool today?"
- <span dir="rtl">درباره هوش مصنوعی در ویرگول چه نوشته‌اند؟</span>
- <span dir="rtl">نظرهای زیر این پست ویرگول را بخوان.</span>

Real answer (18 Nov 2026): `vg_search(query="هوش مصنوعی")` found 1000 posts (the site's search cap); the top three were "هوشِ مصنوعی !" (15 likes, 3 comments), "هوش مصنوعی" (12 likes, 2 comments) and another "هوش مصنوعی" (9 likes, 2 comments).

## Tools

| Tool | What it returns |
|---|---|
| `vg_search` | Posts, authors, publications or tags matching a text; post rows carry the `hash` that `vg_post` reads |
| `vg_post` | One post: title, author, topics, tags, likes, comments, reading time and the full story text (images skipped) |
| `vg_comments` | Public top-level comments of a post, or the replies of one comment |
| `vg_user` | An author's profile (bio, followers, post count, links) and the publications they belong to |
| `vg_user_posts` | An author's published posts, newest first |
| `vg_feed` | Front-page posts: the editors' picks or the newest posts |
| `vg_topics` | All 50 Virgool topics (broad categories) with follower counts |
| `vg_topic_posts` | Latest posts of a topic such as book, economy or psychology |
| `vg_tag_posts` | Latest posts carrying a tag |
| `vg_publications` | Search or list publications (group blogs) |
| `vg_publication_posts` | Latest posts of a publication, newest first |

## Limits

- **Needs an Iranian IP for full results.** From abroad virgool.ir serves a reduced deployment: topics, editors' picks and an author's publications return 404, comments come back empty, and the newest-posts feed differs. The tools detect this and say so in the error or a `note`. The server ignores system proxy variables and connects directly by default; set `VIRGOOL_MCP_PROXY` only if you need a proxy with an Iranian exit.
- Search totals stop at 1000 hits; view counts (`views`) are not shown in search results.
- `vg_comments` lists top-level comments only; read replies by passing `replies_to` with a comment id.
- Virgool has no trending or view-count ranking, so `vg_feed` offers the editors' picks or the newest posts.
- `vg_publications` without a text returns a random sample per call, and some of those publications have no posts yet.
- Publications on a custom domain (for example neshan.blog) answer through their `virgool.ir/<name>` address; one such page did not finish loading in Chrome during checks, so its post list was checked against the API only.
- An author's lists tab, drafts, bookmarks and anything behind a login are not covered.

## فارسی

<div dir="rtl">

**virgool-mcp** یک سرور MCP غیررسمی و فقط‌خواندنی برای ویرگول (virgool.ir) است. با آن یک عامل هوش مصنوعی می‌تواند پست‌ها، نویسندگان، انتشارات و برچسب‌ها را جست‌وجو کند، متن کامل پست و نظرها و پاسخ‌ها را بخواند، پروفایل و پست‌های یک نویسنده را ببیند، منتخب‌های سردبیران و تازه‌ترین پست‌ها را فهرست کند و میان موضوع‌ها، برچسب‌ها و انتشارات بگردد. بدون حساب کاربری و کلید API کار می‌کند. برای نتیجهٔ کامل به IP ایران نیاز دارد؛ سرور به‌طور پیش‌فرض مستقیم وصل می‌شود. نصب در Claude Code:

</div>

```bash
claude mcp add virgool -- uvx virgool-mcp
```

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q          # offline tests on recorded fixtures
uv run python -m pytest -m live -q  # live calls to virgool.ir (direct Iranian line)
```

Releases: bump the version in `pyproject.toml` and `server.json`, run `uv lock`, then push a `v*` tag; GitHub Actions publishes to PyPI.

## Disclaimer

Unofficial and not affiliated with or endorsed by Virgool. It is read-only and uses the public pages and API of virgool.ir, which can change without notice.

## Author

Built and maintained by **Sepehr Radmard** (سپهر رادمرد). [LinkedIn](https://www.linkedin.com/in/sepehr-radmard) · [GitHub](https://github.com/sepehr071) · more servers in [iran-mcp](https://github.com/sepehr071/iran-mcp).

## مجوز استفاده (License)

<a href="https://www.linkedin.com/in/sepehr-radmard"><img src="https://raw.githubusercontent.com/sepehr071/iran-mcp/main/assets/license-banner.png" alt="استفادهٔ شخصی و غیرتجاری رایگان است؛ برای استفادهٔ تجاری با سپهر رادمرد تماس بگیرید. Free for personal and non-commercial use; commercial use needs a license." width="100%"></a>

**استفادهٔ شخصی و غیرتجاری رایگان است.** استفاده در شرکت، محصول پولی یا پروژهٔ مشتری به مجوز تجاری نیاز دارد؛ از راه [لینکدین](https://www.linkedin.com/in/sepehr-radmard) یا [گیت&zwnj;هاب](https://github.com/sepehr071) با سپهر رادمرد تماس بگیرید. متن کامل: [PolyForm Noncommercial 1.0.0](https://github.com/sepehr071/virgool-mcp/blob/main/LICENSE).

Free for personal and non-commercial use under the [PolyForm Noncommercial License 1.0.0](https://github.com/sepehr071/virgool-mcp/blob/main/LICENSE). Using it in a company, a paid product or a client project needs a commercial license: contact Sepehr Radmard on [LinkedIn](https://www.linkedin.com/in/sepehr-radmard) or [GitHub](https://github.com/sepehr071).
