# Instrucciones para agentes

Lee primero [docs/HANDOFF.md](docs/HANDOFF.md): estado, pendientes y siguientes pasos.

**Bot League** es la competición de bots de Market Hub como producto propio, con su web: un
miembro descarga un kit, construye con su agente (Claude Code, Codex…) un bot de reglas, lo prueba
y lo envía con su clave, y aquí se ejecuta en papel y se clasifica. Los datos son los del portal:
las colecciones `bots`, `bot_keys` y `bot_meta` del Firestore `market-hub`, que también lee la
sección Community de `market-hub-landing`.

Reglas que no se negocian:
- **Nada de trading.** No se escribe código que envíe órdenes ni que se conecte a un broker, y no
  se usa ningún conector de broker, ni siquiera para descargar precios. Los bots corren en papel.
- **Describir, no recomendar.** La web ordena bots por lo que han hecho, nada más. Nada de
  "compra", "vende", predicciones ni alertas. Un backtest es para su dueño y se dice que es una
  simulación del pasado. Los bots de la casa son referencias, nunca se clasifican.
- **El motor es el del portal.** `src/botleague/engine.py` es copia de
  `market-hub-landing/src/markethub/bots.py` con solo los imports cambiados: mismo formato
  (`markethub-bot/1`), mismas comprobaciones, mismo motor, mismos documentos y mismo hash de la
  clave. Un cambio en uno se hace en los dos (y `tests/test_engine.py` es copia de sus tests).
  `tests/test_shared.py` comprueba con documentos escritos por el código del portal
  (`scripts/portal_docs.py`) que aquí se leen, se avanzan y se escriben igual. `names.py` copia las
  reglas de nombres del portal (`community.py`, `opinion.publishable`).
- **Un solo escritor de las curvas.** Hasta que el usuario decida (ver HANDOFF), portal y Bot
  League pueden avanzar los bots; los dos comparten el candado y el ritmo de `bot_meta/board`. Lo
  propio de esta web va en `league.py` y en su documento `bot_meta/house` (bots de la casa y el
  índice), que no es de ningún usuario.
- **Los datos del usuario son suyos.** Aquí no se guarda nada nuevo de un usuario: solo lo que ya
  dice la página de privacidad del portal (su bot, su clave hasheada). Los bots de los miembros los
  ven los miembros con sesión; `BOTLEAGUE_PUBLIC_BOARD=1` los enseña a todos y no se activa sin
  que el usuario lo pida y sin cambiar antes la página de privacidad del portal. Las reglas de un
  bot solo las ve su dueño. Borrar la cuenta (en el portal) borra el bot y la clave.
- **El login es el de Market Hub.** Se lee la cookie `mh_session` del portal con su secreto
  (`HUB_SESSION_SECRET`); nunca se pone ni se cambia. Las rutas del agente (`/api/bot/*`) solo leen
  la clave, nunca la cookie. Las escrituras con cookie pasan el control de `Origin`.
- **Claves solo en `.env` o en el entorno.** Nunca en el repo, en logs ni en commits.
- **Nada programado y nada en GitHub Actions.** Todo se lanza a mano desde el `Makefile`. Los bots
  se avanzan cuando una visita los encuentra atrasados.
- **No gasta en ninguna API.** Cierres de Yahoo Finance y lista de empresas de la SEC, sin clave.

Convenciones:
- Hablar con el usuario en español. Código, comentarios y textos de la web en inglés.
- Python 3.12 con `uv`. Tests con `make test`; web con `make check`; todo en local con `make demo`.
- `site/src/styles/global.css` es el del portal con lo propio de Bot League al final; la marca es
  la de Market Hub con un color propio (violeta "signal") para lo tuyo y la entrada.
- La web no explica cómo se calcula cada cifra; eso va aquí y en `docs/HANDOFF.md`.
- Al terminar una tarea relevante, actualizar "Dónde estamos" en `docs/HANDOFF.md`.
