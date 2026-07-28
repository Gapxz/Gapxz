import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

USERNAME = os.environ.get("GITHUB_USERNAME", "Gapxz")
TOKEN = os.environ["GITHUB_TOKEN"]
OUTPUT = Path("assets/contribution-streak.svg")

MONTHS = [
    "jan.", "fev.", "mar.", "abr.", "mai.", "jun.",
    "jul.", "ago.", "set.", "out.", "nov.", "dez.",
]


def graphql(query, variables):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "Gapxz-profile-stats",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def format_day(value):
    return f"{value.day} de {MONTHS[value.month - 1]}"


def format_range(start, end, present=False):
    if present:
        return f"{format_day(start)} de {start.year} - Presente"
    if not start or not end:
        return "Sem sequência"
    left = format_day(start)
    right = format_day(end)
    if start.year != end.year:
        left += f" de {start.year}"
        right += f" de {end.year}"
    return f"{left} - {right}"


def streaks(counts, first_day, today):
    end = today if counts.get(today, 0) else today - timedelta(days=1)
    current = 0
    current_end = end
    cursor = end
    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    current_start = cursor + timedelta(days=1) if current else None

    longest = 0
    longest_start = None
    longest_end = None
    run = 0
    run_start = None
    cursor = first_day
    while cursor <= today:
        if counts.get(cursor, 0) > 0:
            if run == 0:
                run_start = cursor
            run += 1
            if run > longest:
                longest = run
                longest_start = run_start
                longest_end = cursor
        else:
            run = 0
            run_start = None
        cursor += timedelta(days=1)

    return current, current_start, current_end, longest, longest_start, longest_end


user_query = """
query($login: String!) {
  user(login: $login) { createdAt }
}
"""
created_at = datetime.fromisoformat(
    graphql(user_query, {"login": USERNAME})["user"]["createdAt"].replace("Z", "+00:00")
)
now = datetime.now(timezone.utc)
calendar_query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""

counts = {}
chunk_start = created_at
while chunk_start <= now:
    chunk_end = min(chunk_start + timedelta(days=364, hours=23, minutes=59, seconds=59), now)
    data = graphql(
        calendar_query,
        {
            "login": USERNAME,
            "from": chunk_start.isoformat(),
            "to": chunk_end.isoformat(),
        },
    )
    weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    for week in weeks:
        for item in week["contributionDays"]:
            contribution_day = date.fromisoformat(item["date"])
            if created_at.date() <= contribution_day <= now.date():
                counts[contribution_day] = item["contributionCount"]
    chunk_start = chunk_end + timedelta(seconds=1)

total = sum(counts.values())
current, current_start, current_end, longest, longest_start, longest_end = streaks(
    counts, created_at.date(), now.date()
)

joined_range = format_range(created_at.date(), now.date(), present=True)
current_range = format_range(current_start, current_end)
longest_range = format_range(longest_start, longest_end)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-labelledby="title desc">
  <title id="title">Sequência de contribuições de Gap</title>
  <desc id="desc">{total} contribuições, sequência atual de {current} dias e maior sequência de {longest} dias.</desc>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-anchor: middle; }}
    .number {{ fill: #F2F4F3; font-size: 28px; font-weight: 700; }}
    .label {{ fill: #F2F4F3; font-size: 14px; font-weight: 600; }}
    .date {{ fill: #F2F4F3; fill-opacity: .68; font-size: 12px; }}
  </style>
  <rect width="495" height="195" rx="6" fill="#0A0908"/>
  <path d="M165 28V167M330 28V167" stroke="#49111C" stroke-width="2"/>

  <text class="number" x="82.5" y="78">{total}</text>
  <text class="label" x="82.5" y="116">Total de Contribuições</text>
  <text class="date" x="82.5" y="145">{joined_range.split(' - ')[0]}</text>
  <text class="date" x="82.5" y="163">- Presente</text>

  <circle cx="247.5" cy="70" r="40" fill="none" stroke="#49111C" stroke-width="6"/>
  <path d="M247.5 16c7 8 7 15 0 22-7-7-7-14 0-22Zm0 7c-2.5 4-2 7 0 9 2-2 2.5-5 0-9Z" fill="#49111C" fill-rule="evenodd"/>
  <text class="number" x="247.5" y="80">{current}</text>
  <text class="label" x="247.5" y="135">Sequência Atual</text>
  <text class="date" x="247.5" y="160">{current_range}</text>

  <text class="number" x="412.5" y="78">{longest}</text>
  <text class="label" x="412.5" y="116">Maior Sequência</text>
  <text class="date" x="412.5" y="151">{longest_range}</text>
</svg>
'''

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg, encoding="utf-8")
