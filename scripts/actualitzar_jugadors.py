#!/usr/bin/env python3
"""Actualitza data/jugadors.csv amb els jugadors inscrits a les lligues
actives de la Federació Catalana de Billar (intranet.fcbillar.cat).

- Recorre totes les lligues de /frontend/lligues/llistat
- Per a cada club, llegeix /frontend/lligues/participants/<lliga>/<club>
- Fusiona amb el CSV anterior: els nous s'afegeixen, els que canvien de club
  s'actualitzen i els que ja no surten queden amb actiu=No (no s'esborren)
- Afegeix un resum dels canvis a data/canvis.md
"""
import csv, datetime, os, re, sys, time
import requests
from bs4 import BeautifulSoup

BASE = "https://intranet.fcbillar.cat"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "data", "jugadors.csv")
LOG = os.path.join(ROOT, "data", "canvis.md")
CAMPS = ["nom", "club", "id_club", "lligues", "mitjana_3b", "fitxatge",
         "actiu", "alta", "darrera_vegada"]

S = requests.Session()
S.headers["User-Agent"] = "CB-Monforte-actualitzador/1.0"


def sopa(path):
    for _ in range(3):
        try:
            r = S.get(BASE + path, timeout=30)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except requests.RequestException as e:
            print(f"  error {path}: {e}", file=sys.stderr)
            time.sleep(3)
    raise SystemExit(f"No puc llegir {path}")


def lligues():
    s = sopa("/frontend/lligues/llistat")
    out = []
    for a in s.find_all("a", string=re.compile("Equips inscrits")):
        m = re.search(r"/inscripcions/(\d+)", a["href"])
        nom = a.find_parent("tr").find("td").get_text(" ", strip=True)
        out.append((m.group(1), nom))
    return out


def sigla(nom_lliga):
    n = nom_lliga.lower()
    if "tres bandes" in n or "3 bandes" in n:
        return "3B"
    if "4 modalitats" in n:
        return "4M"
    return nom_lliga


def jugadors_lliga(id_lliga):
    s = sopa(f"/frontend/lligues/inscripcions/{id_lliga}")
    for a in s.find_all("a", string=re.compile("Veure inscrits")):
        m = re.search(r"/participants/(\d+)/(\d+)", a["href"])
        if not m:
            continue
        id_club = m.group(2)
        p = sopa(f"/frontend/lligues/participants/{id_lliga}/{id_club}")
        mc = re.search(r"del club (.+)", p.get_text("\n"))
        club = mc.group(1).strip() if mc else "?"
        for tr in p.select("table tbody tr"):
            td = tr.find_all("td")
            if len(td) < 2:
                continue
            fitx = "Fitxatge" in td[1].get_text()
            nom = td[1].find(string=True, recursive=False) or td[1].get_text()
            nom = re.sub(r"\s+", " ", nom).strip()
            yield {"nom": nom, "club": club, "id_club": id_club,
                   "mitjana": td[0].get_text(strip=True), "fitxatge": fitx}
        time.sleep(0.3)


def clau(nom):
    return re.sub(r"\s+", " ", nom.upper()).strip()


def main():
    avui = datetime.date.today().isoformat()
    antic = {}
    if os.path.exists(CSV):
        with open(CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                antic[clau(r["nom"])] = r

    nou = {}
    for id_l, nom_l in lligues():
        sg = sigla(nom_l)
        print(f"Lliga {id_l} {nom_l} ({sg})")
        for j in jugadors_lliga(id_l):
            r = nou.setdefault(clau(j["nom"]), {
                "nom": j["nom"], "club": j["club"], "id_club": j["id_club"],
                "lligues": set(), "mitjana_3b": "", "fitxatge": ""})
            r["lligues"].add(sg)
            if sg == "3B":
                r["club"], r["id_club"] = j["club"], j["id_club"]
                if j["mitjana"]:
                    r["mitjana_3b"] = j["mitjana"]
            if j["fitxatge"]:
                r["fitxatge"] = "Si"

    if len(nou) < 100:
        raise SystemExit(f"Només {len(nou)} jugadors: sembla un error, no toco res")

    altes, canvis_club, baixes, final = [], [], [], {}
    for k, r in nou.items():
        r["lligues"] = ";".join(sorted(r["lligues"]))
        r["actiu"] = "Si"
        r["darrera_vegada"] = avui
        a = antic.get(k)
        r["alta"] = a["alta"] if a and a.get("alta") else avui
        if not a:
            altes.append(f"{r['nom']} ({r['club']})")
        elif a["club"] != r["club"]:
            canvis_club.append(f"{r['nom']}: {a['club']} -> {r['club']}")
        final[k] = r
    for k, a in antic.items():
        if k not in final:
            if a.get("actiu") != "No":
                baixes.append(f"{a['nom']} ({a['club']})")
            a["actiu"] = "No"
            final[k] = a

    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(final.values(), key=lambda r: (r["club"], r["nom"])):
            w.writerow(r)

    if altes or canvis_club or baixes:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"\n## {avui}\n")
            for titol, llista in (("Altes", altes), ("Canvis de club", canvis_club),
                                  ("Ja no inscrits", baixes)):
                if llista:
                    f.write(f"\n**{titol}** ({len(llista)})\n\n")
                    f.writelines(f"- {x}\n" for x in sorted(llista))
    print(f"{len(final)} jugadors | altes {len(altes)} | canvis {len(canvis_club)} | baixes {len(baixes)}")


if __name__ == "__main__":
    main()
