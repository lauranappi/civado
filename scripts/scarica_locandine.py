#!/usr/bin/env python3
"""Scarica i post recenti dei profili in profili_instagram.json (Instagram Business Discovery)
in una cartella 'locandine/' con un file elenco.json: tutte le immagini di ogni post e il testo.
Non li interpreta: li legge l'aggiornamento settimanale. Solo libreria standard.
Variabili d'ambiente: META_TOKEN (token Pagina), IG_USER_ID (ID Instagram di Laura).
"""
import datetime as dt, json, os, sys, urllib.error, urllib.parse, urllib.request

TOKEN = os.environ["META_TOKEN"]
IG_ID = os.environ["IG_USER_ID"]
GIORNI = 14        # età massima dei post
POST = 6           # post recenti richiesti per profilo
IMMAGINI = 20      # immagini massime per post
TESTO = 1500       # caratteri massimi del testo del post
OGGI = dt.date.today()
OUT = "locandine"
PROFILI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profili_instagram.json")


def http(req):
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def chiedi(username, media):
    campi = f"business_discovery.username({username}){{media.limit({POST}){{{media}}}}}"
    url = f"https://graph.facebook.com/v27.0/{IG_ID}?" + urllib.parse.urlencode(
        {"fields": campi, "access_token": TOKEN})
    return json.loads(http(urllib.request.Request(url)))["business_discovery"]["media"]["data"]


def motivo_errore(ex):
    """Messaggio breve, senza mai riportare il token (log e ramo sono pubblici)."""
    codice, testo = None, str(ex)
    if isinstance(ex, urllib.error.HTTPError):
        try:
            err = json.loads(ex.read())["error"]
            codice, testo = err.get("code"), err.get("message", testo)
        except Exception:
            pass
    return codice, testo.replace(TOKEN, "***")[:200]


def post_recenti(username):
    base = "id,timestamp,permalink,caption,media_type,media_url"
    try:  # con l'anteprima dei video, se l'API la concede
        return chiedi(username, base + ",thumbnail_url,children{media_type,media_url,thumbnail_url}")
    except urllib.error.HTTPError:
        return chiedi(username, base + ",children{media_type,media_url}")


def immagine(m):
    """Indirizzo dell'immagine di un elemento; per i video solo l'anteprima."""
    return m.get("thumbnail_url") if m.get("media_type") == "VIDEO" else m.get("media_url")


with open(PROFILI, encoding="utf-8") as f:
    profili = json.load(f)["profili"]

os.makedirs(OUT, exist_ok=True)
elenco, errori, riusciti = [], [], 0
for profilo in profili:
    nome_profilo = profilo["username"]
    try:
        posts = post_recenti(nome_profilo)
    except Exception as ex:
        codice, testo = motivo_errore(ex)
        print("ERRORE profilo", nome_profilo, codice, testo)
        if codice == 190:  # token scaduto o non valido: inutile continuare
            sys.exit("Token Meta scaduto o non valido")
        errori.append({"profilo": nome_profilo, "motivo": testo})
        continue
    riusciti += 1
    for p in posts:
        giorno = dt.date.fromisoformat(p["timestamp"][:10])
        if (OGGI - giorno).days > GIORNI:
            continue
        figli = p.get("children", {}).get("data", [])
        urls = [u for u in (immagine(m) for m in (figli or [p])) if u]
        file_post = []
        for i, u in enumerate(urls[:IMMAGINI], 1):
            nome = f"{giorno.isoformat()}_{p['id']}_{i:02d}.jpg"
            try:
                dati = http(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}))
                with open(os.path.join(OUT, nome), "wb") as out:
                    out.write(dati)
                file_post.append(nome)
            except Exception as ex:
                print("ERRORE", nome, motivo_errore(ex)[1])
        testo = (p.get("caption") or "")[:TESTO]
        if file_post or testo:
            elenco.append({"profilo": nome_profilo, "locale": profilo.get("locale"),
                           "comune": profilo.get("comune"), "post": p["permalink"],
                           "data": giorno.isoformat(), "testo": testo, "file": file_post})

if not riusciti:
    sys.exit("Nessun profilo letto: controllare META_TOKEN e IG_USER_ID")

with open(os.path.join(OUT, "elenco.json"), "w", encoding="utf-8") as f:
    json.dump({"scaricato_il": OGGI.isoformat(), "post": elenco, "errori": errori},
              f, ensure_ascii=False, indent=1)
print(f"Profili letti: {riusciti}/{len(profili)}; post: {len(elenco)}; "
      f"immagini: {sum(len(x['file']) for x in elenco)}")
