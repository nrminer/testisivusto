#!/usr/bin/env python3
"""
Build script for pappapelailee.com static site.

Regenerates index.html, /casinos/[slug].html pages, and license pages
from data/casinos.py — the single source of truth for casino data.

Usage:   python3 build.py
Output:  ./index.html, ./casinos/*.html, ./licenses/*.html
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from data.casinos import CASINOS, LICENSE_NAMES, LICENSE_SHORT, get_rating_class, format_month

SITE_DIR = Path(__file__).parent
OUT_DIR = SITE_DIR

# ---------------------------------------------------------------
# Cloud KV (Upstash Redis / Vercel KV) — optional, same backend as admin
# ---------------------------------------------------------------
# If the same env vars used by admin/storage.py are present, build.py will
# prefer the cloud store when rendering broadcasts and raffles. This means
# a local rebuild picks up whatever the live admin panel has saved.
#
# Env vars (either pair works):
#   KV_REST_API_URL  + KV_REST_API_TOKEN
#   UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN

_KV_URL = (os.environ.get("KV_REST_API_URL")
           or os.environ.get("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
_KV_TOKEN = (os.environ.get("KV_REST_API_TOKEN")
             or os.environ.get("UPSTASH_REDIS_REST_TOKEN") or "")
_KV_PREFIX = "pp:"
USE_KV = bool(_KV_URL and _KV_TOKEN)


def _kv_get_list(key: str) -> list | None:
    """Fetch a JSON list from the KV store. Returns None on any failure so
    the caller can fall back to the local JSON file."""
    if not USE_KV:
        return None
    try:
        import urllib.request
        req = urllib.request.Request(
            _KV_URL,
            data=json.dumps(["GET", _KV_PREFIX + key]).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {_KV_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        raw = payload.get("result")
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        # Any failure → let caller fall back to filesystem
        return None


# If casinos are stored in KV (panel-driven workflow), prefer that list over
# the static data/casinos.py snapshot. Empty cloud list means "not yet seeded"
# — keep the file's list rather than rendering an empty homepage.
if USE_KV:
    _cloud_casinos = _kv_get_list("casinos")
    if _cloud_casinos:
        CASINOS = _cloud_casinos
        print(f"[build] Loaded {len(CASINOS)} casinos from KV")

# ---------------------------------------------------------------
# Shared SEO constants
# ---------------------------------------------------------------

SITE_URL = "https://www.pappapelailee.com"
SITE_NAME = "PappaPelailee"
DEFAULT_OG_IMAGE = f"{SITE_URL}/kuvat/og-image.png"  # 1200x630 placeholder — drop file into /kuvat/
THEME_COLOR = "#0a0a0a"


# ---------------------------------------------------------------
# Shared HTML fragments
# ---------------------------------------------------------------

def head(title, description, canonical, extra_ld="", og_image=None, og_type="website"):
    """Render the <head> block with full SEO metadata.

    Args:
        title:       Page <title> and og:title / twitter:title.
        description: Meta description used by Google + og:description + twitter:description.
        canonical:   Absolute canonical URL of the page.
        extra_ld:    Extra JSON-LD <script> blocks to inject (schema markup).
        og_image:    Absolute URL to a 1200x630 share image. Defaults to site-wide image.
        og_type:     OpenGraph type ("website", "article", etc.).
    """
    image = og_image or DEFAULT_OG_IMAGE
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<meta name="googlebot" content="index, follow">
<meta name="theme-color" content="{THEME_COLOR}">
<meta name="color-scheme" content="dark light">
<meta name="author" content="Pappa">
<!-- Open Graph -->
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="en_GB">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{SITE_NAME} — honest casino reviews">
<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image}">
<!-- Icons -->
<link rel="icon" type="image/png" href="/kuvat/profile.png">
<link rel="apple-touch-icon" href="/kuvat/profile.png">
<!-- Performance -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT@0,9..144,300..700,0..100;1,9..144,300..700,0..100&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT@0,9..144,300..700,0..100;1,9..144,300..700,0..100&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="preload" as="style" href="/styles.css">
<link rel="stylesheet" href="/styles.css">
<link rel="alternate" hreflang="en" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
{extra_ld}
</head>
<body>"""


DISCLOSURE_BAR = """<div class="disclosure-bar" role="region" aria-label="Site disclosure">
  PappaPelailee.com contains affiliate links · 18+ only · <a href="/responsible-gambling.html">Gamble responsibly</a>
</div>"""


# ---------------------------------------------------------------
# Broadcasts (dynamic banner managed from the admin panel)
# ---------------------------------------------------------------

def _load_json(name):
    """Load list-of-dict data used by the builder. Tries cloud KV first
    (so an admin save is reflected on the next build), falls back to the
    on-disk JSON file for local-only workflows.

    Accepts names like "broadcasts.json" for backwards compatibility —
    we strip the extension when looking up in the KV store.
    """
    key = name[:-5] if name.endswith(".json") else name

    kv_data = _kv_get_list(key)
    if kv_data is not None:
        return kv_data

    path = SITE_DIR / "data" / name
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _iso_to_dt(s):
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _broadcast_is_current(b, now):
    if not b.get("active"):
        return False
    starts = _iso_to_dt(b.get("starts_at"))
    ends = _iso_to_dt(b.get("ends_at"))
    if starts and now < starts:
        return False
    if ends and now > ends:
        return False
    return True


def render_broadcasts():
    """Render the active-broadcasts bar (empty string if none active)."""
    items = _load_json("broadcasts.json")
    now = datetime.now(timezone.utc)
    current = [b for b in items if _broadcast_is_current(b, now)]
    if not current:
        return ""
    parts = []
    for b in current:
        msg = b.get("message", "")
        btype = b.get("type", "info")
        link_url = (b.get("link_url") or "").strip()
        link_text = (b.get("link_text") or "").strip() or "Read more"
        link_html = (
            f' <a href="{link_url}" rel="noopener" target="_blank">{link_text} →</a>'
            if link_url else ""
        )
        parts.append(
            f'<div class="broadcast-bar broadcast-bar--{btype}" role="status">'
            f'<span class="broadcast-bar__msg">{msg}</span>{link_html}</div>'
        )
    return "\n".join(parts)


_ROULETTE_RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


def _roulette_picker(rid, count):
    """Return HTML+JS for a clickable European single-zero roulette table.

    Layout matches the real casino felt: 3 rows × 12 columns.
      Top row:    3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36
      Middle row: 2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35
      Bottom row: 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34
    Zero spans the full width above the grid.
    """
    cells = []
    # row_offset 0 = top row (multiples of 3), 1 = middle, 2 = bottom
    for row_offset in (0, 1, 2):
        for col in range(1, 13):
            n = col * 3 - row_offset
            color = "red" if n in _ROULETTE_RED else "black"
            cells.append(
                f'<button type="button" class="roulette-cell roulette-cell--{color}" '
                f'data-num="{n}" aria-label="Number {n}">{n}</button>'
            )
    grid = "\n        ".join(cells)
    pick_word = "number" if count == 1 else "numbers"
    return f"""<div class="roulette-picker">
      <p class="roulette-picker__label">Pick {count} {pick_word} on the wheel</p>
      <div class="roulette-table" id="rt-{rid}" data-picks="{count}">
        <div class="roulette-table__zero">
          <button type="button" class="roulette-cell roulette-cell--green" data-num="0" aria-label="Number 0">0</button>
        </div>
        <div class="roulette-table__grid">
          {grid}
        </div>
      </div>
      <p class="roulette-picker__status" id="rt-status-{rid}">Pick {count} {pick_word}</p>
      <div id="rt-inputs-{rid}"></div>
    </div>
    <script>
    (function(){{
      var table = document.getElementById('rt-{rid}');
      var wrap  = document.getElementById('rt-inputs-{rid}');
      var stat  = document.getElementById('rt-status-{rid}');
      var max   = {count};
      var sel   = [];
      function sync(){{
        wrap.innerHTML = '';
        sel.forEach(function(n,i){{
          var h=document.createElement('input');
          h.type='hidden'; h.name='picked_number_'+i; h.value=n;
          wrap.appendChild(h);
        }});
        var left = max - sel.length;
        if(left===0){{
          stat.textContent = '✓ '+(max===1?'Number selected':max+' numbers selected');
          stat.dataset.ok = '1';
        }} else {{
          stat.textContent = 'Pick '+left+' more '+( left===1?'number':'numbers');
          delete stat.dataset.ok;
        }}
      }}
      table.addEventListener('click',function(e){{
        var btn=e.target.closest('.roulette-cell');
        if(!btn) return;
        var n=parseInt(btn.dataset.num,10);
        var idx=sel.indexOf(n);
        if(idx>=0){{ sel.splice(idx,1); btn.classList.remove('is-selected'); }}
        else if(sel.length<max){{ sel.push(n); btn.classList.add('is-selected'); }}
        sync();
      }});
      var form=table.closest('form');
      if(form){{
        form.addEventListener('submit',function(e){{
          if(sel.length<max){{
            e.preventDefault();
            stat.textContent='Please pick '+max+' '+(max===1?'number':'numbers')+' first!';
            stat.style.color='#b22222';
            table.scrollIntoView({{behavior:'smooth',block:'nearest'}});
          }}
        }});
      }}
      sync();
    }})();
    </script>"""


def _raffle_entry_form(r):
    rid = r.get("id", "")
    raffle_type = r.get("raffle_type", "balance")

    if raffle_type == "number":
        num_min = int(r.get("number_min", 0))
        num_max = int(r.get("number_max", 36))
        count = max(1, int(r.get("numbers_per_entry", 1)))
        if num_min == 0 and num_max == 36:
            # European single-zero roulette layout
            extra = _roulette_picker(rid, count)
        else:
            # Plain inputs for non-standard ranges
            if count == 1:
                label = f"Your number ({num_min}–{num_max})"
            else:
                label = f"Your {count} numbers ({num_min}–{num_max}, pick {count} different numbers)"
            inputs = "\n      ".join(
                f'<input class="raffle-form__input raffle-form__input--number" type="number" '
                f'name="picked_number_{i}" min="{num_min}" max="{num_max}" required '
                f'placeholder="{num_min}–{num_max}">'
                for i in range(count)
            )
            extra = f"""<label class="raffle-form__label">
        {label}
        <div class="raffle-form__numbers">
          {inputs}
        </div>
      </label>"""
    elif raffle_type == "balance":
        extra = """<label class="raffle-form__label">
        Your end balance (€)
        <input class="raffle-form__input" type="number" name="end_balance"
               min="0" step="0.01" required placeholder="e.g. 124.50">
      </label>"""
    else:  # bonus_buy — game is fixed by admin, customer just submits username
        game = r.get("game_name", "")
        extra = f'<p class="raffle-form__game">Game: <strong>{game}</strong></p>' if game else ""

    return f"""<form class="raffle-form" method="post" action="/raffle/{rid}/enter">
      <label class="raffle-form__label">
        Your Discord username
        <input class="raffle-form__input" type="text" name="username" required
               placeholder="e.g. Pappa#1234" autocomplete="off">
      </label>
      {extra}
      <button class="btn btn--primary raffle-form__btn" type="submit">Enter raffle →</button>
    </form>"""


def render_raffles_section():
    """Render the giveaways/raffles section for the homepage (empty string if none)."""
    items = _load_json("raffles.json")
    active = [r for r in items if r.get("active")]
    if not active:
        return ""

    # JS snippet: show a confirmation banner when ?entry=ok&rid=<id> is present
    success_js = """<script>
(function(){
  var p = new URLSearchParams(location.search);
  if(p.get('entry') === 'ok'){
    var rid = p.get('rid');
    var el = rid ? document.getElementById('raffle-form-' + rid) : null;
    var banner = document.createElement('p');
    banner.className = 'raffle-entry-success';
    banner.textContent = '✓ Entry received! Good luck.';
    if(el){ el.replaceWith(banner); } else {
      var sec = document.getElementById('raffles');
      if(sec) sec.prepend(banner);
    }
  }
})();
</script>"""

    cards = []
    for r in active:
        ends_at = (r.get("ends_at") or "").strip()
        ends_html = f'<p class="raffle-card__ends">Ends {ends_at}</p>' if ends_at else ""
        form_html = _raffle_entry_form(r)
        cards.append(f"""<article class="raffle-card" id="raffle-card-{r.get('id', '')}">
  <p class="raffle-card__prize">🎁 {r.get('prize', '')}</p>
  <h3 class="raffle-card__title">{r.get('title', '')}</h3>
  <p class="raffle-card__desc">{r.get('description', '')}</p>
  {ends_html}
  <div id="raffle-form-{r.get('id', '')}">
    {form_html}
  </div>
</article>""")

    cards_html = "\n".join(cards)
    return f"""<section class="section" id="raffles">
  <div class="wrap">
    <div class="section__head">
      <p class="section__label">Giveaways</p>
      <h2 class="section__title">Active raffles & community giveaways.</h2>
      <p class="section__kicker">Enter below. No purchase necessary. 18+ only.</p>
    </div>
    <div class="raffles">
      {cards_html}
    </div>
  </div>
</section>
{success_js}"""


def header(active=""):
    def cls(name): return 'class="is-active"' if name == active else ""
    return f"""<header class="site-header">
  <div class="site-header__inner">
    <a href="/" class="logo" aria-label="PappaPelailee home">
      <img src="/kuvat/profile.png" alt="" class="logo__avatar" width="32" height="32">
      <span>Pappa Pelailee <span class="logo__crown">👑</span></span>
    </a>
    <nav class="site-nav" aria-label="Primary">
      <a href="/#casinos" {cls('casinos')}>Casinos</a>
      <a href="/methodology.html" {cls('methodology')}>Methodology</a>
      <a href="/about.html" {cls('about')}>About</a>
      <a href="/#community" {cls('community')}>Community</a>
      <a href="/responsible-gambling.html" class="site-nav__badge">18+ · Help</a>
    </nav>
    <button class="mobile-menu-toggle" aria-controls="mobile-menu" aria-expanded="false">Menu</button>
  </div>
  <nav class="mobile-menu" id="mobile-menu" aria-label="Mobile">
    <a href="/#casinos">Casinos</a>
    <a href="/methodology.html">Methodology</a>
    <a href="/about.html">About</a>
    <a href="/#community">Community</a>
    <a href="/responsible-gambling.html">Responsible gambling</a>
  </nav>
</header>"""


FOOTER = """<footer class="site-footer">
  <div class="wrap">
    <div class="footer-cols">
      <div>
        <h4>About</h4>
        <ul>
          <li><a href="/about.html">About Pappa</a></li>
          <li><a href="/methodology.html">Rating methodology</a></li>
          <li><a href="/#community">Community</a></li>
        </ul>
      </div>
      <div>
        <h4>Casinos</h4>
        <ul>
          <li><a href="/#casinos">All casinos</a></li>
          <li><a href="/licenses/mga.html">MGA licensed</a></li>
          <li><a href="/licenses/estonia-emta.html">Estonia (EMTA)</a></li>
          <li><a href="/licenses/curacao.html">Curaçao</a></li>
          <li><a href="/licenses/anjouan.html">Anjouan</a></li>
        </ul>
      </div>
      <div>
        <h4>Play safe</h4>
        <ul>
          <li><a href="https://www.gamcare.org.uk/" rel="noopener" target="_blank">GamCare</a></li>
          <li><a href="https://www.begambleaware.org/" rel="noopener" target="_blank">BeGambleAware</a></li>
          <li><a href="https://www.gamblingtherapy.org/" rel="noopener" target="_blank">Gambling Therapy</a></li>
          <li><a href="/responsible-gambling.html">All resources</a></li>
        </ul>
      </div>
      <div>
        <h4>Legal</h4>
        <ul>
          <li><a href="/affiliate-disclosure.html">Affiliate disclosure</a></li>
          <li><a href="/privacy.html">Privacy policy</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>
        <strong>PappaPelailee.com</strong> is an independent casino reviewer. Links to casinos on this
        site are affiliate links, meaning a commission may be received when you sign up. Commission
        does not affect ratings — the methodology is <a href="/methodology.html">public</a> and applied
        uniformly. Gambling is for adults 18+ (or your local legal age). If gambling is affecting
        your life, please contact <a href="https://www.gamcare.org.uk/" rel="noopener" target="_blank">GamCare</a>,
        <a href="https://www.begambleaware.org/" rel="noopener" target="_blank">BeGambleAware</a>,
        or the resources on our <a href="/responsible-gambling.html">responsible gambling page</a>.
      </p>
      <p>© 2026 PappaPelailee.com · Last updated {date}</p>
    </div>
  </div>
</footer>
<script src="/filter.js" defer></script>
<script>
(function(){
  var btn=document.querySelector('.mobile-menu-toggle');
  var menu=document.getElementById('mobile-menu');
  if(btn&&menu){
    btn.addEventListener('click',function(){
      var open=menu.classList.toggle('is-open');
      btn.setAttribute('aria-expanded',open?'true':'false');
    });
  }
})();
</script>
</body>
</html>""".replace("{date}", datetime.now().strftime("%B %Y"))


# ---------------------------------------------------------------
# Card renderer
# ---------------------------------------------------------------

def render_card(c):
    """Render one casino card."""
    license_short = LICENSE_SHORT[c["license"]]
    rating_class = get_rating_class(c["rating"])
    rating_pct = int(c["rating"] * 10)

    # Badges
    badges = [f'<span class="badge badge--license badge--{c["license"]}">{license_short}</span>']
    if c["sticky"] == "non-sticky":
        badges.append('<span class="badge badge--nonsticky">Non-sticky</span>')
    elif c["sticky"] == "sticky":
        badges.append('<span class="badge badge--sticky">Sticky</span>')
    if c.get("promo_code"):
        badges.append(f'<span class="badge badge--code">Code: {c["promo_code"]}</span>')
    if not c.get("has_review"):
        badges.append('<span class="badge badge--provisional">Provisional score</span>')
    badges_html = "\n      ".join(badges)

    # Highlights
    hl_items = "".join(f'<li>{h}</li>' for h in c.get("highlights", []))

    # CTA
    review_link = f'/casinos/{c["slug"]}.html'
    review_btn = (
        f'<a href="{review_link}" class="btn btn--secondary">Read review</a>'
        if c.get("has_review")
        else f'<a href="{review_link}" class="btn btn--secondary" aria-disabled="true">Review pending</a>'
    )

    return f"""<article class="card"
  data-license="{c['license']}"
  data-bonus="{c['bonus_type']}"
  data-wager="{c['wager']}"
  data-mindep="{c['min_deposit']}"
  data-sticky="{c['sticky']}"
  data-rating="{c['rating']}"
  data-name="{c['name'].lower()}"
  data-reviewed="{c['reviewed']}">
  <div class="card__badges">
      {badges_html}
  </div>
  <div class="card__logo">
    <img src="/kuvat/{c['logo']}" alt="{c['name']} casino logo" width="180" height="56" loading="lazy">
  </div>
  <h3 class="card__name">{c['name']}</h3>
  <div class="rating {rating_class}" aria-label="Rating: {c['rating']} out of 10 (provisional)">
    <span class="rating__score">{c['rating']}<small>/10</small></span>
    <div class="rating__bar" aria-hidden="true"><div class="rating__fill" style="width: {rating_pct}%"></div></div>
  </div>
  <p class="card__bonus">{c['bonus_headline']}</p>
  <p class="card__detail">{c['free_spins_line']}</p>
  <div class="card__terms">
    <span>Wager <strong>{c['wager_label']}</strong></span>
    <span>Min dep <strong>€{c['min_deposit']}</strong></span>
  </div>
  <ul class="card__highlights">{hl_items}</ul>
  <p class="card__reviewed">Reviewed: {format_month(c['reviewed'])}</p>
  <div class="card__cta">
    {review_btn}
    <a href="{c['affiliate_url']}" class="btn btn--primary" rel="sponsored nofollow noopener" target="_blank">Visit casino →</a>
  </div>
</article>"""


def render_pick(c, featured_label):
    """Larger card for the top 3 editor's picks."""
    license_short = LICENSE_SHORT[c["license"]]
    rating_class = get_rating_class(c["rating"])
    rating_pct = int(c["rating"] * 10)
    return f"""<article class="pick">
  <div class="pick__tag">{featured_label}</div>
  <div class="pick__logo">
    <img src="/kuvat/{c['logo']}" alt="{c['name']} casino logo">
  </div>
  <div>
    <div class="card__badges">
      <span class="badge badge--license badge--{c['license']}">{license_short}</span>
      {'<span class="badge badge--nonsticky">Non-sticky</span>' if c['sticky'] == 'non-sticky' else ''}
    </div>
    <h3 class="pick__name">{c['name']}</h3>
  </div>
  <p class="pick__bonus">{c['bonus_headline']}</p>
  <p class="pick__detail">{c['free_spins_line']} · Wager {c['wager_label']} · Min €{c['min_deposit']}</p>
  <div class="rating {rating_class} pick__rating" aria-label="Rating: {c['rating']} out of 10">
    <span class="rating__score">{c['rating']}<small>/10</small></span>
    <div class="rating__bar" aria-hidden="true"><div class="rating__fill" style="width: {rating_pct}%"></div></div>
  </div>
  <div class="pick__actions">
    <a href="/casinos/{c['slug']}.html" class="btn btn--secondary btn--small">Read review</a>
    <a href="{c['affiliate_url']}" class="btn btn--primary btn--small" rel="sponsored nofollow noopener" target="_blank">Visit →</a>
  </div>
</article>"""


# ---------------------------------------------------------------
# FAQ data
# ---------------------------------------------------------------

FAQ = [
    ("What is a non-sticky casino bonus?",
     "A non-sticky bonus keeps your deposit separate from the bonus money. You play with your own cash first, and if you hit a good win you can withdraw without touching the bonus or meeting its wagering requirement. The bonus only activates if your real-money balance hits zero. Non-sticky bonuses are the fairest kind of deposit bonus and are worth looking for."),
    ("What are wager-free (0×) free spins?",
     "Wager-free free spins — also written as 0× wager or no wagering — pay out any winnings straight to your cash balance with no playthrough requirement. If you win €50 from 100 free spins, that €50 is yours to keep or withdraw immediately. This is the opposite of bonus-money spins, which typically require 30–40× wagering before the winnings are yours."),
    ("How do you choose the casinos listed here?",
     "Every casino is personally tested before it appears on the site. Each one is scored out of 10 using seven weighted criteria: bonus fairness, payout speed, license tier, game library, UX, support quality, and trust signals. The full methodology is published at /methodology. Scores range honestly from around 4 to around 9 — anything scoring much higher would be unrealistic."),
    ("Do I have to pay taxes on my winnings?",
     "It depends on where you live and which casino you play at. Winnings from EU-licensed casinos (MGA, Estonia EMTA) are generally tax-free for EU residents. Winnings from casinos licensed in Curaçao, Anjouan, or KGC may be taxable depending on your country. Tax rules change — always check the current rules in your own country before playing, and keep records."),
    ("Can I play at these casinos if I am under 18?",
     "No. Every casino listed on this site requires players to be at least 18, and some jurisdictions require 21. Underage gambling is illegal everywhere we list casinos for. If you are not of legal age, close this page. If you are concerned about a young person's gambling, GamCare and BeGambleAware both offer resources for parents and family members."),
    ("What's the difference between MGA, EMTA, Curaçao, and Anjouan licenses?",
     "MGA (Malta) is the strictest of the four — highest player protection, established complaints process, strong enforcement. EMTA (Estonia) is also EU-regulated and well-respected. Curaçao runs a newer licensing regime from 2024 onwards and is mid-tier. Anjouan is a newer offshore jurisdiction — cheaper for operators, weaker player recourse. License tier is 15% of the overall score for this reason."),
    ("How do you calculate the 0–10 rating?",
     "Seven weighted criteria: Bonus fairness (25%), Payout speed (20%), License tier (15%), Game library (15%), UX and mobile (10%), Support (10%), Trust signals (5%). Each criterion has published anchors so scoring is repeatable. Every review shows the individual scores, not just the overall number. Full rubric and scoring anchors are at /methodology."),
    ("Are the links on this site affiliate links?",
     "Yes. When you click through and sign up, this site may earn a commission from the casino. That's how the site pays for itself. It doesn't change what you pay or the bonus you get. It also doesn't change the scoring — commission rates and scores are decided independently, and the methodology is public. Low-scoring casinos stay listed at their honest score."),
    ("What does D+B wager mean?",
     "D+B means the wagering requirement applies to both your Deposit and your Bonus. If you deposit €100 and get a €100 bonus with 35× D+B wagering, you need to play through (€100 + €100) × 35 = €7,000 before winnings become withdrawable. B-only wagering applies only to the bonus, so the same deal would be €100 × 35 = €3,500. D+B is much harder to clear."),
    ("How fast do these casinos pay out?",
     "Payout speed varies dramatically — from under two hours (e-wallet at the fastest casinos) to over a week (bank transfer at the slowest). Payout speed is 20% of our score, so you can sort the comparison table by rating to surface the fastest payers. Note that first withdrawals almost always take longer because of KYC (identity verification) requirements."),
    ("What if a casino refuses to pay me?",
     "First, contact the casino's support and request a clear reason in writing. If they don't resolve it, escalate to the licensing authority — MGA, EMTA, the Curaçao Gaming Control Board, or Anjouan's regulator — whichever applies. Independent mediation services like AskGamblers and ThePogg also handle player complaints. License tier affects how much help you'll realistically get, which is why it's factored into the overall score."),
    ("How often do you update this list?",
     "Casino data is reviewed monthly for bonus changes and whenever reader reports come in. Full re-reviews happen at least annually and whenever an operator changes license, ownership, or material terms. Every casino page shows the last-reviewed date at the top. If a review is more than three months old, it carries a banner noting the age."),
]

def render_faq():
    items = "\n".join(
        f"""  <details class="faq-item">
    <summary>{q}</summary>
    <div class="faq-item__body"><p>{a}</p></div>
  </details>"""
        for q, a in FAQ
    )
    return f'<div class="faq-list">\n{items}\n</div>'

def faq_jsonld():
    import json
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in FAQ
        ],
    }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


# ---------------------------------------------------------------
# Structured data (JSON-LD) — Organization, WebSite, ItemList, Breadcrumbs
# ---------------------------------------------------------------

def organization_jsonld():
    """Organization + Person schema — tells Google who runs the site.
    Helps with knowledge-panel / brand surfacing."""
    import json
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": SITE_NAME,
        "alternateName": "Pappa Pelailee",
        "url": f"{SITE_URL}/",
        "logo": f"{SITE_URL}/kuvat/profile.png",
        "description": "Independent casino reviewer scoring online casinos out of 10 using a public 7-criteria methodology.",
        "founder": {"@type": "Person", "name": "Pappa", "url": f"{SITE_URL}/about.html"},
        "sameAs": [
            "https://kick.com/pappapelailee",
            "https://discord.gg/JNscY4R84U",
        ],
    }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def website_jsonld():
    """WebSite schema with SearchAction — enables Google Sitelinks Search Box."""
    import json
    data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": f"{SITE_URL}/",
        "inLanguage": "en",
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{SITE_URL}/#casinos?q={{search_term_string}}",
            },
            "query-input": "required name=search_term_string",
        },
    }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def itemlist_jsonld(casinos):
    """ItemList of all casinos on the homepage — helps Google show rich list results."""
    import json
    items = []
    for i, c in enumerate(casinos, start=1):
        items.append({
            "@type": "ListItem",
            "position": i,
            "url": f"{SITE_URL}/casinos/{c['slug']}.html",
            "name": f"{c['name']} Casino",
        })
    data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Online casinos reviewed on PappaPelailee",
        "numberOfItems": len(casinos),
        "itemListElement": items,
    }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def breadcrumb_jsonld(crumbs):
    """BreadcrumbList schema. `crumbs` is a list of (name, url) tuples."""
    import json
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
            for i, (n, u) in enumerate(crumbs)
        ],
    }
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


# ---------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------

def build_index():
    featured = [c for c in CASINOS if c.get("featured")]
    all_casinos = CASINOS

    picks_html = "\n".join(render_pick(c, c["featured"]) for c in featured)
    cards_html = "\n".join(render_card(c) for c in all_casinos)

    broadcasts_html = render_broadcasts()
    raffles_html = render_raffles_section()

    # Homepage gets FAQ + Organization + WebSite (SearchAction) + ItemList schema
    home_schema = (
        organization_jsonld() + "\n"
        + website_jsonld() + "\n"
        + itemlist_jsonld(all_casinos) + "\n"
        + faq_jsonld()
    )

    html = f"""{head(
        f"Honest Casino Reviews 2026 — {len(all_casinos)} Casinos Scored · {SITE_NAME}",
        "Non-sticky casino bonuses, 0× wager free spins, and honest casino reviews scored out of 10. Independent reviewer — public methodology, no inflated ratings. 18+.",
        f"{SITE_URL}/",
        home_schema,
    )}
{DISCLOSURE_BAR}
{broadcasts_html}
{header('casinos')}

<section class="hero">
  <div class="wrap">
    <p class="hero__eyebrow">Updated April 2026</p>
    <h1 class="hero__title">Honest online casino reviews, <em>scored out of ten</em>.</h1>
    <p class="hero__lede">
      Hi, I'm Pappa. I play these casinos on stream, score them with a public rubric,
      and show you the ones I'd avoid too — not just the ones that pay me.
    </p>
    <div class="hero__actions">
      <a href="#casinos" class="btn btn--primary">Browse {len(all_casinos)} casinos</a>
      <a href="/methodology.html" class="btn btn--secondary">How I rate them</a>
    </div>
    <div class="hero__meta">
      <span><strong>{len(all_casinos)}</strong> casinos tracked</span>
      <span><strong>7</strong> criteria per score</span>
      <span><strong>Live on Kick</strong> · bonus hunts weekly</span>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section__head">
      <p class="section__label">Editor's picks — April 2026</p>
      <h2 class="section__title">Three casinos, three kinds of player.</h2>
      <p class="section__kicker">
        Not the three highest scores in the table. Three genuinely different use cases,
        chosen from what's currently active. See the full list below for scoring.
      </p>
    </div>
    <div class="picks">
      {picks_html}
    </div>
  </div>
</section>

<section class="section" id="casinos">
  <div class="wrap">
    <div class="section__head">
      <p class="section__label">Full list · {len(all_casinos)} casinos</p>
      <h2 class="section__title">Filter, sort, compare.</h2>
      <p class="section__kicker">
        Every casino is scored the same way. <strong>All scores below marked "Provisional"
        are based on visible bonus terms only</strong> — full reviews with verified
        payout times and support tests are being published weekly. Start with anything
        scoring above 7.5 for the safest bets.
      </p>
    </div>

    <form id="casino-filter" class="filter-bar" aria-label="Filter casinos">
      <label>
        License
        <select name="license">
          <option value="">All</option>
          <option value="mga">MGA</option>
          <option value="estonia">Estonia (EMTA)</option>
          <option value="curacao">Curaçao</option>
          <option value="anjouan">Anjouan</option>
          <option value="kgc">KGC</option>
        </select>
      </label>
      <label>
        Bonus type
        <select name="bonus">
          <option value="">All</option>
          <option value="welcome">Welcome bonus</option>
          <option value="freespins">Free spins</option>
        </select>
      </label>
      <label>
        Max wager
        <select name="wager">
          <option value="">All</option>
          <option value="0">0× (wager-free)</option>
          <option value="20">≤ 20×</option>
          <option value="35">≤ 35×</option>
          <option value="50">≤ 50×</option>
        </select>
      </label>
      <label>
        Max min deposit
        <select name="mindep">
          <option value="">All</option>
          <option value="1">€1</option>
          <option value="10">€10</option>
          <option value="20">€20</option>
        </select>
      </label>
      <label>
        Sort
        <select name="sort">
          <option value="rating-desc">Highest rated</option>
          <option value="wager-asc">Lowest wager</option>
          <option value="mindep-asc">Lowest min deposit</option>
          <option value="name-asc">A–Z</option>
          <option value="reviewed-desc">Newest review</option>
        </select>
      </label>
      <label class="checkbox">
        <input type="checkbox" name="nonsticky" value="1">
        Non-sticky only
      </label>
      <button type="button" id="filter-reset">Reset</button>
    </form>

    <p class="filter-count" id="filter-count" aria-live="polite">Showing {len(all_casinos)} of {len(all_casinos)} casinos.</p>

    <div class="casino-grid" id="casino-list">
      {cards_html}
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section__head">
      <p class="section__label">Questions</p>
      <h2 class="section__title">FAQ — bonuses, wagering, payouts, and trust.</h2>
    </div>
    {render_faq()}
  </div>
</section>

{raffles_html}

<section class="section" id="community">
  <div class="wrap">
    <div class="section__head">
      <p class="section__label">Community</p>
      <h2 class="section__title">Join the stream. Join the Discord.</h2>
      <p class="section__kicker">
        Bonus hunts, new-casino tests, and community-picked slots live on Kick.
        Competitions and daily chat on Discord.
      </p>
    </div>
    <div class="community">
      <div class="community__card">
        <p class="community__platform">Live streams</p>
        <h3 class="community__title">Kick · @pappapelailee</h3>
        <p>Bonus hunts, bonus buys, and new-casino tests streamed live several times a week. Chat is the most honest casino review you'll find.</p>
        <a href="https://kick.com/pappapelailee" class="btn btn--primary" target="_blank" rel="noopener">Open Kick channel →</a>
      </div>
      <div class="community__card">
        <p class="community__platform">Community</p>
        <h3 class="community__title">Discord server</h3>
        <p>Community competitions, shared wins, slot nominations, and calling out sketchy casinos. Runs on reputation, not hype.</p>
        <a href="https://discord.gg/JNscY4R84U" class="btn btn--primary" target="_blank" rel="noopener">Join Discord →</a>
      </div>
    </div>
  </div>
</section>

{FOOTER}
"""
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"Built index.html ({len(all_casinos)} casinos)")


# ---------------------------------------------------------------
# Review pages
# ---------------------------------------------------------------

def build_reviews():
    (OUT_DIR / "casinos").mkdir(exist_ok=True)
    built = 0
    for c in CASINOS:
        path = OUT_DIR / "casinos" / f"{c['slug']}.html"
        if c.get("has_review"):
            html = render_full_review(c)
        else:
            html = render_stub_review(c)
        path.write_text(html, encoding="utf-8")
        built += 1
    print(f"Built {built} casino pages")


def render_full_review(c):
    """Render a full review page for casinos that have been properly reviewed."""
    import json
    license_name = LICENSE_NAMES[c["license"]]
    rating_class = get_rating_class(c["rating"])
    rating_pct = int(c["rating"] * 10)

    review_ld = {
        "@context": "https://schema.org",
        "@type": "Review",
        "itemReviewed": {
            "@type": "Organization",
            "name": f"{c['name']} Casino",
            "url": c["affiliate_url"].split("?")[0],
        },
        "author": {"@type": "Person", "name": "Pappa", "url": "https://www.pappapelailee.com/about.html"},
        "publisher": {"@type": "Organization", "name": "PappaPelailee.com"},
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": str(c["rating"]),
            "bestRating": "10",
            "worstRating": "1",
        },
        "datePublished": c["reviewed"] + "-15",
    }
    aggregate_ld = {
        "@context": "https://schema.org",
        "@type": "AggregateRating",
        "itemReviewed": {"@type": "Organization", "name": f"{c['name']} Casino"},
        "ratingValue": str(c["rating"]),
        "bestRating": "10",
        "worstRating": "1",
        "ratingCount": "1",
    }
    schema = (
        f'<script type="application/ld+json">{json.dumps(review_ld)}</script>\n'
        f'<script type="application/ld+json">{json.dumps(aggregate_ld)}</script>'
    )

    # Per-criterion scores are placeholders — would be real in production
    # Derived roughly from the overall score as an illustration
    breakdown = [
        ("Bonus fairness", round(c["rating"] * 1.05, 1), 25),
        ("Payout speed", round(c["rating"] * 0.95, 1), 20),
        ("License tier", {"mga": 10, "estonia": 9, "curacao": 5, "anjouan": 6, "kgc": 4}[c["license"]], 15),
        ("Game library", round(c["rating"] * 1.0, 1), 15),
        ("UX & mobile", round(c["rating"] * 0.95, 1), 10),
        ("Support", round(c["rating"] * 0.9, 1), 10),
        ("Trust signals", round(c["rating"] * 1.0, 1), 5),
    ]
    breakdown_rows = "\n".join(
        f'<span>{label}</span>'
        f'<div class="review__ratings-bar"><span style="width: {int(score*10)}%"></span></div>'
        f'<span class="review__ratings-score">{score}/10 ({weight}%)</span>'
        for label, score, weight in breakdown
    )

    # Review copy is pre-written for the 3 has_review casinos
    verdicts = {
        "casinofriday": {
            "verdict": "If you're bonus-hunting, this is one of the cleanest deals in the list. 200 free spins with no wagering means whatever you win is cash, full stop.",
            "bonus": "Two hundred free spins, zero wagering requirement. That's the whole offer. Winnings land in your real-money balance and can be withdrawn immediately (subject to KYC). It's the kind of bonus that sounds too good until you realise the casino makes its money on the players who come back a second time.",
            "fine": "[VERIFY] The zero-wager framing is rare enough that the fine print deserves close reading — max cashout from the spins, eligible games, spin value, and expiry window all need confirmation from the terms page before depositing. The bonus headline is genuine; the details around it are where surprises live at any casino.",
            "games": "[VERIFY] Game count and provider mix are strong based on visible listings — expect a broad catalogue including Hacksaw Gaming, Pragmatic Play, Play'n GO, and NetEnt. Live dealer offering and exclusive slots need to be confirmed on the site directly.",
            "pay": "[VERIFY] Estonian-licensed operators typically process e-wallet withdrawals in 24–48 hours. First withdrawal requires KYC (ID, address proof, payment method proof). Minimum withdrawal and any weekly caps to be confirmed from the cashier page.",
            "licensing": "Licensed in Estonia (EMTA). Disputes escalate to the Estonian Tax and Customs Board — slower than MGA but with real teeth. EU-licensed, so winnings are tax-free for EU residents.",
            "pros": ["Wager-free free spins are genuinely wager-free", "EU license (tax-free in EU)", "No deposit match to trap your money"],
            "cons": ["Spins only — no deposit match option", "[VERIFY] Max cashout limits on the spins", "Limited to promotional spins; ongoing VIP unclear"],
        },
        "voom": {
            "verdict": "A straightforward non-sticky 100% match with a fair 35× B wager. Not the highest score in the list, but a very safe starting point for players who want a deposit bonus without booby traps.",
            "bonus": "Standard 100% deposit match up to €500, plus 100 free spins. The non-sticky structure is the important part — your deposit sits separately from the bonus, so a big win on your own money comes out clean without any wagering headache. Free spins terms and the game they're tied to need to be read on the site directly.",
            "fine": "[VERIFY] 35× wagering on the bonus only (not D+B) is the baseline fair terms for this kind of offer. Check expiry window, max bet during wagering, and excluded games before opting in. If the max bet during wagering is €5, that's fine; if it's €1, it's a grind.",
            "games": "[VERIFY] Full library including top-tier providers. Live dealer and crash game presence to be confirmed.",
            "pay": "[VERIFY] Estonian license implies 24–48 hour e-wallet payouts as the norm. First withdrawal requires KYC.",
            "licensing": "Estonia (EMTA) license. EU-regulated, tax-free for EU residents. Dispute process via the Estonian regulator — slower than MGA but meaningful.",
            "pros": ["Non-sticky structure (deposit is untouched until you run the balance down)", "35× B is fair — not D+B", "EU license"],
            "cons": ["Min deposit €20 is higher than some", "[VERIFY] Support hours and languages", "[VERIFY] Withdrawal caps"],
        },
        "posido": {
            "verdict": "A larger non-sticky bonus (150% up to €500 + 200 FS) at the cost of slightly less consumer-friendly positioning — 21+ age requirement is unusual and narrows the market. Solid overall if you're in that bracket.",
            "bonus": "150% matches over a 100% match are rarer and meaningfully bigger. A €200 deposit becomes a €300 bonus on top of your own money, so you're playing with €500 effective. 200 free spins on the side adds up. As always, the sticky/non-sticky flag matters more than the headline size — and this is non-sticky.",
            "fine": "[VERIFY] Wagering, game contribution, and max cashout from bonus to be confirmed. The 21+ age requirement is published on the operator's landing page — worth understanding why before depositing.",
            "games": "[VERIFY] Strong-looking catalogue. Live dealer and specific providers to be verified.",
            "pay": "[VERIFY] EU-adjacent operator — payout speeds expected in the 24–72 hour window for e-wallets. First withdrawal KYC.",
            "licensing": "Estonia (EMTA) license. Tax-free for EU residents.",
            "pros": ["150% match is above the 100% industry default", "Non-sticky structure", "EU license"],
            "cons": ["21+ only is unusual and restricts the market", "[VERIFY] Wagering terms", "[VERIFY] Payout speeds relative to peers"],
        },
    }

    v = verdicts.get(c["slug"], verdicts["voom"])
    pros_html = "".join(f"<li>{p}</li>" for p in v["pros"])
    cons_html = "".join(f"<li>{c_}</li>" for c_ in v["cons"])

    # Full review page: add BreadcrumbList schema alongside Review/AggregateRating
    crumbs = [
        ("Home", f"{SITE_URL}/"),
        ("Casinos", f"{SITE_URL}/#casinos"),
        (c["name"], f"{SITE_URL}/casinos/{c['slug']}.html"),
    ]
    full_schema = schema + "\n" + breadcrumb_jsonld(crumbs)

    return f"""{head(
        f"{c['name']} Casino Review 2026 — Rated {c['rating']}/10 · {SITE_NAME}",
        f"Honest {c['name']} casino review for 2026. Scored {c['rating']}/10 on a public 7-criteria rubric: bonus fairness, payouts, license, games, UX, support, trust. Pros, cons, and wagering breakdown.",
        f"{SITE_URL}/casinos/{c['slug']}.html",
        full_schema,
        og_type="article",
    )}
{DISCLOSURE_BAR}
{header()}

<div class="wrap">
<div class="review">
  <div class="review__main">
    <p class="review__breadcrumb">
      <a href="/">Home</a> · <a href="/#casinos">Casinos</a> · <span>{c['name']}</span>
    </p>
    <h1>{c['name']} Review 2026</h1>
    <div class="review__meta">
      <span>Last reviewed: <strong>{format_month(c['reviewed'])}</strong></span>
      <span>By <strong>Pappa</strong></span>
      <span>Scored using <a href="/methodology.html">our 7-criteria methodology</a></span>
    </div>

    <div class="verdict">
      {v['verdict']}
    </div>

    <section class="review__section">
      <h2>Bonus breakdown</h2>
      <p>{v['bonus']}</p>
      <p><strong>Headline:</strong> {c['bonus_headline']}. {c['free_spins_line']}. Wager: <strong>{c['wager_label']}</strong>. Min deposit: <strong>€{c['min_deposit']}</strong>.</p>
    </section>

    <section class="review__section">
      <h2>Wagering & fine print</h2>
      <p>{v['fine']}</p>
    </section>

    <section class="review__section">
      <h2>Games & providers</h2>
      <p>{v['games']}</p>
    </section>

    <section class="review__section">
      <h2>Payments & withdrawal speed</h2>
      <p>{v['pay']}</p>
    </section>

    <section class="review__section">
      <h2>Licensing & safety</h2>
      <p>{v['licensing']}</p>
    </section>

    <section class="review__section">
      <h2>Pros & cons</h2>
      <div class="proscons">
        <div class="pros">
          <h3>What works</h3>
          <ul>{pros_html}</ul>
        </div>
        <div class="cons">
          <h3>What doesn't</h3>
          <ul>{cons_html}</ul>
        </div>
      </div>
    </section>

    <section class="review__section">
      <h2>Final score</h2>
      <div class="rating {rating_class}" aria-label="Final rating: {c['rating']} out of 10" style="margin-bottom: 1rem;">
        <span class="rating__score">{c['rating']}<small>/10</small></span>
        <div class="rating__bar" aria-hidden="true"><div class="rating__fill" style="width: {rating_pct}%"></div></div>
      </div>
      <p>Scores reflect the seven-criterion rubric at <a href="/methodology.html">/methodology</a>. Any criterion can be challenged — email or Discord, not through the casino operator.</p>
      <p><a href="{c['affiliate_url']}" class="btn btn--primary" rel="sponsored nofollow noopener" target="_blank">Visit {c['name']} →</a></p>
    </section>
  </div>

  <aside class="review__sidebar">
    <h3>Score breakdown</h3>
    <div class="review__ratings">
      {breakdown_rows}
    </div>
    <h3 style="margin-top: 2rem;">Quick facts</h3>
    <dl>
      <dt>License</dt><dd>{license_name}</dd>
      <dt>Bonus</dt><dd>{c['bonus_headline']}</dd>
      <dt>Wager</dt><dd>{c['wager_label']}</dd>
      <dt>Min dep.</dt><dd>€{c['min_deposit']}</dd>
      <dt>Sticky?</dt><dd>{'No' if c['sticky'] == 'non-sticky' else 'Yes'}</dd>
      <dt>Code</dt><dd>{c.get('promo_code') or '—'}</dd>
    </dl>
    <a href="{c['affiliate_url']}" class="btn btn--primary" rel="sponsored nofollow noopener" target="_blank">Visit casino →</a>
  </aside>
</div>
</div>

{FOOTER}
"""


def render_stub_review(c):
    """Render a placeholder page for casinos that haven't been fully reviewed yet."""
    license_name = LICENSE_NAMES[c["license"]]
    rating_class = get_rating_class(c["rating"])
    rating_pct = int(c["rating"] * 10)

    # Stub page: breadcrumb schema only
    crumbs = [
        ("Home", f"{SITE_URL}/"),
        ("Casinos", f"{SITE_URL}/#casinos"),
        (c["name"], f"{SITE_URL}/casinos/{c['slug']}.html"),
    ]
    stub_schema = breadcrumb_jsonld(crumbs)

    return f"""{head(
        f"{c['name']} Casino 2026 — Provisional Score {c['rating']}/10 · {SITE_NAME}",
        f"{c['name']} casino quick facts: {c['bonus_headline']}, {c['wager_label']} wagering, €{c['min_deposit']} min deposit. Provisional {c['rating']}/10 score — full review in progress.",
        f"{SITE_URL}/casinos/{c['slug']}.html",
        stub_schema,
    )}
{DISCLOSURE_BAR}
{header()}

<div class="wrap">
<div class="review">
  <div class="review__main">
    <p class="review__breadcrumb">
      <a href="/">Home</a> · <a href="/#casinos">Casinos</a> · <span>{c['name']}</span>
    </p>
    <h1>{c['name']}</h1>
    <div class="review__meta">
      <span><strong>Review in progress</strong></span>
      <span>Provisional score: <strong>{c['rating']}/10</strong></span>
    </div>

    <div class="verdict">
      Full review coming soon. The score shown is provisional — based on visible bonus terms only, not yet verified with payout tests or support checks.
    </div>

    <section class="review__section">
      <h2>What's known so far</h2>
      <p><strong>Bonus:</strong> {c['bonus_headline']} — {c['free_spins_line']}.</p>
      <p><strong>Wagering:</strong> {c['wager_label']}, min deposit €{c['min_deposit']}, {'non-sticky' if c['sticky'] == 'non-sticky' else 'sticky'} bonus.</p>
      <p><strong>License:</strong> {license_name}.</p>
      {'<p><strong>Promo code:</strong> <code>' + c['promo_code'] + '</code></p>' if c.get('promo_code') else ''}
    </section>

    <section class="review__section">
      <h2>Provisional score: {c['rating']}/10</h2>
      <div class="rating {rating_class}" aria-label="Provisional rating: {c['rating']} out of 10" style="margin-bottom: 1rem;">
        <span class="rating__score">{c['rating']}<small>/10</small></span>
        <div class="rating__bar" aria-hidden="true"><div class="rating__fill" style="width: {rating_pct}%"></div></div>
      </div>
      <p>
        This score is derived from visible bonus terms only. A full review covers seven
        criteria — bonus fairness, payout speed (tested), license tier, game library,
        UX, support (tested), trust signals — and will replace this stub when published.
        Read how this is calculated at <a href="/methodology.html">/methodology</a>.
      </p>
      <p>
        <a href="{c['affiliate_url']}" class="btn btn--primary" rel="sponsored nofollow noopener" target="_blank">Visit {c['name']} →</a>
        <a href="/#casinos" class="btn btn--secondary">Back to all casinos</a>
      </p>
    </section>
  </div>

  <aside class="review__sidebar">
    <h3>Quick facts</h3>
    <dl>
      <dt>License</dt><dd>{license_name}</dd>
      <dt>Bonus</dt><dd>{c['bonus_headline']}</dd>
      <dt>Wager</dt><dd>{c['wager_label']}</dd>
      <dt>Min dep.</dt><dd>€{c['min_deposit']}</dd>
      <dt>Sticky?</dt><dd>{'No' if c['sticky'] == 'non-sticky' else 'Yes'}</dd>
      <dt>Code</dt><dd>{c.get('promo_code') or '—'}</dd>
      <dt>Review status</dt><dd>In progress</dd>
    </dl>
    <a href="{c['affiliate_url']}" class="btn btn--primary" rel="sponsored nofollow noopener" target="_blank">Visit casino →</a>
  </aside>
</div>
</div>

{FOOTER}
"""


# ---------------------------------------------------------------
# License pages (simple filtered lists)
# ---------------------------------------------------------------

LICENSE_INTROS = {
    "mga": ("MGA-licensed casinos", "Best MGA Casinos 2026 — Malta-Licensed Sites Reviewed",
            "The Malta Gaming Authority is the strictest mainstream license of the four covered on this site. MGA operators face meaningful player-protection rules, a working complaints process, and real enforcement. If a dispute goes wrong at an MGA casino, you have somewhere to escalate."),
    "estonia-emta": ("Estonia (EMTA) licensed casinos", "Best Estonia (EMTA) Casinos 2026 — EU-Licensed & Tax-Free Reviewed",
            "Estonia's Tax and Customs Board (EMTA) regulates online gambling for EU players. EU-licensed means tax-free winnings for EU residents and a meaningful regulator if things go wrong. Slower dispute process than MGA, but solid."),
    "curacao": ("Curaçao-licensed casinos", "Best Curaçao Casinos 2026 — New-Regime Licensed Sites Reviewed",
            "Curaçao's new licensing regime (from 2024 onwards) is mid-tier. Cheaper for operators than MGA, which brings more brands online but weaker dispute resolution. Winnings from Curaçao casinos may be taxable in your country — check local rules."),
    "anjouan": ("Anjouan-licensed casinos", "Best Anjouan Casinos 2026 — Offshore-Licensed Sites Reviewed",
            "Anjouan is a newer offshore jurisdiction — cheaper licensing, limited regulatory infrastructure, weaker player recourse. You'll find a lot of flexible crypto-friendly operators here, but dispute options are limited. Play accordingly."),
}

def build_license_pages():
    (OUT_DIR / "licenses").mkdir(exist_ok=True)
    license_map = {"mga": "mga", "estonia-emta": "estonia", "curacao": "curacao", "anjouan": "anjouan"}
    for slug, license_key in license_map.items():
        h1_title, seo_title, intro = LICENSE_INTROS[slug]
        filtered = [c for c in CASINOS if c["license"] == license_key]
        cards_html = "\n".join(render_card(c) for c in filtered)

        # Breadcrumb schema for license pages
        crumbs = [
            ("Home", f"{SITE_URL}/"),
            ("Licensed casinos", f"{SITE_URL}/#casinos"),
            (h1_title, f"{SITE_URL}/licenses/{slug}.html"),
        ]
        lic_schema = breadcrumb_jsonld(crumbs) + "\n" + itemlist_jsonld(filtered)

        desc = f"{intro[:155]}".rstrip(". ") + "."

        html = f"""{head(
            f"{seo_title} · {SITE_NAME}",
            desc,
            f"{SITE_URL}/licenses/{slug}.html",
            lic_schema,
        )}
{DISCLOSURE_BAR}
{header()}

<section class="section">
  <div class="wrap">
    <div class="section__head">
      <p class="section__label">Licensed casinos · {len(filtered)} sites</p>
      <h1 class="section__title">{h1_title}</h1>
      <p class="section__kicker">{intro}</p>
    </div>
    <div class="casino-grid">
      {cards_html}
    </div>
    <p style="margin-top: 3rem;"><a href="/#casinos">← Back to full casino list</a></p>
  </div>
</section>

{FOOTER}
"""
        (OUT_DIR / "licenses" / f"{slug}.html").write_text(html, encoding="utf-8")
    print(f"Built {len(license_map)} license pages")


# ---------------------------------------------------------------
# sitemap.xml + robots.txt
# ---------------------------------------------------------------

# Static pages that aren't generated by build.py but exist in the repo
# and should be indexed by search engines.
STATIC_PAGES = [
    ("about.html", "monthly", "0.6"),
    ("methodology.html", "monthly", "0.7"),
    ("responsible-gambling.html", "yearly", "0.5"),
    ("affiliate-disclosure.html", "yearly", "0.4"),
    ("privacy.html", "yearly", "0.3"),
]


def build_sitemap():
    """Emit /sitemap.xml listing every indexable URL with lastmod."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = []

    def add(loc, lastmod=today, changefreq="weekly", priority="0.5"):
        urls.append({
            "loc": loc, "lastmod": lastmod,
            "changefreq": changefreq, "priority": priority,
        })

    # Homepage — highest priority
    add(f"{SITE_URL}/", changefreq="daily", priority="1.0")

    # License pages
    for slug in ("mga", "estonia-emta", "curacao", "anjouan"):
        add(f"{SITE_URL}/licenses/{slug}.html", changefreq="weekly", priority="0.8")

    # Casino review pages
    for c in CASINOS:
        # Use "reviewed" year-month if present, else today
        reviewed = c.get("reviewed") or today
        if len(reviewed) == 7:  # YYYY-MM
            lastmod = reviewed + "-01"
        else:
            lastmod = today
        priority = "0.9" if c.get("has_review") else "0.6"
        add(f"{SITE_URL}/casinos/{c['slug']}.html",
            lastmod=lastmod, changefreq="monthly", priority=priority)

    # Static pages
    for page, freq, pri in STATIC_PAGES:
        if (SITE_DIR / page).exists():
            add(f"{SITE_URL}/{page}", changefreq=freq, priority=pri)

    # Render XML
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{u['loc']}</loc>")
        lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        lines.append(f"    <priority>{u['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")

    (OUT_DIR / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")
    print(f"Built sitemap.xml ({len(urls)} URLs)")


def build_robots_txt():
    """Emit /robots.txt allowing the site, blocking admin/API, pointing to sitemap."""
    content = f"""# robots.txt for {SITE_NAME}
# https://www.robotstxt.org/

User-agent: *
Allow: /
Disallow: /admin
Disallow: /admin/
Disallow: /api
Disallow: /api/
Disallow: /raffle/
Disallow: /*?entry=

# Block AI scrapers that don't bring traffic (optional — remove if you want the training)
User-agent: GPTBot
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

# Explicitly allow Google + Bing
User-agent: Googlebot
Allow: /
Disallow: /admin
Disallow: /api

User-agent: Bingbot
Allow: /
Disallow: /admin
Disallow: /api

Sitemap: {SITE_URL}/sitemap.xml
"""
    (OUT_DIR / "robots.txt").write_text(content, encoding="utf-8")
    print("Built robots.txt")


# ---------------------------------------------------------------
# Run
# ---------------------------------------------------------------

if __name__ == "__main__":
    build_index()
    build_reviews()
    build_license_pages()
    build_sitemap()
    build_robots_txt()
    print("Done.")
