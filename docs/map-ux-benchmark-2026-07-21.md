# Casablanca Watch - benchmark UX carte et recommandations

Date: 2026-07-21

## Objectif

Comparer 20 portails immobiliers connus pour en tirer une UX carte simple, rapide et partageable pour Casablanca Watch.

## Ce que les meilleurs portails font en boucle

1. Carte persistante + liste synchronisee.
2. Filtres visibles sans changer de page.
3. Zone de recherche libre: dessin, multi-zone, ou selection directe sur carte.
4. Rayon autour d'un point ou d'une zone.
5. Alertes / saved search.
6. Donnees de contexte: quartier, prix, couches ou points d'interet.

## Benchmark des 20 sites

Notation:
- `Oui` = confirme dans la source publique verifiee
- `Partiel` = visible mais incomplet
- `Non verifie` = pas confirme proprement dans la source lue

| Site | Carte / liste | Selection de zone | Rayon / proximite | Alertes | Signal utile |
| --- | --- | --- | --- | --- | --- |
| Zillow | Oui | Oui, zone dessinee | Partiel | Oui | recherche "draw, define and refine your search area" |
| Redfin | Oui | Oui, draw your own search + multi-area | Partiel | Oui | support officiel tres clair sur zone dessinee |
| Realtor.com | Oui | Oui, Draw icon en map view | Partiel | Partiel | couches carte dynamiques |
| Trulia | Oui | Partiel | Partiel | Partiel | 35+ filtres + overlays quartier |
| Homes.com | Oui | Partiel | Partiel | Oui | interactive map layers + real-time alerts |
| Rightmove | Oui | Oui, Draw-a-Search | Partiel | Partiel | pattern historique encore central |
| Zoopla | Oui | Oui, draw own area + drag pins | Partiel | Oui | excellent compromis carte + alerte |
| OnTheMarket | Oui | Oui, draw search area | Partiel | Oui | discours produit tres proche de notre besoin |
| idealista | Oui | Oui, select areas on map + draw area | Partiel | Partiel | multi-zones directement sur carte |
| SeLoger | Partiel | Non verifie | Non verifie | Partiel | carte des prix forte, utile pour contexte quartier |
| Bien'ici | Oui | Partiel | Partiel | Oui | carte 3D + annonces geolocalisees |
| Leboncoin Immobilier | Partiel | Non verifie | Non verifie | Partiel | flux simple, tres transactionnel |
| Immoweb | Oui | Partiel | Non verifie | Partiel | "Search on the map" expose clairement |
| ImmoScout24 | Oui | Oui, draw search areas | Oui, travel time visible | Oui | benchmark fort pour mobile + alertes |
| Immobiliare.it | Partiel | Non verifie | Non verifie | Partiel | tres bon niveau de filtres equipements |
| Daft.ie | Oui | Partiel | Oui, distances +0/+1/+3/+5/+10/+20 km | Partiel | rayon simple et ultra lisible |
| Mubawab | Oui | Partiel, carte + arrondissements | Partiel | Partiel | bon benchmark local Maroc |
| Agenz | Oui, Map/List | Partiel | Partiel | Partiel | quartier tres visible dans l'UX locale |
| Avito Immobilier | Partiel | Partiel | Non verifie | Partiel | flux rapide, dates tres visibles |
| Sarouty Maroc | Partiel | Partiel | Non verifie | Partiel | UX percue comme claire et filtres quartier/budget |

## Sources verifiees

- Zillow app search: https://www.zillow.com/buy/app-download/
- Redfin support / search: https://support.redfin.com/hc/en-us/articles/360001432632-Searching-for-Homes
- Redfin multi-area: https://support.redfin.com/hc/en-us/articles/360025724771-Multiple-Area-Search
- Realtor.com map draw: https://www.realtor.com/homemade/how-to-personalize-your-home-search-on-realtor-com/
- Realtor.com map layers: https://www.realtor.com/homemade/map-view/
- Trulia home: https://www.trulia.com/
- Trulia neighborhoods: https://www.trulia.com/neighborhoods/
- Homes.com about: https://www.homes.com/about/
- Rightmove official: https://www.rightmove.co.uk/
- Rightmove Draw-a-Search mention: https://www.rightmove.co.uk/news/articles/property-news/a-z-of-rightmove/
- Zoopla map help: https://help.zoopla.co.uk/hc/en-gb/articles/360006033758-How-can-I-search-for-properties-using-Map-view
- Zoopla tools / alerts: https://www.zoopla.co.uk/discover/buying/9-tools-on-zoopla-that-will-make-you-a-property-expert/
- OnTheMarket usage guide: https://www.onthemarket.com/content/using-onthemarket-com-to-find-your-next-home/
- idealista home: https://www.idealista.com/en/
- idealista map draw: https://www.idealista.com/en/venta-viviendas/begur-girona/mapa
- SeLoger price map: https://www.seloger.com/
- Bien'ici home: https://www.bienici.com/
- Bien'ici result pages: https://www.bienici.com/recherche/achat/les-arcs-73700
- Immoweb map: https://www.immoweb.be/en/map
- ImmoScout24 home: https://www.immoscout24.ch/en
- Immobiliare.it sale: https://www.immobiliare.it/en/
- Immobiliare.it filters example: https://www.immobiliare.it/vendita-case/milano/
- Daft.ie home: https://www.daft.ie/
- Daft.ie radius example: https://www.daft.ie/property-for-rent/dublin
- Mubawab carte Casablanca: https://www.mubawab.ma/fr/mprpt/casablanca-settat/pr%C3%A9fecture-de-casablanca/casablanca/immobilier-a-vendre
- Agenz Casablanca map/list: https://agenz.ma/en/acheter/immo-casablanca
- Avito Casablanca appartements: https://www.avito.ma/fr/casablanca/appartements-%C3%A0_vendre
- Sarouty Maroc: https://www.sarouty.ma/

## Ce qu'il faut copier pour Casablanca Watch

### A garder absolument

1. Carte toujours visible.
2. Liste toujours synchronisee.
3. Selection directe des quartiers sur la carte.
4. Point manuel + rayon.
5. Bouton "selectionner les quartiers du rayon".
6. Filtres prix / surface / equipements au meme endroit.
7. Resume clair: combien de quartiers, combien d'annonces, quel point, quel rayon.

### A eviter

1. Basculer l'utilisateur vers plusieurs pages pour comprendre la geographie.
2. Cacher les filtres derriere des modales.
3. Reposer uniquement sur la geolocalisation navigateur.
4. Reposer uniquement sur des centroIdes si l'on veut une vraie UX quartier.

## Recommandation technique

### Option recommande maintenant

Leaflet + OSM tiles + GeoJSON de quartiers pre-calcules + Turf cote client.

Pourquoi:
- gratuit
- leger
- suffisant pour 42 quartiers
- facile a deployer sur GitHub Pages
- bon compromis pour un dashboard partageable

### Option recommandee plus tard si la carte devient centrale

MapLibre GL JS + tuiles vectorielles + jeu de limites quartier plus propre.

Quand migrer:
- si le nombre de quartiers/objets augmente fortement
- si on veut du hover plus fluide, du label plus propre, du style plus riche
- si l'on veut des couches plus nombreuses sans perte de perf

### Donnees de limites de quartiers

#### Option gratuite et pragmatique

Precalculer hors-ligne les geometries depuis OSM/Nominatim/Overpass, puis les versionner.

Important:
- la politique Nominatim publique interdit d'en faire un geocoder generique public integre a grande echelle
- usage correct ici: extraction deliberee cote developpeur, cachee et versionnee

Sources:
- Nominatim Search API: https://nominatim.org/release-docs/latest/api/Search/
- Nominatim usage policy: https://operations.osmfoundation.org/policies/nominatim/
- Overpass API: https://wiki.openstreetmap.org/wiki/Overpass_API

#### Option plus complete si on paie

- Geoapify Boundaries API: https://apidocs.geoapify.com/docs/boundaries/
- Google boundaries coverage: https://developers.google.com/maps/documentation/javascript/dds-boundaries/coverage
- Google pricing: https://mapsplatform.google.com/pricing/
- Mapbox boundaries: https://www.mapbox.com/boundaries

## Recommandation produit pour ce repo

1. Garder Leaflet maintenant.
2. Continuer a precalculer les geometries de quartiers hors-ligne.
3. Faire du point + rayon le mecanisme principal.
4. Ajouter les polygones quand ils existent.
5. Considerer un dataset quartier plus propre plus tard si la selection fine devient critique.

## Etat apres correctifs du 2026-07-21

1. Le bouton `Actualiser les annonces` ne casse plus la page.
2. Le bug Leaflet au chargement est corrige.
3. Les 42 quartiers configures ont maintenant une localisation.
4. 14 quartiers disposent d'une geometrie `Polygon`.
5. La carte peut maintenant:
   - filtrer par clic quartier
   - poser un point manuel
   - filtrer par rayon
   - selectionner automatiquement les quartiers du rayon
   - afficher un resume de couverture plus utile
