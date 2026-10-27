"""Generate and validate a static Japanese site before replacing the last good output."""
import html
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .core import GuideError, active_occurrences, atomic_json, read_json, safe_url, serialized
from .normalize import identifier
from .page_places import qualified_places, sustained_listing
from .validation import inspect_text, publishable, validate_data, validate_config
from .travel_guides import reviewed_guides, travel_filename, guide_card, guide_body, search_eligible
from .nearby_guides import NEARBY_IMAGES, reviewed_nearby, nearby_cards, nearby_page_body, nearby_preview_cards
from .official_event_hub import official_event_links, event_finder_body
from .curated_events import public_curated_events, curated_event_cards


PHOTO_ASSETS = ("harima-hero-photo.webp", "awaji-photo.webp", *(image[0] for image in NEARBY_IMAGES.values()))
PHOTO_ASSET_ROOT = Path(__file__).resolve().parent / "assets"


def valid_webp(data):
    return (20 <= len(data) <= 2_000_000 and data[:4] == b"RIFF"
            and data[8:12] == b"WEBP"
            and int.from_bytes(data[4:8], "little") + 8 == len(data))


def load_photo_asset(filename):
    if filename not in PHOTO_ASSETS:
        raise GuideError("未登録の写真素材です")
    path = PHOTO_ASSET_ROOT / filename
    if path.is_symlink() or not path.is_file():
        raise GuideError("画像素材が見つからないか、不正なパスです")
    data = path.read_bytes()
    if not valid_webp(data):
        raise GuideError("写真素材のWebP形式が不正です")
    return data


STYLE = """:root {
  color-scheme: light;
  --ink: #203a34;
  --muted: #526a61;
  --bg: #f7f8f4;
  --paper: #ffffff;
  --brand: #096858;
  --border: #dce7df;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--ink); font: 16px/1.75 system-ui, -apple-system, "Noto Sans JP", sans-serif; }
a { color: var(--brand); text-underline-offset: .2em; }
a:hover { text-decoration-thickness: .13em; }
a:focus-visible, summary:focus-visible { outline: 3px solid #a35f0b; outline-offset: 4px; }
.skip-link { position: absolute; top: -6rem; left: 1rem; z-index: 20; padding: .6rem 1rem; background: var(--paper); }
.skip-link:focus { top: .6rem; }
.site-header { background: linear-gradient(110deg, #e9f3ec, #fff9ec); border-bottom: 1px solid var(--border); }
.site-header__inner, main, .site-footer__inner { max-width: 1040px; margin: 0 auto; padding: 1.5rem clamp(1rem, 4vw, 2.5rem); }
.brand { display: inline-block; color: var(--ink); font-size: clamp(1.4rem, 4vw, 1.9rem); font-weight: 800; letter-spacing: .02em; text-decoration: none; }
.brand:hover { text-decoration: underline; }
.tagline { margin: .2rem 0 1rem; color: var(--muted); font-size: .96rem; }
nav { display: flex; flex-wrap: wrap; gap: .5rem; }
nav a { display: inline-flex; padding: .35rem .8rem; border: 1px solid #c9ded1; border-radius: 999px; background: #fffdf9; font-weight: 650; text-decoration: none; }
nav a:hover { background: #f0f9f3; }
main { padding-top: 2rem; padding-bottom: 3rem; }
h1 { margin: 0 0 1.3rem; font-size: clamp(1.7rem, 4.8vw, 2.45rem); line-height: 1.45; letter-spacing: .01em; }
h2 { margin: 1.7rem 0 .7rem; font-size: 1.3rem; line-height: 1.5; }
h3 { margin: .2rem 0 .6rem; font-size: 1.12rem; line-height: 1.5; }
p { margin: .65rem 0; }
.intro { padding: clamp(1rem, 3vw, 1.6rem); margin-bottom: 1.6rem; background: #eaf3ee; border: 1px solid #d6e9df; border-radius: 18px; }
.intro p { max-width: 68ch; }
.eyebrow { margin: 0; color: #2c6855; font-size: .88rem; font-weight: 800; letter-spacing: .08em; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); gap: 1rem; align-items: start; }
.card, .notice { background: var(--paper); border: 1px solid var(--border); border-radius: 16px; padding: clamp(1rem, 2.5vw, 1.45rem); margin: .65rem 0; box-shadow: 0 2px 10px rgb(16 54 39 / 4%); }
.card h2, .card h3 { margin-top: 0; }
.card dl { display: grid; grid-template-columns: minmax(5em, 7em) 1fr; column-gap: .6rem; row-gap: .25rem; margin: .8rem 0; }
.card dt { font-weight: 750; }
.card dd { min-width: 0; margin: 0; overflow-wrap: anywhere; }
.notice { border-left: 4px solid #80a994; }
.notice h2 { margin-top: 0; }
.muted, .source-credit { color: var(--muted); font-size: .88rem; }
.source-credit { border-top: 1px solid var(--border); margin-top: 1rem; padding-top: .7rem; }
.source-details { margin-top: .6rem; font-size: .88rem; }
.source-details summary { color: var(--brand); cursor: pointer; font-weight: 700; }
.source-details ul { padding-left: 1.15rem; overflow-wrap: anywhere; }
.source-details li + li { margin-top: .65rem; }
.ad-notice { font-weight: 800; padding: .45rem .75rem; margin: .65rem 0; background: #fff9e8; border: 1px solid #dfc995; border-radius: 8px; }
.travel-booking-reference { margin: 1.1rem 0; padding: .65rem; overflow-wrap: anywhere; border: 1px solid var(--border); border-radius: 8px; }
.tag { display: inline-block; padding: .1rem .55rem; background: #edf4e9; border-radius: 999px; color: #315642; font-size: .85rem; }
ul { padding-left: 1.3rem; }
.site-footer { border-top: 1px solid var(--border); background: #eef2ec; color: var(--muted); font-size: .88rem; }
.site-footer__inner { padding-top: 1.15rem; padding-bottom: 1.15rem; }
.about-main { max-width: 880px; }
@media (max-width: 600px) {
  main { padding-top: 1.5rem; }
  nav a { font-size: .94rem; }
  .card dl { grid-template-columns: 1fr; row-gap: 0; }
  .card dd { margin-bottom: .45rem; }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }

/* Original illustration-led homepage; SVG artwork is generated locally. */
.home-main { max-width: 1160px; padding-top: 1.3rem; }
.home-hero { display: grid; grid-template-columns: minmax(0,1.08fr) minmax(0,.92fr); align-items: stretch; margin: 0 0 2.35rem; background: #e9f2e9; border: 1px solid #d3e3d4; border-radius: 28px; overflow: hidden; box-shadow: 0 14px 42px rgb(22 62 43 / 8%); }
.home-hero__copy { padding: clamp(1.45rem,4.2vw,3.45rem); align-self: center; }
.home-hero__copy h1 { margin: .65rem 0 1rem; font-size: clamp(2rem,3.2vw,3.05rem); line-height: 1.28; letter-spacing: .025em; }
.home-hero__copy p:not(.eyebrow) { max-width: 36rem; }
.home-hero__scene { min-height: 370px; background: #d9efe9 url("harima-hero.svg") center center / cover no-repeat; }
.home-hero__actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1.5rem; }
.action-link { display: inline-flex; align-items: center; justify-content: center; min-height: 46px; gap: .45rem; padding: .6rem 1.1rem; border-radius: 999px; font-size: .94rem; font-weight: 800; text-decoration: none; transition: transform .15s ease, background-color .15s ease; }
.action-link--primary { background: #106c5a; color: #fff; box-shadow: 0 4px 11px rgb(4 73 54 / 14%); }
.action-link--primary:hover { color: #fff; background: #095745; transform: translateY(-1px); }
.action-link--secondary { background: #fffefb; border: 1px solid #b6d2c1; color: #125b4c; }
.action-link--secondary:hover { background: #f3fcf5; transform: translateY(-1px); }
.section-kicker { display: block; margin: 0 0 .2rem; color: #516e58; font-size: .81rem; font-weight: 850; letter-spacing: .13em; }
.home-section { margin: 2.2rem 0 3.2rem; }
.home-section__heading { display: flex; align-items: end; justify-content: space-between; flex-wrap: wrap; gap: .5rem 1rem; margin-bottom: 1.05rem; }
.home-section__heading h2 { margin: 0; font-size: clamp(1.4rem,3.5vw,1.85rem); }
.home-section__heading p { margin: .2rem 0 0; color: var(--muted); }
.home-section__more { font-weight: 800; white-space: nowrap; }
.browse-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 1rem; }
.browse-card { display: grid; grid-template-columns: auto 1fr; gap: .8rem; align-items: start; min-height: 119px; padding: 1.25rem; border: 1px solid var(--border); border-radius: 18px; background: #fff; text-decoration: none; color: var(--ink); box-shadow: 0 3px 18px rgb(18 50 35 / 4%); }
.browse-card:hover { background: #eff8f1; }
.browse-card strong { display: block; font-size: 1.08rem; line-height: 1.4; }
.browse-card small { display: block; margin-top: .25rem; color: var(--muted); line-height: 1.5; font-size: .84rem; }
.browse-card__icon { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 13px; background: #e5f1e7; font-size: 1.38rem; }
.browse-card--trip .browse-card__icon { background: #f9edce; }
.browse-card--pending { background: #f0f2ef; border-style: dashed; color: #64756e; }
.browse-card--pending .browse-card__icon { background: #e1e5e2; }
.browse-card--pending:hover { background: #f0f2ef; }
.home-trip-cards { grid-template-columns: repeat(auto-fit,minmax(min(100%,320px),1fr)); }
.trip-card { padding: 0; overflow: hidden; border: 1px solid var(--border); }
.trip-card__visual { height: 206px; background: linear-gradient(115deg,#d9ece8 5%,#e3e9d1 70%,#f1ddab); }
.trip-card__visual--awaji { background: #d3ece9 url("awaji-card.svg") center center / cover no-repeat; }
.trip-card__content { padding: 1.2rem 1.35rem 1.35rem; }
.trip-card__content h3 { margin: .75rem 0; font-size: clamp(1.16rem,2.5vw,1.38rem); }
.trip-card__content h3 a { text-decoration-thickness: 1px; }
.trip-card__content p { line-height: 1.66; }
.trip-card__foot { display: inline-block; margin-top: .65rem; color: #096858; font-size: .92rem; font-weight: 800; }
.place-card { position: relative; border-top: 5px solid #8db5a5; }
.place-card__category { margin: 0 0 .45rem; color: #48745c; font-size: .82rem; font-weight: 800; }
.place-card__heading { line-height: 1.45; }
.place-card__primary-link { font-weight: 800; }
.home-status { padding: 1.3rem 1.6rem; border-left: 4px solid #b9a66a; background: #fff9e9; border-radius: 15px; }
.home-status h2 { margin-top: 0; }
.home-trust { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 1rem; margin: 2.8rem 0 1rem; }
.home-trust__item { padding: 1.1rem 1.25rem; border: 1px solid #dce8df; border-radius: 15px; background: #f2f7f1; }
.home-trust__item strong { display: block; font-size: 1.02rem; margin-bottom: .3rem; }
.home-trust__item p { margin: 0; font-size: .9rem; color: var(--muted); }
.article-cover { height: clamp(190px,31vw,360px); margin-bottom: 1.45rem; border-radius: 19px; background: linear-gradient(100deg,#d3ece9,#f4e2ae); }
.article-cover--awaji { background: #d3ece9 url("awaji-card.svg") center center / cover no-repeat; }
.travel-booking-reference a { display: block; padding: .9rem 1rem; border-radius: 10px; border: 1px solid #a5d3c2; background: #e9f7ef; color: #075d49; font-weight: 800; overflow-wrap: anywhere; }
.travel-booking-reference a:hover { background: #d9f1e4; }
@media (max-width: 850px) {
  .home-hero { grid-template-columns: minmax(0,1fr); }
  .home-hero__scene { min-height: 260px; max-height: 380px; }
  .browse-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .home-trust { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .home-main { padding-top: .8rem; }
  .home-hero { border-radius: 20px; }
  .home-hero__copy { padding: 1.5rem; }
  .home-hero__copy h1 { font-size: clamp(1.95rem,8vw,2.55rem); }
  .home-hero__scene { min-height: 215px; }
  .home-hero__actions { display: grid; }
  .action-link { width: 100%; }
  .browse-grid { grid-template-columns: minmax(0,1fr); gap: .7rem; }
  .browse-card { min-height: unset; padding: 1rem; }
  .home-section { margin: 2rem 0 2.4rem; }
  .trip-card__visual { height: 190px; }
}
@media (prefers-reduced-motion: reduce) { .action-link { transition: none; } }

.site-header--compact .site-header__inner { padding-top: .72rem; padding-bottom: .72rem; }
.site-header--compact nav { justify-content: flex-end; }
@media (max-width: 600px) { .site-header--compact nav { justify-content: center; } }
.travel-booking-reference--picttext { max-width: 100%; overflow-x: auto; }
.travel-booking-reference--picttext a,
.travel-booking-reference--picttext a:hover {
  display: inline; padding: 0; border: 0; border-radius: 0;
  background: none; color: var(--brand); font-size: inherit; font-weight: inherit;
}
.travel-booking-reference--picttext img { max-width: 100%; height: auto; }
.trip-card__visual--sanin {
  background: radial-gradient(ellipse 90% 35% at 15% 115%, #e9d2a2 0 98%, transparent 100%),
              radial-gradient(ellipse 85% 40% at 76% 110%, #c19762 0 98%, transparent 100%),
              linear-gradient(180deg, #8eb8cd 0%, #bed8d0 49%, #d9c19b 65%, #b89363 100%);
}
.article-cover--sanin {
  background-color: #b39061;
  background-image: linear-gradient(0deg, rgb(14 37 41 / 76%), rgb(21 52 55 / 16%) 80%),
                    radial-gradient(ellipse 90% 33% at 12% 112%, #e9d2a2 0 98%, transparent 100%),
                    radial-gradient(ellipse 86% 40% at 80% 107%, #c19762 0 98%, transparent 100%),
                    linear-gradient(180deg, #83b4cb 0%, #c6d7c6 50%, #dec399 67%, #b58a57 100%);
}

/* Text-free illustrative photos + semantic HTML/CSS heading overlays. */
.home-hero {
  position: relative;
  isolation: isolate;
  display: block;
  min-height: clamp(300px, 28vw, 355px);
  background-color: #315a62;
  background-image: linear-gradient(100deg, rgb(5 32 37 / 88%) 0%, rgb(4 35 37 / 67%) 42%, rgb(5 33 40 / 10%) 100%), url("harima-hero-photo.webp");
  background-position: center, center 55%;
  background-size: cover, cover;
  background-repeat: no-repeat;
  color: #fff;
}
.home-hero__copy {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  max-width: 850px;
  min-height: inherit;
  padding: clamp(1.2rem, 2.6vw, 2.2rem);
}
.home-hero__copy h1 {
  margin: .22rem 0 .15rem;
  font-size: clamp(2.25rem, 5vw, 3.8rem);
  line-height: 1.18;
  letter-spacing: .045em;
  color: #fff;
  text-shadow: 0 3px 15px rgb(0 0 0 / 42%);
}
.home-hero__copy .eyebrow { color: #e8f7e7; text-shadow: 0 2px 8px #153a39; }
.home-hero__subtitle {
  margin: .3rem 0 .4rem;
  font-size: clamp(1.08rem, 2.2vw, 1.4rem);
  font-weight: 750;
  text-shadow: 0 2px 12px rgb(0 0 0 / 45%);
}
.home-hero__copy .home-hero__description {
  max-width: 40rem;
  font-size: clamp(.88rem, 1.5vw, 1rem);
  line-height: 1.55;
  text-shadow: 0 1px 6px rgb(0 0 0 / 50%);
}
.home-hero__scene { display: none; }
.home-hero__actions { margin-top: .75rem; }
.home-hero__footnote {
  position: absolute;
  z-index: 1;
  right: 20px;
  bottom: 14px;
  color: #fff;
  font-size: .73rem;
  opacity: .91;
  text-shadow: 0 1px 5px #1b3632;
}
.article-cover {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-height: clamp(215px, 23vw, 300px);
  height: auto;
  overflow: hidden;
  padding: clamp(1.2rem, 3.4vw, 2.3rem);
  color: #fff;
}
.article-cover--awaji {
  background-color: #426d73;
  background-image: linear-gradient(0deg, rgb(5 33 39 / 80%), rgb(12 47 45 / 23%) 75%, rgb(13 43 42 / 15%)), url("awaji-photo.webp");
  background-position: center, center 52%;
  background-size: cover, cover;
  background-repeat: no-repeat;
}
.article-cover h1 {
  max-width: 850px;
  margin: 0 0 .75rem;
  color: #fff;
  font-size: clamp(1.45rem, 3.2vw, 2.45rem);
  line-height: 1.4;
  text-shadow: 0 2px 13px rgb(0 0 0 / 60%);
  overflow-wrap: anywhere;
}
.article-cover__note {
  position: absolute;
  top: .4rem;
  right: 1.1rem;
  color: #fff;
  font-size: .74rem;
  text-shadow: 0 1px 5px #234;
}
.trip-card__visual--awaji { background: #d3ece9 url("awaji-photo.webp") center 55% / cover no-repeat; }
@media (max-width: 600px) {
  .home-hero {
    min-height: 360px;
    background-image: linear-gradient(0deg, rgb(3 31 35 / 84%), rgb(5 35 40 / 32%) 85%), url("harima-hero-photo.webp");
    background-position: 59% center;
  }
  .home-hero__copy {
    justify-content: flex-end;
    min-height: 360px;
    padding: 1.15rem 1.25rem 2.35rem;
  }
  .home-hero__copy h1 { font-size: clamp(1.9rem, 8vw, 2.55rem); }
  .home-hero__subtitle { font-size: 1.08rem; }
  .home-hero__actions { width: 100%; gap: .5rem; margin-top: .65rem; }
  .home-hero__footnote { right: 1.4rem; bottom: .75rem; }
  .article-cover { min-height: 255px; padding: 1.25rem 1.1rem; }
  .article-cover h1 { font-size: clamp(1.45rem, 6vw, 1.9rem); }
}
@media (max-width: 360px) {
  .home-hero__copy h1 { font-size: 1.8rem; }
}


/* Editorial layout refinement: visual navigation, trip cards, and route readability. */
:root { --soft-green: #eaf3eb; --deep-green: #155c4d; --warm-paper: #fbfaf6; }
body { background: #f7f8f5; }
.site-header__inner {
  max-width: 1160px; display: flex; align-items: center; justify-content: space-between;
  gap: 1rem 2rem; padding-top: .9rem; padding-bottom: .9rem;
}
.header-identity { min-width: 0; display: grid; gap: .05rem; }
.header-identity .brand { font-size: clamp(1.22rem, 2.2vw, 1.65rem); line-height: 1.3; }
.header-identity .tagline { margin: 0; font-size: .78rem; line-height: 1.5; }
.site-header nav { justify-content: flex-end; flex-shrink: 0; }
.site-header nav a { min-height: 44px; align-items: center; padding: .45rem .92rem; }
.site-header nav a[aria-current="page"] { background: #116e5b; color: #fff; border-color: #116e5b; }
.site-header nav a:hover { background: #e0f0e8; color: #0a594a; }
.site-header nav a[aria-current="page"]:hover { background: #0c5e4d; color: #fff; }
.site-header--compact .site-header__inner {
  min-height: 66px; padding-block: .6rem; justify-content: flex-end;
}
.site-footer__inner { max-width: 1160px; }
.site-footer__top {
  display: flex; gap: 1rem 2rem; align-items: center;
  justify-content: space-between; margin-bottom: 1rem;
}
.site-footer__brand { font-size: 1.12rem; font-weight: 850; color: var(--ink); text-decoration: none; }
.site-footer nav { display: flex; flex-wrap: wrap; gap: .55rem 1.25rem; }
.site-footer nav a { color: #23685b; font-size: .85rem; font-weight: 700; text-decoration: none; }
.site-footer nav a:hover { text-decoration: underline; }
.home-main, .listing-main { max-width: 1160px; }
.home-main { padding-bottom: 2.2rem; }
.home-section__all { text-align: center; margin-top: 1rem; }
.home-section__all a {
  display: inline-flex; align-items: center; justify-content: center; min-height: 44px;
  padding: .55rem 1.25rem; border-radius: 999px; border: 1px solid #b7d1c3;
  background: #fff; font-weight: 800; text-decoration: none;
}
.home-section__all a:hover { background: #eaf6ee; }
.home-trip-cards, .trip-list-grid { align-items: stretch; gap: 1.25rem; }
.trip-list-grid { grid-template-columns: repeat(auto-fit, minmax(min(100%, 335px), 1fr)); }
.trip-card {
  position: relative; margin: 0; overflow: hidden;
  background: #fff; border: 1px solid #d9e8df;
  box-shadow: 0 7px 22px rgb(20 60 47 / 6%);
  transition: transform .2s ease, box-shadow .2s ease;
}
.trip-card:hover, .trip-card:focus-within {
  transform: translateY(-3px); box-shadow: 0 14px 32px rgb(20 60 47 / 12%);
}
.trip-card__link {
  display: flex; flex-direction: column; height: 100%; color: var(--ink);
  text-decoration: none;
}
.trip-card__link:focus-visible { outline: 3px solid #a35f0b; outline-offset: -4px; }
.trip-card__visual { height: clamp(175px, 21vw, 236px); width: 100%; flex: none; }
.trip-card__content { display: flex; flex-direction: column; flex: 1; gap: .28rem; padding: 1.3rem 1.45rem 1.4rem; }
.trip-card__content .tag { align-self: flex-start; }
.trip-card__content h3 { margin: .65rem 0 .25rem; font-size: clamp(1.12rem, 1.9vw, 1.38rem); line-height: 1.55; color: #145e50; }
.trip-card__content p { margin: .15rem 0; line-height: 1.75; }
.trip-card__content .muted { font-size: .85rem; }
.trip-card__foot {
  display: flex; align-items: center; align-self: flex-start; min-height: 44px;
  margin-top: auto; padding-top: .6rem; font-weight: 850; font-size: .94rem;
  color: #086c58; text-decoration: underline; text-underline-offset: .2em;
}
.trip-card:hover .trip-card__foot { color: #034d3c; }
.listing-main > h1 { margin: .45rem 0 .9rem; font-size: clamp(1.7rem, 4vw, 2.6rem); }
.listing-lead {
  padding: clamp(1.25rem, 3vw, 2rem);
  margin: 0 0 1.5rem; border: 1px solid #d8e8de;
  border-radius: 20px; background: linear-gradient(115deg, #e6f2e9, #fdf8ed);
}
.listing-lead > p { max-width: 68ch; margin: .55rem 0; }
.listing-lead__notes { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: 1rem; }
.listing-lead__notes span {
  display: inline-flex; align-items: center; background: #fff;
  border: 1px solid #d7e6dd; border-radius: 999px; padding: .35rem .8rem;
  font-size: .85rem; font-weight: 750;
}
.listing-lead .listing-lead__disclaimer { font-size: .85rem; color: #486b60; margin-top: .85rem; }
.place-grid { grid-template-columns: repeat(auto-fit, minmax(min(100%, 265px), 1fr)); align-items: stretch; gap: 1rem; }
.listing-main .place-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.place-card {
  display: flex; flex-direction: column; margin: 0;
  border: 1px solid #dae8df; border-top: 4px solid #88b6a4;
  padding: 1.35rem; min-width: 0;
}
.place-card__area {
  width: fit-content; padding: .2rem .65rem; margin: 0 0 .75rem;
  color: #276752; background: #edf6ea; border-radius: 999px;
  font-size: .81rem; font-weight: 800;
}
.place-card h3 { font-size: 1.14rem; line-height: 1.55; margin: 0 0 .7rem; }
.place-card__address { margin: 0 0 .35rem; font-size: .92rem; }
.place-card__price { margin: 0 0 .8rem; font-size: .9rem; font-weight: 650; color: #3d5c52; }
.place-card__official {
  display: inline-flex; width: fit-content; align-items: center; min-height: 44px;
  gap: .25rem; padding: .42rem .9rem; border-radius: 10px;
  border: 1px solid #b5d9c6; background: #e9f6ed;
  font-size: .88rem; font-weight: 800; text-decoration: none;
}
.place-card__official:hover { background: #d9f0e3; }
.place-card .source-credit { margin-top: auto; font-size: .8rem; }
.place-card .source-details { font-size: .84rem; }
.article-main { max-width: 1040px; padding-top: 1.2rem; padding-bottom: 3.5rem; }
.breadcrumbs {
  display: flex; align-items: center; flex-wrap: wrap; gap: .4rem .65rem;
  margin: .1rem 0 1.2rem; font-size: .87rem; font-weight: 700; color: #506e62;
}
.breadcrumbs a { color: #1b7660; text-decoration: none; }
.breadcrumbs a:hover { text-decoration: underline; }
.article-main .article-cover { margin-bottom: 2rem; box-shadow: 0 12px 32px rgb(22 62 43 / 9%); }
.article-main > .intro, .article-main > .notice, .article-main > h2,
.article-main > p, .article-main > .article-jump, .article-main > .route-day,
.article-main > .article-back { max-width: 890px; margin-left: auto; margin-right: auto; }
.article-main > .intro { padding: clamp(1.1rem, 3vw, 1.85rem); background: #eff6ef; margin-bottom: 1.6rem; }
.article-main > h2 { margin-top: 2.1rem; font-size: clamp(1.35rem, 2.9vw, 1.75rem); }
.article-main > .notice { margin-top: 1.5rem; margin-bottom: 1.5rem; }
.article-jump {
  display: flex; flex-wrap: wrap; gap: .7rem; margin: 1.25rem auto 1.7rem;
}
.article-jump a {
  display: inline-flex; align-items: center; justify-content: center;
  min-height: 46px; min-width: 140px; padding: .5rem 1.15rem;
  border: 1px solid #b9daca; border-radius: 11px;
  background: #fff; font-weight: 800; text-decoration: none;
}
.article-jump a:hover { background: #e9f5ee; }
.route-day { margin-top: 2.1rem; margin-bottom: 2.65rem; scroll-margin-top: 1.2rem; }
.route-day__heading { display: flex; flex-wrap: wrap; gap: .4rem 1rem; align-items: center; margin-bottom: 1.1rem; }
.route-day__heading h2 { margin: 0; font-size: clamp(1.22rem, 2.7vw, 1.55rem); }
.route-day__badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: .32rem .7rem; border-radius: 8px;
  background: #125e50; color: white; font-weight: 850;
  font-size: .86rem; letter-spacing: .08em; white-space: nowrap;
}
.route-steps { display: grid; gap: 1rem; margin-left: 16px; padding-left: 23px; border-left: 2px solid #b9d9c7; }
.route-step { position: relative; min-width: 0; padding: 1.2rem 1.4rem; border: 1px solid #dce9df; background: #fff; border-radius: 16px; box-shadow: 0 4px 16px rgb(20 60 47 / 5%); }
.route-step__pin {
  position: absolute; top: 1.15rem; left: -40px; display: grid; place-items: center;
  width: 32px; height: 32px; border-radius: 50%; background: #0e705c;
  color: #fff; font-weight: 850; font-size: .88rem; border: 3px solid #f7f8f5;
}
.route-step h3 { margin: 0 0 .45rem; font-size: 1.13rem; }
.route-step p { margin: .4rem 0 .75rem; }
.route-step__official { display: inline-flex; align-items: center; min-height: 44px; font-size: .91rem; font-weight: 800; }
.article-back { margin-top: 2.2rem; font-weight: 800; }
.article-back a { display: inline-flex; min-height: 44px; align-items: center; }
@media (max-width: 720px) {
  .site-header__inner { flex-direction: column; align-items: stretch; gap: .7rem; }
  .site-header nav { justify-content: flex-start; }
  .site-header--compact .site-header__inner { flex-direction: row; justify-content: center; }
  .site-header--compact nav { justify-content: center; flex-shrink: 1; min-width: 0; }
  .site-header nav a { font-size: .91rem; }
  .site-footer__top { align-items: flex-start; flex-direction: column; }
  .home-trip-cards, .trip-list-grid { grid-template-columns: minmax(0,1fr); }
}
@media (max-width: 600px) {
  .header-identity .tagline { font-size: .73rem; }
  .listing-main > h1 { margin-top: .1rem; }
  .trip-card__visual { height: 205px; }
  .trip-card__content { padding: 1.15rem 1.2rem 1.3rem; }
  .home-section__heading { align-items: flex-start; }
  .place-grid, .place-grid--home { grid-template-columns: minmax(0,1fr); }
  .listing-main .place-grid { grid-template-columns: minmax(0,1fr); }
  .place-card { padding: 1.15rem; }
  .article-main { padding-top: 1rem; }
  .article-main .article-cover { min-height: 270px; margin-bottom: 1.4rem; }
  .article-jump a { flex: 1; min-width: 128px; }
  .route-day__heading { align-items: flex-start; flex-direction: column; }
  .route-step { padding: 1.05rem 1.05rem 1.1rem; }
  .route-step h3 { font-size: 1.04rem; }
}
@media (max-width: 360px) {
  .site-header nav { gap: .25rem; }
  .site-header nav a { padding: .4rem .65rem; font-size: .86rem; }
  .route-step { padding: .9rem; }
}
@media (prefers-reduced-motion: reduce) {
  .trip-card { transition: none; }
  .trip-card:hover, .trip-card:focus-within { transform: none; }
}

/* Keep image attribution clear of CTA buttons at tablet widths. */
@media (min-width: 601px) and (max-width: 1024px) {
  .home-hero { min-height: 340px; }
}


/* Travel stories first: fewer repeated choices, faster reading on mobile. */
.home-main .home-hero { margin-bottom: 1.25rem; }
.home-main .home-section { margin-top: 1.55rem; margin-bottom: 2.45rem; }
.home-main #family-trip { margin-top: .85rem; }
.home-main #family-trip .home-section__heading { margin-bottom: .9rem; }
.home-main #family-trip .home-section__heading p { max-width: 44rem; font-size: .93rem; }
.trip-card__visual { position: relative; isolation: isolate; overflow: hidden; }
.trip-card__visual::after {
  content: ""; position: absolute; z-index: 0; inset: 0;
  background: linear-gradient(0deg, rgb(4 31 38 / 71%) 0%, rgb(9 40 43 / 14%) 54%, transparent 100%);
  pointer-events: none;
}
.trip-card__visual-label {
  position: absolute; left: 1.2rem; bottom: 1rem; z-index: 1; color: #fff;
  font-size: clamp(1.4rem, 2.7vw, 2.05rem); font-weight: 850;
  letter-spacing: .055em; line-height: 1.3; text-shadow: 0 2px 12px rgb(0 0 0 / 50%);
}
.trip-card__visual-note {
  position: absolute; z-index: 1; right: .75rem; top: .55rem;
  color: #fff; font-size: .71rem; font-weight: 650;
  text-shadow: 0 1px 7px rgb(0 0 0 / 90%);
}
.trip-card__badges { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem .55rem; }
.trip-card__badges .tag { font-size: .76rem; }
.trip-card__kind { color: #406457; font-size: .78rem; font-weight: 800; }
.trip-card__summary { color: #314f44; }
.trip-card__notice { color: #567064; }
.trip-card__content h3 { margin-top: .48rem; }
.trip-card--compact .trip-card__content { padding: 1.05rem 1.25rem 1.12rem; }
.trip-card--compact .trip-card__summary {
  display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2;
  line-clamp: 2; overflow: hidden; line-height: 1.55; font-size: .93rem;
}
.trip-card--compact .trip-card__notice { margin-top: .3rem; font-size: .8rem; }
.trip-card--compact .trip-card__foot { margin-top: .35rem; }
@media (max-width: 720px) {
  .home-main #family-trip { margin-top: .65rem; }
  .home-trip-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; }
  .trip-card--compact .trip-card__visual { height: clamp(115px, 32vw, 150px); }
  .trip-card--compact .trip-card__visual-label { left: .7rem; bottom: .7rem; font-size: 1.12rem; }
  .trip-card--compact .trip-card__visual-note { right: .55rem; top: .4rem; font-size: .62rem; }
  .trip-card--compact .trip-card__content { padding: .82rem .85rem 1rem; gap: .15rem; }
  .trip-card--compact .trip-card__content h3 { font-size: 1rem; line-height: 1.4; margin: .35rem 0 .1rem; }
  .trip-card--compact .trip-card__badges { gap: .25rem; }
  .trip-card--compact .trip-card__badges .tag { font-size: .69rem; padding: .08rem .42rem; }
  .trip-card--compact .trip-card__kind { font-size: .71rem; }
  .trip-card--compact .trip-card__summary { font-size: .81rem; line-height: 1.48; }
  .trip-card--compact .trip-card__notice { font-size: .72rem; line-height: 1.45; }
  .trip-card--compact .trip-card__foot { min-height: 36px; font-size: .84rem; }
  .home-main .home-section { margin-bottom: 2rem; }
}
@media (max-width: 340px) {
  .home-trip-cards { grid-template-columns: minmax(0, 1fr); }
  .trip-card--compact .trip-card__visual { height: 165px; }
}
/* Evergreen local outings: compact cards, keyboard-accessible official links. */
.nearby-grid { grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); }
.nearby-card__meta { display: flex; flex-wrap: wrap; gap: .45rem; margin: 0 0 .55rem; }
.nearby-card h2 { font-size: 1.18rem; margin: 0 0 .45rem; }
.nearby-card__official { font-weight: 800; overflow-wrap: anywhere; }
.nearby-card__official:focus-visible { outline: 3px solid #a35f0b; outline-offset: 4px; }
.nearby-card { padding: 0; overflow: hidden; }
.nearby-card__body { padding: 1.2rem; }
.nearby-image { margin: 0; }
.nearby-image__img { display: block; width: 100%; height: auto; aspect-ratio: 16 / 9; object-fit: cover; background: #e8eee3; }
.nearby-image figcaption { padding: .5rem .9rem; background: #f0f3eb; color: #465849; font-size: .73rem; line-height: 1.6; }
.nearby-image--hero { margin: .5rem 0 1.5rem; border: 1px solid var(--border); border-radius: 20px; overflow: hidden; }
.nearby-image--hero .nearby-image__img { max-height: 390px; }
.nearby-image--hero figcaption { font-size: .8rem; }
.nearby-preview-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.25rem; }
.nearby-preview-card { margin: 0; padding: 0; min-width: 0; border-radius: 18px; background: #fffefa; box-shadow: 0 4px 16px rgb(32 58 52 / 4%); }
.nearby-preview-card__link { display: flex; flex-direction: column; height: 100%; color: var(--ink); text-decoration: none; border-radius: inherit; }
.nearby-preview-card__link:hover { color: var(--ink); background: #f3f7ef; }
.nearby-preview-card__link:focus-visible { outline: 3px solid #815716; outline-offset: 4px; }
.nearby-preview-card .nearby-image__img { border-radius: 17px 17px 0 0; }
.nearby-preview-card__body { display: flex; flex-direction: column; flex: 1; padding: 1.1rem 1.15rem 1.2rem; }
.nearby-preview-card h3 { margin: .45rem 0 .6rem; font-size: 1.12rem; line-height: 1.55; }
.nearby-preview-card p { margin: 0; }
.nearby-preview-card__meta { color: #526354; font-size: .77rem; line-height: 1.6; }
.nearby-preview-card__description { font-size: .9rem; line-height: 1.8; }
.nearby-preview-card__more { display: block; margin-top: auto; padding-top: 1rem; color: #276348; font-size: .85rem; font-weight: 700; }
.nearby-preview-note { margin: 1rem 0 0; color: #58685d; font-size: .82rem; }
.nearby-card[id] { scroll-margin-top: 1.5rem; }
@media (max-width: 1000px) {
  .nearby-preview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 600px) {
  .nearby-preview-grid { grid-template-columns: minmax(0, 1fr); }
  .nearby-preview-card__body { padding: 1rem; }
}
"""


# Original, self-contained artwork. No external photos or third-party assets.
HERO_SCENE = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"800\" height=\"600\" viewBox=\"0 0 800 600\">\n  <defs>\n    <linearGradient id=\"sky\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\"><stop offset=\"0\" stop-color=\"#d0ece5\"/><stop offset=\"1\" stop-color=\"#eef9e6\"/></linearGradient>\n    <linearGradient id=\"sea\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\"><stop offset=\"0\" stop-color=\"#8bccc3\"/><stop offset=\"1\" stop-color=\"#3d9f9c\"/></linearGradient>\n    <clipPath id=\"rounded\"><rect width=\"800\" height=\"600\"/></clipPath>\n  </defs>\n  <g clip-path=\"url(#rounded)\">\n    <rect width=\"800\" height=\"600\" fill=\"url(#sky)\"/>\n    <circle cx=\"628\" cy=\"131\" r=\"66\" fill=\"#f6cb83\"/>\n    <g opacity=\".64\" fill=\"#ffffff\"><ellipse cx=\"154\" cy=\"106\" rx=\"97\" ry=\"25\"/><ellipse cx=\"108\" cy=\"86\" rx=\"42\" ry=\"30\"/><ellipse cx=\"200\" cy=\"86\" rx=\"55\" ry=\"28\"/><ellipse cx=\"403\" cy=\"142\" rx=\"72\" ry=\"18\"/></g>\n    <path d=\"M0 321Q102 229 217 287T431 268T800 298V600H0Z\" fill=\"#a2cbbb\"/>\n    <path d=\"M0 366Q121 283 237 335T462 303T800 350V600H0Z\" fill=\"#6fa894\"/>\n    <path d=\"M397 360Q548 313 800 365V600H423Z\" fill=\"url(#sea)\"/>\n    <path d=\"M435 409Q590 379 800 418\" stroke=\"#c2e9df\" stroke-width=\"7\" opacity=\".58\" fill=\"none\"/>\n    <path d=\"M470 463Q610 438 800 463\" stroke=\"#c2e9df\" stroke-width=\"5\" opacity=\".4\" fill=\"none\"/>\n    <path d=\"M0 436Q179 359 325 425T800 503V600H0Z\" fill=\"#c4d7a9\"/>\n    <path d=\"M0 525Q201 445 370 505T800 550V600H0Z\" fill=\"#8fac86\"/>\n    <path d=\"M130 600Q250 483 358 473Q451 464 511 498Q566 532 603 600Z\" fill=\"#f8f2db\"/>\n    <path d=\"M208 600Q295 522 371 511Q446 503 505 544Q541 567 552 600Z\" fill=\"#d5ad75\"/>\n    <path d=\"M352 600Q371 555 405 522\" stroke=\"#fff3d7\" stroke-width=\"6\" stroke-dasharray=\"20 24\" fill=\"none\"/>\n    <g transform=\"translate(241 461)\">\n      <ellipse cx=\"120\" cy=\"95\" rx=\"147\" ry=\"22\" fill=\"#47675b\" opacity=\".22\"/>\n      <rect x=\"13\" y=\"41\" width=\"222\" height=\"59\" rx=\"19\" fill=\"#f8f8ef\" stroke=\"#28584e\" stroke-width=\"7\"/>\n      <path d=\"M59 41L90 4H168L208 41Z\" fill=\"#f8f8ef\" stroke=\"#28584e\" stroke-width=\"7\"/>\n      <path d=\"M99 13H164L188 39H80Z\" fill=\"#83beba\"/>\n      <circle cx=\"63\" cy=\"101\" r=\"23\" fill=\"#254a45\"/><circle cx=\"188\" cy=\"101\" r=\"23\" fill=\"#254a45\"/>\n      <circle cx=\"63\" cy=\"101\" r=\"10\" fill=\"#e3e8db\"/><circle cx=\"188\" cy=\"101\" r=\"10\" fill=\"#e3e8db\"/>\n      <rect x=\"20\" y=\"60\" width=\"26\" height=\"11\" rx=\"5\" fill=\"#efbf76\"/>\n    </g>\n    <g transform=\"translate(65 330)\"><path d=\"M38 117V0\" stroke=\"#476d57\" stroke-width=\"14\" stroke-linecap=\"round\"/><circle cx=\"36\" cy=\"-4\" r=\"43\" fill=\"#5b9e73\"/><circle cx=\"5\" cy=\"28\" r=\"32\" fill=\"#82b68a\"/><circle cx=\"73\" cy=\"30\" r=\"36\" fill=\"#6ba979\"/></g>\n    <g transform=\"translate(706 374)\"><path d=\"M14 77V0\" stroke=\"#476d57\" stroke-width=\"9\"/><circle cx=\"13\" cy=\"-6\" r=\"31\" fill=\"#4f9277\"/><circle cx=\"38\" cy=\"17\" r=\"22\" fill=\"#78b18c\"/></g>\n    <g fill=\"none\" stroke=\"#285e55\" stroke-width=\"5\" stroke-linecap=\"round\"><path d=\"M465 138q11 -9 22 0q10 -9 21 0\"/><path d=\"M507 169q9 -7 18 0q8 -7 18 0\"/></g>\n  </g>\n</svg>"
AWAJI_SCENE = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"880\" height=\"500\" viewBox=\"0 0 880 500\">\n  <defs><linearGradient id=\"air\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\"><stop stop-color=\"#cfe8e6\"/><stop offset=\"1\" stop-color=\"#f4e9ce\"/></linearGradient><linearGradient id=\"water\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"1\"><stop stop-color=\"#7ec4bf\"/><stop offset=\"1\" stop-color=\"#418d92\"/></linearGradient></defs>\n  <rect width=\"880\" height=\"500\" fill=\"url(#air)\"/>\n  <circle cx=\"690\" cy=\"109\" r=\"62\" fill=\"#f6cc85\"/>\n  <g fill=\"#fffefa\" opacity=\".8\"><ellipse cx=\"175\" cy=\"111\" rx=\"90\" ry=\"23\"/><ellipse cx=\"146\" cy=\"92\" rx=\"44\" ry=\"28\"/><ellipse cx=\"222\" cy=\"99\" rx=\"45\" ry=\"29\"/></g>\n  <path d=\"M0 260Q150 218 300 244T600 240T880 251V500H0Z\" fill=\"url(#water)\"/>\n  <path d=\"M0 346Q169 307 316 335T648 325T880 337\" stroke=\"#a4e2d7\" stroke-width=\"8\" fill=\"none\" opacity=\".7\"/>\n  <path d=\"M0 438Q220 408 420 438T880 432\" stroke=\"#a4e2d7\" stroke-width=\"6\" fill=\"none\" opacity=\".4\"/>\n  <path d=\"M0 340Q152 250 337 306T661 320T880 311V500H0Z\" fill=\"#8cb994\"/>\n  <path d=\"M0 401Q185 319 362 372T694 398T880 375V500H0Z\" fill=\"#75a883\"/>\n  <path d=\"M0 442Q169 391 333 429T660 451T880 424V500H0Z\" fill=\"#558a6e\"/>\n  <path d=\"M25 400Q197 349 350 406T675 438\" fill=\"none\" stroke=\"#e8d9ae\" stroke-width=\"23\"/>\n  <path d=\"M26 397Q193 346 349 403T675 435\" fill=\"none\" stroke=\"#fff1c9\" stroke-width=\"3\" stroke-dasharray=\"24 17\"/>\n  <g transform=\"translate(585 225)\"><rect x=\"0\" y=\"28\" width=\"150\" height=\"12\" rx=\"6\" fill=\"#f1ecdd\"/><path d=\"M14 27L38 -55L64 27M83 27L109 -55L136 27\" fill=\"none\" stroke=\"#f1ecdd\" stroke-width=\"7\" stroke-linecap=\"round\"/><path d=\"M38 -55L38 29M109 -55V29\" stroke=\"#f1ecdd\" stroke-width=\"4\"/></g>\n  <g transform=\"translate(162 330)\"><path d=\"M30 77V0\" stroke=\"#365c45\" stroke-width=\"10\"/><circle cx=\"30\" cy=\"0\" r=\"35\" fill=\"#f5ce91\"/><circle cx=\"5\" cy=\"17\" r=\"22\" fill=\"#f2bf78\"/><circle cx=\"58\" cy=\"19\" r=\"25\" fill=\"#fadba1\"/></g>\n  <g fill=\"#e9b4ac\" opacity=\".94\"><circle cx=\"250\" cy=\"398\" r=\"12\"/><circle cx=\"279\" cy=\"410\" r=\"10\"/><circle cx=\"310\" cy=\"423\" r=\"8\"/><circle cx=\"419\" cy=\"429\" r=\"11\"/><circle cx=\"449\" cy=\"432\" r=\"8\"/></g>\n</svg>"


# Cloudflare Pages uses docs/_headers when serving static assets. Defense in
# depth: the HTTP header blocks indexing if no individual HTML is indexable.
def cloudflare_headers(block_indexing):
    result = (
        "/*\n"
        "  X-Frame-Options: DENY\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
    )
    if block_indexing:
        result += "  X-Robots-Tag: noindex\n"
    return result


SITE_NAME = "はりまよりみち"
SITE_TAGLINE = "加古川・明石・姫路と周辺のイベント・お店・おでかけ情報"


def escaped(value):
    return html.escape(str(value), quote=True)


def event_file(event):
    return f"event-{identifier(event['event_id'])}.html"


def date_label(value):
    if value is None:
        return "不明"
    return value.replace("T", " ").replace("+09:00", "（日本時間）")


def page(title, description, body, filename, site_url, indexable, nav, home=False, heading_in_body=False):
    canonical = f'<link rel="canonical" href="{escaped(site_url.rstrip("/") + "/" + filename)}">' if site_url and indexable else ""
    robots = "index,follow" if site_url and indexable else "noindex,follow"
    heading = "" if home or heading_in_body else f"<h1>{escaped(title)}</h1>"
    main_class = (' class="home-main"' if home else
                  ' class="article-main"' if filename.startswith("trip-") else
                  ' class="about-main"' if filename == "about.html" else
                  ' class="listing-main"' if filename in {"travel.html", "places.html", "nearby.html", "event-finder.html"} else "")
    header_class = "site-header site-header--compact" if home else "site-header"
    header_identity = ('<div class="header-identity">'
                       f'<a class="brand" href="index.html">{escaped(SITE_NAME)}</a>'
                       f'<p class="tagline">{escaped(SITE_TAGLINE)}</p></div>') if not home else ""
    active_file = ("index.html" if home else
                   "travel.html" if filename == "travel.html" or filename.startswith("trip-") else
                   "nearby.html" if filename == "nearby.html" else
                   "event-finder.html" if filename == "event-finder.html" else
                   "places.html" if filename == "places.html" else
                   "events.html" if filename == "events.html" or filename.startswith(("event-", "area-", "category-")) else
                   None)
    if active_file:
        nav = nav.replace(f'href="{active_file}"',
                          f'href="{active_file}" aria-current="page"', 1)
    about_link = ('<a href="about.html"'
                  + (' aria-current="page"' if filename == "about.html" else '')
                  + '>このサイトについて</a>')
    hero_preload = ('<link rel="preload" as="image" href="harima-hero-photo.webp" fetchpriority="high">'
                    if home else '')
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escaped(title)} | {escaped(SITE_NAME)}</title><meta name="description" content="{escaped(description)}">
<meta name="robots" content="{robots}">{canonical}{hero_preload}<link rel="stylesheet" href="styles.css"></head>
<body><a class="skip-link" href="#main-content">本文へ移動</a>
<header class="{header_class}"><div class="site-header__inner">
{header_identity}
<nav aria-label="主なページ">{nav}</nav></div></header>
<main id="main-content"{main_class}>{heading}{body}</main>
<footer class="site-footer"><div class="site-footer__inner">
<div class="site-footer__top"><a class="site-footer__brand" href="index.html">{escaped(SITE_NAME)}</a>
<nav aria-label="フッターの案内">{nav}{about_link}</nav></div>
<p>日程・料金・参加条件は変更される場合があります。お出かけ前に公式情報をご確認ください。</p>
<p>確認できない情報は「不明」と表示します。掲載内容は確認済みの事実情報から構成しています。</p>
</div></footer></body></html>'''



def source_links(record, sources):
    ranked = sorted(record["sources"], key=lambda p: (not p["is_primary"], p["source_id"]))
    entries = []
    for provenance in ranked:
        source = sources[provenance["source_id"]]
        publication = date_label(provenance["source_published_at"])
        entries.append(f'<li data-source-id="{escaped(source["id"])}" data-verified-at="{escaped(provenance["last_checked_at"])}"><a href="{escaped(provenance["url"])}" rel="noopener noreferrer">{escaped(source["label"])}（公式・情報源）</a>'
                       f'<br>取得日時：{escaped(date_label(provenance["fetched_at"]))} / 最終確認：{escaped(date_label(provenance["last_checked_at"]))}'
                       f'<br>発表日時：{escaped(publication)} / <a href="{escaped(source["permission_document"])}" rel="noopener noreferrer">利用条件・出典</a></li>')
        if source.get("attribution_url"):
            entries.append(f'<li><a href="{escaped(source["attribution_url"])}" rel="noopener noreferrer">出典：{escaped(source["label"])} 配布ページ</a>'
                           f'<br>{escaped(source.get("adaptation_notice", "出典の事実情報を整理して作成しました。"))}</li>')
    credits = []
    for provenance in ranked:
        source = sources[provenance["source_id"]]
        credit_url = source.get("attribution_url") or provenance["url"]
        credits.append(f'<a href="{escaped(credit_url)}" rel="noopener noreferrer">{escaped(source["label"])}</a>')
    return ('<p class="source-credit">出典：' + "、".join(credits) + '</p>'
            + '<details class="source-details"><summary>出典・確認履歴の詳細</summary>'
            + '<ul class="muted">' + "".join(entries) + '</ul></details>')


def event_content(event, sources, now, detail=False):
    occurrences = active_occurrences(event, now)
    dates = "".join(f'<li>{escaped(date_label(o["start_at"]))} 〜 {escaped(date_label(o["end_at"]))}</li>' for o in occurrences)
    price = {"free": "無料（条件は公式情報で確認）", "paid": "有料", "conditional": "条件付き", "unknown": "不明"}[event["price_type"]]
    indoor = {"indoor": "屋内", "outdoor": "屋外", "mixed": "屋内・屋外", "unknown": "不明"}[event["indoor_outdoor"]]
    title = escaped(event["title"])
    heading = title if detail else f'<a href="{event_file(event)}">{title}</a>'
    reservation = {True: "必要", False: "不要", None: "不明"}[event["reservation_required"]]
    official = f'<p><a href="{escaped(event["official_url"])}" rel="noopener noreferrer">公式の開催情報</a></p>' if event.get("official_url") else ""
    return (f'<article class="card"><h2>{heading}</h2><span class="tag">{escaped(event["municipality"])}</span>'
            f'<h3>確認済みの開催回</h3><ul>{dates}</ul><dl><dt>会場</dt><dd>{escaped(event["location_label"] or "不明")}</dd>'
            f'<dt>料金</dt><dd>{escaped(price)} / {escaped(event["price_description"] or "詳細不明")}</dd>'
            f'<dt>対象年齢</dt><dd>{escaped(event["age_info"] or "不明")}</dd><dt>屋内・屋外</dt><dd>{indoor}</dd>'
            f'<dt>予約</dt><dd>{reservation}</dd><dt>最終確認</dt><dd>{escaped(date_label(event["last_verified_at"]))}</dd></dl>'
            '<p>お出かけ前に公式情報で開催状況と参加条件をご確認ください。</p>' + official + source_links(event, sources) + '</article>')


def place_content(place, sources):
    """Render public facility facts and source attribution; no inferred ratings."""
    address = escaped(place["address"] or "住所不明")
    admission = escaped(place["admission"] or "不明")
    return (f'<article class="card place-card"><p class="place-card__area">{escaped(place["municipality"])}</p>'
            f'<h3>{escaped(place["name"])}</h3>'
            f'<p class="place-card__address">{address}</p>'
            f'<p class="place-card__price">料金：{admission}</p>'
            f'<a class="place-card__official" href="{escaped(place["official_url"])}" rel="noopener noreferrer">'
            '公式サイトを確認 <span aria-hidden="true">↗</span></a>'
            + source_links(place, sources) + '</article>')


def qualified(events, rules):
    minimum = rules["list_pages"]
    return (len(events) >= minimum["min_active_items"]
            and sum(any(s["is_primary"] for s in e["sources"]) for e in events) >= minimum["min_official_items"]
            and len({e.get("organizer_label") for e in events if e.get("organizer_label")}) >= minimum["min_distinct_organizers"])


def about_content():
    """Explain current services without claiming verified live measurement."""
    return (
        '<section class="intro" aria-label="サイトの紹介">'
        '<p class="eyebrow">はりまよりみち</p>'
        '<p>はりまよりみちは、加古川・明石・姫路とその周辺で、'
        '家族のお出かけ先や旅行のアイデアを探しやすく整理した地域ガイドです。</p>'
        '<p>運営表示名は「はりまよりみち」です。</p></section>'
        '<section class="notice" aria-labelledby="about-information">'
        '<h2 id="about-information">掲載情報とご利用にあたって</h2>'
        '<p>施設や旅行先の情報は、公的機関や施設の公式資料などを参考に確認・整理し、'
        '出典や確認日を掲載しています。確認できない事項は推測せず、「不明」として扱います。</p>'
        '<p>山陰の旅行記事は実際に出かけた家族旅行の記録、淡路島の記事は旅の提案となる'
        'モデルコースです。実際の体験と提案を区別して紹介しています。</p>'
        '<p>営業時間・料金・休業日・参加条件・予約方法・イベントの開催状況は変更される場合があります。'
        '掲載情報の正確性や最新性を保証するものではありません。'
        'お出かけや予約の前に、リンク先の公式サイトで最新情報をご確認ください。</p></section>'
        '<section class="notice" aria-labelledby="about-advertising">'
        '<h2 id="about-advertising">広告・アフィリエイトについて</h2>'
        '<p>一部の旅行記事には、楽天トラベルのアフィリエイトリンク（広告・PR）を掲載しています。'
        'リンクから予約等が成立した場合、当サイトが紹介料を受け取ることがあります。</p>'
        '<p>広告のある記事では、記事内や広告の近くにも「広告・PR」を表示しています。'
        '施設の公式情報へのリンクと広告リンクは区別してご案内しています。</p>'
        '<p>予約・契約・決済や個人情報の入力はリンク先の外部サービスで行います。'
        '掲載内容・料金・取引条件は各リンク先でご確認ください。</p></section>'
        '<section class="notice" aria-labelledby="about-privacy">'
        '<h2 id="about-privacy">プライバシーと外部サービス</h2>'
        '<p>当サイトには、会員登録やお問い合わせの入力フォームは設けていません。</p>'
        '<p>当サイトはCloudflare Pagesを利用して公開しています。閲覧状況やページの表示性能を把握し、'
        'サイトの改善に役立てるため、Cloudflare Web Analyticsを利用しています。'
        'ページの閲覧情報や読み込み速度などがCloudflareへ送信・集計されます。</p>'
        '<p>Cloudflare Web Analyticsは、Cookieを利用せず、個々の訪問者を特定するための'
        '個人情報を収集しない仕組みとして提供されています。'
        'なお、サイト配信・セキュリティのための通信情報の取扱いは、この解析とは別に行われる場合があります。</p>'
        '<p>一部の記事には外部の広告画像やリンクが含まれます。画像の表示やリンクの利用に伴い、'
        '外部サービスへの通信が発生する場合があります。各事業者による情報の取扱いは、'
        'それぞれの方針をご確認ください。</p>'
        '<ul><li><a href="https://www.cloudflare.com/privacypolicy/" rel="noopener noreferrer">'
        'Cloudflareのプライバシーポリシー</a></li>'
        '<li><a href="https://privacy.rakuten.co.jp/" rel="noopener noreferrer">'
        '楽天グループの個人情報保護方針</a></li></ul></section>'
        '<section class="notice" aria-labelledby="about-contact">'
        '<h2 id="about-contact">ご連絡について</h2>'
        '<p>現在、当サイト専用のお問い合わせ窓口は設けていません。'
        '施設の営業状況や宿泊予約などのお問い合わせは、各公式サイトの案内をご利用ください。</p>'
        '</section>'
    )


def create_files(root, now):
    data = validate_data(root, now)
    areas, categories, rules, config = validate_config(root, now)
    sources = {s["id"]: s for s in config["sources"]}
    stale = rules["review"]["stale_event_after_hours"]
    events = [e for e in data["events"]["items"] if active_occurrences(e, now) and publishable(e, sources, now, stale)]
    events.sort(key=lambda e: (active_occurrences(e, now)[0]["start_at"], e["event_id"]))
    places = [p for p in data["places"]["items"] if publishable(p, sources, now, stale)]
    travel_guides = reviewed_guides(data.get("travel_guides", {"schema_version": 1, "items": []}), now)
    nearby = reviewed_nearby(root)
    official_links, official_reviewed_on = official_event_links(root)
    curated = public_curated_events(root, now, stale)
    state_path = root / "cache/page_state.json"
    page_state = read_json(state_path) if state_path.exists() else {}
    groups = {}
    for area in areas["areas"]:
        groups[f'area-{area["id"]}.html'] = (area["name"] + "の開催情報", [e for e in events if e["municipality"] in (area["id"], area["name"])])
    for category in categories["primary"]:
        if category["id"] != "trip":
            groups[f'category-{category["id"]}.html'] = (category["label"] + "の開催情報", [e for e in events if category["id"] in e["category_ids"]])
    ready = {}
    for filename, (title, items) in groups.items():
        if sustained_listing(filename, qualified(items, rules), page_state, now,
                             rules["list_pages"]["activate_after_days"]):
            ready[filename] = (title, items)

    # Place listings do not depend on organizer_label or event availability.
    places_ready = sustained_listing("places.html",
                                    qualified_places(places, rules["place_pages"]),
                                    page_state, now, rules["place_pages"]["activate_after_days"])
    nav = ('<a href="index.html">ホーム</a>'
           + ('<a href="event-finder.html">イベントを探す</a>' if official_links else '')
           + ('<a href="events.html">開催情報一覧</a>' if events else '')
           + ('<a href="nearby.html">近場のよりみち</a>' if nearby else '')
           + ('<a href="places.html">施設一覧</a>' if places else '')
           + ('<a href="travel.html">家族旅行</a>' if travel_guides else ''))
    files, indexable_files = {"styles.css": STYLE, "harima-hero.svg": HERO_SCENE,
                              "awaji-card.svg": AWAJI_SCENE,
                              **{name: load_photo_asset(name) for name in PHOTO_ASSETS}}, []
    url = rules["site_url"]

    def add(filename, title, description, body, indexable, *, heading_in_body=False):
        files[filename] = page(title, description, body, filename, url, indexable, nav,
                               home=(filename == "index.html"), heading_in_body=heading_in_body)
        if indexable and url:
            indexable_files.append(filename)

    add("about.html", "このサイトについて",
        "はりまよりみちの運営案内、掲載情報の確認方法、広告・PR、プライバシーと外部サービスについてご案内します。",
        about_content(), False)
    if official_links:
        add("event-finder.html", "公式イベント情報を探す",
            "加古川・明石・姫路と兵庫県の公式イベント案内へのリンク集。日程・料金・参加条件は公式サイトで確認できます。",
            event_finder_body(official_links, official_reviewed_on,
                              curated_event_cards(curated)), False)

    cards = "".join(event_content(e, sources, now) for e in events)
    place_cards = "".join(place_content(p, sources) for p in places)
    home_place_cards = "".join(place_content(p, sources) for p in places[:3])
    hero_actions = []
    if travel_guides:
        hero_actions.append('<a class="action-link action-link--primary" href="travel.html">家族旅行プランを見る →</a>')
    if nearby:
        hero_actions.append('<a class="action-link action-link--secondary" href="nearby.html">近場のよりみちを見る →</a>')
    elif places:
        hero_actions.append('<a class="action-link action-link--secondary" href="places.html">近場の施設を探す →</a>')
    if events:
        hero_actions.append('<a class="action-link action-link--secondary" href="events.html">イベントを探す →</a>')
    hero = ('<section class="home-hero" aria-labelledby="home-headline">'
            '<div class="home-hero__copy">'
            '<p class="eyebrow">播磨のおでかけを、確かな情報から。</p>'
            '<h1 id="home-headline">はりまよりみち</h1>'
            '<p class="home-hero__subtitle">週末、ちょっとよりみちしよう。</p>'
            '<p class="home-hero__description">近場の公園から、少し遠くの家族旅行まで。'
            '加古川・明石・姫路とその周辺の立ち寄り先を、公式情報と一緒に紹介します。</p>'
            + ('<div class="home-hero__actions">' + "".join(hero_actions) + '</div>' if hero_actions else '')
            + '</div><div class="home-hero__scene" aria-hidden="true"></div>'
            '<small class="home-hero__footnote">※画像はイメージです</small></section>')
    # Navigation and hero actions already provide the page shortcuts.
    # Put featured travel stories directly after the scenic hero.
    content = hero
    if travel_guides:
        content += ('<section id="family-trip" class="home-section">'
                    '<div class="home-section__heading"><div><span class="section-kicker">FAMILY TRIP</span>'
                    '<h2>家族で行きたい旅</h2>'
                    '<p>実際に出かけた旅行記と、家族で楽しむモデルコースを紹介します。</p>'
                    '</div><a class="home-section__more" href="travel.html">旅行プラン一覧 →</a></div>'
                    '<div class="cards home-trip-cards">'
                    + "".join(guide_card(g, compact=True) for g in travel_guides) + '</div></section>')
    if nearby:
        preview = nearby_preview_cards(nearby)
        content += (
            '<section id="nearby-guide" class="home-section">'
            '<div class="home-section__heading"><div>'
            '<span class="section-kicker">NEARBY OUTINGS</span>'
            '<h2>近場のよりみちガイド</h2>'
            '<p>公園でのんびり、親子で学びの時間。気軽なよりみち先を見つけてみませんか。</p>'
            f'</div><a class="home-section__more" href="nearby.html">{len(nearby)}件の候補を見る →</a></div>'
            '<div class="cards nearby-preview-grid">' + preview + '</div>'
            '<p class="nearby-preview-note">画像に描かれた風景・設備の実在を保証するものではありません。'
            '営業日や利用条件は、各施設の公式案内をご確認ください。</p></section>'
        )
    if places:
        content += ('<section id="local-spots" class="home-section">'
                    '<div class="home-section__heading"><div><span class="section-kicker">LOCAL SPOTS</span>'
                    '<h2>近場のよりみち候補</h2>'
                    '<p>施設の基本情報、公式サイト、出典を確認できます。</p>'
                    '</div><a class="home-section__more" href="places.html">施設一覧を見る →</a></div>'
                    '<div class="cards place-grid place-grid--home">' + home_place_cards + '</div>'
                    + ('<p class="home-section__all"><a href="places.html">すべての施設を見る →</a></p>'
                       if len(places) > 3 else '') + '</section>')
    if events:
        content += ('<section id="local-events" class="home-section">'
                    '<div class="home-section__heading"><div><span class="section-kicker">EVENTS</span>'
                    '<h2>開催情報</h2></div><a class="home-section__more" href="events.html">一覧を見る →</a></div>'
                    '<div class="cards">' + cards + '</div></section>')
    elif curated:
        content += ('<section id="local-events" class="home-section">'
                    '<div class="home-status"><h2>主催者公式で確認したイベント</h2>'
                    f'<p>手動確認済みの{len(curated)}件を掲載しています。変更や中止は必ず公式情報でご確認ください。</p>'
                    '<p><a href="event-finder.html">開催情報と公式イベント案内を見る →</a></p>'
                    '</div></section>')
    else:
        content += ('<section id="local-events" class="home-section">'
                    '<div class="home-status"><h2>イベント情報は準備中です</h2>'
                    '<p>現在、開催日時や会場を確認できるイベントは掲載していません。'
                    '公式情報と利用条件が確認できたものからご案内します。</p>'
                    + ('<p><a href="event-finder.html">自治体などの公式イベント案内を探す →</a></p>'
                       if official_links else '') + '</div></section>')
    if not events and not places and not travel_guides:
        content += ('<section class="notice"><h2>掲載準備中です</h2>'
                    '<p>現在、公開できる確認済みの情報はありません。'
                    '情報源の利用条件と掲載内容を確認してから掲載します。</p></section>')
    content += ('<section class="home-trust" aria-label="掲載情報について">'
                '<div class="home-trust__item"><strong>公式情報へのリンク</strong>'
                '<p>現地に行く前に、施設や主催者の最新案内を確認できます。</p></div>'
                '<div class="home-trust__item"><strong>確認できないことは「不明」</strong>'
                '<p>料金・日時・利用条件を推測して断定しません。</p></div>'
                '<div class="home-trust__item"><strong>出典を明示</strong>'
                '<p>出典と確認状況を表示します。旅行記事は実際の記録と提案プランを区別して紹介します。</p></div>'
                '</section>')
    travel_indexable = any(search_eligible(g, now) for g in travel_guides)
    add("index.html", "家族で出かける地域ガイド", "加古川・明石・姫路周辺の確認済み開催情報と施設案内、播磨からの家族旅行モデルコース。公式情報と確認日時を表示します。", content, qualified(events, rules) or places_ready or travel_indexable)
    if travel_guides:
        listing = ('<section class="listing-lead" aria-label="旅行記事について">'
                   '<span class="section-kicker">FAMILY TRIP</span>'
                   '<p>実際に出かけた家族旅行の記録と、これからの旅に役立つモデルコース。'
                   '行き先を写真やルートから選べます。</p>'
                   '<div class="listing-lead__notes"><span>🚗 加古川から車でおでかけ</span>'
                   '<span>旅の記録と提案を区別して掲載</span></div>'
                   '<p class="listing-lead__disclaimer">営業時間・料金・宿泊条件は、'
                   '必ず各施設の公式サイトでご確認ください。</p></section>'
                   '<div class="cards trip-list-grid">' +
                   "".join(guide_card(g) for g in travel_guides) + '</div>')
        add("travel.html", "加古川発・家族旅行プラン", "加古川から車で行ける1泊2日旅行のモデルコースと、宿泊予約前に確認したい条件のまとめです。", listing, travel_indexable)
        for guide in travel_guides:
            add(travel_filename(guide), guide["title"], guide["summary"], guide_body(guide),
                search_eligible(guide, now), heading_in_body=(guide["id"] in {"awaji-family-one-night", "sanin-family-one-night"}))
    if nearby:
        nearby_reviewed_on = read_json(root / "data/nearby_spots.json")["reviewed_on"]
        add("nearby.html", "近場のよりみちガイド", "加古川・明石・播磨町周辺の公園・屋内施設を独自編集で紹介。公式リンクで最新の利用条件を確認できます。", nearby_page_body(nearby, nearby_reviewed_on), False)
    if places:
        places_listing = ('<section class="listing-lead" aria-label="施設の探し方">'
                          '<span class="section-kicker">LOCAL SPOTS</span>'
                          '<p>公式情報で確認できる、近場のおでかけ候補を集めました。'
                          '気になる施設の所在地・料金の確認状況・出典を確かめられます。</p>'
                          '<p class="listing-lead__disclaimer">未確認の料金は「不明」と表示します。'
                          'お出かけ前には公式案内をご確認ください。</p></section>'
                          '<div class="cards place-grid">' + place_cards + '</div>')
        add("places.html", "確認済みの施設一覧", "加古川・明石・姫路周辺の施設名称、所在地と公式リンクを出典付きでまとめています。料金など不明な項目は推測しません。", places_listing, places_ready)
    if events:
        add("events.html", "開催情報一覧", "確認済みの将来・開催中の開催回を掲載しています。終了・中止・未確認のイベントは掲載しません。", '<div class="cards">' + cards + '</div>', qualified(events, rules))
        for event in events:
            add(event_file(event), event["title"], f'{event["municipality"]}の開催情報。日程・会場・料金は公式情報をご確認ください。', event_content(event, sources, now, True), True)
    for filename, (title, items) in ready.items():
        add(filename, title, "公式情報・確認日時付きの地域開催情報。変更・中止については公式ページでご確認ください。", '<div class="cards">' + "".join(event_content(e, sources, now) for e in items) + '</div>', True)
    if url:
        files["robots.txt"] = "User-agent: *\n" + ("Allow: /\n" if indexable_files else "Disallow: /\n")
        if indexable_files:
            ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
            ET.register_namespace("", ns)
            tree = ET.Element(f"{{{ns}}}urlset")
            for filename in indexable_files:
                entry = ET.SubElement(tree, f"{{{ns}}}url")
                ET.SubElement(entry, f"{{{ns}}}loc").text = url.rstrip("/") + "/" + filename
            files["sitemap.xml"] = ET.tostring(tree, encoding="unicode", xml_declaration=True)
            files["robots.txt"] += "Sitemap: " + url.rstrip("/") + "/sitemap.xml\n"
    files["_headers"] = cloudflare_headers(not bool(indexable_files))
    files[".guide-manifest.json"] = json.dumps({"schema_version": 1, "generated_at": now.isoformat(),
                                               "files": sorted(files), "events": len(events) + len(curated), "places": len(places),
                                               "travel_guides": len(travel_guides)}, ensure_ascii=False, indent=2) + "\n"
    return files, page_state


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.title, self.headings = [], set(), [], []
        self.metas, self.canonical, self.lang, self.charset = {}, [], None, False
        self.capture = None
        self.stack = []
        self.errors = []
        self.provenance = []
        self.heading_count = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "data-source-id" in values:
            self.provenance.append(values)
        if tag == "img":
            image_url = values.get("src") or ""
            image_parts = urlsplit(image_url)
            approved_ad_image = (image_parts.scheme == "https"
                                 and image_parts.hostname == "hbb.afl.rakuten.co.jp"
                                 and image_parts.path.startswith("/hgb/")
                                 and set(values) == {"src", "border", "style", "alt", "title"}
                                 and values["border"] == "0"
                                 and values["style"] == "margin:2px"
                                 and values["alt"] == ""
                                 and values["title"] == ""
                                 and "section" in self.stack)
            spec = next((entry for entry in NEARBY_IMAGES.values() if entry[0] == image_url), None)
            hero_image = image_url == "nearby-hero.webp"
            image_attributes = {"class", "src", "alt", "width", "height", "loading", "decoding"}
            if hero_image:
                image_attributes.add("fetchpriority")
            approved_nearby_image = (
                spec is not None and image_url in PHOTO_ASSETS
                and set(values) == image_attributes
                and values["class"] == "nearby-image__img"
                and values["alt"] == spec[1]
                and values["width"] == str(spec[2]) and values["height"] == str(spec[3])
                and values["loading"] == ("eager" if hero_image else "lazy")
                and (not hero_image or values.get("fetchpriority") == "high")
                and values["decoding"] == "async" and "figure" in self.stack
            )
            if approved_nearby_image:
                self.links.append(image_url)
            elif not approved_ad_image:
                self.errors.append("許可されていない画像埋め込みがあります")
            else:
                try:
                    safe_url(image_url)
                except GuideError:
                    self.errors.append("楽天広告画像のURLが不正です")
        elif tag in ("script", "iframe", "form", "object", "embed", "base"):
            self.errors.append("許可されない埋め込み要素・動的処理があります")
        if any(k.startswith("on") for k in values):
            self.errors.append("イベント属性は禁止です")
        if tag == "html":
            self.lang = values.get("lang")
        if tag == "meta":
            self.charset |= values.get("charset", "").lower() == "utf-8"
            if "name" in values:
                self.metas[values["name"]] = values.get("content", "")
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical.append(values.get("href"))
        elif "href" in values:
            self.links.append(values["href"])
        if "id" in values:
            if values["id"] in self.ids:
                self.errors.append("HTML IDが重複しています")
            self.ids.add(values["id"])
        if tag in ("title", "h1"):
            self.capture = tag
        if tag == "h1":
            self.heading_count += 1
        if tag not in ("meta", "link", "br", "hr", "input", "img", "source", "wbr", "area", "base", "embed"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.errors.append("HTML要素の対応が不正です")
        if tag == self.capture:
            self.capture = None

    def handle_data(self, data):
        if self.capture == "title":
            self.title.append(data)
        if self.capture == "h1":
            self.headings.append(data)


def validate_site(output, site_url=None):
    output = Path(output)
    manifest = read_json(output / ".guide-manifest.json")
    expected = set(manifest["files"]) | {".guide-manifest.json"}
    if not {"index.html", "styles.css"} <= expected:
        raise GuideError("必須のトップページまたはCSSがありません")
    if {p.name for p in output.iterdir() if p.name != ".gitkeep"} != expected:
        raise GuideError("生成物とマニフェストが一致しません")
    documents = {}
    for filename in expected:
        path = output / filename
        if path.is_symlink() or not path.is_file() or Path(filename).name != filename:
            raise GuideError("生成物のパスが不正です")
        if filename.endswith(".webp"):
            if not valid_webp(path.read_bytes()):
                raise GuideError("生成写真素材のWebP形式が不正です")
            continue
        content = path.read_text(encoding="utf-8")
        inspect_text(content)
        if not content.strip():
            raise GuideError("空の生成物があります")
        if filename.endswith(".html"):
            document = Document()
            document.feed(content)
            document.close()
            if (document.errors or document.stack or document.lang != "ja" or not document.charset
                    or not "".join(document.title).strip() or not "".join(document.headings).strip()
                    or document.heading_count != 1 or not document.metas.get("description") or not document.metas.get("viewport")):
                raise GuideError(f"HTML検証に失敗: {filename}")
            indexable = document.metas.get("robots") == "index,follow"
            canonical = [site_url.rstrip("/") + "/" + filename] if indexable and site_url else []
            if document.canonical != canonical or (indexable and not site_url):
                raise GuideError("canonicalまたはsite_urlが不正です")
            documents[filename] = document
            if filename.startswith("event-"):
                from .core import parse_time
                if not document.provenance:
                    raise GuideError("イベントページの出典がありません")
                for provenance in document.provenance:
                    parse_time(provenance.get("data-verified-at"))
    if "_headers" in expected:
        actual_headers = (output / "_headers").read_text(encoding="utf-8")
        any_indexable = any(doc.metas.get("robots") == "index,follow"
                            for doc in documents.values())
        if actual_headers != cloudflare_headers(not any_indexable):
            raise GuideError("CloudflareのHTTPヘッダーが検索登録条件と一致しません")
    for filename, document in documents.items():
        for link in document.links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc:
                safe_url(link)
            else:
                target = parts.path or filename
                if target not in expected or Path(target).name != target or parts.query:
                    raise GuideError(f"ローカルリンク切れ: {filename}")
                if parts.fragment and (target not in documents or parts.fragment not in documents[target].ids):
                    raise GuideError("ページ内リンク切れです")
    if "sitemap.xml" in expected:
        if not site_url:
            raise GuideError("site_url未確定でsitemapを生成できません")
        xml = ET.fromstring((output / "sitemap.xml").read_text())
        locations = [node.text for node in xml.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        valid = {site_url.rstrip("/") + "/" + name for name, doc in documents.items() if doc.metas["robots"] == "index,follow"}
        if not locations or len(locations) != len(set(locations)) or set(locations) != valid:
            raise GuideError("sitemapに非公開・不正なURLがあります")
    return manifest


@serialized
def build(root, now, output=None):
    output = Path(output) if output else root / "docs"
    if output.is_symlink() or output.parent.resolve() != root.resolve() or output.name != "docs":
        raise GuideError("生成先はリポジトリ直下のdocsのみです")
    files, page_state = create_files(root, now)
    if output.exists():
        previous = read_json(output / ".guide-manifest.json")["files"] if (output / ".guide-manifest.json").exists() else []
        known = set(previous) | {".gitkeep", ".guide-manifest.json"}
        if any(p.name not in known or p.is_symlink() or not p.is_file() for p in output.iterdir()):
            raise GuideError("docsに生成管理外のファイルがあります。上書きせず停止します")
    staging = Path(tempfile.mkdtemp(prefix=".guide-build-", dir=root))
    backup = None
    try:
        for filename, content in files.items():
            if isinstance(content, bytes):
                (staging / filename).write_bytes(content)
            else:
                (staging / filename).write_text(content, encoding="utf-8")
        if (output / ".gitkeep").exists():
            shutil.copy2(output / ".gitkeep", staging / ".gitkeep")
        rules = read_json(root / "config/page_rules.json")
        result = validate_site(staging, rules["site_url"])
        # Complete persistent-state writes before swapping in verified output.
        atomic_json(root / "cache/page_state.json", page_state)
        if output.exists():
            backup = Path(tempfile.mkdtemp(prefix=".guide-backup-", dir=root))
            backup.rmdir()
            os.replace(output, backup)
        try:
            os.replace(staging, output)
        except OSError:
            if backup:
                os.replace(backup, output)
                backup = None
            raise
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if backup and backup.exists():
            shutil.rmtree(backup)
