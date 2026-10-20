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

> 2026-10-20: **Repo creado, todo en local, sin desplegar y sin remoto.** Nombre de producto
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

## Pendiente: lo que tiene que decidir el usuario

1. **El nombre del repo en GitHub** (se propone `market-hub-bots`) para añadirlo como submódulo.
2. **El dominio.** Se propone `bots.themarkethub.app` (o `league.themarkethub.app`): la cookie de
   sesión de Market Hub vive en `.themarkethub.app`, así que un subdominio entra con la misma sesión
   sin hacer nada. Un dominio propio (p. ej. `botleague.app`) necesitaría un paso de entrada nuevo
   en el portal (como `appweb.py` para la app de móvil), porque la cookie no viaja a otro dominio.
3. **Mover el motor y la API del agente fuera del portal.** Propuesta:
   - Bot League es el **único que avanza las curvas** (el refresh) y el dueño del kit, las claves y
     `/api/bot/*`.
   - En el portal, Community > Bot competition pasa a ser una tarjeta con el tablero resumido y el
     enlace a Bot League; se quitan su `POST /api/bots/refresh` y el kit. Mientras haya kits viejos
     apuntando a `themarkethub.app`, el portal puede seguir contestando `/api/bot/*` (escribe en las
     mismas colecciones y no toca curvas) o devolver un mensaje con la dirección nueva; `mh.py` no
     sigue redirecciones de un `PUT`.
   - El portal sigue borrando bot y clave al borrar la cuenta (ya lo hace) y su página de
     privacidad y la de cuenta nombran Bot League como el sitio donde se ve el bot.
   - Hasta que se haga, los dos pueden avanzar los bots sin pisarse: comparten el candado
     (`running_utc`) y el ritmo (`checked_utc`) de `bot_meta/board`, y cada uno comprueba antes de
     escribir que el bot sigue siendo el que leyó.
4. **¿Tablero público?** Hoy los bots de los miembros solo los ven los miembros con sesión (lo que
   dice la privacidad del portal). Enseñarlos a todos en la portada (`BOTLEAGUE_PUBLIC_BOARD=1`)
   exige cambiar antes la página de privacidad del portal.

## Otros pendientes

- Desplegar (`make deploy`, Cloud Run `bot-league`, 2 GiB y 300 s por el refresh de 500 tickers),
  mapear el dominio y el CNAME en Cloudflare: solo con el OK del usuario.
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
