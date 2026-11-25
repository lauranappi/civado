#!/usr/bin/env python3
"""Scarica le locandine recenti di @nightlifebergamo (Instagram Business Discovery)
in una cartella 'locandine/' con un file elenco.json. Non le interpreta: le legge
l'aggiornamento settimanale. Solo libreria standard.
Variabili d'ambiente: META_TOKEN (token Pagina), IG_USER_ID (ID Instagram di Laura).
"""
import datetime as dt, json, os, urllib.parse, urllib.request

TOKEN = os.environ["META_TOKEN"]
IG_ID = os.environ["IG_USER_ID"]
ACCOUNT = "nightlifebergamo"
OGGI = dt.date.today()
GIORNI = 14
OUT = "locandine"


def http(req):
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


campi = (f"business_discovery.username({ACCOUNT})"
         "{media.limit(6){id,timestamp,permalink,media_type,media_url,children{media_url}}}")
url = f"https://graph.facebook.com/v27.0/{IG_ID}?" + urllib.parse.urlencode(
    {"fields": campi, "access_token": TOKEN})
posts = json.loads(http(urllib.request.Request(url)))["business_discovery"]["media"]["data"]

os.makedirs(OUT, exist_ok=True)
elenco = []
for p in posts:
    giorno = dt.date.fromisoformat(p["timestamp"][:10])
    if (OGGI - giorno).days > GIORNI:
        continue
    urls = [c["media_url"] for c in p.get("children", {}).get("data", []) if c.get("media_url")]
    if not urls and p.get("media_url") and p.get("media_type") == "IMAGE":
        urls = [p["media_url"]]
    file_post = []
    for i, u in enumerate(urls[:20], 1):
        nome = f"{giorno.isoformat()}_{p['id']}_{i:02d}.jpg"
        try:
            open(os.path.join(OUT, nome), "wb").write(
                http(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})))
            file_post.append(nome)
        except Exception as ex:
            print("ERRORE", nome, ex)
    if file_post:
        elenco.append({"post": p["permalink"], "data": giorno.isoformat(), "file": file_post})

json.dump({"scaricato_il": OGGI.isoformat(), "post": elenco},
          open(os.path.join(OUT, "elenco.json"), "w"), ensure_ascii=False, indent=1)
print(f"Post scaricati: {len(elenco)}; immagini: {sum(len(x['file']) for x in elenco)}")
