"""Builds every SVG panel in assets/ and README.md.

Run from anywhere:  python3 scripts/build.py   (needs Pillow, macOS for SF Pro metrics)
"""
import base64, io, html
from pathlib import Path
from PIL import Image, ImageFont, ImageFilter

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "scripts" / "src"
FONT = '-apple-system, BlinkMacSystemFont, &quot;SF Pro Display&quot;, &quot;Segoe UI&quot;, Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, &quot;SF Mono&quot;, Menlo, Consolas, monospace'
BLUE, RED, GREEN = "#2997ff", "#ff375f", "#30d158"
W = 1200
X0 = 72                      # left text edge in every panel
TEXT_W = W - 2 * X0
esc = lambda t: html.escape(t, quote=False)

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
        for i, w in enumerate(text.split(" ")):
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
    out, prev = [], None
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
<linearGradient id="name" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f5f5f7"/><stop offset="1" stop-color="#a1c8ff"/></linearGradient>
<radialGradient id="dotg"><stop offset="0" stop-color="#5ab4ff" stop-opacity=".9"/><stop offset=".35" stop-color="#2997ff" stop-opacity=".45"/><stop offset="1" stop-color="#2997ff" stop-opacity="0"/></radialGradient>
<linearGradient id="dp" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2997ff"/><stop offset="1" stop-color="#7cc4ff"/></linearGradient>
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
    return f'<text x="{X0}" y="{y}" font-family="{MONO}" font-size="17" letter-spacing="2.4" font-weight="600" fill="{color}">{label}</text>'
def heading(y, text):
    return f'<text x="{X0 - 2}" y="{y}" font-family="{FONT}" font-size="46" font-weight="700" letter-spacing="-1.2" fill="#f5f5f7">{esc(text)}</text>'
def mascot(pose, h, x=None, y=None, right=56, bottom=None, ph=None):
    im = Image.open(SRC / "poses" / f"{pose}.png")
    w = round(im.width / im.height * h)
    x = W - right - w if x is None else x
    if bottom is not None: y = ph - bottom - h
    b = io.BytesIO(); im.save(b, format="WEBP", lossless=True, method=6)
    uri = "data:image/webp;base64," + base64.b64encode(b.getvalue()).decode()
    return (f'<ellipse cx="{x + w / 2}" cy="{y + h * 0.55}" rx="{w * 0.75}" ry="{h * 0.6}" fill="url(#glow)"/>'
            f'<g class="bob"><image x="{x}" y="{y}" width="{w}" height="{h}" href="{uri}"/></g>')

def save(name, svg):
    open(f"{REPO}/assets/{name}", "w").write(svg)
    print(name, len(svg) // 1024, "KB")

# ================= banner =================
c = Image.open(SRC / "poses" / "main.png")
rgb = c.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
c = Image.merge("RGBA", (*rgb.split(), c.getchannel("A")))
buf = io.BytesIO(); c.save(buf, format="WEBP", lossless=True, quality=100, method=6)
b64 = base64.b64encode(buf.getvalue()).decode()
H = 380
ch = 330; cw = round(c.width / c.height * ch); cx = W - cw - 28; cy = H - ch - 14
gx, gy = cx + cw / 2, cy + ch * 0.42

pills = [("MIT Media Lab", "Top 3 Global", BLUE),
         ("World Robot Championship", "Dubai", BLUE),
         ("GLO Innovation", "1st Place", BLUE)]
def glow_dot(cx, cy, r=5):
    return (f'<circle class="pulse" cx="{cx}" cy="{cy}" r="{r * 3.4}" fill="url(#dotg)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#5ab4ff"/>')
pill_svg = ""
for i, (a, b, col) in enumerate(pills):
    pill_svg += (f'<g transform="translate(476 {118 + i * 52})">' + glow_dot(10, 0) +
                 f'<text x="30" y="6.5" font-family="{FONT}" font-size="18" font-weight="600" fill="#ffffff">{a}'
                 f'<tspan fill="#6e6e73"> &#183; </tspan><tspan fill="#d1d1d6" font-weight="500">{b}</tspan></text></g>')

ceo_w = round(tw("Founder & CEO of ", 20, True) + tw("DeePer", 20, True) + 50)
banner_body = f'''<radialGradient id="g2"><stop offset="0" stop-color="#2997ff" stop-opacity=".45"/><stop offset=".5" stop-color="#2997ff" stop-opacity=".14"/><stop offset="1" stop-color="#2997ff" stop-opacity="0"/></radialGradient>
<radialGradient id="floor"><stop offset="0" stop-color="#6cb6ff" stop-opacity=".20"/><stop offset="1" stop-color="#2997ff" stop-opacity="0"/></radialGradient>
<ellipse class="pulse" cx="{gx}" cy="{gy}" rx="260" ry="220" fill="url(#g2)"/>
<ellipse cx="{gx}" cy="{cy + ch - 8}" rx="240" ry="30" fill="url(#floor)"/>
<image x="{cx}" y="{cy}" width="{cw}" height="{ch}" href="data:image/webp;base64,{b64}"/>
<circle class="blink" cx="70" cy="64" r="6" fill="{GREEN}"/>
<text x="88" y="70" font-family="{MONO}" font-size="18" font-weight="600" letter-spacing="2.4" fill="{BLUE}">PUG-03 &#183; BANGKOK, TH</text>
<text font-family="{FONT}" font-size="68" font-weight="700" letter-spacing="-2.2" fill="#f5f5f7"><tspan x="61" y="148">Nathaporn</tspan><tspan x="61" y="216" fill="#b4d4ff">Saituptim.</tspan></text>
<text x="64" y="264" font-family="{FONT}" font-size="27" font-weight="700" fill="#ffffff">AI. Computer Vision. Robotics.</text>
<g transform="translate(62 288)">
<rect width="{ceo_w}" height="52" rx="26" fill="#2997ff" fill-opacity=".14" stroke="#2997ff" stroke-opacity=".55"/>
{glow_dot(25, 26, 5.5)}
<text x="42" y="33" font-family="{FONT}" font-size="20" font-weight="700" fill="#ffffff">Founder &amp; CEO of <tspan fill="#4aa8ff" font-weight="800">DeePer</tspan></text>
</g>
<text x="{62 + ceo_w + 16}" y="320" font-family="{MONO}" font-size="17" font-weight="600" letter-spacing="1" fill="#a1c8ff">deeper.in.th</text>
{pill_svg}'''
save("banner.svg", panel(H, banner_body, glow=(0.3, 0.2), title="Nathaporn Saituptim"))

# ================= about =================
y = 72
body = eyebrow(y, "ABOUT ME"); y += 52
body += heading(y, "Hey, what's up?"); y += 58
para = [("I'm", "n"), ("Nathaporn Saituptim", "b"),
        ("— a high school student developer and robotics innovator from Thailand. I build end-to-end products that bridge smart software with physical hardware: AI and computer vision, autonomous robots, full-stack web apps, and embedded IoT.", "n")]
for ln in wrap(para, 24, TEXT_W):
    body += line_svg(ln, X0, y, 24); y += 37
y += 26
# DeePer highlight block
deeper = [("A free web app of deep conversation cards for couples, friends & family. 1,050+ curated questions, swipe and take turns on one phone.", "n")]
dl = wrap(deeper, 21, TEXT_W - 56)
bh = 82 + len(dl) * 32
body += (f'<rect x="{X0}" y="{y}" width="{TEXT_W}" height="{bh}" rx="20" fill="#2997ff" fill-opacity=".08" stroke="#2997ff" stroke-opacity=".35"/>'
         f'<text x="{X0 + 28}" y="{y + 44}" font-family="{FONT}" font-size="28" font-weight="700" fill="#ffffff">Founder &amp; CEO of <tspan fill="#4aa8ff">DeePer</tspan></text>'
         f'<text x="{X0 + TEXT_W - 28}" y="{y + 43}" text-anchor="end" font-family="{MONO}" font-size="18" font-weight="600" letter-spacing="1" fill="{BLUE}">deeper.in.th</text>')
yy = y + 84
for ln in dl:
    body += line_svg(ln, X0 + 28, yy, 21); yy += 32
y += bh + 40
bullets = [[("Working at", "n"), ("Yeah Association", "b")],
           [("Currently building autonomous systems, full-stack web apps, and embedded IoT solutions", "n")],
           [("Ask me about AI models, robotics, startups, or slick UI design", "n")],
           [("Fun fact: I love Apple-style minimalist layouts and dark-themed dev setups", "n")]]
for b in bullets:
    body += f'<circle cx="{X0 + 6}" cy="{y - 7}" r="4" fill="{BLUE}"/>'
    for ln in wrap(b, 23, TEXT_W - 30):
        body += line_svg(ln, X0 + 26, y, 23); y += 35
    y += 10
ah = y + 30
body += mascot("happy", 150, bottom=22, ph=ah)
save("about.svg", panel(ah, body, glow=(0.9, 0.15), title="About me"))

# ================= awards =================
groups = {
    "ai": ("AI &amp; SOFTWARE INNOVATION", BLUE, [
        ("Top 3 Global Finalist", "AI & Robotics Hackathon 2025 by MIT Media Lab"),
        ("1st Place Winner", "GLO Innovation 2026 · selected from 173 teams"),
        ("Best App Design for Elderly & Alzheimer's Patients", "KMITL ToBeIT'69"),
        ("Top 4 Finalist", "Play to Build AI Hackathon, SEABW 2026 by AWS · the only solo student against pro teams"),
        ("Top 5 Finalist", "OIC InsurTech Award 2026 · selected from 501 teams"),
        ("AI for Thai Service Standard Award · Top 15", "AI for Thai Service Onboarding · out of 150 teams"),
        ("Semifinalist", "CEDT Innovation Summit 2026 · selected from 484 teams")]),
    "rb": ("ROBOTICS &amp; HARDWARE", BLUE, [
        ("Top 2 Finalist · Dubai Global Finals Qualifier", "World Robot Championship 2026 (3kg RC Sumo)"),
        ("Top 3 Finalist · China Finals Qualifier", "Maker Robotics Challenge 2026 (1.5kg Sumo)")]),
    "web": ("WEB DEVELOPMENT &amp; CONTENT", BLUE, [
        ("1st Place Winner", "Thailand Metaverse Hackathon & Exhibition 2026 by Chulalongkorn University"),
        ("Overall Winner · Best Idea · Best Content", "Junior Webmaster Camp 14")]),
}
def column(keys, x, width, y):
    out = ""
    for k in keys:
        label, col, items = groups[k]
        out += (f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{col}"/>'
                f'<text x="{x + 20}" y="{y}" font-family="{MONO}" font-size="16" font-weight="600" letter-spacing="2" fill="{col}">{label}</text>')
        y += 40
        for rank, ev in items:
            top = y - 22
            for ln in wrap([(rank, "b")], 24, width - 22):
                out += line_svg(ln, x + 22, y, 24); y += 32
            for ln in wrap([(ev, "n")], 20, width - 22):
                out += line_svg(ln, x + 22, y, 20, "#c7c7cc"); y += 28
            out += f'<rect x="{x}" y="{top}" width="3" height="{y - top - 14}" rx="1.5" fill="{col}" fill-opacity=".7"/>'
            y += 18
        y += 22
    return out, y
y0 = 72
head = eyebrow(y0, "TRACK RECORD") + heading(y0 + 52, "Awards & Achievements")
start = y0 + 118
colw = (TEXT_W - 64) / 2
left, ly = column(["ai", "rb", "web"], X0, TEXT_W, start)
head += mascot("stretch", 170, y=26)
head += mascot("o_hoodie", 200, y=round(ly * 0.42), right=80)
head += mascot("drink", 150, bottom=24, ph=ly + 10)
save("awards.svg", panel(ly + 10, head + left, glow=(0.15, 0.1), title="Awards and Achievements"))

# ================= tech stack =================
def icon_uri(n):
    if n == "xcode":
        return "data:image/png;base64," + base64.b64encode(open(f"{REPO}/assets/xcode.png", "rb").read()).decode()
    return "data:image/svg+xml;base64," + base64.b64encode(open(SRC / "icons" / f"{n}.svg", "rb").read()).decode()
def icon(n, x, y, s):
    return f'<image x="{x}" y="{y}" width="{s}" height="{s}" href="{icon_uri(n)}"><title>{n}</title></image>'

main = [
    ("LANGUAGES", "python c cplusplus csharp typescript javascript swift html5 css3"),
    ("WEB &amp; BACKEND", "react nextjs tailwindcss vitejs nodejs express fastapi postgresql supabase mongodb"),
    ("AI &amp; VISION", "opencv ultralytics pytorch tensorflow claude googlegemini"),
    ("ROBOTICS &amp; HARDWARE", "arduino raspberrypi espressif fusion blender unity"),
    ("TOOLS &amp; CLOUD", "git github docker amazonwebservices cloudflare vercel vscode xcode figma"),
]
more = ("java kotlin dart go php solidity vuejs astro flutter expo socketio twilio mysql sqlite prisma keras numpy "
        "huggingface jupyter googlecolab kaggle anthropic githubcopilot antigravity ollama perplexity v0 replit embeddedc "
        "nvidia mqtt autodesk tinkercad matlab unrealengine googlecloud azure cloudflareworkers netlify render digitalocean "
        "gitlab githubactions visualstudio cursor androidstudio apple playwright vitest esbuild npm bash notion trello slack").split()
assert sum(len(s.split()) for _, s in main) == 40 and len(more) == 55

y = 72
body = eyebrow(y, "WHAT I BUILD WITH") + heading(y + 52, "Tech Stack")
y += 110
IS, GAP, LABEL_W = 54, 20, 290
for i, (label, names) in enumerate(main):
    if i: body += f'<line x1="{X0}" y1="{y - 16}" x2="{W - X0}" y2="{y - 16}" stroke="#fff" stroke-opacity=".06"/>'
    body += f'<text x="{X0}" y="{y + IS / 2 + 5}" font-family="{MONO}" font-size="16" font-weight="600" letter-spacing="2" fill="#dcdce1">{label}</text>'
    for j, n in enumerate(names.split()):
        body += icon(n, X0 + LABEL_W + j * (IS + GAP), y, IS)
    y += IS + 34
body += mascot("think", 150, y=22)
save("stack.svg", panel(y + 6, body, glow=(0.9, 0.9), title="Tech Stack"))

PER, IS2, GAP2 = 14, 50, 24
rows = [more[i:i + PER] for i in range(0, len(more), PER)]
y = 72
body = eyebrow(y, "55 MORE") + heading(y + 52, "Tools I've worked with") + mascot("type1", 140, y=26)
y += 120
for r in rows:
    x = (W - (len(r) * IS2 + (len(r) - 1) * GAP2)) / 2
    for j, n in enumerate(r):
        body += icon(n, x + j * (IS2 + GAP2), y, IS2)
    y += IS2 + GAP2
save("stack-more.svg", panel(y + 30, body, glow=(0.5, 0.5), title="More tools"))

# ================= README =================
readme = '''<p align="center">
  <img src="assets/banner.svg" width="100%" alt="Nathaporn Saituptim - AI, Computer Vision, Robotics. Founder & CEO of DeePer" />
</p>

<p align="center">
  <a href="https://deeper.in.th"><img src="assets/about.svg" width="100%" alt="Hey, what's up? I'm Nathaporn Saituptim, a high school student developer and robotics innovator from Thailand. Founder & CEO of DeePer (deeper.in.th). Working at Yeah Association." /></a>
</p>

<p align="center">
  <img src="assets/awards.svg" width="100%" alt="Awards and Achievements" />
</p>

<p align="center">
  <img src="assets/stack.svg" width="100%" alt="Tech Stack: Python, C, C++, C#, TypeScript, JavaScript, Swift, React, Next.js, FastAPI, OpenCV, YOLO, PyTorch, TensorFlow, Arduino, Raspberry Pi, ESP32, Docker, AWS and more" />
</p>

<details>
<summary><b>More tools I've worked with (55)</b></summary>
<br />
<p align="center">
  <img src="assets/stack-more.svg" width="100%" alt="More tools I've worked with" />
</p>
</details>
'''
open(f"{REPO}/README.md", "w").write(readme)
