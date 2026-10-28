"""Draws the daily activity panel (contribution grid + streaks) from the GitHub GraphQL API.

usage: GITHUB_TOKEN=... python3 scripts/activity.py OUT_DIR
Standard library only, so it runs on a bare GitHub Actions runner.
Writes OUT_DIR/activity.svg (desktop) and OUT_DIR/activity-m.svg (phone).
"""
import base64, datetime as dt, json, os, sys, urllib.request
from pathlib import Path

LOGIN = "Pug-03"
SRC = Path(__file__).resolve().parent / "src"
FONT = '-apple-system, BlinkMacSystemFont, &quot;SF Pro Display&quot;, &quot;Segoe UI&quot;, Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, &quot;SF Mono&quot;, Menlo, Consolas, monospace'
BLUE = "#2997ff"
LEVELS = ["#ffffff", "#0d3b70", "#1661bd", "#2997ff", "#7cc4ff"]   # level 0 is drawn at low opacity
POSES = ["type1", "think", "drink", "happy", "stretch", "type2", "o_hoodie"]   # one per weekday

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

def fetch():
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
                                 headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
                                          "Content-Type": "application/json"})
    cal = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"], LEVEL[d["contributionLevel"]]) for d in w["contributionDays"]]
             for w in cal["weeks"]]
    return cal["totalContributions"], weeks

def streaks(days):
    best = run = 0
    for _, n, _ in days:
        run = run + 1 if n else 0
        best = max(best, run)
    cur, i = 0, len(days) - 1
    if days and days[i][1] == 0: i -= 1          # today may simply not have a commit yet
    while i >= 0 and days[i][1]:
        cur += 1; i -= 1
    return cur, best

def mascot(pose, x, y, h):
    uri = "data:image/png;base64," + base64.b64encode((SRC / "poses" / f"{pose}.png").read_bytes()).decode()
    return (f'<ellipse cx="{x + h * 0.42}" cy="{y + h * 0.55}" rx="{h * 0.65}" ry="{h * 0.6}" fill="url(#glow)"/>'
            f'<g class="bob"><image x="{x}" y="{y}" height="{h}" width="{h}" preserveAspectRatio="xMidYMax meet" href="{uri}"/></g>')

def render(total, weeks, mobile):
    W, X0 = (640, 40) if mobile else (1200, 72)
    days = [d for w in weeks for d in w]
    cur, best = streaks(days)
    active = sum(1 for d in days if d[1])
    shown = weeks[-19:] if mobile else weeks
    cell, gap = (24, 5) if mobile else (16, 4)
    pose = POSES[dt.date.fromisoformat(days[-1][0]).weekday()]
    bkk = dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))
    today = bkk.strftime("%-d %b %H:%M").upper() + " BKK"

    y = 72
    body = (f'<text x="{X0}" y="{y}" font-family="{MONO}" font-size="{20 if mobile else 17}" font-weight="600" letter-spacing="2.4" fill="{BLUE}">'
            f'LIVE &#183; UPDATED {today}</text>'
            f'<text x="{X0 - 2}" y="{y + 52}" font-family="{FONT}" font-size="{42 if mobile else 46}" font-weight="700" letter-spacing="-1.2" fill="#f5f5f7">Last 12 months on GitHub</text>')
    body += mascot(pose, W - (24 if mobile else 56) - (110 if mobile else 150) * 0.85, 22, 110 if mobile else 150)
    y += 100
    stats = [(f"{total:,}", "contributions"), (str(cur), "day streak"), (str(best), "best streak"), (str(active), "active days")]
    sw = (W - 2 * X0) / (2 if mobile else 4)
    for i, (v, label) in enumerate(stats):
        sx = X0 + (i % (2 if mobile else 4)) * sw
        sy = y + (i // 2) * 92 * mobile + 46
        body += (f'<text x="{sx}" y="{sy}" font-family="{FONT}" font-size="{44 if mobile else 48}" font-weight="700" letter-spacing="-1" fill="#ffffff">{v}</text>'
                 f'<text x="{sx}" y="{sy + 30}" font-family="{MONO}" font-size="{18 if mobile else 15}" font-weight="600" letter-spacing="1.6" fill="#c7c7cc">{label.upper()}</text>')
    y += (184 if mobile else 100) + 20
    for wi, w in enumerate(shown):
        for d in w:
            di = dt.date.fromisoformat(d[0]).weekday()        # Mon=0
            row = (di + 1) % 7                                 # GitHub grid starts on Sunday
            op = ".07" if d[2] == 0 else "1"
            body += (f'<rect x="{X0 + wi * (cell + gap)}" y="{y + row * (cell + gap)}" width="{cell}" height="{cell}" rx="{cell * 0.28:.1f}" '
                     f'fill="{LEVELS[d[2]]}" fill-opacity="{op}"><title>{d[0]}: {d[1]}</title></rect>')
    y += 7 * (cell + gap) + 44
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{y}" viewBox="0 0 {W} {y}">
<title>GitHub activity</title>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#05070c"/><stop offset="1" stop-color="#0b1220"/></linearGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#fff" stroke-opacity=".035"/></pattern>
<radialGradient id="glow"><stop offset="0" stop-color="#2997ff" stop-opacity=".30"/><stop offset=".5" stop-color="#2997ff" stop-opacity=".09"/><stop offset="1" stop-color="#2997ff" stop-opacity="0"/></radialGradient>
<clipPath id="card"><rect width="{W}" height="{y}" rx="28"/></clipPath>
</defs>
<style>
.bob{{animation:bob 4s ease-in-out infinite}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-5px)}}}}
@media (prefers-reduced-motion: reduce){{.bob{{animation:none}}}}
</style>
<g clip-path="url(#card)">
<rect width="{W}" height="{y}" fill="url(#bg)"/>
<rect width="{W}" height="{y}" fill="url(#grid)"/>
<ellipse cx="{W * 0.2}" cy="{y * 0.9}" rx="420" ry="300" fill="url(#glow)"/>
{body}
</g>
<rect x=".5" y=".5" width="{W-1}" height="{y-1}" rx="27.5" fill="none" stroke="#fff" stroke-opacity=".08"/>
</svg>'''

if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    total, weeks = fetch()
    (out / "activity.svg").write_text(render(total, weeks, False))
    (out / "activity-m.svg").write_text(render(total, weeks, True))
    print("activity panels written to", out)
