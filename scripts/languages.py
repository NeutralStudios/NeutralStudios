"""Builds assets/languages.svg from the languages in your public GitHub repos.

Runs in GitHub Actions (see .github/workflows/profile.yml), so the card is
always up to date and doesn't depend on an outside service.
Only the Python standard library is used.

Settings (environment variables):
  GH_USER          GitHub user or organization name
  GITHUB_TOKEN     token for the API (provided by GitHub Actions)
  LANG_COUNT       how many languages to show (default 6)
  EXCLUDE_LANGS    comma separated languages to hide, e.g. "Batchfile,Dockerfile"
  EXCLUDE_REPOS    comma separated repo names to skip
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "NeutralStudios")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
COUNT = int(os.environ.get("LANG_COUNT", "6"))
EXCLUDE_LANGS = {s.strip().lower() for s in os.environ.get("EXCLUDE_LANGS", "").split(",") if s.strip()}
EXCLUDE_REPOS = {s.strip().lower() for s in os.environ.get("EXCLUDE_REPOS", "").split(",") if s.strip()}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "assets", "languages.svg")

# Brand palette, brightest first (pink -> purple -> blue -> teal ...)
PALETTE = ["#f107a3", "#b026e8", "#7b2ff7", "#4f6bff", "#22b8f0", "#2dd4bf", "#a3a0c2"]


def api(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-languages"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    totals, repos, page = {}, 0, 1
    while True:
        batch = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
        if not batch:
            break
        for repo in batch:
            if repo.get("fork") or repo["name"].lower() in EXCLUDE_REPOS:
                continue
            langs = api(repo["languages_url"])
            if langs:
                repos += 1
            for lang, size in langs.items():
                if lang.lower() not in EXCLUDE_LANGS:
                    totals[lang] = totals.get(lang, 0) + size
        page += 1
    return totals, repos


def render(totals, repos):
    total = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top, rest = ranked[:COUNT], ranked[COUNT:]
    rows = [(name, size / total * 100) for name, size in top]
    other = sum(size for _, size in rest) / total * 100
    if other >= 0.1:
        rows.append(("Other", other))

    W, cols = 840, 3
    lines = (len(rows) + cols - 1) // cols
    H = 128 + lines * 30
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Most used languages: {escape(", ".join(f"{n} {p:.1f}%" for n, p in rows))}">',
         '<defs><linearGradient id="s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7b2ff7"/><stop offset="1" stop-color="#f107a3"/></linearGradient>'
         '<linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d0f42"/><stop offset="1" stop-color="#120829"/></linearGradient>'
         f'<clipPath id="bar"><rect x="32" y="76" width="{W - 64}" height="12" rx="6"/></clipPath></defs>',
         '<style>.t{font:600 18px "Segoe UI",Ubuntu,"Helvetica Neue",Arial,sans-serif;fill:#ffffff}'
         '.m{font:400 13px "Segoe UI",Ubuntu,"Helvetica Neue",Arial,sans-serif;fill:#a79fd0}'
         '.l{font:600 14px "Segoe UI",Ubuntu,"Helvetica Neue",Arial,sans-serif;fill:#ece6ff}'
         '.p{font:400 14px "Segoe UI",Ubuntu,"Helvetica Neue",Arial,sans-serif;fill:#a79fd0}'
         '@keyframes g{from{transform:scaleX(0)}to{transform:scaleX(1)}}.b{animation:g .9s ease-out both;transform-origin:32px 0}</style>',
         f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="url(#f)" stroke="url(#s)" stroke-opacity=".55"/>',
         '<text class="t" x="32" y="48">Most used languages</text>',
         f'<text class="m" x="{W - 32}" y="48" text-anchor="end">across {repos} public repositor{"y" if repos == 1 else "ies"}</text>',
         f'<rect x="32" y="76" width="{W - 64}" height="12" rx="6" fill="#2a1a57"/>',
         '<g clip-path="url(#bar)"><g class="b">']
    x, width = 32.0, W - 64
    for i, (name, pct) in enumerate(rows):
        w = width * pct / 100
        color = PALETTE[-1] if name == "Other" else PALETTE[i % (len(PALETTE) - 1)]
        s.append(f'<rect x="{x:.2f}" y="76" width="{w + 1.5:.2f}" height="12" fill="{color}"/>')
        x += w
    s.append("</g></g>")
    colw = (W - 64) / cols
    for i, (name, pct) in enumerate(rows):
        cx = 32 + (i % cols) * colw
        cy = 122 + (i // cols) * 30
        color = PALETTE[-1] if name == "Other" else PALETTE[i % (len(PALETTE) - 1)]
        s.append(f'<circle cx="{cx + 6:.1f}" cy="{cy - 5}" r="6" fill="{color}"/>'
                 f'<text class="l" x="{cx + 20:.1f}" y="{cy}">{escape(name)}</text>'
                 f'<text class="p" x="{cx + colw - 24:.1f}" y="{cy}" text-anchor="end">{pct:.1f}%</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--placeholder":
        svg = render({}, 0).replace("across 0 public repositories", "updating, check back in a minute")
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(svg)
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        totals, repos = {"Lua": 812000, "JavaScript": 214000, "HTML": 96000, "CSS": 71000, "TypeScript": 22000, "Python": 9000, "Shell": 3000}, 14
    else:
        totals, repos = collect()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(totals, repos))
    print(f"wrote {OUT}: {len(totals)} languages from {repos} repos")
