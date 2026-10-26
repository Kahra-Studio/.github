#!/usr/bin/env python3
"""Kahra Studio GitHub profilindeki SVG görselleri üretir.

GitHub, README'deki SVG'lerin font yüklemesine izin vermez. Bu yüzden metinler
HarfBuzz ile şekillendirilip vektör yola çevrilir; tipografi (Lexend + JetBrains
Mono) sitedekiyle aynı görünür. Her görsel açık ve koyu tema için ayrı üretilir,
README <picture> ile GitHub temasına uygun olanı seçer.

    python -m pip install uharfbuzz fonttools
    python scripts/build_assets.py

Fontlar ilk çalıştırmada google/fonts deposundan .cache/fonts altına indirilir.
"""

from __future__ import annotations

import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "profile" / "assets"
FONT_DIR = ROOT / ".cache" / "fonts"
FONT_SOURCES = {
    "sans": ("Lexend-VF.ttf", "https://raw.githubusercontent.com/google/fonts/main/ofl/lexend/Lexend%5Bwght%5D.ttf"),
    "mono": ("JetBrainsMono-VF.ttf", "https://raw.githubusercontent.com/google/fonts/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf"),
}
UPEM = 1000  # iki fontun da em karesi

# Sitedeki renk değişkenleri (kahrastudio.art :root). Koyu tema sitedekinden türetildi.
# inv_* : terslenen bloklar (CTA). "line": GitHub zemini üzerindeki şeffaf şeritler.
THEMES = {
    "light": {
        "bg": "#f6f4ee", "bg2": "#eeebe3", "fg": "#141412", "fg2": "#3b3a35",
        "muted": "#5f5d57", "faint": "#9a968b", "rule": "#d9d4c8", "rule2": "#c3bdae",
        "accent": "#c2410c", "line": "#d9d4c8",
        "inv_bg": "#141412", "inv_fg": "#f6f4ee", "inv_muted": "#a3a097",
        "inv_rule": "#3a3934", "inv_accent": "#f07c3e",
    },
    "dark": {
        "bg": "#161512", "bg2": "#1d1c18", "fg": "#f2efe6", "fg2": "#d3cfc3",
        "muted": "#a39f94", "faint": "#6e6a60", "rule": "#2d2b26", "rule2": "#46433b",
        "accent": "#ee7b3f", "line": "#3a3832",
        "inv_bg": "#f2efe6", "inv_fg": "#141412", "inv_muted": "#5f5d57",
        "inv_rule": "#d9d4c8", "inv_accent": "#c2410c",
    },
}

W = 1280      # geniş görsellerin viewBox genişliği
RULE = 1.25   # çizgi kalınlığı; README'de ~0.7x küçülünce ~1px kalır

SERVICES = [
    ("01", "Web Uygulaması Geliştirme", "Next.js, React, erişilebilir arayüzler",
     "Hızlı açılan, arama motorlarında görünür, ekibinizin sonradan da geliştirebileceği bir web ürünü."),
    ("02", "İnteraktif & Oyun Deneyimleri", "Etkileşim, oyun döngüsü, çoklu cihaz",
     "Tarayıcıda anında açılan, mobil ve masaüstünde akıcı çalışan etkileşimli bir deneyim."),
    ("03", "Topluluk & Platform Çözümleri", "Kimlik, moderasyon, içerik akışları",
     "Üyelerin içerik ürettiği, ekibinizin güvenle yönetebildiği ve büyümeye dayanıklı bir platform."),
    ("04", "Edge Altyapı & Performans", "Cloudflare Workers, D1, KV ve R2",
     "Kullanıcıya yakın çalışan, öngörülebilir maliyetli ve sunucu bakımı gerektirmeyen bir altyapı."),
]

# Vaka kartlarındaki çizgisel motifler sitedeki plate-motif SVG'lerinden alındı (viewBox 160x120).
WORKS = [
    {
        "slug": "dostlar-studio", "name": "Dostlar Studio", "category": "Mod atölyesi ve topluluk",
        "year": "2026", "metric": "8", "caption": "katalogdaki mod (2 yayında)",
        "desc": "Farming Simulator oyuncuları için tek çatı: dedicated sunuculara yönelik Lua script "
                "modları, iki dilli mod kataloğu, topluluk platformu ve Discord köprüsü.",
        "tags": ["Lua", "FS25", "Next.js", "Cloudflare Workers"],
        "motif": '<rect x="44" y="60" width="30" height="30"/><rect x="78" y="60" width="30" height="30"/>'
                 '<rect x="61" y="30" width="30" height="30"/><path d="M61 45h30M76 30v30"/>'
                 '<path d="M44 75h30M59 60v30M78 75h30M93 60v30"/><rect x="36" y="92" width="80" height="5"/>'
                 '<rect x="36" y="97" width="10" height="7"/><rect x="71" y="97" width="10" height="7"/>'
                 '<rect x="106" y="97" width="10" height="7"/><rect x="36" y="104" width="80" height="4"/>'
                 '<circle cx="76" cy="45" r="2" fill="currentColor" stroke="none"/>',
    },
    {
        "slug": "gokatlas", "name": "Gökatlas", "category": "Bilim ve eğitim platformu",
        "year": "2026", "metric": "8", "caption": "canlı NASA veri modülü",
        "desc": "NASA ve JPL açık verilerini Türkçe anlatımla sunan; günün fotoğrafından asteroit "
                "takibine, 3B güneş sisteminden uzay havasına uzanan bağımsız uzay rehberi.",
        "tags": ["Next.js", "Cloudflare", "NASA API", "3B Görselleştirme"],
        "motif": '<circle cx="104" cy="66" r="16"/><circle cx="104" cy="66" r="32"/><circle cx="104" cy="66" r="48"/>'
                 '<circle cx="140.8" cy="35.1" r="3" fill="currentColor" stroke="none"/>'
                 '<circle cx="104" cy="66" r="2" fill="currentColor" stroke="none"/>'
                 '<path d="M96 66h-6M118 66h-6M104 58v-6M104 80v-6"/>'
                 '<circle cx="22" cy="22" r="1.4" fill="currentColor" stroke="none"/>'
                 '<circle cx="38" cy="98" r="1.4" fill="currentColor" stroke="none"/>'
                 '<circle cx="66" cy="14" r="1.4" fill="currentColor" stroke="none"/>',
    },
    {
        "slug": "the-ark", "name": "The Ark", "category": "Dijital kültür mirası",
        "year": "2026", "metric": "400+", "caption": "kültürel miras noktası",
        "desc": "Dünya'dan 400+ tarihi mekanı kronolojik timeline, keşif, galeri ve harita "
                "deneyimleriyle bir araya getiren iki dilli dijital arşiv.",
        "tags": ["Next.js", "Cloudflare", "Harita", "Çok Dilli"],
        "motif": '<path d="M12 84h136"/>'
                 '<path d="M20 84v-6M28 84v-6M44 84v-6M52 84v-6M60 84v-6M68 84v-6M76 84v-6M92 84v-6'
                 'M100 84v-6M108 84v-6M116 84v-6M132 84v-6M140 84v-6"/>'
                 '<path d="M36 84v-12M84 84v-12M124 84v-12"/><path d="M36 72v-20M84 72v-28M124 72v-16"/>'
                 '<circle cx="36" cy="52" r="3" fill="currentColor" stroke="none"/>'
                 '<circle cx="84" cy="44" r="3" fill="currentColor" stroke="none"/>'
                 '<circle cx="124" cy="56" r="3" fill="currentColor" stroke="none"/>'
                 '<path d="M12 98h40M60 98h24"/>',
    },
]

# Sitedeki "K" işareti (viewBox 512, path birimi 0.1).
K_PATH = ("M250 2560 l0 -2560 620 0 620 0 0 778 1 777 287 300 c157 165 289 301 292 302 3 1 279 -484 "
          "615 -1077 l610 -1080 789 0 788 0 -16 25 c-9 14 -444 705 -967 1537 l-951 1511 45 46 c24 25 454 "
          "486 956 1024 l911 977 -839 0 -839 0 -839 -946 -838 -945 -3 945 -2 946 -620 0 -620 0 0 -2560z")


@dataclass(frozen=True)
class Type:
    family: str          # "sans" (Lexend) ya da "mono" (JetBrains Mono)
    size: float
    weight: int = 400
    track: float = 0.0   # CSS letter-spacing, em
    upper: bool = False


def tr_upper(s: str) -> str:
    return s.replace("i", "İ").upper()


def num(v: float, digits: int = 2) -> str:
    s = f"{v:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


class Fonts:
    def __init__(self) -> None:
        self.faces, self.cmaps, self.cap, self.cache = {}, {}, {}, {}
        for family, (name, url) in FONT_SOURCES.items():
            path = FONT_DIR / name
            if not path.exists():
                FONT_DIR.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(url, path)
            tt = TTFont(path)
            assert tt["head"].unitsPerEm == UPEM, name
            self.cmaps[family] = tt.getBestCmap()
            self.cap[family] = tt["OS/2"].sCapHeight / UPEM
            self.faces[family] = hb.Face(hb.Blob.from_file_path(str(path)))

    def font(self, family: str, weight: int) -> hb.Font:
        key = (family, weight)
        if key not in self.cache:
            font = hb.Font(self.faces[family])
            font.set_variations({"wght": weight})
            self.cache[key] = font
        return self.cache[key]

    def _runs(self, text: str, family: str):
        # Lexend'de ok karakterleri yok; onları JetBrains Mono'dan alırız (sitede de öyle görünür).
        runs: list[list[str]] = []
        for ch in text:
            fam = family if ord(ch) in self.cmaps[family] else "mono"
            if runs and runs[-1][0] == fam:
                runs[-1][1] += ch
            else:
                runs.append([fam, ch])
        return runs

    def shape(self, text: str, t: Type):
        """Glyph listesi [(family, weight, gid, x, y)] (font birimi) ve piksel genişliği."""
        if t.upper:
            text = tr_upper(text)
        track = t.track * UPEM
        x, glyphs = 0.0, []
        for family, chunk in self._runs(text, t.family):
            weight = min(t.weight, 800) if family == "mono" else t.weight
            buf = hb.Buffer()
            buf.add_str(chunk)
            buf.direction, buf.script, buf.language = "ltr", "Latn", "tr"
            features = {"kern": True, "liga": True} if family == "sans" else {"calt": False, "liga": False}
            hb.shape(self.font(family, weight), buf, features)
            for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
                glyphs.append((family, weight, info.codepoint, x + pos.x_offset, pos.y_offset))
                x += pos.x_advance + track
        width = (x - track if glyphs else 0.0) * t.size / UPEM
        return glyphs, width

    def measure(self, text: str, t: Type) -> float:
        return self.shape(text, t)[1]

    def wrap(self, text: str, t: Type, width: float) -> list[str]:
        lines, cur = [], ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if cur and self.measure(trial, t) > width:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        return lines + [cur] if cur else lines

    def outline(self, family: str, weight: int, gid: int) -> str:
        pen = SVGPathPen(None, ntos=lambda v: str(round(v)))
        self.font(family, weight).draw_glyph_with_pen(gid, pen)
        return pen.getCommands()


class Canvas:
    """Tek bir SVG belgesi. Her glyph bir kez <defs> içinde tanımlanır, metinler <use> ile dizilir."""

    def __init__(self, fonts: Fonts, width: float, title: str) -> None:
        self.f, self.w, self.h, self.title = fonts, width, 0.0, title
        self.ids: dict[tuple, str | None] = {}
        self.glyphs: list[str] = []
        self.back: list[str] = []   # zemin ve çizgiler; metnin altında kalır
        self.body: list[str] = []

    def _ref(self, key: tuple) -> str | None:
        if key not in self.ids:
            d = self.f.outline(*key)
            self.ids[key] = f"g{len(self.glyphs)}" if d else None
            if d:
                self.glyphs.append(f'<path id="{self.ids[key]}" d="{d}"/>')
        return self.ids[key]

    def text(self, x: float, y: float, s: str, t: Type, fill: str, anchor: str = "start") -> float:
        glyphs, width = self.f.shape(s, t)
        if anchor == "end":
            x -= width
        elif anchor == "middle":
            x -= width / 2
        uses = []
        for family, weight, gid, gx, gy in glyphs:
            ref = self._ref((family, weight, gid))
            if ref:
                pos = (f' x="{num(gx, 1)}"' if gx else "") + (f' y="{num(gy, 1)}"' if gy else "")
                uses.append(f'<use href="#{ref}"{pos}/>')
        k = t.size / UPEM
        self.body.append(f'<g fill="{fill}" transform="translate({num(x)} {num(y)}) '
                         f'scale({num(k, 5)} {num(-k, 5)})">{"".join(uses)}</g>')
        return width

    def spans(self, x: float, y: float, parts: list[tuple[str, Type, str]]) -> float:
        """Aynı satırda farklı ağırlık/renkte metin parçaları."""
        for s, t, fill in parts:
            x += self.text(x, y, s, t, fill) + t.track * t.size
        return x

    def baseline(self, center: float, t: Type) -> float:
        """Büyük harfleri verilen yüksekliğe ortalayan taban çizgisi."""
        return center + self.f.cap[t.family] * t.size / 2

    def svg(self) -> str:
        defs = f"<defs>{''.join(self.glyphs)}</defs>" if self.glyphs else ""
        h = num(math.ceil(self.h))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(self.w)}" height="{h}" '
                f'viewBox="0 0 {num(self.w)} {h}" role="img"><title>{escape(self.title)}</title>'
                f'{defs}{"".join(self.back)}{"".join(self.body)}</svg>\n')


def rect(x, y, w, h, fill="none", stroke=None, sw=RULE) -> str:
    s = f' stroke="{stroke}" stroke-width="{num(sw)}"' if stroke else ""
    return f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="{fill}"{s}/>'


def hline(x1, x2, y, color, sw=RULE) -> str:
    return f'<path d="M{num(x1)} {num(y)}H{num(x2)}" stroke="{color}" stroke-width="{num(sw)}"/>'


def vline(x, y1, y2, color, sw=RULE) -> str:
    return f'<path d="M{num(x)} {num(y1)}V{num(y2)}" stroke="{color}" stroke-width="{num(sw)}"/>'


def card(w, h, p, fill=None) -> str:
    return rect(RULE / 2, RULE / 2, w - RULE, h - RULE, fill=fill or p["bg"], stroke=p["rule"])


def logo(x, y, size, fill) -> str:
    k = size / 5120
    return (f'<path fill="{fill}" transform="translate({num(x)} {num(y + size)}) '
            f'scale({num(k, 6)} {num(-k, 6)})" d="{K_PATH}"/>')


def motif(markup, x, y, scale, color) -> str:
    return (f'<g transform="translate({num(x)} {num(y)}) scale({num(scale, 3)})" fill="none" '
            f'stroke="{color}" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round">'
            f'{markup.replace("currentColor", color)}</g>')


# Ortak yazı stilleri (site: .mono 11px/0.12em büyük harf, .t-h2 -0.025em, .t-display -0.035em).
# Geniş görseller README'de ~0.69x küçüldüğü için boyutlar siteden biraz büyük.
LABEL = Type("mono", 15, 400, 0.12, upper=True)
ARROW = Type("mono", 20, 400)

# Hero ve CTA, sitedeki gibi solda bir kenar sütunu ve dikey çizgiyle ayrılmış içerik sütunu kullanır.
PAD, MARGIN_RULE, COL = 56, 296, 336


def build_hero(f: Fonts, p: dict) -> Canvas:
    c = Canvas(f, W, "Kahra Studio — Karmaşık işleri okunur ürünlere çeviriyoruz.")
    col_w = W - PAD - COL

    bar = 88
    c.body.append(logo(PAD, 29, 30, p["fg"]))
    word = Type("sans", 17, 600, 0.14)
    c.text(PAD + 30 + 13, c.baseline(44, word), "KAHRA STUDIO", word, p["fg"])
    domain = Type("mono", 15, 400, 0.12)  # tr_upper alan adındaki i'yi İ yapmasın
    c.text(W - PAD, c.baseline(44, domain), "KAHRASTUDIO.ART ↗", domain, p["fg"], anchor="end")
    c.back.append(hline(0, W, bar, p["rule"]))

    top = bar + 58
    size = 84
    while True:
        disp, em = Type("sans", size, 500, -0.035), Type("sans", size, 300, -0.035)
        line1 = f.measure("Karmaşık işleri ", disp) + disp.track * size + f.measure("okunur", em)
        if max(line1, f.measure("ürünlere çeviriyoruz.", disp)) <= col_w:
            break
        size -= 1
    b1 = top + f.cap["sans"] * size
    b2 = b1 + size * 1.04
    c.spans(COL, b1, [("Karmaşık işleri ", disp, p["fg"]), ("okunur", em, p["accent"])])
    c.text(COL, b2, "ürünlere çeviriyoruz.", disp, p["fg"])

    c.text(PAD, top + 11, "Dijital ürün stüdyosu", LABEL, p["muted"])
    c.text(PAD, top + 36, "Türkiye · 2025", LABEL, p["faint"])

    fy, row_h = b2 + size * 0.3 + 44, 108
    cw = col_w / 4
    value, caption = Type("sans", 32, 500, -0.02), Type("mono", 14, 400, 0.12, upper=True)
    facts = [("2025", "Kuruluş"), ("3", "Yayındaki çalışma"), ("2 iş günü", "İlk dönüş"), ("Türkiye", "Konum")]
    c.back += [hline(COL, W - PAD, fy, p["rule"]), hline(COL, W - PAD, fy + row_h, p["rule"])]
    for i, (val, cap) in enumerate(facts):
        x = COL + cw * i + (24 if i else 0)
        if i:
            c.back.append(vline(COL + cw * i, fy, fy + row_h, p["rule"]))
        c.text(x, fy + 54, val, value, p["fg"])
        c.text(x, fy + 84, cap, caption, p["muted"])
    c.back.append(vline(MARGIN_RULE, top - 6, fy + row_h, p["rule"]))

    c.h = fy + row_h + 56
    c.back.insert(0, card(W, c.h, p))
    return c


def build_button(f: Fonts, p: dict, label: str, primary: bool) -> Canvas:
    t, h, padx = Type("sans", 16, 500, 0.005), 52, 26
    arrow = Type("mono", 16, 400)
    w = math.ceil(padx * 2 + f.measure(label, t) + (12 + f.measure("→", arrow) if primary else 0))
    c = Canvas(f, w, label)
    color = p["bg"] if primary else p["fg"]
    c.back.append(rect(0, 0, w, h, fill=p["fg"]) if primary else rect(0.5, 0.5, w - 1, h - 1, stroke=p["fg"], sw=1))
    c.text(padx, c.baseline(h / 2, t), label, t, color)
    if primary:
        c.text(w - padx, c.baseline(h / 2, arrow), "→", arrow, color, anchor="end")
    c.h = h
    return c


def build_section(f: Fonts, p: dict, idx: str, label: str, title: str, link: str) -> Canvas:
    c = Canvas(f, W, f"{idx} · {label} — {title}")
    c.back.append(hline(0, W, RULE / 2, p["line"]))
    y = 48
    x = c.text(0, y, idx, Type("mono", 15, 400, 0.12), p["accent"])
    c.text(x + 16, y, label, LABEL, p["muted"])
    t_title, t_link = Type("sans", 44, 500, -0.025), Type("sans", 20, 500, 0.005)
    yt = y + 30 + f.cap["sans"] * t_title.size
    c.text(0, yt, title, t_title, p["fg"])
    aw = c.text(W, yt, "→", ARROW, p["fg"], anchor="end")
    c.text(W - aw - 10, yt, link, t_link, p["fg"], anchor="end")
    c.h = yt + 24
    return c


def build_services(f: Fonts, p: dict) -> Canvas:
    c = Canvas(f, W, "Hizmetler — " + "; ".join(f"{n} {title}: {desc}" for n, title, _, desc in SERVICES))
    row_h, inset = 132, 40
    x_title, x_desc = inset + 76, 660
    t_idx, t_title = Type("mono", 15, 400, 0.08), Type("sans", 28, 500, -0.02)
    t_body = Type("sans", 18, 400)
    for i, (n, title, sub, desc) in enumerate(SERVICES):
        y = i * row_h + 58
        if i:
            c.back.append(hline(inset, W - inset, i * row_h, p["rule"]))
        c.text(inset, y, n, t_idx, p["muted"])
        c.text(x_title, y, title, t_title, p["fg"])
        c.text(x_title, y + 32, sub, t_body, p["muted"])
        for j, line in enumerate(f.wrap(desc, t_body, W - inset - 72 - x_desc)):
            c.text(x_desc, y + j * 28, line, t_body, p["muted"])
        c.text(W - inset, y, "→", ARROW, p["fg2"], anchor="end")
    c.h = len(SERVICES) * row_h
    c.back.insert(0, card(W, c.h, p))
    return c


PLATE_W, PLATE_PAD, COVER_H = 400, 26, 300
P_LABEL = Type("mono", 14, 400, 0.1, upper=True)
P_NAME, P_DESC = Type("sans", 29, 500, -0.015), Type("sans", 18, 400)
P_TAG = Type("mono", 14, 400, 0.04)
TAG_H, TAG_PADX, TAG_GAP = 32, 10, 8


def tag_rows(f: Fonts, tags: list[str], width: float):
    rows, cur, cur_w = [], [], 0.0
    for tag in tags:
        w = f.measure(tag, P_TAG) + 2 * TAG_PADX
        if cur and cur_w + TAG_GAP + w > width:
            rows.append(cur)
            cur, cur_w = [], 0.0
        cur.append((tag, w))
        cur_w += (TAG_GAP if len(cur) > 1 else 0) + w
    return rows + [cur] if cur else rows


def plate_height(f: Fonts, work: dict) -> float:
    inner = PLATE_W - 2 * PLATE_PAD
    lines = len(f.wrap(work["desc"], P_DESC, inner))
    rows = len(tag_rows(f, work["tags"], inner))
    return COVER_H + 50 + 38 + (lines - 1) * 27 + 30 + rows * TAG_H + (rows - 1) * TAG_GAP + PLATE_PAD


def build_plate(f: Fonts, p: dict, work: dict, height: float) -> Canvas:
    title = (f"{work['name']} — {work['category']}, {work['year']}. {work['metric']} {work['caption']}. "
             f"{work['desc']} ({', '.join(work['tags'])})")
    c = Canvas(f, PLATE_W, title)
    pad, inner = PLATE_PAD, PLATE_W - 2 * PLATE_PAD
    c.h = height
    c.back += [card(PLATE_W, height, p),
               rect(RULE, RULE, PLATE_W - 2 * RULE, COVER_H - RULE, fill=p["bg2"]),
               hline(0, PLATE_W, COVER_H, p["rule"])]

    c.text(pad, pad + 16, work["category"], P_LABEL, p["muted"])
    c.text(PLATE_W - pad, pad + 16, work["year"], P_LABEL, p["muted"], anchor="end")
    c.back.append(motif(work["motif"], PLATE_W - pad - 200, 62, 1.25, p["faint"]))
    c.text(pad, COVER_H - pad - 34, work["metric"], Type("sans", 76, 500, -0.04), p["fg"])
    c.text(pad, COVER_H - pad, work["caption"], P_LABEL, p["muted"])

    y = COVER_H + 50
    c.text(pad, y, work["name"], P_NAME, p["fg"])
    sw = c.text(PLATE_W - pad, y, "Yayında", P_LABEL, p["muted"], anchor="end")
    c.back.append(f'<circle cx="{num(PLATE_W - pad - sw - 12)}" cy="{num(y - 5)}" r="4" fill="{p["accent"]}"/>')
    y += 38
    for line in f.wrap(work["desc"], P_DESC, inner):
        c.text(pad, y, line, P_DESC, p["muted"])
        y += 27

    rows = tag_rows(f, work["tags"], inner)
    ty = height - pad - len(rows) * TAG_H - (len(rows) - 1) * TAG_GAP
    for row in rows:
        x = pad
        for tag, w in row:
            c.back.append(rect(x, ty, w, TAG_H, stroke=p["rule2"], sw=1))
            c.text(x + TAG_PADX, c.baseline(ty + TAG_H / 2, P_TAG), tag, P_TAG, p["fg2"])
            x += w + TAG_GAP
        ty += TAG_H + TAG_GAP
    return c


def build_cta(f: Fonts, p: dict) -> Canvas:
    lead = "Kapsamı birlikte netleştirelim. Kısa bir mesaj bırakın, 2 iş günü içinde dönüş yapalım."
    c = Canvas(f, W, f"Bir projeniz mi var? {lead} İletişim: hello@kahrastudio.art")
    top = 64
    h2, em = Type("sans", 56, 500, -0.025), Type("sans", 56, 300, -0.025)
    b1 = top + f.cap["sans"] * h2.size
    c.spans(COL, b1, [("Bir projeniz mi ", h2, p["inv_fg"]), ("var", em, p["inv_accent"]), ("?", h2, p["inv_fg"])])
    t_lead = Type("sans", 21, 400)
    y = b1 + 56
    for line in f.wrap(lead, t_lead, 540):
        c.text(COL, y, line, t_lead, p["inv_muted"])
        y += 32
    last = y - 32

    t_btn, arrow = Type("sans", 19, 500, 0.005), Type("mono", 19, 400)
    bw = 64 + f.measure("İletişime geçin", t_btn) + 14 + f.measure("→", arrow)
    bh = 64
    bx, by = W - PAD - bw, last + 10 - bh
    c.back.append(rect(bx, by, bw, bh, fill=p["inv_fg"]))
    c.text(bx + 32, c.baseline(by + bh / 2, t_btn), "İletişime geçin", t_btn, p["inv_bg"])
    c.text(bx + bw - 32, c.baseline(by + bh / 2, arrow), "→", arrow, p["inv_bg"], anchor="end")

    c.text(PAD, top + 11, "Başlayalım", LABEL, p["inv_muted"])
    c.text(PAD, last, "hello@kahrastudio.art", Type("mono", 16, 400, 0.02), p["inv_fg"])
    c.back.append(vline(MARGIN_RULE, top - 6, last + 10, p["inv_rule"]))

    c.h = last + 64
    c.back.insert(0, rect(0, 0, W, c.h, fill=p["inv_bg"]))
    return c


def main() -> None:
    f = Fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    plate_h = max(plate_height(f, w) for w in WORKS)
    for theme, p in THEMES.items():
        assets = {
            "hero": build_hero(f, p),
            "btn-iletisim": build_button(f, p, "Görüşme planlayın", primary=True),
            "btn-calismalar": build_button(f, p, "Çalışmaları inceleyin", primary=False),
            "sec-hizmetler": build_section(f, p, "01", "Hizmetler", "Hangi işleri üstleniyoruz", "Tüm hizmetler"),
            "hizmetler": build_services(f, p),
            "sec-calismalar": build_section(f, p, "02", "Çalışmalar", "Seçili vaka çalışmaları", "Tüm çalışmalar"),
            "sec-acik-kaynak": build_section(f, p, "03", "Açık kaynak", "GitHub'daki depolar", "Tüm depolar"),
            "cta": build_cta(f, p),
        }
        for work in WORKS:
            assets[f"work-{work['slug']}"] = build_plate(f, p, work, plate_h)
        for name, canvas in assets.items():
            path = OUT / f"{name}-{theme}.svg"
            path.write_text(canvas.svg(), encoding="utf-8", newline="\n")
            print(f"{path.relative_to(ROOT)}  {canvas.w:.0f}x{math.ceil(canvas.h)}  {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
