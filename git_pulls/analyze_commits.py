#!/usr/bin/env python3
"""
GitHub Commit Analyzer
Pulls commits from the past week, analyzes code quality, and estimates hours spent.
Requires: pip install requests python-dotenv openai
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

import requests
from groq import Groq

load_dotenv()

# ─── Config ──────────────────────────────────────────────────────────────────

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")  # optional override

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ─── GitHub helpers ───────────────────────────────────────────────────────────


def get_authenticated_user() -> str:
    """Return the authenticated GitHub username."""
    r = requests.get("https://api.github.com/user", headers=HEADERS)
    r.raise_for_status()
    return r.json()["login"]


def get_user_repos(username: str) -> list[dict]:
    """Return all repos (public + private) the user has push access to."""
    repos = []
    page = 1
    while True:
        r = requests.get(
            "https://api.github.com/user/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "affiliation": "owner,collaborator"},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def get_commits_since(owner: str, repo: str, author: str, since: datetime) -> list[dict]:
    """Return commits by *author* in *repo* made after *since*."""
    commits = []
    page = 1
    since_iso = since.isoformat()
    while True:
        r = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits",
            headers=HEADERS,
            params={
                "author": author,
                "since": since_iso,
                "per_page": 100,
                "page": page,
            },
        )
        if r.status_code == 409:  # empty repo
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        commits.extend(batch)
        page += 1
    return commits


def get_commit_diff(owner: str, repo: str, sha: str) -> str:
    """Fetch the unified diff for a single commit (truncated for large diffs)."""
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
        headers={**HEADERS, "Accept": "application/vnd.github.diff"},
    )
    r.raise_for_status()
    diff = r.text
    # Keep the first 8 000 chars to stay within token limits
    return diff[:8000] + ("\n...[diff truncated]" if len(diff) > 8000 else "")


def get_commit_detail(owner: str, repo: str, sha: str) -> dict:
    """Return stats + file list for a commit."""
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


# ─── Time estimation heuristic ───────────────────────────────────────────────

LINES_PER_HOUR = 50  # conservative estimate: ~50 net new lines of real code / hour


def estimate_hours(commits: list[dict]) -> float:
    """
    Rough estimate based on:
    - additions / LINES_PER_HOUR for coding time
    - 15 min baseline per commit session (context-switch cost)
    """
    total_additions = sum(
        c.get("stats", {}).get("additions", 0) for c in commits
    )
    coding_hours = total_additions / LINES_PER_HOUR
    session_overhead = len(commits) * 0.25  # 15 min per commit
    return round(coding_hours + session_overhead, 2)


# ─── AI analysis ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior software engineer conducting a thorough weekly code review.
You will receive a structured summary of a developer's GitHub commits from the past 7 days.

Your job is to produce a report with these exact sections:

## 1. Overall Code Quality Score  
Rate 1–10 with a one-sentence justification.

## 2. Strengths  
Bullet-point list of 3–5 genuine positives observed in the diffs and commit messages.

## 3. Areas for Improvement  
Bullet-point list of 3–5 specific, actionable weaknesses (bad naming, missing error handling, large functions, missing tests, etc.).

## 4. Commit Hygiene  
Comment on message clarity, commit size, and frequency.

## 5. Estimated Hours  
Based on the line-change statistics provided, give your own estimate of hours spent and briefly explain your reasoning.  
Compare it against the heuristic estimate already calculated.

## 6. Recommendations  
Three concrete next steps the developer should take this week.

Be honest, precise, and constructive. Avoid vague praise. Ground every observation in the actual code shown."""


def build_prompt(username: str, commits_data: list[dict]) -> str:
    """Construct the user message sent to the AI."""
    lines = [
        f"Developer: {username}",
        f"Analysis window: past 7 days",
        f"Total commits analyzed: {len(commits_data)}",
        "",
    ]

    total_add = sum(c["additions"] for c in commits_data)
    total_del = sum(c["deletions"] for c in commits_data)
    lines += [
        f"Aggregate stats: +{total_add} additions, -{total_del} deletions",
        "",
        "─── COMMITS ───",
        "",
    ]

    for c in commits_data:
        lines += [
            f"Repo: {c['repo']}",
            f"SHA:  {c['sha'][:10]}",
            f"Date: {c['date']}",
            f"Message: {c['message']}",
            f"Stats: +{c['additions']} / -{c['deletions']} across {c['changed_files']} file(s)",
            "Diff (excerpt):",
            c["diff"],
            "",
            "─" * 60,
            "",
        ]

    return "\n".join(lines)


def analyze_with_ai(username: str, commits_data: list[dict], heuristic_hours: float) -> str:
    """Send commit data to Groq and return the formatted report."""
    client = Groq(api_key=GROQ_API_KEY)
    user_msg = build_prompt(username, commits_data)
    user_msg += f"\n\nHeuristic hour estimate (lines-based): {heuristic_hours} hours\n"

    print("  Sending data to Groq for analysis…")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    return response.choices[0].message.content


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Analyze your GitHub commits from the past week.")
    parser.add_argument("--username", help="GitHub username (overrides env var / API lookup)")
    parser.add_argument("--days", type=int, default=7, help="How many days back to look (default 7)")
    parser.add_argument("--output", default="report.md", help="Output markdown file (default: report.md)")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI analysis (just print stats)")
    args = parser.parse_args()

    # Validate credentials
    if not GITHUB_TOKEN:
        sys.exit("ERROR: GITHUB_TOKEN not set. Add it to your .env file.")
    if not args.no_ai and not GROQ_API_KEY:
        sys.exit("ERROR: GROQ_API_KEY not set. Add it to your .env file (or use --no-ai).")

    # Determine username
    username = args.username or GITHUB_USERNAME or get_authenticated_user()
    print(f"GitHub user : {username}")

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    print(f"Looking back: {args.days} days  (since {since.strftime('%Y-%m-%d %H:%M UTC')})")

    # Gather repos
    print("Fetching repositories…")
    repos = get_user_repos(username)
    print(f"  Found {len(repos)} repos")

    # Collect commits across all repos
    all_commits_raw: list[tuple[str, str, dict]] = []  # (owner, repo_name, commit_json)
    for repo in repos:
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        commits = get_commits_since(owner, repo_name, username, since)
        if commits:
            print(f"  {repo_name}: {len(commits)} commit(s)")
            for c in commits:
                all_commits_raw.append((owner, repo_name, c))

    if not all_commits_raw:
        print("No commits found in the past week. Nothing to analyze.")
        return

    print(f"\nTotal commits to analyze: {len(all_commits_raw)}")

    # Enrich each commit with diff + stats
    commits_data = []
    for i, (owner, repo_name, commit) in enumerate(all_commits_raw, 1):
        sha = commit["sha"]
        print(f"  [{i}/{len(all_commits_raw)}] Fetching diff for {repo_name}/{sha[:8]}…")
        try:
            detail = get_commit_detail(owner, repo_name, sha)
            diff = get_commit_diff(owner, repo_name, sha)
            commits_data.append({
                "repo": f"{owner}/{repo_name}",
                "sha": sha,
                "date": commit["commit"]["author"]["date"],
                "message": commit["commit"]["message"].strip(),
                "additions": detail.get("stats", {}).get("additions", 0),
                "deletions": detail.get("stats", {}).get("deletions", 0),
                "changed_files": len(detail.get("files", [])),
                "diff": diff,
                # raw stats for heuristic
                "stats": detail.get("stats", {}),
            })
        except Exception as e:
            print(f"    Warning: could not fetch detail for {sha[:8]}: {e}")

    # Heuristic hour estimate
    heuristic_hours = estimate_hours(commits_data)
    print(f"\nHeuristic hour estimate: {heuristic_hours} hrs")

    # AI analysis
    if args.no_ai:
        report = f"# Commit Analysis — {username}\n\n*(AI analysis skipped — run without --no-ai to enable)*\n\n"
        report += f"**Commits analyzed:** {len(commits_data)}\n"
        report += f"**Heuristic hour estimate:** {heuristic_hours} hrs\n"
    else:
        print("\nRunning AI analysis…")
        report_body = analyze_with_ai(username, commits_data, heuristic_hours)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        report = (
            f"# Weekly Code Analysis — {username}\n"
            f"_Generated {now} | Past {args.days} days | {len(commits_data)} commits_\n\n"
            + report_body
        )

    # Write report
    output_path = os.path.join(os.path.dirname(__file__), args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport written to: {output_path}")
    print("\n" + "═" * 60)
    print(report)


if __name__ == "__main__":
    main()
