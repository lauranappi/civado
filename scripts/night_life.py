#!/usr/bin/env python3
"""Legge le locandine di @nightlifebergamo (Instagram Business Discovery),
le fa leggere a Claude e aggiunge le serate a eventi.json (id che iniziano con 'nl-').
Solo libreria standard. Variabili d'ambiente richieste:
  META_TOKEN  token Pagina Facebook (non scade) collegata all'Instagram di Laura
  IG_USER_ID  ID dell'account Instagram professionale di Laura
  ANTHROPIC_API_KEY  chiave API Anthropic
"""
import base64, datetime as dt, hashlib, json, os, re, sys, urllib.parse, urllib.request

TOKEN = os.environ["META_TOKEN"]
IG_ID = os.environ["IG_USER_ID"]
KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
ACCOUNT = "nightlifebergamo"
OGGI = dt.date.today()
STATO_FILE = "scripts/night_life_stato.json"


def http(req, timeout=120):
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def graph():
    campi = (f"business_discovery.username({ACCOUNT})"
             "{media.limit(6){id,timestamp,permalink,media_type,media_url,children{media_url}}}")
    url = f"https://graph.facebook.com/v27.0/{IG_ID}?" + urllib.parse.urlencode(
        {"fields": campi, "access_token": TOKEN})
    return json.loads(http(urllib.request.Request(url)))["business_discovery"]["media"]["data"]


def scarica(url):
    data = http(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}))
    return base64.b64encode(data).decode()


def leggi_immagini(immagini, permalink):
    contenuto = []
    for b64 in immagini:
        contenuto.append({"type": "image",
                          "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
    contenuto.append({"type": "text", "text": (
        f"Oggi è {OGGI.isoformat()}. Queste immagini sono le locandine di un post di Night Life Bergamo "
        "con le serate e gli eventi serali di Bergamo e provincia. Estrai SOLO gli eventi con data "
        f"uguale o successiva a oggi. Rispondi solo con un array JSON (nessun altro testo), "
        'ogni elemento: {"title": nome evento o serata, "date": "AAAA-MM-GG", "place": locale e comune, '
        '"desc": breve descrizione con DJ/ospiti/orari se leggibili, max 140 caratteri, "sicuro": true/false}. '
        "Se non leggi bene una data, un nome o un locale, ometti l'evento oppure metti sicuro=false. "
        "Non inventare nulla. Se non ci sono eventi validi rispondi []. "
        "Se la data riporta solo giorno e mese, deduci l'anno più vicino a oggi.")})
    corpo = json.dumps({"model": MODEL, "max_tokens": 4000,
                        "messages": [{"role": "user", "content": contenuto}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=corpo, headers={
        "x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    testo = json.loads(http(req, 300))["content"][0]["text"]
    m = re.search(r"\[.*\]", testo, re.S)
    return json.loads(m.group(0)) if m else []


def main():
    try:
        stato = json.load(open(STATO_FILE))
    except FileNotFoundError:
        stato = {"post_letti": []}
    letti = set(stato["post_letti"])
    nuovi_eventi, errori = [], []
    for post in graph():
        giorno = dt.date.fromisoformat(post["timestamp"][:10])
        if post["id"] in letti or (OGGI - giorno).days > 21:
            continue
        urls = [c["media_url"] for c in post.get("children", {}).get("data", []) if c.get("media_url")]
        if not urls and post.get("media_url") and post.get("media_type") == "IMAGE":
            urls = [post["media_url"]]
        if not urls:
            continue
        try:
            immagini = [scarica(u) for u in urls[:20]]
            for e in leggi_immagini(immagini, post["permalink"]):
                nuovi_eventi.append((e, post["permalink"]))
            letti.add(post["id"])
        except Exception as ex:  # il post resta da rileggere alla prossima esecuzione
            errori.append(f"{post['permalink']}: {ex}")
    d = json.load(open("eventi.json"))
    esistenti = {e["id"]: e for e in d["eventi"]}
    aggiunti = 0
    for e, permalink in nuovi_eventi:
        try:
            data = dt.date.fromisoformat(e["date"])
        except Exception:
            continue
        if data < OGGI or not e.get("title"):
            continue
        eid = "nl-" + hashlib.sha1(f'{e["title"]}|{e["date"]}|{e.get("place","")}'.lower().encode()).hexdigest()[:8]
        if eid in esistenti:
            continue
        esistenti[eid] = {"id": eid, "title": e["title"], "cat": "serate", "start": e["date"],
                          "place": e.get("place", "Bergamo"), "desc": e.get("desc", ""),
                          "url": permalink, "stato": "controllare" if e.get("sicuro", True) is not False else "da-confermare"}
        aggiunti += 1
    # toglie le serate di Night Life ormai passate
    d["eventi"] = [e for e in esistenti.values()
                   if not (e["id"].startswith("nl-") and dt.date.fromisoformat(e["start"]) < OGGI)]
    if aggiunti:
        d["aggiornato"] = OGGI.isoformat()
    json.dump(d, open("eventi.json", "w"), ensure_ascii=False, indent=1)
    stato["post_letti"] = sorted(letti)[-40:]
    stato["ultimo_errore"] = errori
    json.dump(stato, open(STATO_FILE, "w"), ensure_ascii=False, indent=1)
    print(f"Serate aggiunte: {aggiunti}; errori: {len(errori)}")
    for x in errori:
        print("ERRORE", x)
    if errori and not aggiunti:
        sys.exit(1)


main()
