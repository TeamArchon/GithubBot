from __future__ import annotations

import html
from typing import Any


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def cut(value: Any, limit: int = 180) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def actor(obj: Any) -> str:
    if isinstance(obj, dict):
        return esc(obj.get("login") or obj.get("name") or "unknown")
    return "unknown"


def repository(data: dict) -> dict:
    return data.get("repository") or {}


def repo_name(data: dict) -> str:
    repo = repository(data)
    return esc(repo.get("full_name") or repo.get("name") or "unknown/repository")


def repo_url(data: dict) -> str:
    return repository(data).get("html_url") or "https://github.com"


def _pack(title: str, lines: list[str], button: str, url: str | None):
    text = title + ("\n" + "\n".join(lines) if lines else "")
    return text, button, url or repo_url({"repository": {"html_url": "https://github.com"}})


def result(data: dict, max_commits: int = 5):
    action = data.get("action")
    repo = repository(data)
    name = repo_name(data)
    rurl = repo_url(data)
    sender = data.get("sender") or {}

    # GitHub Star event
    if "starred_at" in data or (action in {"created", "deleted"} and "starred_at" in data):
        word = "Star Added" if action != "deleted" else "Star Removed"
        return _pack(
            f'<b>⭐ [{name}] {word}</b>',
            [f"By: {actor(sender)}", f"Total Stars: <code>{esc(repo.get('stargazers_count', 0))}</code>"],
            "View Repository", rurl,
        )

    # Push event
    if "head_commit" in data and data.get("ref"):
        commits = data.get("commits") or []
        branch = str(data.get("ref", "")).split("/", 2)[-1] or "unknown"
        lines = [f"🌿 Branch: <code>{esc(branch)}</code>", f"👤 Pushed by: {actor(data.get('pusher') or sender)}"]
        shown = commits[:max_commits]
        for commit in shown:
            sha = str(commit.get("id") or "")[:7]
            message = cut((commit.get("message") or "").splitlines()[0], 160)
            lines.append(f"<code>{esc(sha)}</code> {esc(message)} — {actor(commit.get('author'))}")
        if len(commits) > len(shown):
            lines.append(f"… and {len(commits) - len(shown)} more commit(s)")
        head = data.get("head_commit") or {}
        return _pack(
            f'<b>📦 [{name}] {len(commits) or 1} new commit(s)</b>',
            lines,
            "View Commit", head.get("url") or rurl,
        )

    # Fork event
    if data.get("forkee"):
        fork = data["forkee"] or {}
        fork_name = esc(fork.get("full_name") or fork.get("name") or "unknown")
        return _pack(
            f'<b>🍴 [{name}] Fork Created</b>',
            [f"Fork: <code>{fork_name}</code>", f"By: {actor(sender)}"],
            "View Fork", fork.get("html_url") or rurl,
        )

    # Issues
    if data.get("issue"):
        issue = data["issue"]
        allowed = {"opened", "closed", "reopened", "edited", "deleted", "locked", "unlocked", "pinned", "unpinned", "transferred", "assigned", "unassigned", "labeled", "unlabeled", "milestoned", "demilestoned"}
        if action in allowed:
            return _pack(
                f'<b>🐛 [{name}] Issue {esc(action)}</b>',
                [f"#{esc(issue.get('number'))} — {esc(cut(issue.get('title'), 100))}", f"By: {actor(issue.get('user') or sender)}", f"{esc(cut(issue.get('body'), 250))}"],
                "View Issue", issue.get("html_url") or rurl,
            )

    # Pull requests
    if data.get("pull_request"):
        pr = data["pull_request"]
        allowed = {"opened", "closed", "reopened", "edited", "deleted", "locked", "unlocked", "ready_for_review", "converted_to_draft", "assigned", "unassigned", "labeled", "unlabeled", "synchronize"}
        if action in allowed:
            return _pack(
                f'<b>🔀 [{name}] Pull Request {esc(action)}</b>',
                [f"#{esc(data.get('number'))} — {esc(cut(pr.get('title'), 100))}", f"By: {actor(pr.get('user') or sender)}", f"{esc(cut(pr.get('body'), 250))}"],
                "View Pull Request", pr.get("html_url") or rurl,
            )

    # Releases
    if data.get("release"):
        release = data["release"]
        allowed = {"published", "unpublished", "created", "edited", "deleted", "prereleased", "released"}
        if action in allowed:
            tag = release.get("tag_name") or release.get("name") or "untagged"
            return _pack(
                f'<b>🚀 [{name}] Release {esc(action)}</b>',
                [f"Tag: <code>{esc(tag)}</code>", f"By: {actor(release.get('author') or sender)}"],
                "View Release", release.get("html_url") or rurl,
            )

    # GitHub Actions workflow_run
    if data.get("workflow_run"):
        run = data["workflow_run"]
        allowed = {"requested", "in_progress", "completed", "queued", "waiting", "pending", "completed"}
        if action in allowed:
            workflow = data.get("workflow") or {}
            workflow_name = run.get("name") or workflow.get("name") or "Unknown workflow"
            conclusion = run.get("conclusion") or "running"
            return _pack(
                f'<b>⚙️ [{name}] Workflow {esc(action)}</b>',
                [f"Workflow: <code>{esc(workflow_name)}</code>", f"Status: <code>{esc(run.get('status') or action)}</code>", f"Conclusion: <code>{esc(conclusion)}</code>"],
                "View Workflow", run.get("html_url") or rurl,
            )

    return None
