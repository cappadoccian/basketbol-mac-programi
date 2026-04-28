"""
Basketfaul.com.tr - Maç Yayın Programı
Kivy tabanlı Android/Masaüstü uygulaması
"""

import re
import threading
from datetime import datetime

# ── Kivy Config (Android'de ekran boyutunu otomatik ayarlar) ──────────────────
from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '700')

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import get_color_from_hex

# ── Renkler ───────────────────────────────────────────────────────────────────
C_BG       = get_color_from_hex("#0D0F1A")
C_CARD     = get_color_from_hex("#161929")
C_HEADER   = get_color_from_hex("#1A1E35")
C_BLUE     = get_color_from_hex("#4F8EF7")
C_GOLD     = get_color_from_hex("#FFB347")
C_GREEN    = get_color_from_hex("#3DDC97")
C_RED      = get_color_from_hex("#FF5757")
C_TEXT     = get_color_from_hex("#E8EAFF")
C_SUB      = get_color_from_hex("#7C82A8")
C_WHITE    = get_color_from_hex("#FFFFFF")
C_BORDER   = get_color_from_hex("#252A45")

DAY_COLORS = [
    "#4F8EF7", "#A78BFA", "#3DDC97", "#FFB347",
    "#FF5757", "#64B5F6", "#F06292"
]

URL = "https://basketfaul.com.tr/ekran-basina/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Mobile Safari/537.36"
    )
}

# ── Scraping ──────────────────────────────────────────────────────────────────
MATCH_RE = re.compile(
    r"^(\d{1,2}:\d{2})\s+"
    r"(.+?)\s+"
    r"\(([^)]+)\)\s*"
    r"(.*)$"
)


def fetch_matches():
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(URL, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.content, "html.parser")

    days = []
    for p in soup.find_all("p"):
        first_strong = p.find("strong")
        if not first_strong:
            continue
        day_text = first_strong.get_text(strip=True)
        if not re.match(r"^\d{1,2}\s+\w+\s+\w+$", day_text, re.UNICODE):
            continue
        for br in p.find_all("br"):
            br.replace_with("\n")
        lines = [l.strip() for l in p.get_text(separator="").splitlines()]
        matches = []
        for line in lines:
            if not line or line == day_text:
                continue
            m = MATCH_RE.match(line)
            if m:
                matches.append({
                    "time":    m.group(1).strip(),
                    "teams":   m.group(2).strip(),
                    "league":  m.group(3).strip(),
                    "channel": m.group(4).strip() or "—",
                })
        if matches:
            days.append({"date": day_text, "matches": matches})
    return days


# ── Yardımcı Widget'lar ───────────────────────────────────────────────────────
class ColoredBox(Widget):
    """Arka plan rengi olan basit kutu."""
    def __init__(self, color, **kwargs):
        super().__init__(**kwargs)
        self._color = color
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._color)
            Rectangle(pos=self.pos, size=self.size)


class Separator(Widget):
    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(1))
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*C_BORDER)
            Rectangle(pos=self.pos, size=self.size)


def make_label(text, color=None, font_size=None, bold=False,
               halign="left", size_hint_y=None, height=None, **kwargs):
    lbl = Label(
        text=text,
        color=color or C_TEXT,
        font_size=font_size or dp(14),
        bold=bold,
        halign=halign,
        valign="middle",
        text_size=(None, None),
        size_hint_y=size_hint_y,
        height=height or dp(28),
        **kwargs
    )
    lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))
    return lbl


# ── Maç Satırı ────────────────────────────────────────────────────────────────
class MatchRow(BoxLayout):
    def __init__(self, match, accent_hex, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            padding=[dp(8), dp(6), dp(8), dp(6)],
            spacing=dp(8),
            **kwargs
        )
        accent = get_color_from_hex(accent_hex)

        with self.canvas.before:
            Color(*C_CARD)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        # Saat badge
        time_box = BoxLayout(
            size_hint=(None, None),
            size=(dp(52), dp(40)),
        )
        with time_box.canvas.before:
            Color(*accent)
            RoundedRectangle(
                pos=time_box.pos, size=time_box.size,
                radius=[dp(6), dp(6), dp(6), dp(6)]
            )
        time_box.bind(pos=lambda w, p: self._redraw_time(w, accent),
                      size=lambda w, s: self._redraw_time(w, accent))
        self._time_box = time_box

        time_lbl = Label(
            text=match["time"],
            color=C_WHITE,
            font_size=dp(12),
            bold=True,
        )
        time_box.add_widget(time_lbl)

        # Orta: takım + lig
        info = BoxLayout(orientation="vertical", spacing=dp(2))
        teams_lbl = Label(
            text=match["teams"],
            color=C_TEXT,
            font_size=dp(13),
            bold=True,
            halign="left", valign="middle",
            text_size=(None, None),
            size_hint_y=0.55,
        )
        teams_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        league_lbl = Label(
            text=f"🏆 {match['league']}",
            color=C_SUB,
            font_size=dp(11),
            halign="left", valign="middle",
            text_size=(None, None),
            size_hint_y=0.45,
        )
        league_lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0], None)))

        info.add_widget(teams_lbl)
        info.add_widget(league_lbl)

        # Kanal
        ch_text = match["channel"].split(",")[0].strip()
        ch_lbl = Label(
            text=ch_text,
            color=C_GOLD,
            font_size=dp(10),
            bold=True,
            size_hint=(None, None),
            size=(dp(72), dp(40)),
            halign="right", valign="middle",
            text_size=(dp(72), None),
        )

        self.add_widget(time_box)
        self.add_widget(info)
        self.add_widget(ch_lbl)

    def _upd(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _redraw_time(self, widget, color):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*color)
            RoundedRectangle(
                pos=widget.pos, size=widget.size,
                radius=[dp(6)] * 4
            )


# ── Gün Kartı ─────────────────────────────────────────────────────────────────
class DayCard(BoxLayout):
    def __init__(self, day_data, accent_hex, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            spacing=0,
            padding=[dp(12), dp(8), dp(12), dp(8)],
            **kwargs
        )

        with self.canvas.before:
            Color(*C_CARD)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        # Üst renkli şerit
        bar = Widget(size_hint_y=None, height=dp(3))
        with bar.canvas:
            Color(*get_color_from_hex(accent_hex))
            bar._rect = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda w, p: setattr(w._rect, 'pos', p),
                 size=lambda w, s: setattr(w._rect, 'size', s))
        self.add_widget(bar)

        # Gün başlığı
        day_lbl = make_label(
            f"📅  {day_data['date']}",
            color=get_color_from_hex(accent_hex),
            font_size=dp(14),
            bold=True,
            size_hint_y=None,
            height=dp(36),
        )
        self.add_widget(day_lbl)
        self.add_widget(Separator())

        # Maç satırları
        for match in day_data["matches"]:
            self.add_widget(MatchRow(match, accent_hex))
            self.add_widget(Separator())

        # Yüksekliği hesapla
        h = dp(3) + dp(36) + dp(1)
        h += len(day_data["matches"]) * (dp(64) + dp(1))
        h += dp(16)
        self.height = h

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size


# ── Ana Layout ────────────────────────────────────────────────────────────────
class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        with self.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        self._all_days = []
        self._build_header()
        self._build_toolbar()
        self._build_content()
        Clock.schedule_once(lambda dt: self._load_data(), 0.3)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            padding=[dp(14), dp(8), dp(14), dp(8)],
            spacing=dp(10),
        )
        with header.canvas.before:
            Color(*C_HEADER)
            r = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda w, p: setattr(r, 'pos', p),
                    size=lambda w, s: setattr(r, 'size', s))

        icon = Label(text="🏀", font_size=dp(28), size_hint=(None, 1), width=dp(40))
        header.add_widget(icon)

        titles = BoxLayout(orientation="vertical")
        titles.add_widget(Label(
            text="Basketbol Maç Programı",
            color=C_WHITE, font_size=dp(15), bold=True,
            halign="left", valign="middle",
            text_size=(None, None),
        ))
        titles.add_widget(Label(
            text="basketfaul.com.tr",
            color=C_SUB, font_size=dp(10),
            halign="left", valign="middle",
            text_size=(None, None),
        ))
        header.add_widget(titles)

        self._refresh_btn = Button(
            text="⟳ Yenile",
            size_hint=(None, None),
            size=(dp(80), dp(36)),
            background_color=C_BLUE,
            background_normal="",
            color=C_WHITE,
            font_size=dp(12),
            bold=True,
        )
        self._refresh_btn.bind(on_press=lambda _: self._load_data())
        header.add_widget(self._refresh_btn)
        self.add_widget(header)

    # ── Toolbar / Arama ───────────────────────────────────────────────────────
    def _build_toolbar(self):
        bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            padding=[dp(12), dp(6), dp(12), dp(6)],
            spacing=dp(6),
        )
        with bar.canvas.before:
            Color(*C_BG)
            r = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda w, p: setattr(r, 'pos', p),
                 size=lambda w, s: setattr(r, 'size', s))

        bar.add_widget(Label(text="🔍", font_size=dp(16),
                             size_hint=(None, 1), width=dp(24), color=C_SUB))

        self._search = TextInput(
            hint_text="Takım, lig veya kanal ara...",
            multiline=False,
            font_size=dp(12),
            foreground_color=C_TEXT,
            hint_text_color=C_SUB,
            background_color=C_HEADER,
            cursor_color=C_TEXT,
            padding=[dp(8), dp(6), dp(8), dp(6)],
        )
        self._search.bind(text=self._on_search)
        bar.add_widget(self._search)

        self._status_lbl = Label(
            text="",
            color=C_SUB,
            font_size=dp(10),
            size_hint=(None, 1),
            width=dp(90),
            halign="right",
            text_size=(dp(90), None),
        )
        bar.add_widget(self._status_lbl)
        self.add_widget(bar)

        # İnce ayırıcı
        sep = Widget(size_hint_y=None, height=dp(1))
        with sep.canvas:
            Color(*C_BORDER)
            Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, p: None, size=lambda w, s: None)
        self.add_widget(sep)

    # ── İçerik Alanı ─────────────────────────────────────────────────────────
    def _build_content(self):
        self._scroll = ScrollView(do_scroll_x=False)
        self._grid = GridLayout(
            cols=1,
            size_hint_y=None,
            spacing=dp(10),
            padding=[dp(10), dp(10), dp(10), dp(10)],
        )
        self._grid.bind(minimum_height=self._grid.setter('height'))
        self._scroll.add_widget(self._grid)
        self.add_widget(self._scroll)

        # Loading label
        self._loading_lbl = make_label(
            "⏳  Veriler yükleniyor...",
            color=C_SUB, font_size=dp(14),
            halign="center", size_hint_y=None, height=dp(40),
        )
        self._grid.add_widget(self._loading_lbl)

    # ── Veri Yükleme ──────────────────────────────────────────────────────────
    def _load_data(self):
        self._refresh_btn.disabled = True
        self._refresh_btn.text = "..."
        self._status_lbl.text = "Yükleniyor"
        self._grid.clear_widgets()
        self._grid.add_widget(make_label(
            "⏳  Yükleniyor...",
            color=C_SUB, font_size=dp(14),
            halign="center", size_hint_y=None, height=dp(40),
        ))
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self):
        try:
            days = fetch_matches()
            Clock.schedule_once(lambda dt: self._on_ready(days, None))
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_ready([], str(e)))

    def _on_ready(self, days, error):
        self._refresh_btn.disabled = False
        self._refresh_btn.text = "⟳ Yenile"
        self._all_days = days

        if error:
            self._status_lbl.text = "HATA"
            self._render([])
            return

        total = sum(len(d["matches"]) for d in days)
        now = datetime.now().strftime("%H:%M")
        self._status_lbl.text = f"{total} maç\n{now}"
        self._render(days)

    # ── Render ────────────────────────────────────────────────────────────────
    def _render(self, days):
        self._grid.clear_widgets()
        if not days:
            self._grid.add_widget(make_label(
                "📭  Maç bulunamadı.",
                color=C_SUB, font_size=dp(14),
                halign="center", size_hint_y=None, height=dp(60),
            ))
            return
        for idx, day_data in enumerate(days):
            color = DAY_COLORS[idx % len(DAY_COLORS)]
            self._grid.add_widget(DayCard(day_data, color))

        self._grid.add_widget(make_label(
            "© basketfaul.com.tr",
            color=C_SUB, font_size=dp(10),
            halign="center", size_hint_y=None, height=dp(30),
        ))

    # ── Arama ─────────────────────────────────────────────────────────────────
    def _on_search(self, _, text):
        q = text.strip().lower()
        if not q:
            self._render(self._all_days)
            return
        filtered = []
        for day in self._all_days:
            matches = [
                m for m in day["matches"]
                if q in m["teams"].lower()
                or q in m["league"].lower()
                or q in m["channel"].lower()
                or q in m["time"]
            ]
            if matches:
                filtered.append({"date": day["date"], "matches": matches})
        self._render(filtered)


# ── App ───────────────────────────────────────────────────────────────────────
class BasketbolApp(App):
    def build(self):
        Window.clearcolor = C_BG
        self.title = "Basketbol Maç Programı"
        return MainLayout()


if __name__ == "__main__":
    BasketbolApp().run()
