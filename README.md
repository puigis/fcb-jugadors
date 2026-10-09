# Jugadors Federació Catalana de Billar

Base de dades dels jugadors inscrits a les lligues de la FCB, per reutilitzar en
altres projectes del C.B. Monforte (marcador wifibillar, cartells de resultats...).

- `data/jugadors.csv` — un jugador per fila: nom, club, id_club, lligues (3B, 4M),
  mitjana_3b, fitxatge, actiu, alta, darrera_vegada.
- `data/canvis.md` — historial d'altes, canvis de club i baixes.
- `scripts/actualitzar_jugadors.py` — llegeix la intranet de la FCB i actualitza el CSV.

Per actualitzar: pestanya **Actions → Actualitzar jugadors FCB → Run workflow**.

Els jugadors que deixen de sortir no s'esborren: queden amb `actiu = No`.
