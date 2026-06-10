# nowplaying

Page plein écran "En lecture" pour MPD. Affiche le titre en cours avec un dégradé de fond extrait de la pochette, des badges de qualité audio et la détection Hi-Res.

Pas besoin de nginx - le bridge sert tout sur le port 8766.

## Ce que ça affiche

- Dégradé de fond extrait des couleurs de la pochette
- Pochettes via Last.fm
- Badges FLAC / profondeur de bits / fréquence d'échantillonnage
- Logo Hi-Res Audio pour tout ce qui est >= 88,2 kHz ou >= 24 bits
- Barre de progression avec temps écoulé et total
- Défilement automatique pour les titres longs
- Assombrissement en pause
- Horloge en haut à droite

## Prérequis

- MPD
- Python 3
- Une clé API Last.fm - gratuite sur https://www.last.fm/api

## Démarrage
```bash
git clone https://github.com/MAT-GRC/nowplaying.git
cd nowplaying
pip install python-mpd2 requests
export LASTFM_API_KEY=votre_clé
python mpd-bridge.py
```

Ouvrez ensuite http://localhost:8766 dans un navigateur.

Version française : http://localhost:8766/index.fr.html ou http://localhost:8766?lang=fr

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| LASTFM_API_KEY | obligatoire | Votre clé API Last.fm |
| ALSA_CARD | 0 | Numéro de carte ALSA pour la détection du format audio |
| MPD_HOST | 127.0.0.1 | Hôte MPD |
| MPD_PORT | 6600 | Port MPD |

Copiez `.env.example` en `.env` et remplissez vos valeurs.

## Docker

Un `docker-compose.yml` est inclus. Renseignez `LASTFM_API_KEY` dans la section environment puis :
docker compose up -d

## Licence

MIT
