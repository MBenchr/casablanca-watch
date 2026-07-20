# Casablanca Watch

Outil local pour surveiller les annonces autour de CFC avec:

- budget `100000-950000 DH`
- surface `30-60 m2`
- quartiers etendus depuis votre carte
- bouton `Actualiser` dans l'interface live et sur la version publique
- vue mixee avec filtres quartiers / sources / equipements

Quartiers actuellement integres depuis la carte:

- Casablanca Finance City
- Ferme Bretonne
- CIL
- Beausejour
- Riviera
- L'Oasis
- Maarif
- Hay Hassani
- Quartier El Hana
- Littoral
- Ain Diab / Sindibad
- Sid Al Khadir
- El Oulfa
- Californie
- Bachkou / Taddart
- Sidi Maarouf
- Ghandi
- Anoual
- Hermitage
- Longchamps
- Polo
- Derb Ghallef

## Ce que ce dossier apporte maintenant

- un scan multi-sites configurable
- un scan recent centre sur les flux ville entiere puis filtre localement par quartier
- une interface live locale sur `http://127.0.0.1:8765`
- un dashboard statique de secours
- une version publique generee dans `public/` pour GitHub Pages
- une base des annonces deja vues
- une detection des nouveaux liens
- des notifications locales macOS
- un workflow GitHub Actions pour republier le site et envoyer les alertes

## Fichiers importants

- `config.json`: criteres, quartiers, slugs de sites, pages officielles
- `watch.py`: moteur principal et serveur local
- `output/dashboard.html`: version statique du dernier scan
- `public/index.html`: version publique a deployer
- `public/last_scan.json`: snapshot public du dernier scan
- `data/state.json`: base persistante des annonces deja vues
- `data/last_scan.json`: snapshot du dernier scan

## Commandes utiles

Lancer l'interface live:

```bash
cd /Users/mohyi/CHATGPT/casablanca_watch
/Users/mohyi/CHATGPT/.venv/bin/python watch.py serve --open-browser
```

Faire un scan unique:

```bash
/Users/mohyi/CHATGPT/.venv/bin/python watch.py scan --notify stdout
```

Installer la surveillance locale macOS toutes les 30 minutes:

```bash
/Users/mohyi/CHATGPT/.venv/bin/python watch.py install-launchd
```

## Fichiers cliquables

- `open_dashboard.command`: demarre le serveur si besoin et ouvre l'interface live
- `check_now.command`: force un scan si le serveur tourne, sinon lance un scan simple

## Fiabilite des liens externes

- `Agenz`: liens verifies avec filtre prix/surface et tri recent directement dans l'URL
- `Mubawab`: bonne source d'agences, mais le filtre public exact par URL n'est pas assez fiable; la vue interne reste la reference propre
- `MarocAnnonces`: bon complement avec dates et images souvent lisibles
- `Avito`: utile, mais bloque l'automatisation serveur par Cloudflare; conserve en source manuelle directe
- `Yakeey`: pages publiques actuellement instables, donc desactive du scan automatique par defaut

## Hebergement public

Le repo contient maintenant un workflow reel dans `.github/workflows/casablanca-watch.yml`.

Le principe:

1. le workflow planifie relance le scan toutes les 30 minutes
2. il regenere `public/index.html` et `public/last_scan.json`
3. il deploie `public/` sur GitHub Pages
4. tu peux partager l'URL publique avec n'importe qui

## Alertes e-mail GitHub

Usage type:

1. laissez `data/state.json` versionne pour garder la memoire des liens deja vus
2. configurez le workflow pour assigner les issues au compte GitHub qui doit recevoir l'alerte
3. le workflow planifie executera le scan toutes les 30 minutes
4. si un nouveau bien exact apparait, une issue GitHub sera creee
5. GitHub enverra alors un e-mail de notification contenant les details du bien et son URL

## Alertes e-mail SendGrid optionnelles

Le code supporte aussi `--notify sendgrid-email` si vous voulez plus tard un vrai expediteur dedie.

Variables supportees:

- `WATCH_EMAIL_FROM`: expediteur SendGrid, idealement sur un domaine deja authentifie
- `WATCH_EMAIL_TO`: une ou plusieurs adresses separees par virgules
- `WATCH_EMAIL_FROM_NAME`: libelle expediteur
- `WATCH_PUBLIC_URL`: URL publique du dashboard a inclure dans l'e-mail

## Adapter les criteres

Editez `config.json`:

- `max_price_mad`
- `min_price_mad`
- `min_surface_m2`
- `max_surface_m2`
- `required_keywords_all`
- `required_keywords_any`
- `excluded_keywords`
- `areas`
- `scan_sites`

## Limites connues

- l'interface locale est la vue exacte de reference
- la page publique recharge le dernier `public/last_scan.json` publie quand on clique sur `Actualiser`
- le premier run initialise la base et n'envoie pas d'alerte, sinon il vous spammerait avec tout l'existant
- les liens externes `Agenz` restent les plus fiables quand vous voulez aussi verifier directement les pages source avec tri recent
- certaines sources restent en manuel par choix de robustesse: mieux vaut un lien direct qui marche qu'un scraper fragile qui casse silencieusement
