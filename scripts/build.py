"""Builds every SVG panel in assets/ (desktop) and assets/m/ (phone) plus README.md.

Run from anywhere:  python3 scripts/build.py   (needs Pillow, macOS for SF Pro metrics)
"""
import base64, io, html
from pathlib import Path
from PIL import Image, ImageFont, ImageFilter

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "scripts" / "src"
RAW = "https://raw.githubusercontent.com/Pug-03/Pug-03/main"
FONT = '-apple-system, BlinkMacSystemFont, &quot;SF Pro Display&quot;, &quot;Segoe UI&quot;, Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, &quot;SF Mono&quot;, Menlo, Consolas, monospace'
BLUE, GREEN = "#2997ff", "#30d158"
esc = lambda t: html.escape(t, quote=False)

# Desktop panels are 1200 wide and shown at ~850px. Phone panels are 640 wide and shown
# at ~360px, so their type is set larger relative to the canvas.
MODES = {
    "desktop": dict(W=1200, X0=72, dir="assets", eyebrow=17, h=46, body=(24, 37), dp_title=28, dp_desc=(21, 32),
                    bullet=(23, 35), rank=(24, 32), ev=(20, 28), group=16, label=16, icon=(54, 20), more=(50, 24, 14)),
    "mobile": dict(W=640, X0=40, dir="assets/m", eyebrow=20, h=42, body=(26, 39), dp_title=28, dp_desc=(23, 34),
                   bullet=(25, 37), rank=(26, 35), ev=(22, 31), group=19, label=19, icon=(56, 16), more=(56, 20, 7)),
}
L = MODES["desktop"]
W = X0 = TEXT_W = 0

def use(mode):
    global L, W, X0, TEXT_W
    L = MODES[mode]; W, X0 = L["W"], L["X0"]; TEXT_W = W - 2 * X0
    (REPO / L["dir"]).mkdir(parents=True, exist_ok=True)

# --- text measurement (SF Pro), with headroom for wider fonts such as Segoe UI ---
_fonts = {}
def font(size, bold):
    key = (size, bold)
    if key not in _fonts:
        f = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", size)
        try: f.set_variation_by_name("Bold" if bold else "Regular")
        except Exception: pass
        _fonts[key] = f
    return _fonts[key]
def tw(text, size, bold=False):
    return font(size, bold).getlength(text) * 1.06

def wrap(segments, size, width):
    """segments: [(text, style)] where style in {'n','b','hl'} -> list of lines of segments"""
    words = []
    for text, st in segments:
        for w in text.split(" "):
            if w: words.append((w, st))
    lines, cur, curw = [], [], 0
    for w, st in words:
        ww = tw(w + " ", size, st != "n")
        if cur and curw + ww > width:
            lines.append(cur); cur, curw = [], 0
        cur.append((w, st)); curw += ww
    if cur: lines.append(cur)
    return lines

def line_svg(line, x, y, size, base="#dcdce1"):
    out = []
    for w, st in line:
        attrs = {"n": f'fill="{base}"', "b": 'fill="#f5f5f7" font-weight="700"',
                 "hl": f'fill="{BLUE}" font-weight="700"'}[st]
        out.append(f'<tspan {attrs}>{esc(w)} </tspan>')
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}">{"".join(out)}</text>'

def panel(h, body, glow=(0.85, 0.3), title=""):
    gx, gy = glow
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">
<title>{title}</title>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#05070c"/><stop offset="1" stop-color="#0b1220"/></linearGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#fff" stroke-opacity=".035"/></pattern>
<radialGradient id="glow"><stop offset="0" stop-color="#2997ff" stop-opacity=".30"/><stop offset=".5" stop-color="#2997ff" stop-opacity=".09"/><stop offset="1" stop-color="#2997ff" stop-opacity="0"/></radialGradient>
<radialGradient id="dotg"><stop offset="0" stop-color="#5ab4ff" stop-opacity=".9"/><stop offset=".35" stop-color="#2997ff" stop-opacity=".45"/><stop offset="1" stop-color="#2997ff" stop-opacity="0"/></radialGradient>
<clipPath id="card"><rect width="{W}" height="{h}" rx="28"/></clipPath>
</defs>
<style>
.pulse{{animation:pulse 6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}
@keyframes pulse{{0%,100%{{opacity:.7;transform:scale(1)}}50%{{opacity:1;transform:scale(1.07)}}}}
.blink{{animation:blink 2s ease-in-out infinite}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
.bob{{animation:bob 4s ease-in-out infinite}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-5px)}}}}
@media (prefers-reduced-motion: reduce){{.pulse,.blink,.bob{{animation:none}}}}
</style>
<g clip-path="url(#card)">
<rect width="{W}" height="{h}" fill="url(#bg)"/>
<rect width="{W}" height="{h}" fill="url(#grid)"/>
<ellipse cx="{W * gx}" cy="{h * gy}" rx="420" ry="300" fill="url(#glow)"/>
{body}
</g>
<rect x=".5" y=".5" width="{W-1}" height="{h-1}" rx="27.5" fill="none" stroke="#fff" stroke-opacity=".08"/>
</svg>'''

def eyebrow(y, label, color=BLUE):
    return f'<text x="{X0}" y="{y}" font-family="{MONO}" font-size="{L["eyebrow"]}" letter-spacing="2.4" font-weight="600" fill="{color}">{label}</text>'
def heading(y, text):
    return f'<text x="{X0 - 2}" y="{y}" font-family="{FONT}" font-size="{L["h"]}" font-weight="700" letter-spacing="-1.2" fill="#f5f5f7">{esc(text)}</text>'

_uris = {}
def webp_uri(im):
    b = io.BytesIO(); im.save(b, format="WEBP", lossless=True, method=6)
    return "data:image/webp;base64," + base64.b64encode(b.getvalue()).decode()
def mascot(pose, h, x=None, y=None, right=56, bottom=None, ph=None):
    im = Image.open(SRC / "poses" / f"{pose}.png")
    w = round(im.width / im.height * h)
    x = W - right - w if x is None else x
    if bottom is not None: y = ph - bottom - h
    if pose not in _uris: _uris[pose] = webp_uri(im)
    return (f'<ellipse cx="{x + w / 2}" cy="{y + h * 0.55}" rx="{w * 0.75}" ry="{h * 0.6}" fill="url(#glow)"/>'
            f'<g class="bob"><image x="{x}" y="{y}" width="{w}" height="{h}" href="{_uris[pose]}"/></g>')
def glow_dot(cx, cy, r=5):
    return (f'<circle class="pulse" cx="{cx}" cy="{cy}" r="{r * 3.4}" fill="url(#dotg)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#5ab4ff"/>')

def save(name, svg):
    (REPO / L["dir"] / name).write_text(svg)
    print(f'{L["dir"]}/{name}', len(svg) // 1024, "KB")

# ================= banner =================
def banner_char():
    c = Image.open(SRC / "poses" / "main.png")
    rgb = c.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    c = Image.merge("RGBA", (*rgb.split(), c.getchannel("A")))
    return c, webp_uri(c)

PILLS = [("MIT Media Lab", "Top 3 Global"), ("World Robot Championship", "Dubai"), ("GLO Innovation", "1st Place")]

def code_lines(cx, cy, ch):
    """Short blue code lines that rise off the laptop screen and fade, so the banner looks like work in progress."""
    k = ch / 682                       # main.png is 682px tall; the laptop lid sits around x 350-495, y 180
    x0, y0 = cx + 330 * k, cy + 165 * k
    lines = [(0, 26, 0.0), (10, 40, 0.7), (4, 18, 1.4), (16, 32, 2.1), (2, 24, 2.8)]
    out = '<style>.code{animation:rise 3.5s ease-out infinite;opacity:0}' \
          '@keyframes rise{0%{opacity:0;transform:translateY(0)}15%{opacity:1}100%{opacity:0;transform:translateY(-90px)}}' \
          '.breathe{animation:breathe 4.5s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}' \
          '@keyframes breathe{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.008)}}' \
          '@media (prefers-reduced-motion: reduce){.code,.breathe{animation:none}}</style>'
    for dx, w, delay in lines:
        out += (f'<rect class="code" style="animation-delay:{delay}s" x="{x0 + dx * k * 3:.1f}" y="{y0:.1f}" '
                f'width="{w * k * 3:.1f}" height="{max(5, 12 * k):.1f}" rx="3" fill="#5ab4ff"/>')
    out += (f'<text class="code" style="animation-delay:1.75s" x="{x0 + 70 * k:.1f}" y="{y0 - 6:.1f}" '
            f'font-family="{MONO}" font-size="{max(12, 34 * k):.0f}" font-weight="700" fill="#7cc4ff">&lt;/&gt;</text>')
    return out

def banner(mobile):
    c, uri = banner_char()
    if not mobile:
        H, ch, px, py, pgap, psize = 380, 330, 476, 118, 52, 18
        name_size, name_y, tag = 68, (148, 216), (264, 27)
        ceo_y, ceo_size, status_size = 288, 20, 18
    else:
        H, ch, px, py, pgap, psize = 520, 220, X0, 368, 50, 22
        name_size, name_y, tag = 64, (138, 202), (250, 26)
        ceo_y, ceo_size, status_size = 272, 22, 20
    cw = round(c.width / c.height * ch)
    cx, cy = W - cw - (28 if not mobile else 16), H - ch - 14
    gx, gy = cx + cw / 2, cy + ch * 0.42
    pill_svg = "".join(
        f'<g transform="translate({px} {py + i * pgap})">' + glow_dot(10, 0) +
        f'<text x="30" y="{psize * 0.36:.1f}" font-family="{FONT}" font-size="{psize}" font-weight="600" fill="#ffffff">{a}'
        f'<tspan fill="#6e6e73"> &#183; </tspan><tspan fill="#d1d1d6" font-weight="500">{b}</tspan></text></g>'
        for i, (a, b) in enumerate(PILLS))
    ceo_w = round(tw("Founder & CEO of ", ceo_size, True) + tw("DeePer", ceo_size, True) + 50)
    ceo_h = round(ceo_size * 2.6)
    link = ("" if mobile else
            f'<text x="{62 + ceo_w + 16}" y="{ceo_y + 32}" font-family="{MONO}" font-size="17" font-weight="600" letter-spacing="1" fill="#a1c8ff">deeper.in.th</text>')
    body = f'''<radialGradient id="g2"><stop offset="0" stop-color="#2997ff" stop-opacity=".45"/><stop offset=".5" stop-color="#2997ff" stop-opacity=".14"/><stop offset="1" stop-color="#2997ff" stop-opacity="0"/></radialGradient>
<radialGradient id="floor"><stop offset="0" stop-color="#6cb6ff" stop-opacity=".20"/><stop offset="1" stop-color="#2997ff" stop-opacity="0"/></radialGradient>
<ellipse class="pulse" cx="{gx}" cy="{gy}" rx="{ch * 0.79:.0f}" ry="{ch * 0.67:.0f}" fill="url(#g2)"/>
<ellipse cx="{gx}" cy="{cy + ch - 8}" rx="{ch * 0.73:.0f}" ry="30" fill="url(#floor)"/>
<g class="breathe"><image x="{cx}" y="{cy}" width="{cw}" height="{ch}" href="{uri}"/></g>
{code_lines(cx, cy, ch)}
<circle class="blink" cx="{X0 - 2}" cy="64" r="6" fill="{GREEN}"/>
<text x="{X0 + 16}" y="70" font-family="{MONO}" font-size="{status_size}" font-weight="600" letter-spacing="2.4" fill="{BLUE}">PUG-03 &#183; BANGKOK, TH</text>
<text font-family="{FONT}" font-size="{name_size}" font-weight="700" letter-spacing="-2.2" fill="#f5f5f7"><tspan x="{X0 - 11}" y="{name_y[0]}">Nathaporn</tspan><tspan x="{X0 - 11}" y="{name_y[1]}" fill="#b4d4ff">Saituptim.</tspan></text>
<text x="{X0 - 8}" y="{tag[0]}" font-family="{FONT}" font-size="{tag[1]}" font-weight="700" fill="#ffffff">AI. Computer Vision. Robotics.</text>
<g transform="translate({X0 - 10} {ceo_y})">
<rect width="{ceo_w}" height="{ceo_h}" rx="{ceo_h / 2}" fill="#2997ff" fill-opacity=".14" stroke="#2997ff" stroke-opacity=".55"/>
{glow_dot(25, ceo_h / 2, 5.5)}
<text x="42" y="{ceo_h / 2 + ceo_size * 0.35:.1f}" font-family="{FONT}" font-size="{ceo_size}" font-weight="700" fill="#ffffff">Founder &amp; CEO of <tspan fill="#4aa8ff" font-weight="800">DeePer</tspan></text>
</g>
{link}
{pill_svg}'''
    save("banner.svg", panel(H, body, glow=(0.3, 0.2), title="Nathaporn Saituptim"))

# ================= about =================
def about(mobile):
    y = 72
    body = eyebrow(y, "ABOUT ME"); y += 52
    body += heading(y, "Hey, what's up?"); y += 58
    para = [("I'm", "n"), ("Nathaporn Saituptim", "b"),
            ("— a high school student developer and robotics innovator from Thailand. I build end-to-end products that bridge smart software with physical hardware: AI and computer vision, autonomous robots, full-stack web apps, and embedded IoT.", "n")]
    size, lh = L["body"]
    for ln in wrap(para, size, TEXT_W):
        body += line_svg(ln, X0, y, size); y += lh
    y += 26
    deeper = [("A free web app of deep conversation cards for couples, friends & family. 1,050+ curated questions, swipe and take turns on one phone.", "n")]
    dsize, dlh = L["dp_desc"]
    dl = wrap(deeper, dsize, TEXT_W - 56)
    top = 84 if not mobile else 118
    bh = top - 2 + len(dl) * dlh
    link_x, link_y, anchor = (X0 + TEXT_W - 28, y + 43, "end") if not mobile else (X0 + 28, y + 80, "start")
    body += (f'<rect x="{X0}" y="{y}" width="{TEXT_W}" height="{bh}" rx="20" fill="#2997ff" fill-opacity=".08" stroke="#2997ff" stroke-opacity=".35"/>'
             f'<text x="{X0 + 28}" y="{y + 44}" font-family="{FONT}" font-size="{L["dp_title"]}" font-weight="700" fill="#ffffff">Founder &amp; CEO of <tspan fill="#4aa8ff">DeePer</tspan></text>'
             f'<text x="{link_x}" y="{link_y}" text-anchor="{anchor}" font-family="{MONO}" font-size="18" font-weight="600" letter-spacing="1" fill="{BLUE}">deeper.in.th</text>')
    yy = y + top
    for ln in dl:
        body += line_svg(ln, X0 + 28, yy, dsize); yy += dlh
    y += bh + 40
    bullets = [[("Working at", "n"), ("Yeah Association", "b")],
               [("Currently building autonomous systems, full-stack web apps, and embedded IoT solutions", "n")],
               [("Ask me about AI models, robotics, startups, or slick UI design", "n")],
               [("Fun fact: I love Apple-style minimalist layouts and dark-themed dev setups", "n")]]
    bsize, blh = L["bullet"]
    for b in bullets:
        body += f'<circle cx="{X0 + 6}" cy="{y - 7}" r="4" fill="{BLUE}"/>'
        for ln in wrap(b, bsize, TEXT_W - 30):
            body += line_svg(ln, X0 + 26, y, bsize); y += blh
        y += 10
    ah = y + 30
    body += mascot("happy", 150, bottom=22, ph=ah) if not mobile else mascot("happy", 110, y=26, right=28)
    save("about.svg", panel(ah, body, glow=(0.9, 0.15), title="About me"))

# ================= awards =================
GROUPS = [
    ("AI &amp; SOFTWARE INNOVATION", [
        ("Top 3 Global Finalist", "AI & Robotics Hackathon 2025 by MIT Media Lab"),
        ("1st Place Winner", "GLO Innovation 2026 · selected from 173 teams"),
        ("Best App Design for Elderly & Alzheimer's Patients", "KMITL ToBeIT'69"),
        ("Top 4 Finalist", "Play to Build AI Hackathon, SEABW 2026 by AWS · the only solo student against pro teams"),
        ("Top 5 Finalist", "OIC InsurTech Award 2026 · selected from 501 teams"),
        ("AI for Thai Service Standard Award · Top 15", "AI for Thai Service Onboarding · out of 150 teams"),
        ("Semifinalist", "CEDT Innovation Summit 2026 · selected from 484 teams")]),
    ("ROBOTICS &amp; HARDWARE", [
        ("Top 2 Finalist · Dubai Global Finals Qualifier", "World Robot Championship 2026 (3kg RC Sumo)"),
        ("Top 3 Finalist · China Finals Qualifier", "Maker Robotics Challenge 2026 (1.5kg Sumo)")]),
    ("WEB DEVELOPMENT &amp; CONTENT", [
        ("1st Place Winner", "Thailand Metaverse Hackathon & Exhibition 2026 by Chulalongkorn University"),
        ("Overall Winner · Best Idea · Best Content", "Junior Webmaster Camp 14")]),
]
def awards(mobile):
    rsize, rlh = L["rank"]; esize, elh = L["ev"]
    x, width, y = X0, TEXT_W, 190
    out = ""
    for label, items in GROUPS:
        out += (f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{BLUE}"/>'
                f'<text x="{x + 20}" y="{y}" font-family="{MONO}" font-size="{L["group"]}" font-weight="600" letter-spacing="2" fill="{BLUE}">{label}</text>')
        y += 40
        for rank, ev in items:
            top = y - 22
            for ln in wrap([(rank, "b")], rsize, width - 22):
                out += line_svg(ln, x + 22, y, rsize); y += rlh
            for ln in wrap([(ev, "n")], esize, width - 22):
                out += line_svg(ln, x + 22, y, esize, "#c7c7cc"); y += elh
            out += f'<rect x="{x}" y="{top}" width="3" height="{y - top - 14}" rx="1.5" fill="{BLUE}" fill-opacity=".7"/>'
            y += 18
        y += 22
    h = y + 10
    head = eyebrow(72, "TRACK RECORD") + heading(124, "Awards & Achievements")
    if not mobile:
        head += mascot("stretch", 170, y=26)
        head += mascot("o_hoodie", 200, y=round(y * 0.42), right=80)
        head += mascot("drink", 150, bottom=24, ph=h)
    else:
        head += mascot("stretch", 120, y=18, right=24)
    save("awards.svg", panel(h, head + out, glow=(0.15, 0.1), title="Awards and Achievements"))

# ================= tech stack =================
def icon_uri(n):
    if n == "xcode":
        return "data:image/png;base64," + base64.b64encode((REPO / "assets" / "xcode.png").read_bytes()).decode()
    return "data:image/svg+xml;base64," + base64.b64encode((SRC / "icons" / f"{n}.svg").read_bytes()).decode()
def icon(n, x, y, s):
    return f'<image x="{x}" y="{y}" width="{s}" height="{s}" href="{icon_uri(n)}"><title>{n}</title></image>'

MAIN = [
    ("LANGUAGES", "python c cplusplus csharp typescript javascript swift html5 css3"),
    ("WEB &amp; BACKEND", "react nextjs tailwindcss vitejs nodejs express fastapi postgresql supabase mongodb"),
    ("AI &amp; VISION", "opencv ultralytics pytorch tensorflow claude googlegemini"),
    ("ROBOTICS &amp; HARDWARE", "arduino raspberrypi espressif fusion blender unity"),
    ("TOOLS &amp; CLOUD", "git github docker amazonwebservices cloudflare vercel vscode xcode figma"),
]
MORE = ("java kotlin dart go php solidity vuejs astro flutter expo socketio twilio mysql sqlite prisma keras numpy "
        "huggingface jupyter googlecolab kaggle anthropic githubcopilot antigravity ollama perplexity v0 replit embeddedc "
        "nvidia mqtt autodesk tinkercad matlab unrealengine googlecloud azure cloudflareworkers netlify render digitalocean "
        "gitlab githubactions visualstudio cursor androidstudio apple playwright vitest esbuild npm bash notion trello slack").split()
assert sum(len(s.split()) for _, s in MAIN) == 40 and len(MORE) == 55

def stack(mobile):
    y = 72
    body = eyebrow(y, "WHAT I BUILD WITH") + heading(y + 52, "Tech Stack")
    y += 110
    IS, GAP = L["icon"]
    for i, (label, names) in enumerate(MAIN):
        names = names.split()
        if i: body += f'<line x1="{X0}" y1="{y - 16}" x2="{W - X0}" y2="{y - 16}" stroke="#fff" stroke-opacity=".06"/>'
        lab = f'font-family="{MONO}" font-size="{L["label"]}" font-weight="600" letter-spacing="2" fill="#dcdce1">{label}</text>'
        if not mobile:
            body += f'<text x="{X0}" y="{y + IS / 2 + 5}" ' + lab
            for j, n in enumerate(names):
                body += icon(n, X0 + 290 + j * (IS + GAP), y, IS)
            y += IS + 34
        else:
            body += f'<text x="{X0}" y="{y + 10}" ' + lab
            y += 30
            per = (TEXT_W + GAP) // (IS + GAP)
            for j, n in enumerate(names):
                body += icon(n, X0 + (j % per) * (IS + GAP), y + (j // per) * (IS + GAP), IS)
            y += ((len(names) - 1) // per + 1) * (IS + GAP) + 30
    body += mascot("think", 150, y=22) if not mobile else mascot("think", 110, y=22, right=24)
    save("stack.svg", panel(y + 6, body, glow=(0.9, 0.9), title="Tech Stack"))

def stack_more(mobile):
    IS2, GAP2, PER = L["more"]
    rows = [MORE[i:i + PER] for i in range(0, len(MORE), PER)]
    y = 72
    title = "Tools I've worked with" if not mobile else "More tools"
    body = eyebrow(y, "55 MORE") + heading(y + 52, title)
    body += mascot("type1", 140, y=26) if not mobile else mascot("type1", 110, y=22, right=24)
    y += 120
    for r in rows:
        x = (W - (len(r) * IS2 + (len(r) - 1) * GAP2)) / 2
        for j, n in enumerate(r):
            body += icon(n, x + j * (IS2 + GAP2), y, IS2)
        y += IS2 + GAP2
    save("stack-more.svg", panel(y + 30, body, glow=(0.5, 0.5), title="More tools"))

for mode in MODES:
    use(mode)
    m = mode == "mobile"
    banner(m); about(m); awards(m); stack(m); stack_more(m)

# ================= README =================
def pic(name, alt, link=None):
    """Desktop panel by default; the phone panel when the viewport is narrow."""
    img = (f'<picture>\n    <source media="(max-width: 700px)" srcset="{RAW}/assets/m/{name}" />\n'
           f'    <img src="assets/{name}" width="100%" alt="{alt}" />\n  </picture>')
    if link: img = f'<a href="{link}">\n  {img}\n  </a>'
    return f'<p align="center">\n  {img}\n</p>\n'

readme = "\n".join([
    pic("banner.svg", "Nathaporn Saituptim - AI, Computer Vision, Robotics. Founder &amp; CEO of DeePer"),
    pic("about.svg", "Hey, what's up? I'm Nathaporn Saituptim, a high school student developer and robotics innovator from Thailand. Founder &amp; CEO of DeePer (deeper.in.th). Working at Yeah Association.", "https://deeper.in.th"),
    pic("awards.svg", "Awards and Achievements"),
    ('<p align="center">\n  <picture>\n'
     f'    <source media="(max-width: 700px)" srcset="{RAW.replace("/main", "/output")}/activity-m.svg" />\n'
     f'    <img src="{RAW.replace("/main", "/output")}/activity.svg" width="100%" alt="GitHub activity over the last 12 months, updated daily" />\n'
     '  </picture>\n</p>\n'),
    pic("stack.svg", "Tech Stack: Python, C, C++, C#, TypeScript, JavaScript, Swift, React, Next.js, FastAPI, OpenCV, YOLO, PyTorch, TensorFlow, Arduino, Raspberry Pi, ESP32, Docker, AWS and more"),
    "<details>\n<summary><b>More tools I've worked with (55)</b></summary>\n<br />\n",
    pic("stack-more.svg", "More tools I've worked with") + "</details>\n",
])
(REPO / "README.md").write_text(readme)
