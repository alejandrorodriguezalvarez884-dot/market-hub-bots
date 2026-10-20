# Bot League · Handoff

Última actualización: 2026-10-20.

## Qué se pidió

El 2026-10-20 se montó en el portal (`market-hub-landing`, My Hub > Community > Bot competition)
una competición de bots: un kit para el agente del miembro, un bot de reglas (`markethub-bot/1`),
una clave del usuario para enviarlo, ejecución en papel desde el cierre siguiente al envío y una
clasificación por día, semana, mes, año y desde el inicio. El mismo día el usuario pidió tratarlo
como **un producto aparte, con su propia web** ("una web chula específica para esto"), con **la
misma base de datos, compartida**, en un repo nuevo dentro del workspace.

Decisiones del usuario que vienen del portal: el bot es un fichero de reglas, no código; solo
largo entre las 500 mayores de EE. UU.; se envía con una clave del usuario; la clasificación cuenta
solo desde el envío (el backtest es privado). Por defecto (no las pidió él): un bot por miembro y
reglas privadas.

## Dónde estamos

> 2026-10-20: **"Your bot" (`/me/`), más simple y dibujada** (en main, sin desplegar). El usuario
> la quería "mucho más visual": sin bot, solo crearlo; con bot, el bot ocupa la página y lo de
> hacerlo de cero queda en un rincón pequeño.
> - **Sin bot**: el robot en gris (con el nombre del miembro), "Create your bot" y tres tarjetas:
>   descargar el kit (con la clave), abrirlo con el agente, decir "Let's build my bot". La clave,
>   plegada debajo ("Already have the kit?").
> - **Con bot**: cabecera con su robot, nombre, idea y una píldora de estado (en marcha desde…, en
>   pausa, o "Starts at the close of …"), el cambio que espera al próximo cierre (abre "Change it"),
>   y dos acciones: **Change it** (abre el editor, el chat y los interruptores, con las pestañas
>   "Rules · Ask Claude · Pause or leave out", y "Done" para cerrar) y su página pública. Debajo:
>   las cinco cifras con su puesto dibujado como una marca en una fila (el 1.º a la izquierda); la
>   curva **contra el S&P 500** (lee `/api/board/bot/{slug}`, que ya da la curva con el índice y
>   `starts`; si falla, la curva sola de `/api/bots`); **lo que tiene** como un treemap (cada
>   empresa del tamaño de su peso, la liquidez rayada; enlaza a la ficha del portal); lo que ha
>   tenido (`strip()`); y **lo que ha hecho** como una línea de tiempo: cada rebalanceo una barra
>   arriba (compró o subió) y otra abajo (vendió o bajó), en escala de raíz cuadrada, y un rombo
>   por cada cambio de reglas, pausa o reanudación; al pasar o tocar se lee debajo. Las empresas
>   excluidas, en fichas. Las reglas en palabras y "Start again from scratch" (kit, clave y
>   retirar el bot), plegados al pie.
> - **Sin empezar**: el treemap de lo que tendría, con borde discontinuo y la etiqueta "preview",
>   junto a la curva en espera con la fecha en que empieza.
> - Dibujos nuevos en `site/src/lib/mybot.ts` (`treemap`, `rankMeter`, `timeline`, `detail`); CSS
>   al final de `global.css`. **La API no cambia**: ni el portal ni la app de móvil se tocan.
> - Probado con `make check` (50 tests, `astro check` limpio) y en local con `make demo`, de
>   escritorio y a 375 px sin scroll lateral, en los tres estados (con historial, recién enviado,
>   sin bot), abriendo "Change it" y sus pestañas, el rincón y la lectura de la línea de tiempo.

> 2026-10-20: **Desplegado** `bot-league-00005-4lj` desde un export limpio de b17c2a0 (la rama
> `visuals` fusionada en main sin conflictos, con el OK del usuario, más la actividad, el editor y el
> chat). El chat queda **encendido**: `BOTLEAGUE_CHAT=1`, `claude-haiku-5-5`, esfuerzo `high`, 15
> mensajes al día por jugador y sin tope diario del servicio (decisión del usuario), con el secreto
> `ANTHROPIC_API_KEY` que ya lee el portal. La configuración cambia solo en eso. Comprobado: páginas y
> salud en 200, el chat pide sesión (401). Falta probar un mensaje real con la sesión del usuario.

> 2026-10-20: **Gráficas y una cara para cada bot** (rama `visuals`, sin desplegar). El usuario
> pidió trabajar la visual de las gráficas y "un monigote de un robot gracioso" por bot.
> - **Robots** (`site/src/lib/robot.ts`): cada bot tiene un robot dibujado en SVG a partir de su
>   slug (FNV-1a + mulberry32): cabeza (8 formas), tono de la carcasa (5 grises, uno claro con la
>   cara en negro), ojos (10), boca (8), antena (8), orejas (4), pecho (5), cero a dos extras
>   (pajarita, monóculo, bigote, cascos, chistera, cejas, mofletes, tornillo, parche) y a veces la
>   cabeza ladeada. Solo tinta, sin color. Sale en las filas del tablero y de la portada, grande en
>   la página del bot y en "Your bot" (con el slug que la página ya usa para el enlace,
>   `handle_key`). El S&P 500 lleva un panel con una línea (`indexFace`). `/robots/` (noindex, sin
>   enlace) enseña los de la casa, 72 inventados y los tamaños, y cuenta cuántas caras distintas
>   salen entre 1.000 bots. Cambiar una lista o el orden de los `r()` en `traits()` cambia la
>   cara de todos los bots.
> - **Gráficas** (`site/src/lib/chart.ts`, mismas firmas): en la del bot, el hueco entre el bot y
>   el S&P sombreado en verde (por delante) o rojo (por detrás), cifras al final de cada línea,
>   porcentajes a la izquierda, meses en el eje, una banda debajo con la caída desde su máximo
>   (al menos 4 % de fondo, para que una caída pequeña se vea pequeña), botones 1M/3M/1Y/All
>   (rebasados al cierre anterior) cuando la curva es más larga, puntos con pocas sesiones y una
>   lectura al pasar el ratón o el dedo (fecha, cada línea, "Ahead/Behind by", desde el máximo).
>   Sin curva aún, `chartWaiting` dibuja la línea de salida con "Its line starts at the next
>   close". Las sparklines llevan el área desde el inicio en el color del final y un punto al
>   final; sin empezar, una línea de puntos. En "Your bot", la misma gráfica con una sola línea.
>   En el móvil (<480 px) la portada quita la sparkline de sus filas para dejar sitio al nombre.
> - Cambios en las páginas, pequeños: `board.ts`, `board/`, `bot/` y `me/` solo añaden la cara y
>   llaman a `chartWaiting`; el resto va en los dos módulos y al final de `global.css`.
> - Probado con `make check` y en local (`make demo`) de escritorio y a 375 px sin scroll lateral.

> 2026-10-20: **Ver lo que hace cada bot y cambiarlo en vivo desde la web.** El usuario echaba en falta
> ver qué lleva y qué hace el bot de cada jugador, y poder darle instrucciones desde la web. Decisiones
> suyas: un cambio **conserva el historial**, se aplica **desde el próximo cierre** (nunca hacia atrás),
> **una vez al día**, y la página del bot dice en público "rules changed on <fecha>" (no las reglas
> nuevas); editor con controles **y** un chat con Claude que propone y el miembro confirma; **nada de
> órdenes**, solo reglas e interruptores (pausar a liquidez, reanudar, excluir o readmitir una empresa).
> - **Motor** (`engine.py` = `bots.py` del portal, mismo parche): `run()` registra cada rebalanceo que
>   negocia (`log`: antes y después, rotación y coste; se guardan los 260 últimos) y acepta `force`
>   (rebalancear en el cierre en que cambia) y `paused` (liquidez). `edit()` y `switch()` dejan el cambio
>   en `pending`; `_advance` lo aplica en su primer cierre, guarda la versión (`versions`: desde qué
>   cierre, qué cambió, las reglas, que solo ve su dueño) y fuerza el rebalanceo allí. Un bot que aún no
>   empezó cambia sin más. Las exclusiones del interruptor sobreviven a un cambio de reglas (salen con
>   "include"). Al enviar o cambiar un bot sin empezar, `preview` guarda lo que tendría al último cierre.
>   El refresh no guarda su trabajo si el dueño tocó el bot mientras corría (`_edits`).
> - **Página de cada bot** (pública): lo que tiene, cada rebalanceo (+ compró, − vendió, ↑ subió, ↓
>   bajó), lo que tuvo a lo largo del tiempo, los cambios con su fecha y, antes de empezar, cuándo
>   empieza y lo que tendría (marcado como vista previa).
> - **Página del dueño**: lo que hizo, lo que espera al próximo cierre, y "Change it, live" con el
>   editor (controles, reglas en palabras y vista previa con `POST /api/bots/preview`), el chat y los
>   interruptores. Rutas: `PUT /api/bots/mine/rules`, `POST /api/bots/mine/switch`,
>   `POST /api/bots/mine/chat`, y para el agente `PATCH /api/bot` (`mh.py update`).
> - **Chat** (`chat.py`): salida estructurada (`output_config.format`), la propuesta pasa por `check()`
>   y el miembro la aplica. No se guarda nada del chat. **Apagado** (`BOTLEAGUE_CHAT=0`): gasta con la
>   clave de Anthropic del usuario y está pendiente de su OK al modelo y a los topes (propuesta:
>   `claude-opus-5-5` con esfuerzo bajo, unos 0,03–0,06 $ por mensaje; 15 mensajes por miembro y día;
>   2 $ al día en total, libro en `bot_meta/chat`). Con Opus/Sonnet 5.5 manda `fallbacks: "default"`.
> - La privacidad y la cuenta del portal ya dicen lo nuevo que se guarda y lo que va al modelo.
> Tests: 54 aquí, y los del portal. Sin desplegar.

> 2026-10-20: **El logo de Bot League.** El usuario pidió un logo serio. La marca es una B que sale
> de la de The Market Hub: su eje, el trazo que la cruza (aquí la cintura de la B) y el punto, con
> las panzas cortadas a 45 grados como pistas de circuito. En tinta, sin color: el verde del portal
> significa "sube" en los datos. Está en `site/src/components/Mark.astro` (cabecera),
> `site/public/favicon.svg` y `brand/share.mjs`; si cambia, se cambian los tres. `make icons` dibuja
> `favicon.ico`, `favicon-192.png`, `apple-touch-icon.png` y `logo.png` desde el SVG, y `make share`
> la imagen de un enlace compartido (`share.png`, 1200×630), las dos con el Chrome del equipo, como en
> el portal. El `<head>` enlaza los iconos y pone `og:image` con tarjeta grande. **Desplegado** como
> `bot-league-00004-52g` desde un export limpio de 7aff24f (configuración igual antes y después).

> 2026-10-20: **El aspecto, el de The Market Hub.** Al usuario no le gustó que la web cambiara tanto
> el look & feel frente al portal, y pidió "by The Market Hub" con enlace a la web. Fuera el violeta,
> la rejilla con brillo, las sombras y el titular grueso: la capa propia de `global.css` toma las
> medidas de la portada del portal (titular y capítulos de peso 500, línea fina sobre cada bloque,
> botones en tinta, marcos como sus tarjetas) y la cabecera y el pie son los del portal, con su
> marca, "Bot League" y "by The Market Hub" enlazando a https://themarkethub.app. Los textos dicen
> "The Market Hub". Los nombres `signal` siguen en las páginas, pero valen la tinta. Desplegado como
> `bot-league-00003-bjb` desde un export limpio de 80e8185; la configuración del servicio no cambia.

> 2026-10-20: **Desplegado en https://bots.themarkethub.app** (Cloud Run `bot-league`, revisión
> `bot-league-00002-ptm`, desde un export limpio de 67afcca), con el OK del usuario. La primera
> revisión (00001, de 3d8ea41) falló al escribir en Firestore: **Firestore no admite un array dentro
> de otro**, y las curvas son `[[fecha, valor], …]`. Ahora `FirestoreBots` y `FirestoreHouse` guardan
> cada fila como `{"row": [...]}` y la desenvuelven al leer (`engine.packed`/`unpacked`, igual en el
> `bots.py` del portal). Mapeo de dominio creado y CNAME `bots` → `ghs.googlehosted.com` (sin proxy)
> en Cloudflare; HTTPS desde las 12:18 UTC. El primer refresh arrancó los seis bots de la casa (su
> historial empieza al cierre del 2026-10-20) y guardó el índice. Aún no hay bots de miembros.
> Entorno: `MARKETHUB_FIRESTORE=1`, `market-hub`, `HUB_URL`, `HUB_SESSION_SECRET` (secreto
> `market-hub-session-secret`), `SEC_USER_AGENT`, `BOTLEAGUE_PUBLIC_BOARD=1`; 2 GiB, 300 s, 0–2.
> Un `POST` sin cuerpo a Cloud Run necesita `Content-Length` (curl `-d ''`); httpx ya lo manda.

> 2026-10-20: **Repo creado (primera versión, en local).** Nombre de producto
> elegido aquí: **Bot League** (by Market Hub); carpeta `market-hub-bots/`, paquete `botleague`.
> Se puede cambiar.
> - **Backend** (`src/botleague/`): `engine.py` es copia del `bots.py` del portal (solo cambian
>   los imports); `league.py` añade lo propio: los **bots de la casa** (los seis ejemplos del kit,
>   ejecutados en papel desde el cierre siguiente a su arranque, como cualquier bot: referencias que
>   nunca se clasifican), el índice de tres años para las páginas de bot, el tablero tal como lo
>   enseña la web (con sparkline de cada bot) y la página de cada bot. Guarda un solo documento
>   propio, `bot_meta/house`. `names.py` copia las reglas de nombres del portal; `market.py` lee la
>   lista de la SEC y los cierres de Yahoo como el portal; `hubauth.py` lee la cookie de Market Hub
>   sin cerrar la web (las páginas y el tablero se ven sin sesión). Con Firestore, `FirestoreMembers`
>   **solo lee** `shared_portfolios` y `competition_entries` del portal para que un nombre ocupado
>   allí lo esté aquí, como hace el portal.
> - **API** (`api.py`): públicas `/api/board`, `/api/board/refresh`, `/api/board/bot/{slug}`,
>   `/api/me`; del miembro con cookie, **las mismas rutas que el portal** (`/api/bots`, `kit`,
>   `key`, `mine`, `refresh`); del agente con clave, **las mismas** (`/api/bot/spec|check|backtest`,
>   `PUT/GET /api/bot`). El `tools/mh.py` del kit funciona igual contra el portal o contra Bot League:
>   solo cambia `MARKETHUB_URL`. Una clave hecha en uno vale en el otro (misma colección y hash).
> - **El kit** (`src/botleague/kit/`) es el del portal con los textos apuntando a Bot League
>   (`{{SITE}}/me/`, `{{SITE}}/board/`) en vez de a My Hub.
> - **Web** (`site/`, Astro + Tailwind, tema oscuro del portal con un violeta propio): portada con
>   el tablero en vivo como protagonista junto al titular, los tres pasos con el agente escribiendo
>   en un terminal, qué es un bot (el fichero y el mismo bot en palabras), para quién, las reglas y
>   preguntas; `/board/` (cinco periodos, el S&P 500 y los bots de la casa intercalados como
>   referencia); `/bot/?b=slug` (curva contra el S&P 500, rentabilidades y puestos, lo que tiene,
>   reglas si es de la casa o tuyo); `/me/` (tu bot, el kit con la clave, la clave); `/rules/` (las
>   reglas y las siete cifras, leídas de `/api/bot/spec`). Visitantes sin sesión: ven los bots de la
>   casa, el índice y cuántos bots de miembros hay, con el aviso de entrar para verlos.
> - **Probado**: 38 tests (`make test`): los del motor del portal, compatibilidad con documentos
>   escritos por el código del portal, y rutas. En local con `make demo` (cierres inventados,
>   siete bots inventados y los de la casa) en el navegador, de escritorio y a 375 px sin scroll
>   horizontal; de punta a punta con el kit (descargar con clave → `mh.py status/check/backtest/submit`);
>   y el código del portal lee los bots que escribió este servicio en el mismo almacén.

> 2026-10-20 (tarde): **El usuario contestó las cuatro preguntas.**
> - Repo: https://github.com/alejandrorodriguezalvarez884-dot/market-hub-bots, submódulo del workspace.
> - Dominio: **bots.themarkethub.app**. Más adelante querrá además un dominio propio (abajo, qué
>   haría falta). Nada en el código fija el host: el kit toma la dirección de la petición, la web
>   llama a su propio origen y solo `site/SITE_URL` (enlaces canónicos) nombra el subdominio.
> - **Bot League es el único que avanza las curvas** y el dueño del kit, las claves y `/api/bot/*`.
>   Hecho también en el portal (`market-hub-landing`, fd9a91a): su refresh se lo pide a
>   `/api/board/refresh` de aquí (ruta abierta, sin cookie, al ritmo de la competición), ya no hace
>   kit ni claves nuevas, su página es un resumen con el camino aquí y sus `/api/bot/*` contestan 410
>   con esta dirección. La app de móvil (700bda2) solo cambia textos.
> - **Tablero público**: la privacidad del portal ya lo dice; `BOTLEAGUE_PUBLIC_BOARD` vale 1 por
>   defecto. Textos del kit (SPEC, AGENTS), portada y reglas, cambiados.

## Un segundo dominio, más adelante

La sesión de Market Hub es la cookie `mh_session` del portal, en `.themarkethub.app`: en otro
dominio (p. ej. `botleague.app`) el navegador no la manda. Haría falta:
1. **Un paso de entrada en el portal**, como `appweb.py` para la app de móvil: el visitante pulsa
   "Sign in" en el dominio nuevo, va al portal, que (con sesión) le devuelve a una ruta de Bot League
   con un token firmado y de un solo uso; Bot League lo comprueba con el secreto del hub y pone **su
   propia** cookie de sesión en su dominio. El portal debe aceptar solo direcciones de vuelta que él
   nombre (lista cerrada).
2. En Bot League, leer esa cookie propia además de `mh_session` (`hubauth.py`), y cerrar sesión en los dos.
3. Mapear el dominio en Cloud Run al mismo servicio y su DNS; `site/SITE_URL` decide cuál es el canónico.
4. Las escrituras con cookie ya comparan `Origin` con el host de la petición: valen en los dos dominios.
El kit y la API del agente no necesitan nada: la clave no depende del dominio.

## Otros pendientes

- **Desplegar** (`make deploy`, Cloud Run `bot-league`, 2 GiB y 300 s por el refresh de 500
  tickers), luego el portal, en ese orden (los `410` del portal mandan aquí). Mapeo de dominio
  `gcloud beta run domain-mappings create --service bot-league --domain bots.themarkethub.app
  --region europe-west1` y en Cloudflare un CNAME `bots` → `ghs.googlehosted.com` (sin proxy). El
  usuario dio el OK al dominio; el despliegue se le confirma antes, con lo que sale.
- Imagen para compartir (`og:image`) propia; la portada aún no tiene.
- Que el healthcheck del mantenimiento diario lea la web cuando esté desplegada.
- La app de móvil no tiene la competición.
- Los festivos de EE. UU. no se conocen al decidir si un bot "está atrasado" (como en el portal): un
  festivo pide un refresh que no mueve nada, a lo sumo cada 30 min.

## Cómo se trabaja

- `make test` (pytest), `make check` (tests + `astro check` + build).
- `make demo`: construye la web, siembra `data/bots` con bots inventados sobre cierres inventados
  (`scripts/seed_local.py`) y sirve todo en `:8080` como un miembro local. `?visitor=1` en cualquier
  página la ve como visitante (hasta `?visitor=0`).
- `make serve`: lo mismo sobre cierres reales de Yahoo (descarga 5 años de 500 tickers la primera vez).
- `make api` + `make dev`: API en `:8000` y web con recarga en `:4321`.
- Los documentos de `tests/fixtures/portal_docs.json` se regeneran con el código del portal:
  `cd ../market-hub-landing && uv run python ../market-hub-bots/scripts/portal_docs.py ../market-hub-bots/tests/fixtures/portal_docs.json`.
- Variables: `.env.example`. Producción: `MARKETHUB_FIRESTORE=1`, `HUB_URL`, el secreto
  `market-hub-session-secret` como `HUB_SESSION_SECRET`, `SEC_USER_AGENT`.
