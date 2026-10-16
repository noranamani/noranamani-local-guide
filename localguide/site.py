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


PHOTO_ASSETS = ("harima-hero-photo.webp", "awaji-photo.webp")
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
.section-kicker { display: block; margin: 0 0 .2rem; color: #66816b; font-size: .81rem; font-weight: 850; letter-spacing: .13em; }
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
  min-height: clamp(400px, 46vw, 535px);
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
  max-width: 950px;
  min-height: inherit;
  padding: clamp(2rem, 6vw, 5.2rem);
}
.home-hero__copy h1 {
  margin: .4rem 0 .35rem;
  font-size: clamp(2.65rem, 7vw, 5.4rem);
  line-height: 1.18;
  letter-spacing: .045em;
  color: #fff;
  text-shadow: 0 3px 15px rgb(0 0 0 / 42%);
}
.home-hero__copy .eyebrow { color: #e8f7e7; text-shadow: 0 2px 8px #153a39; }
.home-hero__subtitle {
  margin: .55rem 0 .6rem;
  font-size: clamp(1.28rem, 2.5vw, 1.8rem);
  font-weight: 750;
  text-shadow: 0 2px 12px rgb(0 0 0 / 45%);
}
.home-hero__copy .home-hero__description {
  max-width: 40rem;
  font-size: clamp(.95rem, 1.6vw, 1.05rem);
  line-height: 1.7;
  text-shadow: 0 1px 6px rgb(0 0 0 / 50%);
}
.home-hero__scene { display: none; }
.home-hero__actions { margin-top: 1.2rem; }
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
  min-height: clamp(270px, 34vw, 435px);
  height: auto;
  overflow: hidden;
  padding: clamp(1.2rem, 4.5vw, 3.2rem);
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
  font-size: clamp(1.55rem, 4vw, 3rem);
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
    min-height: 515px;
    background-image: linear-gradient(0deg, rgb(3 31 35 / 84%), rgb(5 35 40 / 32%) 85%), url("harima-hero-photo.webp");
    background-position: 59% center;
  }
  .home-hero__copy {
    justify-content: flex-end;
    min-height: 515px;
    padding: 2rem 1.45rem 3.3rem;
  }
  .home-hero__copy h1 { font-size: clamp(2.2rem, 9.7vw, 3.7rem); }
  .home-hero__subtitle { font-size: 1.23rem; }
  .home-hero__actions { width: 100%; }
  .home-hero__footnote { right: 1.4rem; bottom: .75rem; }
  .article-cover { min-height: 340px; padding: 1.5rem 1.1rem; }
  .article-cover h1 { font-size: clamp(1.55rem, 7vw, 2.1rem); }
}
@media (max-width: 360px) {
  .home-hero__copy h1 { font-size: 1.9rem; }
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
    main_class = ' class="home-main"' if home else ""
    header_class = "site-header site-header--compact" if home else "site-header"
    header_identity = (f'<a class="brand" href="index.html">{escaped(SITE_NAME)}</a>'
                       f'<p class="tagline">{escaped(SITE_TAGLINE)}</p>') if not home else ""
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escaped(title)} | {escaped(SITE_NAME)}</title><meta name="description" content="{escaped(description)}">
<meta name="robots" content="{robots}">{canonical}<link rel="stylesheet" href="styles.css"></head>
<body><a class="skip-link" href="#main-content">本文へ移動</a>
<header class="{header_class}"><div class="site-header__inner">
{header_identity}
<nav aria-label="主なページ">{nav}</nav></div></header>
<main id="main-content"{main_class}>{heading}{body}</main>
<footer class="site-footer"><div class="site-footer__inner">
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
    return (f'<article class="card"><h3>{escaped(place["name"])}</h3>'
            f'<p>{escaped(place["municipality"])} / {address}</p>'
            f'<p>料金：{admission}</p>'
            f'<a href="{escaped(place["official_url"])}" rel="noopener noreferrer">公式情報</a>'
            + source_links(place, sources) + '</article>')


def qualified(events, rules):
    minimum = rules["list_pages"]
    return (len(events) >= minimum["min_active_items"]
            and sum(any(s["is_primary"] for s in e["sources"]) for e in events) >= minimum["min_official_items"]
            and len({e.get("organizer_label") for e in events if e.get("organizer_label")}) >= minimum["min_distinct_organizers"])


def create_files(root, now):
    data = validate_data(root, now)
    areas, categories, rules, config = validate_config(root, now)
    sources = {s["id"]: s for s in config["sources"]}
    stale = rules["review"]["stale_event_after_hours"]
    events = [e for e in data["events"]["items"] if active_occurrences(e, now) and publishable(e, sources, now, stale)]
    events.sort(key=lambda e: (active_occurrences(e, now)[0]["start_at"], e["event_id"]))
    places = [p for p in data["places"]["items"] if publishable(p, sources, now, stale)]
    travel_guides = reviewed_guides(data.get("travel_guides", {"schema_version": 1, "items": []}), now)
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
           + ('<a href="events.html">開催情報一覧</a>' if events else '')
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

    cards = "".join(event_content(e, sources, now) for e in events)
    place_cards = "".join(place_content(p, sources) for p in places)
    hero_actions = []
    if travel_guides:
        hero_actions.append('<a class="action-link action-link--primary" href="travel.html">家族旅行プランを見る →</a>')
    if places:
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
    browse = []
    if places:
        browse.append('<a class="browse-card" href="places.html">'
                      '<span class="browse-card__icon" aria-hidden="true">🌿</span>'
                      '<span><strong>近場のスポット</strong><small>施設情報と公式リンクから探す</small></span></a>')
    if travel_guides:
        browse.append('<a class="browse-card browse-card--trip" href="travel.html">'
                      '<span class="browse-card__icon" aria-hidden="true">🚙</span>'
                      '<span><strong>家族で小旅行</strong><small>加古川発のモデルコースを読む</small></span></a>')
    if events:
        browse.append('<a class="browse-card" href="events.html">'
                      '<span class="browse-card__icon" aria-hidden="true">📅</span>'
                      '<span><strong>イベントを探す</strong><small>確認済みの開催情報をチェック</small></span></a>')
    else:
        browse.append('<div class="browse-card browse-card--pending">'
                      '<span class="browse-card__icon" aria-hidden="true">📅</span>'
                      '<span><strong>イベント情報</strong><small>公式情報の確認ができ次第ご案内</small></span></div>')
    content = hero + ('<section class="home-section" aria-label="おでかけの探し方">'
                      '<div class="home-section__heading"><div><span class="section-kicker">DISCOVER</span>'
                      '<h2>気分にあわせて探す</h2></div></div>'
                      '<div class="browse-grid">' + "".join(browse) + '</div></section>')
    if travel_guides:
        content += ('<section id="family-trip" class="home-section">'
                    '<div class="home-section__heading"><div><span class="section-kicker">FAMILY TRIP</span>'
                    '<h2>家族旅行のプランを探す</h2>'
                    '<p>実際に訪れたルートと、公式情報をもとにした旅のアイデアを紹介します。</p>'
                    '</div><a class="home-section__more" href="travel.html">旅行プラン一覧 →</a></div>'
                    '<div class="cards home-trip-cards">'
                    + "".join(guide_card(g) for g in travel_guides) + '</div></section>')
    if places:
        content += ('<section id="local-spots" class="home-section">'
                    '<div class="home-section__heading"><div><span class="section-kicker">LOCAL SPOTS</span>'
                    '<h2>近場のよりみち候補</h2>'
                    '<p>施設の基本情報、公式サイト、出典を確認できます。</p>'
                    '</div><a class="home-section__more" href="places.html">施設一覧を見る →</a></div>'
                    '<div class="cards">' + place_cards + '</div></section>')
    if events:
        content += ('<section id="local-events" class="home-section">'
                    '<div class="home-section__heading"><div><span class="section-kicker">EVENTS</span>'
                    '<h2>開催情報</h2></div><a class="home-section__more" href="events.html">一覧を見る →</a></div>'
                    '<div class="cards">' + cards + '</div></section>')
    else:
        content += ('<section id="local-events" class="home-section">'
                    '<div class="home-status"><h2>イベント情報は準備中です</h2>'
                    '<p>現在、開催日時や会場を確認できるイベントは掲載していません。'
                    '公式情報と利用条件が確認できたものからご案内します。</p></div></section>')
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
                '<p>データの取得元と確認状況を表示します。旅行コースは提案であり、実訪問を保証しません。</p></div>'
                '</section>')
    travel_indexable = any(search_eligible(g, now) for g in travel_guides)
    add("index.html", "家族で出かける地域ガイド", "加古川・明石・姫路周辺の確認済み開催情報と施設案内、播磨からの家族旅行モデルコース。公式情報と確認日時を表示します。", content, qualified(events, rules) or places_ready or travel_indexable)
    if travel_guides:
        listing = ('<p>加古川発の家族旅行の記録とモデルコースを紹介します。'
                   '訪問記録と提案コースを区別して掲載しています。営業時間・料金は各公式サイトでご確認ください。</p>'
                   '<div class="cards">' + "".join(guide_card(g) for g in travel_guides) + '</div>')
        add("travel.html", "加古川発・家族旅行プラン", "加古川から車で行ける1泊2日旅行のモデルコースと、宿泊予約前に確認したい条件のまとめです。", listing, travel_indexable)
        for guide in travel_guides:
            add(travel_filename(guide), guide["title"], guide["summary"], guide_body(guide),
                search_eligible(guide, now), heading_in_body=(guide["id"] in {"awaji-family-one-night", "sanin-family-one-night"}))
    if places:
        add("places.html", "確認済みの施設一覧", "加古川・明石・姫路周辺の施設名称、所在地と公式リンクを出典付きでまとめています。料金など不明な項目は推測しません。", '<div class="cards">' + place_cards + '</div>', places_ready)
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
                                               "files": sorted(files), "events": len(events), "places": len(places),
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
            if not approved_ad_image:
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
