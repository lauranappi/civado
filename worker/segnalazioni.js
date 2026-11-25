// Cloudflare Worker: riceve il modulo "Nuovo evento" di Ci Vado e crea una Issue su GitHub.
// Variabili (Settings > Variables and Secrets del Worker):
//   ALLOWED_ORIGIN  es. https://lauranappi.github.io  (separate da virgola se più di una)
//   GITHUB_TOKEN    segreto: token con solo il permesso Issues (lettura e scrittura) sul repo civado
const REPO = "lauranappi/civado";
const CATS = ["mostre", "corsi", "ragazzi", "spettacoli", "serate", "feste"];
const DATA = /^\d{4}-\d{2}-\d{2}$/;

const pulisci = (v, max) => String(v ?? "").replace(/[`\u0000-\u001f]/g, " ").replace(/\s+/g, " ").trim().slice(0, max);

export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin") || "";
    const consentiti = (env.ALLOWED_ORIGIN || "").split(",").map(s => s.trim());
    const cors = {
      "Access-Control-Allow-Origin": consentiti.includes(origin) ? origin : "null",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Vary": "Origin",
    };
    const risp = (stato, testo) => new Response(JSON.stringify({ ok: stato === 200, messaggio: testo }),
      { status: stato, headers: { ...cors, "Content-Type": "application/json" } });

    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (req.method !== "POST") return risp(405, "Metodo non consentito");
    if (!consentiti.includes(origin)) return risp(403, "Origine non consentita");

    let f;
    try { f = await req.json(); } catch { return risp(400, "Dati non validi"); }
    if (f.sito) return risp(200, "Grazie"); // campo trappola per i bot: finge di accettare

    const e = {
      title: pulisci(f.title, 120),
      cat: pulisci(f.cat, 20),
      start: pulisci(f.start, 10),
      end: pulisci(f.end, 10),
      place: pulisci(f.place, 120),
      url: pulisci(f.url, 300),
      desc: pulisci(f.desc, 500),
    };
    if (!e.title || !e.place) return risp(400, "Titolo e luogo sono obbligatori");
    if (!CATS.includes(e.cat)) return risp(400, "Categoria non valida");
    if (!DATA.test(e.start) || (e.end && !DATA.test(e.end))) return risp(400, "Data non valida");
    if (e.url && !/^https?:\/\//i.test(e.url)) return risp(400, "Il link deve iniziare con http");

    // Il contenuto sta in un blocco di codice: le @menzioni non notificano nessuno
    const corpo = "Segnalazione ricevuta dal sito. Da verificare prima di pubblicarla.\n\n```json\n" +
      JSON.stringify(e, null, 1) + "\n```";
    const r = await fetch(`https://api.github.com/repos/${REPO}/issues`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "civado-segnalazioni",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title: `Segnalazione: ${e.title}`, body: corpo, labels: ["segnalazione"] }),
    });
    if (!r.ok) return risp(502, "Non siamo riusciti a registrare la segnalazione, riprova più tardi");
    return risp(200, "Grazie! La controlliamo e la pubblichiamo.");
  },
};
