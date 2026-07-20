from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import textwrap
import webbrowser
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urljoin, urlparse

import httpx
from jinja2 import Template
from lxml import html


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parent
CONFIG_PATH = ROOT / "config.json"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
PUBLIC_DIR = ROOT / "public"
STATE_PATH = DATA_DIR / "state.json"
LAST_SCAN_PATH = DATA_DIR / "last_scan.json"
DASHBOARD_PATH = OUTPUT_DIR / "dashboard.html"
PUBLIC_DASHBOARD_PATH = PUBLIC_DIR / "index.html"
PUBLIC_LAST_SCAN_PATH = PUBLIC_DIR / "last_scan.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TIMEOUT = 25.0
DEFAULT_PORT = 8765
SOURCE_ORDER = ["agenz", "mubawab", "marocannonces", "yakeey"]

AMENITY_PATTERNS = {
    "terrace": r"\bterrasse?s?\b",
    "balcony": r"\bbalcon(?:s)?\b",
    "elevator": r"\bascenseur\b",
    "parking": r"\b(parking|garage|place de parking)\b",
    "concierge": r"\bconcierge|gardien|gardiennage\b",
    "furnished": r"\bmeubl[éee]?\b",
    "new_project": r"\b(projet neuf|immobilier neuf|comme neuf|neuf)\b",
}

AMENITY_LABELS = {
    "terrace": "Terrasse",
    "balcony": "Balcon",
    "elevator": "Ascenseur",
    "parking": "Parking",
    "concierge": "Concierge",
    "furnished": "Meuble",
    "new_project": "Neuf",
}

MAROCANNONCES_MONTHS = {
    "jan": 1,
    "janv": 1,
    "janvier": 1,
    "fev": 2,
    "fevr": 2,
    "fevrier": 2,
    "fév": 2,
    "févr": 2,
    "février": 2,
    "mar": 3,
    "mars": 3,
    "avr": 4,
    "avril": 4,
    "mai": 5,
    "jun": 6,
    "juin": 6,
    "jul": 7,
    "juil": 7,
    "juillet": 7,
    "aou": 8,
    "aoû": 8,
    "aout": 8,
    "août": 8,
    "sep": 9,
    "sept": 9,
    "septembre": 9,
    "oct": 10,
    "octobre": 10,
    "nov": 11,
    "novembre": 11,
    "dec": 12,
    "déc": 12,
    "decembre": 12,
    "décembre": 12,
}


DASHBOARD_TEMPLATE = Template(
    """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Casablanca Watch</title>
  <style>
    :root {
      --bg: #f5f1e7;
      --paper: #fffdfa;
      --ink: #182c3c;
      --muted: #5a6d7d;
      --line: #d7d0bf;
      --accent: #185f56;
      --accent-2: #9d6a1d;
      --accent-3: #0f4e7b;
      --new: #d3533d;
      --soft: #eef3f7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #eee6d7 0, transparent 22%),
        radial-gradient(circle at top right, #e2efe9 0, transparent 20%),
        var(--bg);
      font-family: Georgia, "Times New Roman", serif;
    }
    a { color: #125a8b; text-decoration: none; }
    a:hover { text-decoration: underline; }
    code {
      background: rgba(12, 32, 44, 0.06);
      padding: 2px 6px;
      border-radius: 6px;
      font-size: 13px;
    }
    .wrap {
      max-width: 1380px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero {
      border-radius: 28px;
      padding: 28px;
      color: white;
      background: linear-gradient(135deg, #16324a, #20554c 58%, #7c5623);
      box-shadow: 0 20px 54px rgba(12, 28, 38, 0.18);
    }
    .hero-bar {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
    }
    .hero-copy {
      min-width: 0;
      flex: 1;
    }
    .hero h1 {
      margin: 0 0 10px;
      font-size: 46px;
      line-height: 1;
      letter-spacing: -0.03em;
    }
    .hero p {
      max-width: 930px;
      margin: 0;
      color: rgba(255,255,255,0.88);
      font-size: 18px;
      line-height: 1.48;
    }
    .meta {
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      border: 1px solid rgba(255,255,255,0.2);
      background: rgba(255,255,255,0.09);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 14px;
    }
    .actions {
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
    button.action {
      appearance: none;
      border: none;
      cursor: pointer;
      border-radius: 999px;
      padding: 12px 18px;
      background: white;
      color: #17344b;
      font-weight: 700;
      font-size: 14px;
      box-shadow: 0 8px 22px rgba(10, 18, 26, 0.14);
    }
    button.action.secondary {
      background: rgba(255,255,255,0.12);
      color: white;
      border: 1px solid rgba(255,255,255,0.18);
      box-shadow: none;
    }
    button.action.emphasis {
      background: var(--accent);
      color: white;
      box-shadow: 0 12px 28px rgba(17, 94, 84, 0.22);
    }
    button.action:disabled {
      opacity: 0.7;
      cursor: wait;
    }
    .layout {
      display: grid;
      grid-template-columns: 1.75fr 1fr;
      gap: 20px;
      margin-top: 22px;
    }
    .panel {
      border-radius: 24px;
      background: var(--paper);
      border: 1px solid var(--line);
      padding: 20px;
      box-shadow: 0 14px 38px rgba(19, 33, 45, 0.06);
    }
    .panel h2 {
      margin: 0 0 10px;
      font-size: 28px;
      line-height: 1.1;
      letter-spacing: -0.02em;
    }
    .panel h3 {
      margin: 18px 0 10px;
      font-size: 20px;
      line-height: 1.15;
    }
    .small {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.52;
    }
    .grid-two {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    .stat-card {
      padding: 14px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: white;
    }
    .stat-big {
      display: block;
      font-size: 28px;
      font-weight: 700;
      margin-top: 4px;
    }
    .warning {
      margin-top: 12px;
      border-left: 4px solid var(--accent-2);
      padding-left: 12px;
      color: #65451a;
    }
    .button-list {
      display: grid;
      gap: 8px;
    }
    .button-list a, .button-list button.linkish {
      display: block;
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      background: white;
      border-radius: 14px;
      padding: 10px 12px;
      font-size: 15px;
      color: var(--accent-3);
    }
    .group {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }
    .group:first-of-type {
      margin-top: 0;
      padding-top: 0;
      border-top: none;
    }
    .badge-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 8px 0 10px;
    }
    .badge {
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.03em;
      background: var(--soft);
      color: #2d445b;
    }
    .badge.new {
      background: rgba(211, 83, 61, 0.12);
      color: var(--new);
    }
    .badge.status-exact {
      background: rgba(24, 95, 86, 0.12);
      color: #0f5d53;
    }
    .badge.status-raw {
      background: rgba(157, 106, 29, 0.14);
      color: #855312;
    }
    .badge.status-internal {
      background: rgba(15, 78, 123, 0.1);
      color: #0f4e7b;
    }
    .area-grid, .source-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
    }
    .area-card, .source-card {
      display: block;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: white;
      color: inherit;
    }
    .area-card strong, .source-card strong {
      display: block;
      font-size: 18px;
      margin-bottom: 6px;
    }
    .count {
      color: var(--accent);
      font-size: 26px;
      font-weight: 700;
    }
    .cards {
      display: grid;
      gap: 14px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 14px;
      background: white;
    }
    .card h4 {
      margin: 0;
      font-size: 21px;
      line-height: 1.15;
    }
    .kv {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      margin: 8px 0;
      color: #24384b;
      font-size: 15px;
    }
    .links {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .links a {
      display: inline-flex;
      padding: 8px 12px;
      border-radius: 999px;
      background: #edf4f8;
      color: #144d77;
      font-size: 13px;
      font-weight: 700;
    }
    .empty {
      padding: 18px;
      border-radius: 16px;
      background: #f7f3ec;
      border: 1px dashed #c9bdab;
      color: #715d44;
    }
    .section-anchor {
      scroll-margin-top: 16px;
    }
    .search-link {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 10px 12px;
      background: white;
      margin-top: 8px;
    }
    .search-link-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .filter-shell {
      margin-top: 18px;
      padding: 16px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: #fcfaf5;
    }
    .filter-shell h3 {
      margin: 0 0 10px;
    }
    .chip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    .chip {
      border: 1px solid var(--line);
      background: white;
      color: var(--ink);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 13px;
      cursor: pointer;
    }
    .chip.active {
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }
    .numeric-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }
    .range-field {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: white;
      padding: 12px;
    }
    .range-field input[type="number"],
    .range-field select {
      width: 100%;
      margin-top: 8px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 8px 10px;
      background: #fffdfa;
      color: var(--ink);
      font: inherit;
    }
    .range-field input[type="range"] {
      width: 100%;
      margin-top: 8px;
    }
    .mini-label {
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }
    .table-actions {
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .listings-grid {
      display: grid;
      gap: 14px;
      margin-top: 18px;
    }
    .listing-row {
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 14px;
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 14px;
      background: white;
    }
    .thumb {
      position: relative;
      border-radius: 16px;
      overflow: hidden;
      min-height: 130px;
      background: linear-gradient(135deg, #e9edf1, #d9e4dd);
    }
    .thumb img {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .thumb-fallback, .thumb-empty {
      display: grid;
      place-items: center;
      height: 100%;
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      text-align: center;
      padding: 16px;
    }
    .thumb-fallback {
      background: linear-gradient(135deg, rgba(22, 50, 74, 0.06), rgba(32, 85, 76, 0.08));
    }
    .thumb-fallback strong {
      display: block;
      color: #24465d;
      font-size: 15px;
      letter-spacing: 0;
      text-transform: none;
      margin-bottom: 6px;
    }
    .thumb-fallback span {
      display: block;
      line-height: 1.45;
      text-transform: none;
      letter-spacing: 0;
    }
    .listing-copy h3 {
      margin: 0;
      font-size: 22px;
      line-height: 1.15;
    }
    .listing-topline {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }
    .listing-links {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 10px;
      min-width: 180px;
    }
    .listing-source-note {
      color: var(--muted);
      font-size: 13px;
      text-align: right;
    }
    .listing-cta {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 180px;
      padding: 11px 16px;
      border-radius: 999px;
      background: var(--accent-3);
      color: white;
      font-weight: 700;
      text-decoration: none;
      box-shadow: 0 10px 24px rgba(15, 78, 123, 0.18);
    }
    .listing-cta:hover {
      text-decoration: none;
      background: #0c4770;
    }
    .feature-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .feature-pill {
      padding: 6px 10px;
      border-radius: 999px;
      background: #eef4ef;
      color: #195e54;
      font-size: 12px;
      font-weight: 700;
    }
    .secondary-debug {
      margin-top: 24px;
      border-top: 1px solid var(--line);
      padding-top: 18px;
    }
    .secondary-debug summary {
      cursor: pointer;
      font-weight: 700;
    }
    @media (max-width: 980px) {
      .layout {
        grid-template-columns: 1fr;
      }
      .hero-bar {
        flex-direction: column;
      }
      .hero h1 {
        font-size: 34px;
      }
      .grid-two {
        grid-template-columns: 1fr;
      }
      .listing-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-bar">
        <div class="hero-copy">
          <h1>Casablanca Watch</h1>
          <p>
            Interface locale pour surveiller les annonces autour de CFC, avec les quartiers de votre carte,
            un bouton d'actualisation direct, et des vues exactes filtrees dans cette interface meme.
          </p>
        </div>
      </div>
    </section>

    <div class="layout">
      <main class="panel">
        <h2>Flux mixte CFC</h2>
        <p class="small">
          {% if refresh_mode == "live" %}
          Le bouton <code>Actualiser</code> relance le scan, puis la vue melangee se remet a jour.
          {% elif refresh_mode == "reload" %}
          Le bouton <code>Actualiser</code> recharge le dernier snapshot publie sur le site partageable.
          {% endif %}
        </p>
        {% if bootstrapped %}
        <div class="warning small">
          Premier scan initialise: pas de notification de nouveaute sur ce run pour eviter de traiter tout l'historique
          comme du neuf.
        </div>
        {% endif %}
        <div class="filter-shell">
          <h3>Filtres rapides</h3>
          <p class="small">
            Selectionnez les quartiers a garder, bougez les seuils prix/surface, puis actualisez la liste.
            L'ordre par defaut suit la fraicheur detectable du scan.
          </p>
          <div class="group">
            <strong>Quartiers CFC suivis</strong>
            <div id="areaFilters" class="chip-list"></div>
          </div>
          <div class="group">
            <strong>Equipements utiles</strong>
            <div id="amenityFilters" class="chip-list"></div>
          </div>
          <div class="numeric-grid">
            <label class="range-field">
              <span class="mini-label">Prix min</span>
              <input id="minPriceRange" type="range" min="0" max="2000000" step="25000" value="{{ criteria.min_price_mad }}">
              <input id="minPriceNumber" type="number" min="0" step="25000" value="{{ criteria.min_price_mad }}">
            </label>
            <label class="range-field">
              <span class="mini-label">Prix max</span>
              <input id="maxPriceRange" type="range" min="200000" max="2000000" step="25000" value="{{ criteria.max_price_mad }}">
              <input id="maxPriceNumber" type="number" min="0" step="25000" value="{{ criteria.max_price_mad }}">
            </label>
            <label class="range-field">
              <span class="mini-label">Surface min</span>
              <input id="minSurfaceRange" type="range" min="15" max="120" step="1" value="{{ criteria.min_surface_m2 }}">
              <input id="minSurfaceNumber" type="number" min="0" step="1" value="{{ criteria.min_surface_m2 }}">
            </label>
            <label class="range-field">
              <span class="mini-label">Surface max</span>
              <input id="maxSurfaceRange" type="range" min="15" max="120" step="1" value="{{ criteria.max_surface_m2 }}">
              <input id="maxSurfaceNumber" type="number" min="0" step="1" value="{{ criteria.max_surface_m2 }}">
            </label>
            <label class="range-field">
              <span class="mini-label">Tri</span>
              <select id="sortModeSelect">
                <option value="latest">Plus recents / visibles d'abord</option>
                <option value="price_asc">Prix croissant</option>
                <option value="price_desc">Prix decroissant</option>
                <option value="surface_desc">Surface decroissante</option>
              </select>
            </label>
          </div>
          <div class="table-actions">
            {% if refresh_mode == "live" %}
            <button id="refreshButton" class="action emphasis" onclick="refreshNow()">Actualiser les annonces</button>
            {% elif refresh_mode == "reload" %}
            <button id="refreshButton" class="action emphasis" onclick="reloadPublishedSnapshot()">Actualiser les annonces</button>
            {% endif %}
            <button class="action secondary" onclick="resetDashboardFilters()">Reinitialiser les filtres</button>
          </div>
          <p id="mixedSummary" class="small"></p>
        </div>

        <div id="mixedRows" class="listings-grid"></div>

        <details class="secondary-debug">
          <summary>Vues secondaires par quartier</summary>

          <h2 style="margin-top: 18px;">Quartiers presents dans le scan</h2>
          <div class="area-grid">
            {% for area in area_cards %}
            <a class="area-card" href="#{{ area.anchor }}">
              <strong>{{ area.label }}</strong>
              <span class="count">{{ area.count }}</span>
              <span class="small">{{ area.note }}</span>
            </a>
            {% endfor %}
          </div>

          {% for area in area_sections %}
          <section class="section-anchor" id="{{ area.anchor }}" style="margin-top: 26px;">
            <h2>{{ area.label }}</h2>
            {% if area.listings %}
            <div class="cards">
              {% for item in area.listings %}
              <article class="card">
                <h4>{{ item.title }}</h4>
                <div class="badge-row">
                  {% if item.is_new %}<span class="badge new">Nouveau</span>{% endif %}
                  <span class="badge">{{ item.source_name }}</span>
                  {% if item.age_label %}<span class="badge">{{ item.age_label }}</span>{% endif %}
                </div>
                <div class="kv">
                  <span><strong>Prix:</strong> {{ item.price_label }}</span>
                  <span><strong>Surface:</strong> {{ item.surface_label }}</span>
                  {% if item.rooms_label %}<span><strong>Pieces:</strong> {{ item.rooms_label }}</span>{% endif %}
                  {% if item.bedrooms_label %}<span><strong>Ch:</strong> {{ item.bedrooms_label }}</span>{% endif %}
                  {% if item.bathrooms_label %}<span><strong>Sdb:</strong> {{ item.bathrooms_label }}</span>{% endif %}
                </div>
                <p class="small">{{ item.summary }}</p>
                <div class="links">
                  <a href="{{ item.url }}" target="_blank" rel="noreferrer">Annonce</a>
                  <a href="#source-{{ item.source }}">{{ item.source_name }}</a>
                </div>
              </article>
              {% endfor %}
            </div>
            {% else %}
            <div class="empty">Aucun bien exact actuellement pour ce quartier.</div>
            {% endif %}
          </section>
          {% endfor %}
        </details>
      </main>

      <aside class="panel">
        <h2>Etat du scan en temps reel</h2>
        <div class="grid-two">
          <div class="stat-card">
            <span class="small">Biens parses</span>
            <span id="allListingsStat" class="stat-big">{{ all_listings_count }}</span>
          </div>
          <div class="stat-card">
            <span class="small">Dans vos criteres</span>
            <span id="matchesStat" class="stat-big">{{ matches|length }}</span>
          </div>
          <div class="stat-card">
            <span class="small">Nouveautes</span>
            <span id="newMatchesStat" class="stat-big">{{ new_matches|length }}</span>
          </div>
          <div class="stat-card">
            <span class="small">Dernier scan</span>
            <span id="lastScanStat" class="stat-big" style="font-size:20px;">{{ generated_at }}</span>
          </div>
        </div>

        {% if public_mode %}
        <h3>Acces public</h3>
        <p class="small">
          Cette version est faite pour etre partagee. Toute personne avec ce lien voit les annonces exactes du dernier scan publie.
        </p>
        <div class="button-list">
          <button class="linkish" onclick="reloadPublishedSnapshot()">Recharger le snapshot</button>
        </div>
        {% else %}
        <h3>Commande locale</h3>
        <p class="small">
          Dossier: <code>{{ project_root }}</code><br>
          Server: <code>{{ server_url }}</code><br>
          Dashboard statique: <code>{{ dashboard_path }}</code>
        </p>
        <div class="button-list">
          <a href="{{ server_url }}" target="_blank" rel="noreferrer">Ouvrir l'interface live</a>
          <a href="file://{{ dashboard_path }}" target="_blank" rel="noreferrer">Ouvrir le dashboard statique</a>
          <a href="file://{{ project_root }}/open_dashboard.command" target="_blank" rel="noreferrer">Lancer l'interface live</a>
          <a href="file://{{ project_root }}/check_now.command" target="_blank" rel="noreferrer">Forcer un scan</a>
        </div>
        {% endif %}

        <h3>Liens externes exacts verifies</h3>
        <p class="small">
          Ici je ne mets que les liens dont le filtre prix/surface et le tri recent sont directement portes par l'URL.
        </p>
        {% for group in exact_search_groups %}
        <div class="group">
          <strong>{{ group.name }}</strong>
          {% for link in group.links %}
          <div class="search-link">
            <div>
              <div><a href="{{ link.url }}" target="_blank" rel="noreferrer">{{ link.label }}</a></div>
              <div class="small">{{ link.help }}</div>
            </div>
            <div class="search-link-meta">
              <span class="badge status-exact">{{ link.status }}</span>
            </div>
          </div>
          {% endfor %}
        </div>
        {% endfor %}

        <h3>Pages quartier brutes</h3>
        <p class="small">
          Ces liens ouvrent bien les quartiers, mais je ne les marque pas "exacts" quand le site n'expose pas un filtre URL
          fiable pour le prix ou le tri date. La vue interne ci-contre reste la reference propre.
        </p>
        {% for group in raw_search_groups %}
        <div class="group">
          <strong>{{ group.name }}</strong>
          {% for link in group.links %}
          <div class="search-link">
            <div>
              <div><a href="{{ link.url }}" target="_blank" rel="noreferrer">{{ link.label }}</a></div>
              <div class="small">{{ link.help }}</div>
            </div>
            <div class="search-link-meta">
              <span class="badge status-raw">{{ link.status }}</span>
            </div>
          </div>
          {% endfor %}
        </div>
        {% endfor %}

        <h3>Verification officielle</h3>
        <div class="button-list">
          {% for link in official_pages %}
          <a href="{{ link.url }}" target="_blank" rel="noreferrer">{{ link.label }}</a>
          {% endfor %}
        </div>

        <h3>Sources manuelles</h3>
        <div class="button-list">
          {% for link in manual_pages %}
          <a href="{{ link.url }}" target="_blank" rel="noreferrer">{{ link.label }}</a>
          {% endfor %}
        </div>

        <h3>Notes de fiabilite</h3>
        <p class="small">
          <strong>Agenz</strong>: URL verifiees avec filtre prix/surface et tri <code>date_desc</code>.<br>
          <strong>Mubawab</strong>: bonnes pages quartier, mais le site n'applique pas proprement le filtre prix/surface via une simple URL publique stable.<br>
          <strong>MarocAnnonces</strong>: bon complement city-wide, avec dates et images lisibles dans beaucoup de fiches.<br>
          <strong>Avito</strong>: utile a surveiller, mais protection Cloudflare cote bot; conserve ici en source manuelle directe.<br>
          <strong>Yakeey</strong>: source conservee, mais comportement actuellement instable sur certaines pages publiques.
        </p>
      </aside>
    </div>
  </div>

  <script>
    function openMany(urls) {
      if (!Array.isArray(urls) || urls.length === 0) {
        return;
      }
      for (const url of urls) {
        window.open(url, "_blank", "noopener,noreferrer");
      }
    }

    const DEFAULT_FILTERS = {
      minPrice: {{ criteria.min_price_mad }},
      maxPrice: {{ criteria.max_price_mad }},
      minSurface: {{ criteria.min_surface_m2 }},
      maxSurface: {{ criteria.max_surface_m2 }}
    };
    const SNAPSHOT_URL = "{{ snapshot_url }}";
    const INITIAL_MATCHES = {{ matches_json }};
    const INITIAL_NEW_MATCHES = {{ new_matches_json }};
    const INITIAL_AREA_OPTIONS = {{ area_filter_options_json }};
    const INITIAL_SOURCE_OPTIONS = {{ source_filter_options_json }};
    const INITIAL_AMENITY_OPTIONS = {{ amenity_filter_options_json }};

    const amenityLabelMap = Object.fromEntries(
      INITIAL_AMENITY_OPTIONS.map((item) => [item.id, item.label])
    );

    let dashboardState = {
      selectedAreas: new Set(),
      selectedAmenities: new Set(),
      minPrice: DEFAULT_FILTERS.minPrice,
      maxPrice: DEFAULT_FILTERS.maxPrice,
      minSurface: DEFAULT_FILTERS.minSurface,
      maxSurface: DEFAULT_FILTERS.maxSurface,
      sortMode: "latest"
    };

    let currentScanData = normalizeScanData({
      generated_at: "{{ generated_at }}",
      all_listings_count: {{ all_listings_count }},
      matches: INITIAL_MATCHES,
      new_matches: INITIAL_NEW_MATCHES,
      bootstrapped: {{ "true" if bootstrapped else "false" }}
    });

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function formatPrice(priceMad) {
      if (!Number.isFinite(priceMad)) {
        return "Prix non lu";
      }
      return `${priceMad.toLocaleString("fr-FR")} DH`;
    }

    function formatSurface(surfaceM2) {
      if (!Number.isFinite(surfaceM2)) {
        return "Surface non lue";
      }
      return `${surfaceM2} m2`;
    }

    function sourceDisplayName(source, fallback) {
      const match = INITIAL_SOURCE_OPTIONS.find((item) => item.id === source);
      return match?.label || fallback || source || "Source";
    }

    function normalizeListing(item, index, newUrls) {
      const amenityKeys = Array.isArray(item.amenity_keys) ? item.amenity_keys : [];
      const amenityLabels = Array.isArray(item.amenity_labels) && item.amenity_labels.length
        ? item.amenity_labels
        : amenityKeys.map((key) => amenityLabelMap[key] || key);
      return {
        ...item,
        area_guess: item.area_guess || item.location_text || "",
        price_mad: Number.isFinite(item.price_mad) ? item.price_mad : null,
        surface_m2: Number.isFinite(item.surface_m2) ? item.surface_m2 : null,
        photo_count: Number.isFinite(item.photo_count) ? item.photo_count : (item.image_url ? 1 : 0),
        default_sort_index: Number.isFinite(item.default_sort_index) ? item.default_sort_index : index,
        published_at_ts: Number.isFinite(item.published_at_ts) ? item.published_at_ts : null,
        published_label: item.published_label || item.age_label || "",
        price_label: item.price_label || formatPrice(item.price_mad),
        surface_label: item.surface_label || formatSurface(item.surface_m2),
        source_name: sourceDisplayName(item.source, item.source_name),
        image_url: item.image_url || "",
        summary: item.summary || "",
        amenity_keys: amenityKeys,
        amenity_labels: amenityLabels,
        is_new: Boolean(item.is_new || newUrls.has(item.url))
      };
    }

    function normalizeScanData(payload) {
      const newUrls = new Set((payload.new_matches || []).map((item) => item.url));
      const matches = (payload.matches || []).map((item, index) => normalizeListing(item, index, newUrls));
      const countsByArea = {};
      const countsBySource = {};
      for (const item of matches) {
        const areaLabel = item.area_guess || "";
        if (areaLabel) {
          countsByArea[areaLabel] = (countsByArea[areaLabel] || 0) + 1;
        }
        const sourceId = item.source || "";
        if (sourceId) {
          countsBySource[sourceId] = (countsBySource[sourceId] || 0) + 1;
        }
      }

      const areaOptions = INITIAL_AREA_OPTIONS.map((item) => ({ ...item }));
      const knownAreas = new Set(areaOptions.map((item) => item.label));
      for (const option of areaOptions) {
        option.count = countsByArea[option.label] || 0;
      }
      for (const [label, count] of Object.entries(countsByArea)) {
        if (knownAreas.has(label)) {
          continue;
        }
        areaOptions.push({ label, count });
      }
      areaOptions.sort((left, right) => {
        if (right.count !== left.count) {
          return right.count - left.count;
        }
        return left.label.localeCompare(right.label, "fr");
      });

      const sourceOptions = INITIAL_SOURCE_OPTIONS.map((item) => ({ ...item }));
      const knownSources = new Set(sourceOptions.map((item) => item.id));
      for (const option of sourceOptions) {
        option.count = countsBySource[option.id] || 0;
      }
      for (const [id, count] of Object.entries(countsBySource)) {
        if (knownSources.has(id)) {
          continue;
        }
        sourceOptions.push({ id, label: sourceDisplayName(id, ""), count });
      }
      sourceOptions.sort((left, right) => {
        if (right.count !== left.count) {
          return right.count - left.count;
        }
        return left.label.localeCompare(right.label, "fr");
      });

      return {
        generated_at: payload.generated_at || "",
        all_listings_count: payload.all_listings_count || 0,
        matches,
        new_matches: matches.filter((item) => item.is_new),
        bootstrapped: Boolean(payload.bootstrapped),
        area_options: areaOptions,
        source_options: sourceOptions
      };
    }

    function activeFilterSummary() {
      const parts = [];
      if (dashboardState.selectedAreas.size) {
        parts.push(`${dashboardState.selectedAreas.size} quartier(s)`);
      }
      if (dashboardState.selectedAmenities.size) {
        parts.push(`${dashboardState.selectedAmenities.size} equipement(s)`);
      }
      if (!parts.length) {
        return "Aucun filtre quartier/equipement actif";
      }
      return parts.join(" • ");
    }

    function setChipList(containerId, options, selectedSet, getValue) {
      const container = document.getElementById(containerId);
      if (!container) {
        return;
      }
      container.innerHTML = options.map((option) => {
        const value = getValue(option);
        const active = selectedSet.has(value) ? " active" : "";
        return `
          <button class="chip${active}" type="button" data-chip-value="${escapeHtml(value)}">
            ${escapeHtml(option.label)} <span class="small">(${option.count || 0})</span>
          </button>
        `;
      }).join("");
      for (const button of container.querySelectorAll("[data-chip-value]")) {
        button.addEventListener("click", () => {
          const value = button.getAttribute("data-chip-value") || "";
          if (selectedSet.has(value)) {
            selectedSet.delete(value);
          } else {
            selectedSet.add(value);
          }
          renderDashboard();
        });
      }
    }

    function syncNumericControls() {
      const minPriceRange = document.getElementById("minPriceRange");
      const minPriceNumber = document.getElementById("minPriceNumber");
      const maxPriceRange = document.getElementById("maxPriceRange");
      const maxPriceNumber = document.getElementById("maxPriceNumber");
      const minSurfaceRange = document.getElementById("minSurfaceRange");
      const minSurfaceNumber = document.getElementById("minSurfaceNumber");
      const maxSurfaceRange = document.getElementById("maxSurfaceRange");
      const maxSurfaceNumber = document.getElementById("maxSurfaceNumber");
      const sortModeSelect = document.getElementById("sortModeSelect");

      if (!minPriceRange || !minPriceNumber || !maxPriceRange || !maxPriceNumber || !minSurfaceRange || !minSurfaceNumber || !maxSurfaceRange || !maxSurfaceNumber || !sortModeSelect) {
        return;
      }

      minPriceRange.value = String(dashboardState.minPrice);
      minPriceNumber.value = String(dashboardState.minPrice);
      maxPriceRange.value = String(dashboardState.maxPrice);
      maxPriceNumber.value = String(dashboardState.maxPrice);
      minSurfaceRange.value = String(dashboardState.minSurface);
      minSurfaceNumber.value = String(dashboardState.minSurface);
      maxSurfaceRange.value = String(dashboardState.maxSurface);
      maxSurfaceNumber.value = String(dashboardState.maxSurface);
      sortModeSelect.value = dashboardState.sortMode;
    }

    function listingVisible(item) {
      if (dashboardState.selectedAreas.size && !dashboardState.selectedAreas.has(item.area_guess)) {
        return false;
      }
      if (dashboardState.selectedAmenities.size) {
        for (const amenity of dashboardState.selectedAmenities) {
          if (!item.amenity_keys.includes(amenity)) {
            return false;
          }
        }
      }
      if (Number.isFinite(item.price_mad) && item.price_mad < dashboardState.minPrice) {
        return false;
      }
      if (Number.isFinite(item.price_mad) && item.price_mad > dashboardState.maxPrice) {
        return false;
      }
      if (!Number.isFinite(item.surface_m2)) {
        return false;
      }
      if (item.surface_m2 < dashboardState.minSurface || item.surface_m2 > dashboardState.maxSurface) {
        return false;
      }
      return true;
    }

    function compareListings(left, right) {
      switch (dashboardState.sortMode) {
        case "price_asc":
          return (left.price_mad ?? Number.MAX_SAFE_INTEGER) - (right.price_mad ?? Number.MAX_SAFE_INTEGER);
        case "price_desc":
          return (right.price_mad ?? -1) - (left.price_mad ?? -1);
        case "surface_desc":
          return (right.surface_m2 ?? -1) - (left.surface_m2 ?? -1);
        case "latest":
        default: {
          const leftTs = left.published_at_ts ?? null;
          const rightTs = right.published_at_ts ?? null;
          if (leftTs !== rightTs) {
            return (rightTs ?? -1) - (leftTs ?? -1);
          }
          return (left.default_sort_index ?? 9999) - (right.default_sort_index ?? 9999);
        }
      }
    }

    function visibleListings() {
      return currentScanData.matches.filter(listingVisible).sort(compareListings);
    }

    function listingBadges(item) {
      const badges = [];
      if (item.is_new) {
        badges.push('<span class="badge new">Nouveau</span>');
      }
      if (item.area_guess) {
        badges.push(`<span class="badge">${escapeHtml(item.area_guess)}</span>`);
      }
      if (item.published_label) {
        badges.push(`<span class="badge">${escapeHtml(item.published_label)}</span>`);
      }
      if (item.photo_count) {
        badges.push(`<span class="badge">${item.photo_count} photo(s)</span>`);
      }
      return badges.join("");
    }

    function listingFeatures(item) {
      const features = [];
      if (item.rooms_label) {
        features.push(`<span><strong>Pieces:</strong> ${escapeHtml(item.rooms_label)}</span>`);
      }
      if (item.bedrooms_label) {
        features.push(`<span><strong>Ch:</strong> ${escapeHtml(item.bedrooms_label)}</span>`);
      }
      if (item.bathrooms_label) {
        features.push(`<span><strong>Sdb:</strong> ${escapeHtml(item.bathrooms_label)}</span>`);
      }
      return features.join("");
    }

    function listingAmenityPills(item) {
      return item.amenity_labels.map((label) => {
        return `<span class="feature-pill">${escapeHtml(label)}</span>`;
      }).join("");
    }

    function thumbFallbackMarkup(item) {
      const message = item.source === "agenz"
        ? "Photo protegee par la source. Ouvrez l'annonce pour la voir."
        : "Photo non chargee. Ouvrez l'annonce source pour la voir.";
      return `
        <div class="thumb-fallback" ${item.image_url ? 'style="display:none"' : ""}>
          <div>
            <strong>${item.photo_count ? `${item.photo_count} photo(s)` : "Apercu indisponible"}</strong>
            <span>${escapeHtml(message)}</span>
          </div>
        </div>
      `;
    }

    function renderRows(listings) {
      const container = document.getElementById("mixedRows");
      if (!container) {
        return;
      }
      if (!listings.length) {
        container.innerHTML = '<div class="empty">Aucune annonce visible avec ces filtres.</div>';
        return;
      }
      container.innerHTML = listings.map((item) => {
        const thumb = item.image_url
          ? `
            <img
              src="${escapeHtml(item.image_url)}"
              alt="${escapeHtml(item.title)}"
              loading="lazy"
              referrerpolicy="no-referrer"
              onerror="this.style.display='none'; const fallback=this.parentElement.querySelector('.thumb-fallback'); if (fallback) fallback.style.display='grid';"
            >
            ${thumbFallbackMarkup(item)}
          `
          : thumbFallbackMarkup(item);
        const amenities = listingAmenityPills(item);
        const summary = item.summary ? `<p class="small">${escapeHtml(item.summary)}</p>` : "";
        return `
          <article class="listing-row">
            <div class="thumb">${thumb}</div>
            <div class="listing-copy">
              <div class="listing-topline">
                <div>
                  <div class="badge-row">${listingBadges(item)}</div>
                  <h3>${escapeHtml(item.title)}</h3>
                </div>
                <div class="listing-links">
                  <div class="listing-source-note">Annonce sur ${escapeHtml(item.source_name)}</div>
                  <a class="listing-cta" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">Voir l'annonce</a>
                </div>
              </div>
              <div class="kv">
                <span><strong>Prix:</strong> ${escapeHtml(item.price_label)}</span>
                <span><strong>Surface:</strong> ${escapeHtml(item.surface_label)}</span>
                ${listingFeatures(item)}
              </div>
              ${amenities ? `<div class="feature-row">${amenities}</div>` : ""}
              ${summary}
            </div>
          </article>
        `;
      }).join("");
    }

    function updateCounters(listings) {
      const summary = document.getElementById("mixedSummary");
      const generatedAt = document.getElementById("heroGeneratedAt");
      const heroMatches = document.getElementById("heroMatchesCount");
      const allListingsStat = document.getElementById("allListingsStat");
      const matchesStat = document.getElementById("matchesStat");
      const newMatchesStat = document.getElementById("newMatchesStat");
      const lastScanStat = document.getElementById("lastScanStat");

      if (summary) {
        summary.textContent = `${listings.length} annonce(s) visibles sur ${currentScanData.matches.length} match(s). ${activeFilterSummary()}.`;
      }
      if (generatedAt) {
        generatedAt.textContent = `Dernier scan: ${currentScanData.generated_at || "n/a"}`;
      }
      if (heroMatches) {
        heroMatches.textContent = `Matches: ${currentScanData.matches.length}`;
      }
      if (allListingsStat) {
        allListingsStat.textContent = String(currentScanData.all_listings_count || 0);
      }
      if (matchesStat) {
        matchesStat.textContent = String(currentScanData.matches.length);
      }
      if (newMatchesStat) {
        newMatchesStat.textContent = String(currentScanData.new_matches.length);
      }
      if (lastScanStat) {
        lastScanStat.textContent = currentScanData.generated_at || "n/a";
      }
    }

    function renderDashboard() {
      syncNumericControls();
      setChipList("areaFilters", currentScanData.area_options, dashboardState.selectedAreas, (item) => item.label);
      setChipList("amenityFilters", INITIAL_AMENITY_OPTIONS.map((item) => ({ ...item, count: currentScanData.matches.filter((listing) => listing.amenity_keys.includes(item.id)).length })), dashboardState.selectedAmenities, (item) => item.id);
      const listings = visibleListings();
      renderRows(listings);
      updateCounters(listings);
    }

    function readInteger(value, fallback) {
      const parsed = Number.parseInt(String(value || ""), 10);
      return Number.isFinite(parsed) ? parsed : fallback;
    }

    function bindControls() {
      const minPriceRange = document.getElementById("minPriceRange");
      const minPriceNumber = document.getElementById("minPriceNumber");
      const maxPriceRange = document.getElementById("maxPriceRange");
      const maxPriceNumber = document.getElementById("maxPriceNumber");
      const minSurfaceRange = document.getElementById("minSurfaceRange");
      const minSurfaceNumber = document.getElementById("minSurfaceNumber");
      const maxSurfaceRange = document.getElementById("maxSurfaceRange");
      const maxSurfaceNumber = document.getElementById("maxSurfaceNumber");
      const sortModeSelect = document.getElementById("sortModeSelect");

      const setMinPrice = (value) => {
        dashboardState.minPrice = Math.max(0, readInteger(value, DEFAULT_FILTERS.minPrice));
        if (dashboardState.minPrice > dashboardState.maxPrice) {
          dashboardState.maxPrice = dashboardState.minPrice;
        }
        renderDashboard();
      };
      const setMaxPrice = (value) => {
        dashboardState.maxPrice = Math.max(0, readInteger(value, DEFAULT_FILTERS.maxPrice));
        if (dashboardState.maxPrice < dashboardState.minPrice) {
          dashboardState.minPrice = dashboardState.maxPrice;
        }
        renderDashboard();
      };
      const setMinSurface = (value) => {
        dashboardState.minSurface = Math.max(0, readInteger(value, DEFAULT_FILTERS.minSurface));
        if (dashboardState.minSurface > dashboardState.maxSurface) {
          dashboardState.maxSurface = dashboardState.minSurface;
        }
        renderDashboard();
      };
      const setMaxSurface = (value) => {
        dashboardState.maxSurface = Math.max(0, readInteger(value, DEFAULT_FILTERS.maxSurface));
        if (dashboardState.maxSurface < dashboardState.minSurface) {
          dashboardState.minSurface = dashboardState.maxSurface;
        }
        renderDashboard();
      };

      minPriceRange?.addEventListener("input", (event) => setMinPrice(event.target.value));
      minPriceNumber?.addEventListener("change", (event) => setMinPrice(event.target.value));
      maxPriceRange?.addEventListener("input", (event) => setMaxPrice(event.target.value));
      maxPriceNumber?.addEventListener("change", (event) => setMaxPrice(event.target.value));
      minSurfaceRange?.addEventListener("input", (event) => setMinSurface(event.target.value));
      minSurfaceNumber?.addEventListener("change", (event) => setMinSurface(event.target.value));
      maxSurfaceRange?.addEventListener("input", (event) => setMaxSurface(event.target.value));
      maxSurfaceNumber?.addEventListener("change", (event) => setMaxSurface(event.target.value));
      sortModeSelect?.addEventListener("change", (event) => {
        dashboardState.sortMode = event.target.value || "latest";
        renderDashboard();
      });
    }

    function openNewListings() {
      openMany(currentScanData.new_matches.map((item) => item.url));
    }

    function openAllCurrentListings() {
      openMany(currentScanData.matches.map((item) => item.url));
    }

    function resetDashboardFilters() {
      dashboardState = {
        selectedAreas: new Set(),
        selectedAmenities: new Set(),
        minPrice: DEFAULT_FILTERS.minPrice,
        maxPrice: DEFAULT_FILTERS.maxPrice,
        minSurface: DEFAULT_FILTERS.minSurface,
        maxSurface: DEFAULT_FILTERS.maxSurface,
        sortMode: "latest"
      };
      renderDashboard();
    }

    async function loadSnapshot(url) {
      const response = await fetch(`${url}?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Fetch failed: ${response.status}`);
      }
      return response.json();
    }

    async function reloadPublishedSnapshot() {
      const button = document.getElementById("refreshButton");
      const original = button?.textContent || "Actualiser";
      if (button) {
        button.disabled = true;
        button.textContent = "Actualisation...";
      }
      try {
        const payload = await loadSnapshot(SNAPSHOT_URL);
        currentScanData = normalizeScanData(payload);
        renderDashboard();
      } catch (error) {
        alert("Impossible de recharger le dernier snapshot publie.");
      } finally {
        if (button) {
          button.disabled = false;
          button.textContent = original;
        }
      }
    }

    async function refreshNow() {
      const button = document.getElementById("refreshButton");
      if (!button) return;
      const original = button.textContent;
      button.disabled = true;
      button.textContent = "Actualisation...";
      try {
        const response = await fetch("/api/scan", { method: "POST" });
        if (!response.ok) {
          throw new Error("Scan failed");
        }
        currentScanData = normalizeScanData(await loadSnapshot("/api/state"));
        renderDashboard();
      } catch (error) {
        alert("Le scan a echoue. Regardez le terminal si besoin.");
      } finally {
        button.disabled = false;
        button.textContent = original;
      }
    }

    bindControls();
    renderDashboard();
  </script>
</body>
</html>
"""
)


@dataclass
class Listing:
    source: str
    source_name: str
    source_page: str
    url: str
    title: str
    price_mad: int | None
    surface_m2: int | None
    location_text: str
    area_guess: str
    rooms_label: str
    bedrooms_label: str
    bathrooms_label: str
    age_label: str
    summary: str
    rank_in_source: int
    source_listing_id: str
    image_url: str = ""
    photo_count: int = 0
    amenity_keys: list[str] = field(default_factory=list)
    published_at_ts: int | None = None
    is_new: bool = False
    first_seen_at: str = ""

    @property
    def price_label(self) -> str:
        if self.price_mad is None:
            return "Prix non lu"
        return f"{self.price_mad:,}".replace(",", " ") + " DH"

    @property
    def surface_label(self) -> str:
        if self.surface_m2 is None:
            return "Surface non lue"
        return f"{self.surface_m2} m2"


def normalize_spaces(value: str) -> str:
    value = (
        value.replace("\xa0", " ")
        .replace("\u202f", " ")
        .replace("\u200e", " ")
        .replace("\u2019", "'")
    )
    return " ".join(value.split())


def ascii_fold(value: str) -> str:
    replacements = {
        "à": "a",
        "â": "a",
        "ä": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ö": "o",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
    }
    folded = value.lower()
    for old, new in replacements.items():
        folded = folded.replace(old, new)
    return folded


def visible_text(node: Any) -> str:
    texts = node.xpath(".//text()[not(ancestor::script) and not(ancestor::style)]")
    return normalize_spaces(" ".join(texts))


def unique_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def slugify_fragment(value: str) -> str:
    value = value.lower()
    replacements = {
        "à": "a",
        "â": "a",
        "ä": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ö": "o",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
        "'": "",
        "/": "-",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "zone"


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def fetch_html(url: str) -> str:
    with httpx.Client(
        headers={"user-agent": USER_AGENT},
        follow_redirects=True,
        timeout=TIMEOUT,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def parse_price_mad(text: str) -> int | None:
    cleaned = normalize_spaces(text)
    matches = []
    for match in re.finditer(r"(\d[\d\s]*)\s*DH", cleaned, flags=re.IGNORECASE):
        after = cleaned[match.end() : match.end() + 10].lower()
        if "/mois" in after:
            continue
        raw_int = int(re.sub(r"[^\d]", "", match.group(1)))
        if raw_int > 0:
            matches.append(raw_int)
    if not matches:
        return None
    return max(matches)


def parse_surface_m2(text: str) -> int | None:
    cleaned = normalize_spaces(text)
    matches = [
        int(match)
        for match in re.findall(r"\b(\d{2,3})\s*m[²2]\b", cleaned, flags=re.IGNORECASE)
    ]
    if not matches:
        return None
    return min(matches)


def parse_rooms_label(text: str) -> str:
    match = re.search(r"\b(\d+)\s*Pi[eè]ces?\b", normalize_spaces(text), flags=re.IGNORECASE)
    return match.group(1) if match else ""


def parse_bedrooms_label(text: str) -> str:
    cleaned = normalize_spaces(text)
    for pattern in [
        r"\b(\d+)\s*Ch\.\b",
        r"\b(\d+)\s*CH\b",
        r"\b(\d+)\s*chambres?\b",
    ]:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def parse_bathrooms_label(text: str) -> str:
    cleaned = normalize_spaces(text)
    for pattern in [
        r"\b(\d+)\s*SDB\b",
        r"\b(\d+)\s*Salles? de bains?\b",
        r"\b(\d+)\s*Salle de bain\b",
        r"\b(\d+)\s*bathroom\b",
    ]:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def normalize_date_label(text: str) -> str:
    cleaned = normalize_spaces(text)
    cleaned = cleaned.replace("Publiée le:", "").replace("Publiee le:", "").strip()
    return cleaned


def parse_age_label(text: str) -> str:
    cleaned = normalize_spaces(text)
    patterns = [
        r"\b[Ii]l y a (?:un|une|\d+)\s+(?:heure|heures|jour|jours|mois|an|ans)\b",
        r"\b[Aa]ujourd'hui\s+\d{1,2}:\d{2}\b",
        r"\bHier\s+\d{1,2}:\d{2}\b",
        r"\b\d{1,2}\s+[A-Za-zéûôî\.]+\s*-\s*\d{1,2}:\d{2}\b",
        r"\ba day ago\b",
        r"\b\d+\s+days?\s+ago\b",
        r"\b\d+\s+months?\s+ago\b",
        r"\b\d+\s+years?\s+ago\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return ""


def parse_relative_age_seconds(label: str) -> int | None:
    cleaned = normalize_spaces(label).lower()
    if not cleaned:
        return None

    def number_from_label(text: str) -> int | None:
        if "un" in text or "une" in text or text == "a day ago":
            return 1
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else None

    amount = number_from_label(cleaned)
    if amount is None:
        return None
    if "heure" in cleaned:
        return amount * 3600
    if "jour" in cleaned or "day" in cleaned:
        return amount * 86400
    if "mois" in cleaned or "month" in cleaned:
        return amount * 30 * 86400
    if "an" in cleaned or "year" in cleaned:
        return amount * 365 * 86400
    return None


def parse_absolute_age_ts(label: str) -> int | None:
    cleaned = normalize_date_label(label)
    folded = ascii_fold(cleaned).replace(".", "")
    now = dt.datetime.now(dt.timezone.utc)

    today_match = re.search(r"aujourd'hui\s+(\d{1,2}):(\d{2})", cleaned, flags=re.IGNORECASE)
    if today_match:
        published = now.astimezone().replace(
            hour=int(today_match.group(1)),
            minute=int(today_match.group(2)),
            second=0,
            microsecond=0,
        )
        return int(published.timestamp())

    yesterday_match = re.search(r"hier\s+(\d{1,2}):(\d{2})", cleaned, flags=re.IGNORECASE)
    if yesterday_match:
        published = now.astimezone() - dt.timedelta(days=1)
        published = published.replace(
            hour=int(yesterday_match.group(1)),
            minute=int(yesterday_match.group(2)),
            second=0,
            microsecond=0,
        )
        return int(published.timestamp())

    absolute_match = re.search(
        r"(\d{1,2})\s+([a-zéûôî]+)\s*-?\s*(\d{1,2}:\d{2})?",
        folded,
        flags=re.IGNORECASE,
    )
    if not absolute_match:
        return None
    day = int(absolute_match.group(1))
    month_name = absolute_match.group(2).lower()
    month = MAROCANNONCES_MONTHS.get(month_name)
    if not month:
        return None
    year = now.year
    hour = 0
    minute = 0
    if absolute_match.group(3):
        hour, minute = [int(part) for part in absolute_match.group(3).split(":")]
    try:
        published = dt.datetime(year, month, day, hour, minute, tzinfo=now.astimezone().tzinfo)
    except ValueError:
        return None
    if published > now.astimezone() + dt.timedelta(hours=2):
        published = published.replace(year=year - 1)
    return int(published.timestamp())


def derive_published_ts(label: str) -> int | None:
    relative_seconds = parse_relative_age_seconds(label)
    if relative_seconds is not None:
        return int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=relative_seconds)).timestamp())
    return parse_absolute_age_ts(label)


def parse_numeric_id(value: str) -> int | None:
    matches = re.findall(r"(\d+)", value or "")
    if not matches:
        return None
    return int(matches[-1])


def extract_amenity_keys(text: str) -> list[str]:
    cleaned = normalize_spaces(text)
    keys = []
    for key, pattern in AMENITY_PATTERNS.items():
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            keys.append(key)
    return keys


def amenity_labels(keys: list[str]) -> list[str]:
    return [AMENITY_LABELS[key] for key in keys if key in AMENITY_LABELS]


def first_image_url(urls: list[str]) -> str:
    for url in unique_preserve(urls):
        if url.startswith("http"):
            return url
    return ""


def slug_to_title(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1]
    tail = re.sub(r"-(ca|pn)\d+$", "", tail, flags=re.IGNORECASE)
    tail = re.sub(r"^[a-z]{2}-ma-", "", tail)
    return tail.replace("-", " ").strip().title() or url


def compile_area_alias_pattern(alias: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in re.split(r"[\s-]+", alias) if part]
    pattern = r"[-\s]+".join(parts)
    return re.compile(rf"(?<!\w){pattern}(?!\w)", flags=re.IGNORECASE)


def area_candidates(config: dict[str, Any]) -> list[tuple[int, str, re.Pattern[str]]]:
    candidates: list[tuple[int, str, re.Pattern[str]]] = []
    for area in config["areas"]:
        aliases = list(area["aliases"]) + [area["label"]]
        for alias in aliases:
            normalized_alias = normalize_spaces(alias).lower()
            if not normalized_alias:
                continue
            candidates.append(
                (len(normalized_alias), area["label"], compile_area_alias_pattern(normalized_alias))
            )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates


def find_area_match(text: str, config: dict[str, Any]) -> str:
    cleaned = normalize_spaces(text).lower()
    candidates = area_candidates(config)
    for _, label, pattern in candidates:
        if pattern.search(cleaned):
            return label
    return ""


def score_area_match(fields: list[tuple[str, int]], config: dict[str, Any]) -> str:
    candidates = area_candidates(config)
    scores: dict[str, int] = {}
    longest_hits: dict[str, int] = {}
    for text, weight in fields:
        cleaned = normalize_spaces(text).lower()
        if not cleaned:
            continue
        matched_lengths: dict[str, int] = {}
        for alias_length, label, pattern in candidates:
            if pattern.search(cleaned):
                matched_lengths[label] = max(matched_lengths.get(label, 0), alias_length)
        for label, alias_length in matched_lengths.items():
            scores[label] = scores.get(label, 0) + weight
            longest_hits[label] = max(longest_hits.get(label, 0), alias_length)
    if not scores:
        return ""
    return max(scores, key=lambda label: (scores[label], longest_hits.get(label, 0), label))


def guess_listing_area(
    title: str,
    url: str,
    location_text: str,
    summary: str,
    config: dict[str, Any],
) -> str:
    return score_area_match(
        [
            (title, 5),
            (url, 4),
            (location_text, 3),
            (summary, 1),
        ],
        config,
    )


def find_area_guess(text: str, config: dict[str, Any]) -> str:
    return find_area_match(text, config)


def parse_agenz_location_text(title: str, text: str) -> str:
    cleaned_title = normalize_spaces(title)
    if cleaned_title:
        location = re.sub(r"^(studio|appartement|duplex|penthouse|loft)\s+à\s+vendre\s+", "", cleaned_title, flags=re.IGNORECASE)
        location = re.sub(r"^casablanca\s*-\s*", "", location, flags=re.IGNORECASE)
        return location.strip() or cleaned_title
    return make_summary(text, limit=90)


def make_summary(text: str, limit: int = 220) -> str:
    cleaned = normalize_spaces(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def criteria_query(config: dict[str, Any]) -> dict[str, str]:
    criteria = config["criteria"]
    return {
        "prixmax": str(criteria["max_price_mad"]),
        "surfacemin": str(criteria["min_surface_m2"]),
        "surfacemax": str(criteria["max_surface_m2"]),
        "sort": "date_desc",
    }


def build_agenz_city_url(config: dict[str, Any]) -> str:
    base = "https://agenz.ma/fr/acheter/immo-casablanca/vente-appartements"
    query = criteria_query(config)
    query_string = "&".join(f"{key}={quote(value)}" for key, value in query.items())
    return f"{base}?{query_string}"


def build_agenz_area_url(area: dict[str, Any], config: dict[str, Any]) -> str | None:
    slug = area.get("agenz_slug")
    if not slug:
        return None
    base = f"https://agenz.ma/fr/acheter/immo-casablanca/vente-appartements/{slug}"
    query = criteria_query(config)
    query_string = "&".join(f"{key}={quote(value)}" for key, value in query.items())
    return f"{base}?{query_string}"


def build_mubawab_area_url(area: dict[str, Any]) -> str | None:
    slug = area.get("mubawab_slug")
    if not slug:
        return None
    return f"https://www.mubawab.ma/fr/sd/casablanca/{slug}/appartements-a-vendre"


def build_mubawab_city_url() -> str:
    return "https://www.mubawab.ma/fr/st/casablanca/appartements-a-vendre"


def build_yakeey_area_url(area: dict[str, Any], with_filter_hint: bool = True) -> str | None:
    slug = area.get("yakeey_slug")
    if not slug:
        return None
    base = f"https://yakeey.com/fr-ma/achat/appartement/casablanca/{slug}"
    if not with_filter_hint:
        return base
    return base + "?sortBy=dateDesc"


def build_marocannonces_city_url(page_number: int) -> str:
    return f"https://www.marocannonces.com/maroc/vente-appartements-casablanca-b315-t563.html?pge={page_number}"


def build_scan_pages(config: dict[str, Any]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []

    if config["scan_sites"].get("agenz", True):
        pages.append(
            {
                "parser": "agenz",
                "label": "Agenz Casablanca",
                "area_label": "Casablanca",
                "url": build_agenz_city_url(config),
            }
        )

    if config["scan_sites"].get("mubawab", True):
        pages.append(
            {
                "parser": "mubawab",
                "label": "Mubawab Casablanca",
                "area_label": "Casablanca",
                "url": build_mubawab_city_url(),
            }
        )

    if config["scan_sites"].get("yakeey", True):
        for area in config["areas"]:
            url = build_yakeey_area_url(area, with_filter_hint=True)
            if not url:
                continue
            pages.append(
                {
                    "parser": "yakeey",
                    "label": f"Yakeey {area['label']}",
                    "area_label": area["label"],
                    "url": url,
                }
            )

    if config["scan_sites"].get("marocannonces", True):
        max_pages = int(config.get("scan_limits", {}).get("marocannonces_pages", 2))
        for page_number in range(1, max_pages + 1):
            pages.append(
                {
                    "parser": "marocannonces",
                    "label": f"MarocAnnonces Casablanca page {page_number}",
                    "area_label": "Casablanca",
                    "url": build_marocannonces_city_url(page_number),
                }
            )

    return pages


def scrape_agenz(page: dict[str, Any], config: dict[str, Any]) -> list[Listing]:
    doc = html.fromstring(fetch_html(page["url"]))
    listings: list[Listing] = []
    for rank, card in enumerate(doc.xpath('//div[@data-card-wrapper="true"]'), start=1):
        data_url = card.attrib.get("data-url", "")
        if not data_url or data_url.endswith("/video"):
            continue
        text = visible_text(card)
        url = urljoin(page["url"], data_url)
        title = normalize_spaces(" ".join(card.xpath('.//a[contains(@href, "/annonces/")][1]//text()')))
        source_listing_id = card.attrib.get("data-id", url.split("/")[-1])
        published_label = normalize_date_label(
            normalize_spaces(" ".join(card.xpath('.//*[contains(@class, "dateCreationList")]//text()')))
        )
        image_urls = unique_preserve(
            card.xpath('.//img[contains(@src, "media.agenz.ma")]/@src')
            + card.xpath('.//img[contains(@srcset, "media.agenz.ma")]/@src')
        )
        listings.append(
            Listing(
                source="agenz",
                source_name=page["label"],
                source_page=page["url"],
                url=url,
                title=title or slug_to_title(url),
                price_mad=parse_price_mad(text),
                surface_m2=parse_surface_m2(text),
                location_text=parse_agenz_location_text(title, text),
                area_guess="",
                rooms_label=parse_rooms_label(text),
                bedrooms_label=parse_bedrooms_label(text),
                bathrooms_label=parse_bathrooms_label(text),
                age_label=published_label or parse_age_label(text),
                summary=make_summary(text),
                rank_in_source=rank,
                source_listing_id=source_listing_id,
                image_url=first_image_url(image_urls),
                photo_count=len(image_urls),
                amenity_keys=extract_amenity_keys(text),
                published_at_ts=derive_published_ts(published_label or parse_age_label(text)),
            )
        )
    for item in listings:
        item.area_guess = guess_listing_area(item.title, item.url, item.location_text, item.summary, config)
    return listings


def scrape_mubawab(page: dict[str, Any], config: dict[str, Any]) -> list[Listing]:
    doc = html.fromstring(fetch_html(page["url"]).encode("utf-8"))
    listings: list[Listing] = []
    for rank, card in enumerate(doc.xpath('//div[contains(@class, "listingBox")][@linkref]'), start=1):
        url = card.attrib.get("linkref", "").strip()
        if not url:
            continue
        text = visible_text(card)
        title = normalize_spaces(" ".join(card.xpath(".//h2//a//text()")))
        location_text = normalize_spaces(" ".join(card.xpath('.//*[contains(@class, "listingH3")]//text()')))
        source_listing_id = (
            normalize_spaces(" ".join(card.xpath('.//input[contains(@class, "adId")]/@value')))
            or url.split("/a/")[-1].split("/")[0]
        )
        image_urls = unique_preserve(
            card.xpath('.//img[contains(@class, "sliderImage")]/@data-lazy')
            + card.xpath('.//img[contains(@class, "sliderImage")]/@data-url')
            + card.xpath('.//img[contains(@class, "sliderImage")]/@src')
        )
        listings.append(
            Listing(
                source="mubawab",
                source_name=page["label"],
                source_page=page["url"],
                url=url,
                title=title or slug_to_title(url),
                price_mad=parse_price_mad(text),
                surface_m2=parse_surface_m2(text),
                location_text=location_text,
                area_guess="",
                rooms_label=parse_rooms_label(text),
                bedrooms_label=parse_bedrooms_label(text),
                bathrooms_label=parse_bathrooms_label(text),
                age_label=parse_age_label(text),
                summary=make_summary(text),
                rank_in_source=rank,
                source_listing_id=source_listing_id,
                image_url=first_image_url(image_urls),
                photo_count=len(image_urls),
                amenity_keys=extract_amenity_keys(text),
            )
        )
    for item in listings:
        item.area_guess = guess_listing_area(item.title, item.url, item.location_text, item.summary, config)
    return listings


def looks_like_listing_card_text(text: str) -> bool:
    cleaned = normalize_spaces(text)
    return "DH" in cleaned and ("m2" in cleaned.lower() or "m²" in cleaned.lower())


def nearest_interesting_ancestor(node: Any) -> Any:
    current = node
    best = node
    for _ in range(8):
        if current is None:
            break
        text = visible_text(current)
        if looks_like_listing_card_text(text):
            best = current
        current = current.getparent()
    return best


def scrape_yakeey(page: dict[str, Any], config: dict[str, Any]) -> list[Listing]:
    doc = html.fromstring(fetch_html(page["url"]))
    listings: list[Listing] = []
    seen_urls: set[str] = set()
    anchors = doc.xpath('//a[contains(@href, "/fr-ma/acheter-appartement-casablanca-")]')
    rank = 0
    for anchor in anchors:
        href = anchor.attrib.get("href", "")
        if not href:
            continue
        url = urljoin(page["url"], href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        card = nearest_interesting_ancestor(anchor)
        text = visible_text(card)
        if "Casablanca" not in text or "DH" not in text:
            continue
        rank += 1
        listings.append(
            Listing(
                source="yakeey",
                source_name=page["label"],
                source_page=page["url"],
                url=url,
                title=slug_to_title(url),
                price_mad=parse_price_mad(text),
                surface_m2=parse_surface_m2(text),
                location_text=text,
                area_guess="",
                rooms_label=parse_rooms_label(text),
                bedrooms_label=parse_bedrooms_label(text),
                bathrooms_label=parse_bathrooms_label(text),
                age_label=parse_age_label(text),
                summary=make_summary(text),
                rank_in_source=rank,
                source_listing_id=url.rstrip("/").split("-")[-1],
                amenity_keys=extract_amenity_keys(text),
            )
        )
    for item in listings:
        item.area_guess = guess_listing_area(item.title, item.url, item.location_text, item.summary, config)
    return listings


def scrape_marocannonces(page: dict[str, Any], config: dict[str, Any]) -> list[Listing]:
    doc = html.fromstring(fetch_html(page["url"]))
    listings: list[Listing] = []
    for rank, row in enumerate(doc.xpath('//li[a[div[@class="holder"]]]'), start=1):
        link = row.xpath('./a[div[@class="holder"]][1]')
        if not link:
            continue
        anchor = link[0]
        url = urljoin(page["url"], anchor.attrib.get("href", "").strip())
        title = normalize_spaces(anchor.attrib.get("title", "") or " ".join(anchor.xpath('.//h3//text()')))
        location_text = normalize_spaces(" ".join(anchor.xpath('.//span[contains(@class, "location")]//text()')))
        price_text = normalize_spaces(" ".join(anchor.xpath('.//strong[contains(@class, "price")]//text()')))
        image_candidates = unique_preserve(
            [urljoin(page["url"], src) for src in anchor.xpath('.//img/@data-original')]
            + [urljoin(page["url"], src) for src in anchor.xpath('.//img/@src')]
        )
        published_label = normalize_date_label(
            normalize_spaces(" ".join(row.xpath('.//div[contains(@class, "time")]//text()')))
        )
        description_text = ""
        page_text = visible_text(row)
        try:
            detail_text = fetch_html(url)
            detail_doc = html.fromstring(detail_text)
            description_bits = [
                item
                for item in detail_doc.xpath('//div[contains(@class, "description")]//text()')
                if normalize_spaces(item)
            ]
            description_text = normalize_spaces(" ".join(description_bits))
            page_text = visible_text(detail_doc)
        except Exception:
            pass
        searchable_text = normalize_spaces(" ".join([price_text, location_text, description_text, page_text]))
        source_listing_id = url.rstrip("/").split("/")[-2] if "/annonce/" in url else url.rstrip("/").split("/")[-1]
        listings.append(
            Listing(
                source="marocannonces",
                source_name=page["label"],
                source_page=page["url"],
                url=url,
                title=title or slug_to_title(url),
                price_mad=parse_price_mad(price_text or searchable_text),
                surface_m2=parse_surface_m2(searchable_text),
                location_text=location_text,
                area_guess="",
                rooms_label=parse_rooms_label(searchable_text),
                bedrooms_label=parse_bedrooms_label(searchable_text),
                bathrooms_label=parse_bathrooms_label(searchable_text),
                age_label=published_label,
                summary=make_summary(description_text or searchable_text),
                rank_in_source=rank,
                source_listing_id=source_listing_id,
                image_url=first_image_url(image_candidates),
                photo_count=len(image_candidates),
                amenity_keys=extract_amenity_keys(searchable_text),
                published_at_ts=derive_published_ts(published_label),
            )
        )
    for item in listings:
        item.area_guess = guess_listing_area(item.title, item.url, item.location_text, item.summary, config)
    return listings


SCRAPERS = {
    "agenz": scrape_agenz,
    "mubawab": scrape_mubawab,
    "marocannonces": scrape_marocannonces,
    "yakeey": scrape_yakeey,
}


def dedupe_listings(listings: list[Listing]) -> list[Listing]:
    deduped: dict[str, Listing] = {}
    for item in listings:
        current = deduped.get(item.url)
        if current is None:
            deduped[item.url] = item
            continue
        if item.rank_in_source < current.rank_in_source:
            deduped[item.url] = item
    return list(deduped.values())


def listing_matches(listing: Listing, config: dict[str, Any]) -> bool:
    criteria = config["criteria"]
    min_price_mad = int(criteria.get("min_price_mad", 0))
    if listing.price_mad is None or listing.price_mad < min_price_mad or listing.price_mad > criteria["max_price_mad"]:
        return False
    if listing.surface_m2 is None:
        return False
    if listing.surface_m2 < criteria["min_surface_m2"] or listing.surface_m2 > criteria["max_surface_m2"]:
        return False

    searchable = normalize_spaces(
        " ".join(
            [
                listing.title,
                listing.location_text,
                listing.area_guess,
                listing.summary,
                listing.url,
            ]
        )
    ).lower()

    if re.search(r"\b(a louer|à louer|location)\b", searchable, flags=re.IGNORECASE):
        return False
    if "casablanca" not in searchable and "cfc" not in searchable:
        return False

    matched_area = guess_listing_area(
        listing.title,
        listing.url,
        listing.location_text,
        listing.summary,
        config,
    )
    if not matched_area:
        return False
    listing.area_guess = matched_area

    all_keywords = [item.lower() for item in criteria.get("required_keywords_all", [])]
    any_keywords = [item.lower() for item in criteria.get("required_keywords_any", [])]
    excluded_keywords = [item.lower() for item in criteria.get("excluded_keywords", [])]

    if any(keyword not in searchable for keyword in all_keywords):
        return False
    if any_keywords and not any(keyword in searchable for keyword in any_keywords):
        return False
    if any(keyword in searchable for keyword in excluded_keywords):
        return False
    return True


def load_state() -> dict[str, Any]:
    default = {"schema": 1, "seen": {}}
    state = load_json(STATE_PATH, default)
    if "seen" not in state:
        state = default
    return state


def update_state(listings: list[Listing], state: dict[str, Any]) -> tuple[list[Listing], bool]:
    now = now_iso()
    bootstrapped = not bool(state["seen"])
    new_matches: list[Listing] = []
    for listing in listings:
        seen_entry = state["seen"].get(listing.url)
        if seen_entry is None:
            state["seen"][listing.url] = {
                "first_seen_at": now,
                "title": listing.title,
                "source": listing.source,
            }
            listing.first_seen_at = now
            listing.is_new = not bootstrapped
            if not bootstrapped:
                new_matches.append(listing)
        else:
            listing.first_seen_at = seen_entry.get("first_seen_at", "")
            listing.is_new = False
    return new_matches, bootstrapped


def scan_all(config: dict[str, Any]) -> list[Listing]:
    pages = build_scan_pages(config)
    listings: list[Listing] = []
    for page in pages:
        scraper = SCRAPERS[page["parser"]]
        try:
            listings.extend(scraper(page, config))
        except Exception as exc:
            print(f"[WARN] source failed: {page['label']} -> {exc}", file=sys.stderr)
    return dedupe_listings(listings)


def listing_sort_key(item: Listing) -> tuple[Any, ...]:
    numeric_id = parse_numeric_id(item.source_listing_id or item.url)
    source_priority = SOURCE_ORDER.index(item.source) if item.source in SOURCE_ORDER else 99
    if item.published_at_ts is not None:
        return (0, -item.published_at_ts, source_priority, item.rank_in_source, item.url)
    age_seconds = parse_relative_age_seconds(item.age_label)
    if age_seconds is not None:
        return (1, age_seconds, source_priority, item.rank_in_source, item.url)
    if numeric_id is not None:
        return (2, -numeric_id, source_priority, item.rank_in_source, item.url)
    return (3, source_priority, item.rank_in_source, item.url)


def sort_matches(listings: list[Listing]) -> list[Listing]:
    return sorted(listings, key=listing_sort_key)


def serialize_listing(item: Listing) -> dict[str, Any]:
    payload = asdict(item)
    payload["price_label"] = item.price_label
    payload["surface_label"] = item.surface_label
    payload["area_anchor"] = f"area-{slugify_fragment(item.area_guess)}" if item.area_guess else ""
    payload["published_label"] = item.age_label
    payload["amenity_labels"] = amenity_labels(item.amenity_keys)
    return payload


def notify_stdout(new_matches: list[Listing], bootstrapped: bool) -> None:
    if bootstrapped:
        print("Baseline initialised. No notifications sent on the first run.")
        return
    if not new_matches:
        print("No new matching listings.")
        return
    print(f"{len(new_matches)} new matching listing(s):")
    for item in new_matches:
        print(f"- {item.title} | {item.price_label} | {item.surface_label} | {item.url}")


def notify_macos(new_matches: list[Listing], bootstrapped: bool) -> None:
    if bootstrapped or not new_matches:
        return
    subtitle = (
        f"{len(new_matches)} nouveau(x) bien(s) matching autour de CFC"
        if len(new_matches) > 1
        else f"Nouveau bien: {new_matches[0].price_label} / {new_matches[0].surface_label}"
    )
    body = new_matches[0].title[:110]
    subprocess.run(
        [
            "osascript",
            "-e",
            f'display notification "{body}" with title "Casablanca Watch" subtitle "{subtitle}"',
        ],
        check=False,
    )


def split_csvish(value: str) -> list[str]:
    if not value.strip():
        return []
    return [item.strip() for item in re.split(r"[,\n;]+", value) if item.strip()]


def sendgrid_email_settings(config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("notifications", {}).get("sendgrid_email", {})
    to_env = os.environ.get("WATCH_EMAIL_TO", "").strip()
    return {
        "from_email": os.environ.get("WATCH_EMAIL_FROM", "").strip() or settings.get("from_email", "").strip(),
        "from_name": os.environ.get("WATCH_EMAIL_FROM_NAME", "").strip() or settings.get("from_name", "Casablanca Watch").strip(),
        "to_emails": split_csvish(to_env) or settings.get("to_emails", []),
        "subject_prefix": os.environ.get("WATCH_EMAIL_SUBJECT_PREFIX", "").strip()
        or settings.get("subject_prefix", "Casablanca Watch").strip(),
        "public_url": os.environ.get("WATCH_PUBLIC_URL", "").strip() or settings.get("public_url", "").strip(),
    }


def notify_sendgrid_email(new_matches: list[Listing], bootstrapped: bool, config: dict[str, Any]) -> None:
    if bootstrapped or not new_matches:
        return

    api_key = os.environ.get("SENDGRID_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY is required for sendgrid-email notifications.")

    settings = sendgrid_email_settings(config)
    if not settings["from_email"]:
        raise RuntimeError("WATCH_EMAIL_FROM or notifications.sendgrid_email.from_email is required.")
    if not settings["to_emails"]:
        raise RuntimeError("WATCH_EMAIL_TO or notifications.sendgrid_email.to_emails is required.")

    subject = f"{settings['subject_prefix']}: {len(new_matches)} nouveau(x) bien(s)"
    text_lines = [
        "Nouveaux biens Casablanca Watch :",
        "",
    ]
    html_items = []
    for item in new_matches:
        text_lines.extend(
            [
                item.title,
                f"Prix: {item.price_label}",
                f"Surface: {item.surface_label}",
                f"Quartier: {item.area_guess or item.location_text or 'A verifier'}",
                f"Source: {item.source_name}",
                f"Annonce: {item.url}",
                "",
            ]
        )
        html_items.append(
            (
                "<li>"
                f"<strong>{item.title}</strong><br>"
                f"Prix: {item.price_label}<br>"
                f"Surface: {item.surface_label}<br>"
                f"Quartier: {item.area_guess or item.location_text or 'A verifier'}<br>"
                f"Source: {item.source_name}<br>"
                f"<a href=\"{item.url}\">Voir l'annonce</a>"
                "</li>"
            )
        )

    if settings["public_url"]:
        text_lines.extend(["Site public:", settings["public_url"], ""])

    payload = {
        "personalizations": [
            {
                "to": [{"email": email} for email in settings["to_emails"]],
                "subject": subject,
            }
        ],
        "from": {
            "email": settings["from_email"],
            "name": settings["from_name"],
        },
        "content": [
            {
                "type": "text/plain",
                "value": "\n".join(text_lines).strip() + "\n",
            },
            {
                "type": "text/html",
                "value": (
                    "<p>Nouveaux biens Casablanca Watch :</p>"
                    f"<ul>{''.join(html_items)}</ul>"
                    + (
                        f"<p><a href=\"{settings['public_url']}\">Ouvrir le site public</a></p>"
                        if settings["public_url"]
                        else ""
                    )
                ),
            },
        ],
    }

    response = httpx.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"SendGrid email failed: {response.status_code} {response.text[:300]}")


def github_repository_from_config(config: dict[str, Any]) -> str:
    from_env = os.environ.get("GITHUB_NOTIFY_REPO") or os.environ.get("GITHUB_REPOSITORY")
    if from_env:
        return from_env
    return config.get("notifications", {}).get("github_issue", {}).get("repository", "").strip()


def github_assignees_from_config(config: dict[str, Any]) -> list[str]:
    from_env = os.environ.get("GITHUB_NOTIFY_ASSIGNEES", "").strip()
    if from_env:
        return split_csvish(from_env)
    return config.get("notifications", {}).get("github_issue", {}).get("assignees", [])


def notify_github_issue(new_matches: list[Listing], bootstrapped: bool, config: dict[str, Any]) -> None:
    if bootstrapped or not new_matches:
        return
    repository = github_repository_from_config(config)
    if not repository:
        raise RuntimeError(
            "GitHub issue notification requested, but no repository was provided. "
            "Set GITHUB_NOTIFY_REPO=owner/repo or fill notifications.github_issue.repository in config.json."
        )

    title = f"Casablanca Watch: {len(new_matches)} new matching listing(s)"
    lines = [
        "New Casablanca / CFC matching listings detected:",
        "",
    ]
    for item in new_matches:
        lines.extend(
            [
                f"- {item.title}",
                f"  - Price: {item.price_label}",
                f"  - Surface: {item.surface_label}",
                f"  - Area: {item.area_guess or item.location_text or 'To verify'}",
                f"  - Source: {item.source_name}",
                f"  - URL: {item.url}",
            ]
        )
    body = "\n".join(lines)
    command = ["gh", "issue", "create", "--repo", repository, "--title", title, "--body", body]
    assignees = github_assignees_from_config(config)
    if assignees:
        command.extend(["--assignee", ",".join(assignees)])
    subprocess.run(command, check=True)


def dispatch_notifications(notifiers: list[str], new_matches: list[Listing], bootstrapped: bool, config: dict[str, Any]) -> None:
    for name in notifiers:
        if name == "stdout":
            notify_stdout(new_matches, bootstrapped)
        elif name == "macos":
            notify_macos(new_matches, bootstrapped)
        elif name == "sendgrid-email":
            notify_sendgrid_email(new_matches, bootstrapped, config)
        elif name == "github-issue":
            notify_github_issue(new_matches, bootstrapped, config)
        else:
            raise ValueError(f"Unsupported notifier: {name}")


def create_scan_snapshot(config: dict[str, Any], notifiers: list[str]) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_listings = scan_all(config)
    matches = [item for item in all_listings if listing_matches(item, config)]
    matches = sort_matches(matches)

    state = load_state()
    new_matches, bootstrapped = update_state(matches, state)
    new_matches = sort_matches(new_matches)

    save_json(STATE_PATH, state)

    scan_data = {
        "generated_at": now_iso(),
        "all_listings_count": len(all_listings),
        "matches": [serialize_listing(item) for item in matches],
        "new_matches": [serialize_listing(item) for item in new_matches],
        "bootstrapped": bootstrapped,
    }
    save_json(LAST_SCAN_PATH, scan_data)
    dispatch_notifications(notifiers, new_matches, bootstrapped, config)
    return scan_data


def build_exact_search_groups(config: dict[str, Any]) -> list[dict[str, Any]]:
    links = []
    for area in config["areas"]:
        url = build_agenz_area_url(area, config)
        if not url:
            continue
        links.append(
            {
                "label": area["label"],
                "url": url,
                "status": "exact + recent",
                "help": "Filtre prix/surface et tri date verifies sur l'URL.",
            }
        )
    return [{"name": "Agenz", "links": links}]


def build_raw_search_groups(config: dict[str, Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []

    groups.append(
        {
            "name": "MarocAnnonces",
            "links": [
                {
                    "label": "Casablanca - page recente",
                    "url": build_marocannonces_city_url(1),
                    "status": "ville brute",
                    "help": "Page recente Casablanca avec dates visibles; le filtrage exact est fait dans Casablanca Watch.",
                }
            ],
        }
    )

    mubawab_links = []
    for area in config["areas"]:
        url = build_mubawab_area_url(area)
        if not url:
            continue
        mubawab_links.append(
            {
                "label": area["label"],
                "url": url,
                "status": "quartier brut",
                "help": "Bonne page quartier, mais filtre prix/date non garanti proprement par URL publique.",
            }
        )
    if mubawab_links:
        groups.append({"name": "Mubawab", "links": mubawab_links})

    yakeey_links = []
    for area in config["areas"]:
        url = build_yakeey_area_url(area, with_filter_hint=True)
        if not url:
            continue
        yakeey_links.append(
            {
                "label": area["label"],
                "url": url,
                "status": "quartier brut",
                "help": "Bonne page quartier; le tri hint est present, mais le filtre exact doit surtout etre lu dans Casablanca Watch.",
            }
        )
    if yakeey_links:
        groups.append({"name": "Yakeey", "links": yakeey_links})

    return groups


def group_items_by_source(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = {source: [] for source in SOURCE_ORDER}
    for item in matches:
        grouped.setdefault(item["source"], []).append(item)
    sections = []
    notes = {
        "agenz": "Ordre recent fiable via pages filtrees et tri date_desc.",
        "mubawab": "Vue interne exacte; le site brut n'expose pas un tri date URL aussi fiable.",
        "marocannonces": "Source additionnelle utile avec dates visibles sur la liste et details complets sur la fiche.",
        "yakeey": "Vue interne exacte; le site brut sert surtout comme page quartier complementaire.",
    }
    labels = {
        "agenz": "Agenz",
        "mubawab": "Mubawab",
        "marocannonces": "MarocAnnonces",
        "yakeey": "Yakeey",
    }
    for source in SOURCE_ORDER:
        sections.append(
            {
                "id": source,
                "label": labels[source],
                "note": notes[source],
                "listings": grouped.get(source, []),
            }
        )
    return sections


def group_items_by_area(config: dict[str, Any], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections = []
    for area in config["areas"]:
        label = area["label"]
        items = [item for item in matches if item.get("area_guess") == label]
        sections.append(
            {
                "label": label,
                "anchor": f"area-{slugify_fragment(label)}",
                "listings": items,
            }
        )
    return sections


def build_area_cards(config: dict[str, Any], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for area in config["areas"]:
        label = area["label"]
        count = sum(1 for item in matches if item.get("area_guess") == label)
        cards.append(
            {
                "label": label,
                "count": count,
                "anchor": f"area-{slugify_fragment(label)}",
                "note": "Cliquez pour voir les biens exacts de ce quartier.",
            }
        )
    return cards


def build_source_cards(source_sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": section["id"],
            "label": section["label"],
            "count": len(section["listings"]),
            "note": section["note"],
        }
        for section in source_sections
    ]


def build_area_filter_options(config: dict[str, Any], matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = {}
    for item in matches:
        label = item.get("area_guess") or ""
        counts[label] = counts.get(label, 0) + 1
    options = []
    known_labels = set()
    for area in config["areas"]:
        known_labels.add(area["label"])
        options.append(
            {
                "label": area["label"],
                "count": counts.get(area["label"], 0),
            }
        )
    for label, count in counts.items():
        if not label or label in known_labels:
            continue
        options.append({"label": label, "count": count})
    options.sort(key=lambda item: (-item["count"], item["label"]))
    return options


def build_source_filter_options(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = {
        "agenz": "Agenz",
        "mubawab": "Mubawab",
        "marocannonces": "MarocAnnonces",
        "yakeey": "Yakeey",
    }
    counts = {}
    for item in matches:
        source = item.get("source") or ""
        counts[source] = counts.get(source, 0) + 1
    options = [
        {
            "id": source,
            "label": labels.get(source, source.title()),
            "count": counts.get(source, 0),
        }
        for source in SOURCE_ORDER
        if counts.get(source, 0) or source in labels
    ]
    known_sources = {item["id"] for item in options}
    for source, count in counts.items():
        if not source or source in known_sources:
            continue
        options.append(
            {
                "id": source,
                "label": labels.get(source, source.title()),
                "count": count,
            }
        )
    options.sort(key=lambda item: (-item["count"], item["label"]))
    return options


def build_dashboard_payload(config: dict[str, Any], scan_data: dict[str, Any], refresh_enabled: bool) -> dict[str, Any]:
    matches = scan_data.get("matches", [])
    new_matches = scan_data.get("new_matches", [])
    for index, item in enumerate(matches):
        item["default_sort_index"] = index
    exact_groups = build_exact_search_groups(config)
    raw_groups = build_raw_search_groups(config)
    source_sections = group_items_by_source(matches)
    area_sections = group_items_by_area(config, matches)
    server = config.get("server", {})
    host = server.get("host", "127.0.0.1")
    port = server.get("port", DEFAULT_PORT)
    server_url = f"http://{host}:{port}"
    public_mode = bool(config.get("_public_mode"))
    refresh_mode = "live" if refresh_enabled else ("reload" if public_mode else "none")

    return {
        "criteria": config["criteria"],
        "generated_at": scan_data.get("generated_at", ""),
        "all_listings_count": scan_data.get("all_listings_count", 0),
        "matches": matches,
        "new_matches": new_matches,
        "bootstrapped": scan_data.get("bootstrapped", False),
        "project_root": str(ROOT),
        "dashboard_path": str(DASHBOARD_PATH),
        "server_url": server_url,
        "official_pages": config["official_pages"],
        "manual_pages": config["manual_pages"],
        "exact_search_groups": exact_groups,
        "raw_search_groups": raw_groups,
        "source_sections": source_sections,
        "area_sections": area_sections,
        "area_cards": build_area_cards(config, matches),
        "source_cards": build_source_cards(source_sections),
        "refresh_enabled": refresh_enabled,
        "refresh_mode": refresh_mode,
        "public_mode": public_mode,
        "new_match_urls_json": json.dumps([item["url"] for item in new_matches]),
        "current_match_urls_json": json.dumps([item["url"] for item in matches]),
        "agenz_exact_urls_json": json.dumps(
            [link["url"] for group in exact_groups for link in group["links"]]
        ),
        "raw_external_urls_json": json.dumps(
            [link["url"] for group in raw_groups for link in group["links"]]
        ),
        "matches_json": json.dumps(matches, ensure_ascii=False),
        "new_matches_json": json.dumps(new_matches, ensure_ascii=False),
        "area_filter_options_json": json.dumps(
            build_area_filter_options(config, matches), ensure_ascii=False
        ),
        "source_filter_options_json": json.dumps(
            build_source_filter_options(matches), ensure_ascii=False
        ),
        "amenity_filter_options_json": json.dumps(
            [{"id": key, "label": label} for key, label in AMENITY_LABELS.items()],
            ensure_ascii=False,
        ),
        "snapshot_url": "last_scan.json" if public_mode else "/api/state",
    }


def render_dashboard(config: dict[str, Any], scan_data: dict[str, Any], refresh_enabled: bool) -> str:
    payload = build_dashboard_payload(config, scan_data, refresh_enabled)
    return DASHBOARD_TEMPLATE.render(**payload)


def write_dashboard(config: dict[str, Any], scan_data: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PATH.write_text(render_dashboard(config, scan_data, refresh_enabled=False), encoding="utf-8")


def write_public_site(config: dict[str, Any], scan_data: dict[str, Any]) -> None:
    public_config = dict(config)
    public_config["_public_mode"] = True
    save_text(PUBLIC_DASHBOARD_PATH, render_dashboard(public_config, scan_data, refresh_enabled=False))
    save_json(PUBLIC_LAST_SCAN_PATH, scan_data)
    save_text(PUBLIC_DIR / ".nojekyll", "")


def run_scan(config: dict[str, Any], notifiers: list[str], open_dashboard_after: bool) -> dict[str, Any]:
    scan_data = create_scan_snapshot(config, notifiers)
    write_dashboard(config, scan_data)
    write_public_site(config, scan_data)
    print(f"Dashboard: {DASHBOARD_PATH}")
    print(f"Public site: {PUBLIC_DASHBOARD_PATH}")
    print(f"All parsed listings: {scan_data['all_listings_count']}")
    print(f"Matching listings: {len(scan_data['matches'])}")
    print(f"New matching listings: {len(scan_data['new_matches'])}")
    if open_dashboard_after:
        command_open_dashboard(config)
    return {
        "all_listings_count": scan_data["all_listings_count"],
        "matches_count": len(scan_data["matches"]),
        "new_matches_count": len(scan_data["new_matches"]),
        "bootstrapped": scan_data["bootstrapped"],
    }


def open_urls(urls: list[str]) -> None:
    for url in urls:
        webbrowser.open_new_tab(url)


def command_open_dashboard(config: dict[str, Any]) -> None:
    server = config.get("server", {})
    host = server.get("host", "127.0.0.1")
    port = server.get("port", DEFAULT_PORT)
    webbrowser.open(f"http://{host}:{port}")


def command_install_launchd(config: dict[str, Any]) -> Path:
    python_path = WORKSPACE_ROOT / ".venv" / "bin" / "python"
    if not python_path.exists():
        python_path = Path(sys.executable)

    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents_dir / "com.mohyi.casablanca-watch.plist"
    scan_cmd = (
        f'cd "{ROOT}" && "{python_path}" "{ROOT / "watch.py"}" scan --notify macos --notify stdout'
    )
    plist = textwrap.dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
          <dict>
            <key>Label</key>
            <string>com.mohyi.casablanca-watch</string>
            <key>ProgramArguments</key>
            <array>
              <string>/bin/zsh</string>
              <string>-lc</string>
              <string>{scan_cmd}</string>
            </array>
            <key>WorkingDirectory</key>
            <string>{ROOT}</string>
            <key>StartInterval</key>
            <integer>{config["notifications"]["launchd"]["interval_seconds"]}</integer>
            <key>StandardOutPath</key>
            <string>{ROOT / "data" / "launchd.log"}</string>
            <key>StandardErrorPath</key>
            <string>{ROOT / "data" / "launchd.err.log"}</string>
            <key>RunAtLoad</key>
            <true/>
          </dict>
        </plist>
        """
    )
    plist_path.write_text(plist, encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
    subprocess.run(["launchctl", "load", str(plist_path)], check=True)
    return plist_path


def make_server_handler(config: dict[str, Any]):
    class WatchHandler(BaseHTTPRequestHandler):
        def _send_html(self, content: str, status: int = 200) -> None:
            body = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json({"ok": True})
                return
            if parsed.path == "/api/state":
                scan_data = load_json(LAST_SCAN_PATH, {})
                if not scan_data:
                    scan_data = create_scan_snapshot(config, [])
                    write_dashboard(config, scan_data)
                    write_public_site(config, scan_data)
                self._send_json(scan_data)
                return
            if parsed.path in ["/", "/index.html"]:
                scan_data = load_json(LAST_SCAN_PATH, {})
                if not scan_data:
                    scan_data = create_scan_snapshot(config, [])
                    write_dashboard(config, scan_data)
                    write_public_site(config, scan_data)
                self._send_html(render_dashboard(config, scan_data, refresh_enabled=True))
                return
            self._send_html("Not found", status=404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/scan":
                scan_data = create_scan_snapshot(config, [])
                write_dashboard(config, scan_data)
                write_public_site(config, scan_data)
                self._send_json(
                    {
                        "ok": True,
                        "generated_at": scan_data["generated_at"],
                        "matches_count": len(scan_data["matches"]),
                        "new_matches_count": len(scan_data["new_matches"]),
                    }
                )
                return
            self._send_json({"ok": False, "error": "not found"}, status=404)

    return WatchHandler


def command_serve(config: dict[str, Any], open_browser: bool) -> None:
    server_config = config.get("server", {})
    host = server_config.get("host", "127.0.0.1")
    port = int(server_config.get("port", DEFAULT_PORT))
    handler = make_server_handler(config)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Serving Casablanca Watch on http://{host}:{port}")
    if open_browser:
        webbrowser.open(f"http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Casablanca / CFC listing watcher")
    parser.add_argument(
        "command",
        choices=["scan", "open-dashboard", "install-launchd", "open-new", "serve"],
    )
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument(
        "--notify",
        action="append",
        default=[],
        choices=["stdout", "macos", "github-issue", "sendgrid-email"],
    )
    parser.add_argument("--open-dashboard", action="store_true")
    parser.add_argument("--open-browser", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json(Path(args.config), {})
    if not config:
        raise RuntimeError(f"Config not found or empty: {args.config}")

    if args.command == "scan":
        run_scan(config, args.notify, args.open_dashboard)
        return
    if args.command == "open-dashboard":
        command_open_dashboard(config)
        return
    if args.command == "install-launchd":
        plist_path = command_install_launchd(config)
        print(f"Launchd installed: {plist_path}")
        return
    if args.command == "open-new":
        last_scan = load_json(LAST_SCAN_PATH, {})
        urls = [item["url"] for item in last_scan.get("new_matches", [])]
        if not urls:
            print("No new matches recorded in the last scan.")
            return
        open_urls(urls)
        return
    if args.command == "serve":
        command_serve(config, args.open_browser)
        return
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
