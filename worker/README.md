# Segnalazioni di eventi (Cloudflare Worker)

Il modulo "Nuovo evento" di `index.html` invia i dati a questo Worker, che crea una Issue
con etichetta `segnalazione` nel repository. GitHub avvisa chi fa "Watch" sul repository.
L'aggiornamento settimanale legge le Issue aperte, verifica gli eventi e li aggiunge a
`eventi.json` ("controllare"); la Issue si chiude con `Fixes #N` nel messaggio di commit.

## Attivazione (una volta)
1. GitHub > Settings > Developer settings > Fine-grained tokens: nuovo token, solo repository
   `civado`, permesso **Issues: Read and write**. Copialo senza incollarlo in chat.
2. Cloudflare > Workers & Pages > Create > Worker. Incolla `segnalazioni.js` e distribuisci.
3. Nel Worker: Settings > Variables and Secrets:
   - `ALLOWED_ORIGIN` = `https://lauranappi.github.io`
   - `GITHUB_TOKEN` = il token (tipo Secret)
4. Copia l'indirizzo del Worker (`https://....workers.dev`) e mettilo in `index.html`
   nella costante `SEGNALAZIONI_URL`.
5. Repository civado > Watch > Custom > Issues, per ricevere l'avviso.

## Configurazione sincronizzata
`wrangler.jsonc` contiene il nome del Worker e la variabile `ALLOWED_ORIGIN`, così le distribuzioni da Wrangler
e dal pannello restano allineate. Il segreto `GITHUB_TOKEN` non sta nel file: si imposta a parte.
