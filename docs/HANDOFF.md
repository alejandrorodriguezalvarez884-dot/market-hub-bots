# Bot League · Handoff

Última actualización: 2026-11-09.

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

> 2026-11-09: **Desplegado** `bot-league-00016-nqw` desde un export limpio de 6ef7a90 (los premios semanales), con el OK
> del usuario. `.env` rehecho solo en el export con los valores del servicio y borrado después; configuración igual antes y
> después (variables, secretos, recursos, escalado, concurrencia, cuenta de servicio, entrada y tiempo de espera).
> Comprobado: portada, `/es/`, clasificación en los dos idiomas, reglas, "Tu bot", salud y `/api/board` en 200; la sección
> "Premios semanales" y "Un trofeo cada semana" en producción. Un `POST /api/board/refresh` (lo que hace una visita) guardó
> en `bot_meta/board.weeks` las dos semanas jugadas enteras hasta hoy (26 oct y 2 nov), sin nombres, y el resto del
> documento quedó igual. Con 2 bots en producción, las dos las ganó "Bag holder", el único que las jugó enteras (la del 2
> nov con −14,9 %: gana el mejor aunque pierda). **La bienvenida (`bl-onboarding`, entrada de abajo) se fusionó en
> `main` después de este despliegue: no está desplegada.**

> 2026-11-09: **Bienvenida en la primera visita** (rama `bl-onboarding`, fusionada en `main` con el OK del usuario; **sin desplegar**). Pedido junto con la
> bienvenida de la app de iPhone (`market-hub-bots-mobile`, misma rama). La portada ya tiene "Cómo se juega"; quien llega
> por un enlace a la clasificación o a un bot no la ve. Por eso, lo mínimo equivalente: **una tarjeta de tres pasos**
> (`components/Welcome.astro`, textos en `i18n/welcome.ts`, los mismos que la app) en la clasificación y en la página de
> un bot: qué es (un juego gratis, un bot de reglas hecho con Claude, en papel y con clasificación), solo papel y nunca
> consejo, y "Crea tu bot con Claude" / "Entendido" / "Cómo se juega →". En pantalla ancha, los tres pasos en fila; en el
> móvil, se deslizan de uno en uno. Se muestra hasta que se cierra (× o "Entendido"), o hasta que se ve la portada, o si
> el lector ya tiene un bot en la clasificación (con un instante visible en un navegador nuevo, hasta que carga). Lo único
> que se guarda es `bl.welcome = "seen"` en `localStorage` del navegador: **ninguna cookie** nueva (solo `mh_lang`, como
> antes) y nada en el servidor. "Tu bot" sin sesión ya explica el juego ("Entra para jugar", gratis y en papel) y no lleva
> la tarjeta. Probado con `make demo` (en el puerto 8133): en español y en inglés, en escritorio y en móvil, cerrar y
> recargar, la portada y "Tu puesto". `make check` en verde.

> 2026-11-09: **Premios semanales** (rama `bl-weekly-winners`, aquí y en `market-hub-bots-mobile`; fusionada en `main`
> el mismo día con el OK del usuario; desplegada, entrada de arriba). El usuario: "añadir como premios semanales, cada semana un ganador y que haya una clasificación de eso
> también". Un trofeo, solo reconocimiento: nada de dinero. El motor no cambia (todo en `league.py`), así que el portal tampoco.
> - **Cómo se calcula** (`weeks()`, `winner()`): una semana son los cierres de lunes a viernes (Nueva York). Juega una
>   semana entera el bot cuyo historial empezó en una semana anterior y que llegó al último cierre de esa semana; su
>   rentabilidad es su valor en ese cierre entre su valor en el último cierre de antes de la semana (la misma curva del
>   tablero). Gana la mejor; **empate** (a la sexta cifra de la curva, que es como se guarda) = la comparten. Cambiar
>   reglas o pausar a mitad de semana **no** saca a un bot (su historial sigue, como en el tablero); uno enviado durante
>   la semana juega desde la siguiente. Una semana está **cerrada** cuando ha cerrado su viernes o un cierre posterior
>   (si el viernes es festivo, se sabe el lunes; el motor no conoce festivos).
> - **Se guarda sin nada programado**: después de cada refresh, `League.record()` escribe en `bot_meta/board` (`weeks`)
>   el ganador de cada semana cerrada que aún no esté, una sola vez, así que **el premio no cambia si su bot se retira o se
>   sustituye después**. Solo se guarda el `public_id` aleatorio y la fecha del primer cierre del bot (y las cifras de la
>   semana), **nunca un nombre**: el nombre se lee del bot que hay, y un ganador que ya no juega (retirado, sustituido o
>   cuenta borrada) sale como "Un bot que ya no juega". Así no se guarda nada nuevo de nadie. Entre el cierre del viernes
>   y el refresh siguiente, la semana se calcula igual al leer el tablero. El primer refresh tras desplegar guardará todas
>   las semanas pasadas con los bots que hay (los retirados antes no cuentan).
> - **API**: `/api/board` lleva `weekly` (`current`: la semana en juego con los 3 primeros, el del lector si juega, y el
>   S&P 500 en los mismos cierres; `winners`, la más reciente primero, con el S&P 500 y cuántos jugaron; `ranking`: más
>   semanas ganadas, luego la más reciente; los retirados no entran) y cada línea `wins`; `/api/board/bot/{slug}` lleva
>   `wins` (las semanas que ganó). Nada cambia en `/api/bots` ni en lo que lee el portal.
> - **Web**: en la clasificación, la sección "Premios semanales" (`lib/weekly.ts`, textos en `i18n/weekly.ts`) con
>   "Esta semana", "Más semanas ganadas" y "Ganadores", un enlace arriba y un trofeo con el número en cada línea (también
>   en la portada); en la página de un bot, la insignia y "Semanas ganadas"; en Reglas, "Un trofeo cada semana".
>   Glosario de [i18n.md](i18n.md) con premios, ganador y trofeo.
> - **Tests**: `tests/test_weekly.py` (semana entera, empate, semana cerrada y Viernes Santo, lo que ya está guardado, y
>   por la API: guardar, retirar al ganador, la semana en juego). `make test` y `astro check` en verde.
> - **Probado** en local con la demo (`make demo` en el puerto 8093): 35 semanas pasadas con ganador, en los dos idiomas,
>   de escritorio y a 375 px sin scroll lateral; y una copia de la demo congelada al miércoles 4 de noviembre para ver la
>   semana a medias. Sin probar con datos de producción. Pendiente para otra vez si se quiere: Community del portal no
>   los enseña.

> 2026-11-09: **Compartir un bot como imagen** (rama `bl-share-card`, sin fusionar ni desplegar). Lo pidió el usuario:
> que un jugador pueda compartir su bot como imagen, en la web y en la app de iPhone.
> - **La tarjeta la dibuja el servidor** (`src/botleague/card.py`): `GET /api/board/bot/{slug}/card.png?format=story|square|link&period=1d|1w|1m|1y|all&lang=en|es`.
>   Un SVG escrito desde la página del bot (`League.bot`) y pasado a PNG con resvg (`resvg-py`, una rueda de 2 MB sin
>   dependencias del sistema) con las fuentes de la web (IBM Plex, OFL, en `src/botleague/fonts/`, sin fuentes del sistema:
>   la misma imagen en cualquier máquina). Así la web, la app y la vista previa de un enlace son la misma imagen, y hay
>   un solo diseño que mantener. Se ve quien ve la página del bot (con el tablero cerrado, solo miembros); caché pública
>   de 15 min (privada de 5 si el tablero no es público) y las 48 últimas en memoria. Tarda 0,1-0,35 s.
> - **Qué dice**: la cara del bot, su nombre, el nombre de pila del jugador, el periodo con sus fechas, su rentabilidad
>   (verde o roja, los colores del mercado), su puesto entre los bots con puesto en ese periodo ("3.º de 7 bots"), el
>   S&P 500 en las mismas sesiones, las dos líneas desde 1, y "Bot League · un juego en papel, sin dinero real" con la
>   dirección. Solo describe; un test comprueba que no dice comprar, vender, invertir ni objetivo. Antes del primer
>   cierre: "Empieza a jugar en el cierre del …". Formatos: historia 1080×1920, cuadrada 1080×1080, enlace 1200×630.
> - **La cara es la de la web**: `src/botleague/robot.py` es copia de `site/src/lib/robot.ts`, carácter a carácter (los
>   números como los escribe JavaScript). `node scripts/robot_faces.mjs` escribe con el `.ts` las caras de 90 slugs en
>   `tests/fixtures/robot_faces.json` y `tests/test_card.py` comprueba que Python dibuja las mismas. Anotado en `CLAUDE.md`.
> - **Web**: botón "Compartir" en la página del bot y en "Tu bot" (`lib/share.ts`, textos en `i18n/share.ts`): un
>   diálogo con la tarjeta, Historia/Cuadrada, los periodos con cifra, y "Compartir" (Web Share API con el archivo; la
>   imagen se pide al elegir, para que el clic llegue a la hoja de compartir, como exige Safari), "Descargar" y "Copiar
>   enlace". Donde el navegador no comparte archivos, el botón no sale y quedan los otros dos.
> - **Vista previa de cada bot**: `/bot/?b=…` y `/es/bot/?b=…` los sirve ahora FastAPI con el título, la descripción
>   ("De Ana · +12,4 % desde el inicio · 3.º de 7 bots · S&P 500 +8,8 %. Bot League es un juego en papel, sin dinero real.")
>   y la imagen (`og:image`, formato enlace) de ese bot, solo si está en el tablero público. El resto de la web, igual.
> - **App de iPhone**: misma rama en `market-hub-bots-mobile`; descarga esta imagen y abre la hoja de compartir.
> - Probado: `make test` (89 tests) y `astro check`; en local (`make demo` en el puerto 8096) el diálogo en la página de
>   un bot y en "Tu bot", en los dos idiomas, de escritorio y a 375 px, la descarga y las etiquetas de la vista previa.
>   **Sin probar**: la hoja de compartir del navegador (el panel de pruebas no comparte archivos: hace falta Safari o
>   Chrome en un móvil) y cómo pinta la vista previa cada red (WhatsApp, X…), que solo se ve desplegado.
> - **Para desplegar**: nueva dependencia (`resvg-py`, `fonttools`), así que la imagen de Docker cambia; nada de
>   configuración nueva.

> 2026-11-09: **El resumen al entrar** (rama `bl-daily-summary`, sin fusionar ni desplegar). El usuario: "lo de la
> notificación con el resumen, que salga también un resumen cada vez que entres en la app".
> - **API, solo un añadido**: `GET /api/bots/summary?since=AAAA-MM-DD` (con sesión o token de la app; `league.summary`).
>   Cuenta desde `since` (el último cierre que el navegador o el teléfono enseñó) o, si no hay cierre nuevo desde entonces
>   o no llega, desde el cierre anterior al último. Devuelve la rentabilidad del bot y la del S&P 500 en esos mismos
>   cierres, su puesto desde el inicio ahora y entonces (con la misma ordenación que el tablero), sus rebalanceos en ese
>   tramo (3 y la cuenta), los cambios que entraron, la pausa y lo que espera al próximo cierre (y cuándo entra). Un
>   `since` anterior a su inicio cuenta desde el inicio (frente al índice desde la sesión anterior a su primera). El motor
>   no cambia (el portal tampoco). Test nuevo en `tests/test_api.py`.
> - **Nada nuevo en el servidor**: la "última visita" es una fecha de cierre que guarda el navegador (`localStorage`,
>   `bl-seen`: el id público del bot, ese cierre y desde cuál contó). Mientras no hay cierre nuevo se repite el mismo
>   resumen, así que la clasificación y "Tu bot" dicen lo mismo. No hace falta tocar la privacidad del portal.
> - **Web** (`site/src/lib/summary.ts`, textos en `i18n/summary.ts`): una tarjeta arriba de la clasificación y de "Tu bot",
>   cuando el jugador tiene bot, tras mover los bots al último cierre. "Desde tu última visita / En el último cierre /
>   Desde que empezó", del cierre X al Y, N cierres; tu bot ±x % y el S&P 500 ±y %; "2.º de 7 desde el inicio · sube desde
>   el 4.º"; los rebalanceos en palabras; "◆ Desde el …: reglas cambiadas"; "En el próximo cierre (…): excluye AMGN". Un ×
>   la oculta en esa página. Antes de empezar, dice cuándo empieza. Solo describe.
> - Probado: `make test` y `astro check` en verde, y en local con la demo (puerto 8140) en los dos idiomas, de escritorio y
>   a 375 px sin scroll lateral: sin visita previa, con una visita de hace 13 cierres y con un cambio pendiente.
> - **La notificación diaria**: el usuario eligió un aviso local programado por la app de iPhone (rama `bl-daily-summary`
>   de `market-hub-bots-mobile`); aquí no cambia nada ni se programa nada.

> 2026-11-09: **Por qué hizo cada movimiento** (rama `bl-why-moves`, sin desplegar ni fusionar). El usuario: "poder
> indagar el por qué de cada movimiento". Tocar un rebalanceo explica, con las reglas del bot y las cifras que el motor
> leyó en ese cierre, por qué entró cada compra, por qué salió cada venta y por qué cambiaron los pesos.
> - **Cómo: se guarda al rebalancear, no se recalcula.** `engine.reasons()` anota en cada movimiento del registro
>   (`log[].why`): cuántas empresas miró y cuántas pasaron sus filtros, cuántos puestos llena (`hold` menos las de
>   "siempre"), la cifra de la regla de mercado, las reglas que leyó (filtros, puntuación, ponderación, tope) y, para cada
>   acción comprada, vendida o con más o menos peso, su puesto, cada cifra de sus filtros y de su puntuación (4 cifras
>   significativas) y el motivo: `rank`/`always` si la tiene; `paused`, `excluded`, `left`, `missing`, `filter` (con el
>   primero que no pasó), `below` o `cash` si no. Recalcular para una fecha pasada pediría cientos de cierres por
>   petición y las reglas de entonces (no siempre se guardan), y Yahoo puede revisar cierres. Para no acercarse al
>   límite de 1 MB de un documento, solo los últimos `WHY_KEPT` = 60 movimientos guardan el porqué; los anteriores
>   y los de antes de este cambio se leen como siempre (sin motivos, y la web lo dice).
> - **Es el motor del portal**: el mismo cambio en `market-hub-landing` (`bots.py`, `test_bots.py`, misma rama), y
>   `tests/fixtures/portal_docs.json` rehecho con su código; `test_shared.py` comprueba que lo que guarda el portal se
>   cuenta aquí. `decide()` usa ahora `_ranked()`, el mismo orden de siempre (mismos tests).
> - **En palabras, aquí** (`why.py`, EN/ES, aplicado en `league.doings` y en las rutas del dueño con `api.owned`):
>   **el público** ve lo que hicieron las reglas sin lo que son: el tipo de motivo ("No pasó uno de sus filtros",
>   "Puesto 12 por su puntuación, fuera de las 8 mejores que mantiene", "Excluida por su dueño", "Su regla de mercado
>   pasó parte de la cartera a liquidez", "Vuelve al peso del último rebalanceo: los precios lo habían movido") y el
>   puesto; nunca un factor, una cifra, un umbral ni un ajuste. **El dueño** ve además cuántas pasaron, cada cifra con
>   su regla ("Su media de 20 sesiones frente a la de 100: +1,8 % (pide al menos 0 %)"), la cifra de la regla de mercado,
>   la ponderación y el tope. La descarga de lo guardado (`/api/bots/mine`) lleva el `why` tal cual.
> - **Web** (`lib/history.ts`): en "Qué cambió ese día", "Por qué" arriba y bajo cada acción su motivo; las cifras del
>   dueño, plegadas en "Sus cifras en ese cierre". Pie: "Solo tú ves las cifras" o "Lo que hicieron sus reglas…".
> - Probado: `make test` (85) y `astro check`/build sin avisos; en local con la demo, la página pública de un bot y Tu bot
>   en español, de escritorio y a 375 px sin scroll lateral. La app, en `market-hub-bots-mobile` (misma rama).
> - **Decidido por el usuario (2026-11-09)**: la división público/dueño se queda así ("Keep it"): el público ve el motivo
>   y el puesto, nunca las cifras ni las reglas. Pendiente suyo: fusionar y desplegar Bot League y el portal a la vez
>   (el motor).

> 2026-11-09: **Desplegado** `bot-league-00015-j7f` desde un export limpio de ff10c5e (el login de la app de iPhone), con el OK
> del usuario. `.env` rehecho solo en el export con los valores del servicio y borrado después; configuración igual antes y
> después (variables, secretos, recursos y tiempo de espera). Comprobado: portada, `/es/`, clasificación, "Tu bot", reglas,
> salud y `/api/board` en 200; con un token falso, `/api/me` da nadie, `/api/bots` 401 y una escritura sin `Origin` 403.
> Probado por el usuario el mismo día: entrar desde la app con su cuenta contra producción funciona.

> 2026-11-09: **La app de iPhone de Bot League** (fusionado en `main` con el OK del usuario; desplegado, entrada de arriba). El usuario: "abrir una
> rama para hacer la app de móvil de iPhone de bot league"; eligió una app aparte, en un repo nuevo (`market-hub-bots-mobile`,
> misma rama). Aquí solo cambia el login: **Bot League lee el token de la app del portal** (`hubauth.py`), el que el portal
> da en `/api/app/auth/...` (`tokens.py`: el mismo secreto, la sal `markethub.app-token`, un mes). Una petición con
> `Authorization: Bearer <token>` es su usuario o nadie (la cookie no se mira); sus escrituras no necesitan `Origin` (un
> navegador no añade esa cabecera solo); una clave `mhb_` no es un token, y las rutas del agente siguen sin aceptar el token.
> El idioma sigue llegando en `x-mh-lang`. Test nuevo en `tests/test_api.py`; `make test` en verde. **Hasta desplegarlo, la
> app solo ve lo público en producción.** Probado con la app en el simulador contra este servicio en local (`HUB_URL` al
> portal local y el mismo secreto): crear, enviar y cambiar un bot con el chat de guion.

> 2026-11-08: **Desplegados** `bot-league-00014-fvr` (c0deabc) y el portal `market-hub-00072-hc4` (56a10ee, su copia del
> motor), con el OK del usuario y a la vez. Desde exports limpios, con el `.env` rehecho solo en cada export con los
> valores del servicio (en el portal, `SESSION_SECRET` y `FMP_API_KEY` leídos de Secret Manager y comprobados iguales,
> y `ANTHROPIC_SECRET=ANTHROPIC_API_KEY`), borrados después. Configuración igual antes y después en los dos; la clave de
> sesión sigue en su versión 1. Comprobado: las páginas de los dos en los dos idiomas y `/api/health` en 200, Reglas
> con `always`, y "Siempre y nunca" en el código de "Tu bot". El chat de verdad no se ha probado con el tema.

> 2026-11-08: **Temas, "siempre" y "nunca"** (sin desplegar). El usuario: pidió un bot "de IA y semis" y el chat no le
> entendió; y "quiero que se permita de forma clara e intuitiva incluir empresas que tiene que coger sí o sí y otras que
> no tiene que incluir nunca", "a las que tiene que incluir sí o sí, fijarle también el peso mínimo".
> - **Por qué no entendía**: las instrucciones del chat decían que el formato "no tiene sectores" y que lo rechazara,
>   aunque `universe.tickers` sí permite una lista elegida. Ahora el chat recibe la lista de las 500 mayores **con su
>   nombre** (`Directory.names`, del mismo fichero de la SEC, que ya traía el nombre) y monta un tema como lista de
>   tickers, diciendo cuáles ha elegido. Unos 4.000 tokens más por mensaje (Haiku 5.5: ~0,0004 $ por mensaje).
> - **Campo nuevo `always`** en `markethub-bot/1` (opcional, solo se escribe si hay alguna, así que los bots de antes no
>   cambian): hasta 10 `{"ticker", "min_weight"}`. Se mantienen en cada cierre digan lo que digan filtros y puntuación,
>   cuentan en `hold`, y su `min_weight` es del total de la cartera, también cuando la regla de mercado pasa a liquidez
>   (lo que falta sale primero de la liquidez y luego de las demás, en proporción: `_floor`). Con la ponderación `score`
>   no tienen puesto y reciben el peso del medio. Comprobaciones: entre las 500, no en `exclude`, `min_weight` ≤
>   `max_weight`, suma ≤ 1, no más que `hold`. Cambios: `pinned NVDA` / `unpinned NVDA`.
> - **Interruptores `pin` y `unpin`** (`/api/bots/mine/switch` con `min_weight`), como `exclude`/`include`: desde el
>   próximo cierre y sin gastar el cambio del día. Una empresa está en una lista como mucho: "siempre" la saca de "nunca"
>   y al revés.
> - **Web**: el bloque **"Siempre y nunca"** (`lib/companies.ts`) en el borrador (cambia el borrador al momento) y en
>   "Cambia tu bot" (sustituye a "Excluidas"), con las que tiene para tocar, el peso mínimo opcional y deshacer. Las
>   reglas en palabras lo dicen ("Mantiene siempre NVDA (al menos el 15 %)…"); Reglas y `SPEC.md` del kit, también.
> - **Arreglado de paso**: en el cierre en que entraba un cambio pendiente no se leían los cierres de las empresas nuevas
>   que traía (afectaba también a un `include` o a cambiar de 20 a 100 empresas); ahora el refresh los lee.
> - El motor es el del portal: el mismo cambio y los mismos tests en `market-hub-landing` (`bots.py`, `test_bots.py`), y
>   `tests/fixtures/portal_docs.json` rehecho con su código. Probado en local con la demo (chat de guion: "IA y semis,
>   siempre NVDA al 15 % y nunca TSLA"); el chat de verdad (Haiku) no se ha probado.

> 2026-11-08: **Desplegado** `bot-league-00013-9wq` desde un export limpio de af24615 ("Que se vea que es un juego"), con el
> OK del usuario. Configuración igual antes y después (variables, secretos, recursos, escalado y tiempo de espera; `.env`
> rehecho solo en el export con los valores del servicio, `bash scripts/deploy-cloudrun.sh`). Comprobado: portada,
> clasificación, reglas y "Tu bot" en los dos idiomas, salud y `/api/board` en 200, con los textos nuevos en producción.

> 2026-11-08: **Que se vea que es un juego, y más simple** (sin desplegar). El usuario: "quiero que quede más claro que
> es un juego. Además quiero simplificar todo. Que la funcionalidad sea la misma, pero que sea más intuitivo". Solo
> cambian textos y presentación; la API, el motor y lo que se puede hacer son iguales.
> - **Portada**: "A free game by The Market Hub" / "Un juego gratis de The Market Hub"; el titular en tres líneas,
>   "Build a bot. Let it play. Climb the board." / "Crea un bot. Déjalo jugar. Sube en la clasificación."; bajo el botón,
>   tres insignias (Free · No real money · No code). "How to play" / "Cómo se juega" en tres pasos (crear, juega en cada
>   cierre, sube en la clasificación) con la conversación de ejemplo. Las preguntas pasan de seis a tres: fuera las que
>   repetían las reglas (dinero, coste, copiar, cómo se clasifica) y entra "¿Puedo cambiar mi bot cuando ya juega?".
> - **Cabecera**: Leaderboard · How to play · Rules (Clasificación · Cómo se juega · Reglas); en el móvil, sin partir líneas.
> - **Clasificación**: "Who's ahead" / "Quién va delante", y a quien juega, una tarjeta **"Your place" / "Tu puesto"** bajo el
>   podio: su robot, su puesto en el periodo elegido entre los bots con puesto en él ("2.º de 6 en el mes") y su
>   rentabilidad; lleva a "Tu bot". La columna "Running" pasa a "Playing for" / "En juego".
> - **Tu bot, ficha y chat**: "Playing · …" / "En juego · …", "you play as Local" / "juegas como Local", "Sign in to play" /
>   "Entra para jugar"; el chat de crear se titula "Chat with Claude" / "Habla con Claude" (antes repetía "Build").
> - **Reglas**: "Rules of the game" / "Reglas del juego", "One bot per player"; el formato campo a campo y las siete cifras,
>   plegados bajo "For the curious" / "Para curiosos".
> - Glosario de [i18n.md](i18n.md) con juego, jugar, tu puesto, Cómo se juega y Reglas del juego.
> - Probado: `make check` (74 tests, `astro check` sin avisos) y en local con la demo, en los dos idiomas, de escritorio y a
>   375 px sin scroll lateral (el botón de la portada acaba a 546 px en español). Sin probar con datos de producción.

> 2026-11-04: **Desplegado** `bot-league-00012-c2f` desde un export limpio de 50bb963 ("Su cartera, cierre a cierre"), con el
> OK del usuario y la configuración igual antes y después (mismo `.env` rehecho del servicio, `bash scripts/deploy-cloudrun.sh`).
> Comprobado: páginas y salud en 200, y la sección nueva en la página pública de "Bag holder" en producción, sin errores.

> 2026-11-04: **"Su cartera, cierre a cierre": movimientos y composición, más claros** (sin desplegar). El usuario: "en la
> pestaña de mi bot no quedan claros los movimientos que hace el bot ni tampoco la composición de la cartera en función del
> tiempo". Una sección nueva (`site/src/lib/history.ts`, textos en `i18n/history.ts`) sustituye a "Lo que tiene", "Lo que ha
> tenido" (la cuadrícula sin fechas) y "Lo que ha hecho" (las barras):
> - **Una fecha cada vez**: un deslizador con ‹ › por cada rebalanceo y "Hoy" al final; para la fecha elegida, el treemap de lo
>   que tenía (lo que compró ese día, marcado "nueva") y al lado, en palabras, qué cambió: compró, vendió, más peso, menos peso
>   (antes → después) y cuánto movió de la cartera y su coste. En "Hoy", que no ha operado desde el último y qué hizo en él.
> - **Todos sus movimientos** debajo, una línea en palabras cada uno ("Compró AMGN y AXP, vendió TXN y CRM · movió el 41 %"),
>   el más reciente primero, 8 y "Ver los N"; los cambios de reglas o interruptores van entre ellos con ◆. Tocar uno lleva el
>   deslizador a esa fecha.
> - Lo mismo en la página pública de cada bot (`views/Bot.astro`), que perdía también su sección "Cambios" (va en la lista).
>   Fuera `timeline`, `detail`, `strip`, `moves`, `bars` y `versions` y sus textos. La API no cambia.
> - Probado: `make test`, `astro check` y en local con la demo, en los dos idiomas, de escritorio y a 375 px sin scroll lateral:
>   deslizador, botones, tocar un movimiento. Sin probar dibujada una fila de cambio de reglas (la demo no tiene ninguna).

> 2026-11-04: **Desplegado** `bot-league-00011-g7c` desde un export limpio de 0e1c40e, con el OK del usuario. Lleva **la web
> en inglés y en español** (c7ade99 y siguientes) y **solo el chat** (la entrada de abajo). Desplegado desde el Mac, que no
> tenía `.env`: se rehízo, solo en el export, con los valores del servicio. Configuración igual salvo que
> `BOTLEAGUE_CHAT_DAILY_MAX_USD` sale ahora vacía (antes no estaba): `config.py` lo lee igual, sin tope del servicio. Nota:
> `scripts/deploy-cloudrun.sh` no es ejecutable en git; en Mac se lanza con `bash scripts/deploy-cloudrun.sh`. Comprobado:
> portada, `/es/`, `/me/`, `/rules/`, clasificación y salud en 200; el botón al chat en los dos idiomas, sin el kit, y en
> el móvil dentro de la primera pantalla. El portal se desplegó a la vez (`market-hub-00071-5vg`), con su español.

> 2026-11-04: **Fuera la vía "en tu ordenador": solo el chat** (sin desplegar). El usuario lo pidió: "eliminar la
> posibilidad de crear el bot en tu ordenador. Quiero simplificar la app para que sea muy claro y lo primero que salga un
> botón que lleva al chat para crear tu bot".
> - **Portada**: lo primero, centrado y solo, es el botón grande **"Build your bot with Claude" / "Crea tu bot con
>   Claude"** (a `/me/`), con el titular y una frase; en el móvil, a lo ancho y dentro de la primera pantalla. Debajo, más
>   ligero: la clasificación (5 líneas), los tres pasos con la conversación de ejemplo, las reglas en seis, las preguntas y
>   el botón otra vez. Fuera: el bloque del kit con el terminal, el `bot.json` de ejemplo y "para quién es".
> - **"Your bot"**: fuera el kit plegado ("Prefer your own agent?"), la descarga, la clave (crear, ver, retirar) y el kit
>   de "Start again from scratch" (queda crear otro con Claude y retirar el bot). El chat apagado o sin mensajes ya no
>   manda al kit. `/rules/`, el pie y las preguntas ya no hablan del kit ni de la clave.
> - **El backend no cambia**: `/api/bots/kit`, `/api/bots/key` y `/api/bot/*` siguen (las claves que hay siguen
>   funcionando; `/api/bot/spec` lo usa la web). Nada se borra de Firestore. Quitar esas rutas es decisión del usuario.
> - **Fuera de este repo**: Community del portal (`market-hub-landing` d1e33a8) y la app (`market-hub-mobile` cce88c1)
>   ya mandan al chat; a quien aún tiene clave le dejan retirarla.
> - Probado: `make check` (74 tests) y en local con la demo, de escritorio y a 375 px (el botón acaba a 528 px, sin
>   scroll lateral), en inglés y en español, también "Crear otro con Claude".

> 2026-11-04: **La web en inglés y en español** (sin desplegar). El usuario pidió que Bot League "se vea entero en
> español para quien lo prefiera, que quede perfectamente", como piloto del portal. Decisiones suyas (2026-11-04): los
> textos de la web pasan a ser en inglés **y** en español (cambiado en los `CLAUDE.md`), Bot League y el portal a la vez,
> y el idioma lo elige el lector: un aviso discreto cuando el navegador pide el otro idioma, la cookie `mh_lang` en
> `.themarkethub.app` (compartida con el portal) y un selector `English · Español` en el pie; nunca por IP.
> - **Rutas**: inglés en la raíz, español en `/es/` (`/es/board/`, `/es/me/`…). Cada página es una vista
>   (`site/src/views/*.astro`, con `lang`) y dos páginas de dos líneas la pintan; `hreflang` y canónicas por idioma.
>   `/robots/` (interna) sigue solo en inglés.
> - **Textos**: `site/src/i18n/<zona>.ts`, inglés y español uno junto al otro (`words(en, es)`); el chequeo de tipos
>   falla si falta una clave. Cifras y fechas con el idioma de la página (`+30,5 %`, `4 nov 2026`, `3.º de 7`).
> - **El servidor**: la página manda `X-MH-Lang`; con `es`, `src/botleague/es.py` escribe en español las reglas en
>   palabras (`describe(..., lang)`, también en el `bots.py` del portal), los ~70 mensajes de error y avisos, las notas
>   del backtest y de las cifras, y el chat (Claude contesta en español de España; `Scripted` también). Las rutas del
>   agente, el kit y lo que llega sin la cabecera siguen en inglés. Un test falla si un mensaje nuevo no tiene español.
> - Mecanismo, estilo, glosario y plantillas de las reglas en español en [i18n.md](i18n.md).
> - Probado: `make check` (tests en verde) y en local con la demo en los dos idiomas: portada, clasificación, página de
>   un bot, reglas, "Your bot" (cambiar con el chat, crear de cero con el chat, mapa, backtest, cada regla a mano), de
>   escritorio y a 375 px sin scroll lateral.
> - **Al desplegar**: el pie y los avisos enlazan a `/es/privacy/` y `/es/terms/` del portal, así que conviene desplegar
>   antes (o a la vez) el portal con su español.

> 2026-11-04: **Desplegado** `bot-league-00010-lvf` desde un export limpio de 5b14998 (la respuesta ya no espera al mapa), con
> el OK del usuario y sin cambios de configuración. Probado en producción en su Chrome: la respuesta llegó en ~22 s (todo
> Claude, con Haiku 5.5 a esfuerzo alto y la conversación ya larga) con "mapping what it would hold…", y el mapa unos segundos
> después. Si se quiere más rapidez, la palanca es el esfuerzo del chat (decisión del usuario).

> 2026-11-04: **La respuesta de Claude ya no espera al mapa.** `POST /api/bots/draft/chat` devuelve la respuesta y las
> reglas en palabras (`bots.check`), sin `holds`; la página pide después lo que tendría a `/api/bots/preview` (cuenta en el tope
> de 30 por hora con los backtests). Mientras tanto, el paso dice "mapping what it would hold…" y el borrador enseña el hueco
> del mapa "Reading the closes of its companies…"; si falla, "Try again". Un borrador guardado sin mapa lo pide al abrir la
> página. Arregla los ~50 s del primer mensaje con la instancia en frío (el usuario lo pidió).

> 2026-11-04: **Probado en producción con Haiku de verdad**, con la sesión del usuario en su Chrome ("Build a new one with
> Claude", sin enviar: "Bag holder" sigue igual). Dos mensajes en español: Claude contestó en español, propuso un bot entero
> que pasó las comprobaciones a la primera (5 reglas, 10 valores) y, tras un backtest a 1 año, lo comentó como simulación del
> pasado, avisó de la rotación y del coste de mirarlo cada semana, y aplicó el cambio (antes → después bien). **Pendiente:
> la primera respuesta tardó ~50 s** con la instancia en frío: Claude contestó en ~15 s y el resto fue la vista previa
> bajando de Yahoo los cierres del universo; el segundo mensaje, ~15 s. Arreglo posible: devolver la respuesta de Claude
> enseguida y pedir el mapa aparte.

> 2026-11-04: **Desplegado** `bot-league-00009-l94` desde un export limpio de 2a42479 (crear el bot hablando con Claude y la
> revisión visual), con el OK del usuario. La configuración cambia solo en `BOTLEAGUE_CHAT_PER_MEMBER_PER_DAY` (15 → 30);
> recursos, secretos y demás variables, iguales. Comprobado: páginas y salud en 200, la portada nueva, el chat de creación
> pide sesión (401) y un envío desde otro origen se rechaza (403). Falta un mensaje real con la sesión del usuario.

> 2026-11-04: **Revisión para que la web sea más intuitiva y visual** (sin desplegar). El usuario lo pidió tras lo de
> crear desde la web. La entrada principal ya no es el kit sino hablar con Claude en la web:
> - **Portada**: "Tell Claude your idea. The market keeps score."; botón "Build your bot, it's free" (a `/me/`); los tres
>   pasos son ahora decir la idea, verla antes de enviarla (reglas en palabras, mapa, backtest) y competir desde el
>   próximo cierre, con una **maqueta de la conversación** que se escribe sola (`#mock`); el kit pasa a un bloque
>   propio, "Or with your own agent", con el terminal (sin el `--handle` de antes, que ya no existe). Para quién,
>   preguntas, llamada final, pie y `/rules/` dicen las dos vías.
> - **Tablero**: un **podio** con los tres primeros del periodo (sus robots, el 1.º en medio y más alto) y, a quien
>   no tiene bot, "Your bot could be on this board" con "Build your bot".
> - **Página de un bot**: lo que tiene como **treemap** (como en "Your bot", en vez de barras), lo que hizo como la
>   **línea de tiempo** de "Your bot" (tocar una barra la lee) con la lista entera plegada debajo, "Changes" solo si
>   hay alguno, y "Have an idea of your own? · Build your bot" a quien no es su dueño.
> - Probado: `make check` y en local; a 375 px sin scroll lateral en todas las páginas.

> 2026-11-04: **Crear el bot desde la web, hablando con Claude** (sin desplegar). El usuario lo pidió:
> "que el bot league se pudiese crear/modificar directamente en la web… con lenguaje natural, de manera
> similar a como se hace con Claude". Decisiones suyas (2026-11-04): **30 mensajes al día por jugador,
> crear y cambiar juntos** (antes 15), Claude Haiku 5.5 con esfuerzo alto, sin tope del servicio, la
> "mezcla" de abajo y el contador por instancia, para más adelante (sigue el pendiente de abajo).
> - **"Your bot" sin bot** (`site/src/lib/build.ts`): a la izquierda la conversación (Claude saluda, seis ideas
>   con su dibujito: momentum, tendencia, valores tranquilos, comprar caídas, cerca de máximos, unos pocos
>   gigantes; caja para escribir y chips de un toque). Entre las respuestas, **los pasos del código como los
>   de un agente**: "Draft 2 · nombre — checked: 4 rules · would hold 12 stocks today", "Backtest of draft 2,
>   1 year — bot +x% · S&P 500 +y% · worst fall · a simulation of the past". A la derecha **el borrador**: su
>   robot (se va rellenando), las reglas en palabras (desde el segundo, antes → después), el treemap de lo que
>   tendría, el backtest a petición (1 o 3 años: curva contra el S&P 500, total, al año, peor caída, las notas
>   de siempre y la etiqueta "simulation of the past"), "Every rule, by hand" (el editor de siempre, que deja
>   el resultado como borrador) y **Send it in** con un resumen antes (público, nombre de pila, reglas
>   privadas, cuándo empieza, y si sustituye a otro). El kit sigue debajo, plegado ("Prefer your own agent?").
>   El borrador y la conversación viven solo en el navegador (`localStorage`, `bl-build:<slug>`); en el
>   servidor no se guarda nada hasta enviarlo. En el móvil, el borrador va debajo y cada paso lleva "See it ↓".
> - **Con bot**: "Change it" sigue igual; en "Start again from scratch", "Build a new one with Claude" abre la
>   misma conversación (con × para volver), y al enviarlo sustituye al bot (su historial acaba).
> - **La mezcla** (herramientas en el servidor o en la página): cada propuesta pasa por `bots.check` (reglas y
>   universo) y, si no pasa, **vuelve a Claude una vez en la misma petición** con los problemas (como un agente
>   tras `mh.py check`; cuenta como un mensaje, se pagan dos llamadas); la vista previa la pone siempre el
>   código; **el backtest lo pulsa el miembro** y sus cifras (solo números, `chat.figures`) viajan con el
>   mensaje siguiente para que Claude las comente. Claude no lanza backtests: así no se afina al pasado y el
>   coste y la espera son previsibles. El chat de cambios también gana la corrección automática.
> - **API, solo añadidos** (el motor no cambia, el portal tampoco salvo un párrafo de su privacidad):
>   `POST /api/bots/draft/chat` {message, history, draft?, backtest?}, `POST /api/bots/backtest` {bot, years}
>   (con la cookie; comparte el tope de 30 por hora con la vista previa) y `PUT /api/bots/mine` {bot} (envía con
>   `engine.submit`, el nombre de pila de la sesión, tope de 10 al día). Las tres pasan el control de `Origin`.
>   `chat.create_prompt()` sigue los pasos del `AGENTS.md` del kit. `chat.Scripted` (la demo) también crea.
> - Coste estimado con Haiku 5.5: ~0,002 $ por mensaje (unos 3.000 tokens de entrada y otros tantos de salida),
>   ~0,06 $ por miembro y día como mucho.
> - **Privacidad del portal** (`market-hub-landing`): su párrafo de Bot League dice ahora que, al construir un
>   bot, van al modelo el borrador y las cifras del backtest. Hay que desplegar el portal para que se vea.
> - Probado: `make check` (58 tests: crear de punta a punta, la corrección en la misma petición, sesión y
>   `Origin`, cifras del backtest) y en local con la demo, de escritorio y a 375 px sin scroll lateral: ideas,
>   borrador, recarga (sigue ahí), backtest, cambio con antes → después, enviar, y "Build a new one" con bot.
>   Falta un mensaje real con Haiku (la demo usa `Scripted`).

> **Pendiente, el tope del chat.** Los 15 mensajes al día por jugador se cuentan en memoria, en cada
> instancia (`Chat._asked`). El servicio escala a cero y llega a 2 instancias, así que el contador se
> reinicia a menudo y el tope real es más flojo que el que pidió el usuario. Arreglarlo es guardar la
> cuenta por miembro y día (por ejemplo en `bot_meta/chat`, con un hash del id), y decirlo antes en
> la privacidad del portal. Se le ha contado al usuario; no está hecho.

> 2026-10-20: **"Change it", mucho más simple y bonito** (fusionado en main y **desplegado** como
> `bot-league-00008-vll`, export limpio de d075e3d, configuración igual antes y después). El
> usuario lo pidió: "simplificar mucho más y hacer más bonita la parte de modificar el bot".
> - **Lo fácil primero** (`site/src/lib/change.ts`): una caja para decirlo con su botón dentro y chips de un
>   toque (More defensive, Fewer stocks, More stocks, Look again monthly/weekly, Drop a sector, Pause o
>   Resume). La propuesta de Claude sale como **antes → después de las reglas en palabras** (cada regla que se
>   va tachada junto a la que entra; las que se quedan, plegadas), con el mapa de lo que tendría (vista previa)
>   y un botón: **Apply at the next close** (sin `confirm()`: se puede cancelar), "Fine-tune by hand" o "Not this".
> - **Los interruptores** a la derecha: un toggle Running/Paused y "Left out" en fichas (× para readmitir;
>   "+ Leave one out" ofrece en fichas lo que tiene, o un ticker). Cada interruptor deja un aviso con **Undo**
>   (el interruptor contrario).
> - **Estados**: arriba, lo que espera al próximo cierre (fecha, qué cambia en fichas, el antes → después si son
>   reglas) con **Cancel it**; el aviso de lo que acaba de pasar; el cambio del día ya usado (la caja lo dice y no
>   deja escribir); los mensajes que quedan ("13 of 15 messages left today") o que no quedan; el chat apagado; y
>   los errores en su sitio.
> - **Cada regla a mano** (`editor.ts`, reescrito; "Every rule, by hand ›"): grupos (dónde mira, qué guarda, cómo
>   ordena, cómo reparte, cuando cae el mercado, nombre e idea) con deslizadores que dicen su valor y selectores
>   segmentados (`controls.ts`); a la derecha, fijo, el antes → después en palabras **en vivo** (`words.ts` escribe
>   las reglas como `describe()` de `engine.py`: si cambia una frase allí, se cambia aquí) y el mapa, que se
>   pide a `/api/bots/preview` 1,2 s después de dejar de mover (si se llega al tope de 30 por hora, el mapa se
>   para y las palabras siguen). En el móvil, una barra fija abajo con cuántas reglas cambian y "Apply".
> - **API, solo añadidos** (el motor no cambia, ni el portal ni la app): `DELETE /api/bots/mine/pending` (en
>   `league.cancel_pending`) quita todo lo que espera al cierre; **unas reglas canceladas no cuentan como el cambio
>   del día** (nunca llegaron al bot), así que se puede pedir otro (decisión mía, se revierte en una línea).
>   `GET /api/bots/chat` y cada respuesta del chat dicen `left`. Con `make demo` (`BOTLEAGUE_SAMPLE=1` y el chat de
>   verdad apagado) el chat es **`chat.Scripted`**: contesta a unas pocas instrucciones por regla, sin red y sin gastar.
> - Probado: `make check` (tests nuevos de cancelar y del chat de la demo) y en local, de escritorio y a 375 px sin
>   scroll lateral, en sus estados (recién abierto, el chat proponiendo, cambio pendiente con el día usado, sin
>   mensajes, interruptores, cada regla a mano).

> 2026-10-20: Con el OK del usuario, **borrado `bot_meta/house`** de Firestore (los bots de la casa y su índice).
> En `bot_meta` queda solo `board` (y `chat` cuando el chat gaste algo).

> 2026-10-20: **Desplegado** `bot-league-00007-6c8` desde un export limpio de bca6636 (sin bots de la casa, jugador = nombre de
> pila, id público, renombrar), sin cambios de configuración. El bot de producción ya tiene id (`c398143b54`); pasa a
> "Alejandro" cuando su dueño abra su página.

> 2026-10-20: **Sin bots de la casa, renombrar el bot y el jugador es el login.** Pedido del usuario:
> "quitar los bots random de prueba", poder cambiar el nombre del bot, y que el usuario sea el del login;
> eligió mostrar **solo el nombre de pila** (como en los comentarios de opinión).
> - Fuera los seis bots de la casa: ya no se ejecutan ni se enseñan. `bot_meta/house` **queda en
>   Firestore** sin leerse ni escribirse (no lo borré: es del usuario decidirlo). El índice de las
>   páginas de bot sale ahora del `benchmark` de `bot_meta/board` (el último año). Los ejemplos siguen
>   en el kit.
> - El jugador ya no elige nombre: `handle` es el **nombre de pila de la cuenta** (`engine.first_name`),
>   de la sesión en la web (`sync_player` en `GET /api/bots`) o, para el agente, el que se guardó con su
>   clave al hacerla con sesión (`issue_key(user_id, name)`); nunca de la petición. Fuera las reglas de
>   nombres únicos y las lecturas de `shared_portfolios`/`competition_entries` (`FirestoreMembers`).
> - Cada bot tiene un **id público aleatorio** (`public_id`, 10 hex), estable para el miembro, que es su
>   dirección (`/bot/?b=<id>`) y la semilla de su robot. Los bots de antes lo reciben en el siguiente
>   refresh (`ensure_ids`); el de "alejandros portfolio" pasa a "Alejandro" cuando su dueño abra su
>   página.
> - **Renombrar**: `PUT /api/bots/mine/name` (`Bots.rename`) cambia el nombre y la idea al momento,
>   conserva el historial, no cuenta como el cambio del día y deja en el registro público "renamed from
>   <nombre anterior>". En "Your bot", un botón "Rename" junto al nombre.
> - Mismo parche en el `bots.py` del portal, sus tests, su privacidad y su `CLAUDE.md`. Sin desplegar.

> 2026-10-20: **"Your bot" (`/me/`), más simple y dibujada** (**desplegada** como `bot-league-00006-nr7`, export limpio de 664f4ac, configuración igual). El usuario
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
