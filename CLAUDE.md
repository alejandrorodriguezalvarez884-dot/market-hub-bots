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
- **Un solo escritor de las curvas: Bot League** (decisión del usuario, 2026-10-20). Aquí se
  avanzan los bots (refresh), se hacen el kit y las claves y se contesta al agente (`/api/bot/*`).
  El portal lee los mismos documentos, pide el refresh a `/api/board/refresh` cuando los encuentra
  atrasados, deja retirar un bot o una clave y los borra con la cuenta; sus `/api/bot/*` contestan
  410 con esta dirección. Lo propio de esta web va en `league.py` y en su documento
  `bot_meta/house` (bots de la casa y el índice), que no es de ningún usuario.
- **Los datos del usuario son suyos.** Aquí no se guarda nada nuevo de un usuario: solo lo que ya
  dice la página de privacidad del portal (su bot, su clave hasheada). **El tablero es público**
  (decisión del usuario, 2026-10-20, y así lo dice la privacidad del portal): cualquiera ve el
  nombre, el bot, su idea, sus rentabilidades, su curva y lo que tiene. `BOTLEAGUE_PUBLIC_BOARD=0`
  lo cierra a los miembros con sesión. Las reglas de un bot solo las ve su dueño. Borrar la cuenta (en el portal) borra el bot y la clave.
- **El login es el de Market Hub.** Se lee la cookie `mh_session` del portal con su secreto
  (`HUB_SESSION_SECRET`); nunca se pone ni se cambia. Las rutas del agente (`/api/bot/*`) solo leen
  la clave, nunca la cookie. Las escrituras con cookie pasan el control de `Origin`.
- **Claves solo en `.env` o en el entorno.** Nunca en el repo, en logs ni en commits.
- **Nada programado y nada en GitHub Actions.** Todo se lanza a mano desde el `Makefile`. Los bots
  se avanzan cuando una visita los encuentra atrasados.
- **No gasta en ninguna API, salvo el chat.** Cierres de Yahoo Finance y lista de empresas de la SEC,
  sin clave. El chat del dueño (`chat.py`) gasta con la clave de Anthropic del usuario (secreto
  `ANTHROPIC_API_KEY`). Modelo y topes son decisión suya (2026-10-20): Claude Haiku 5.5 con esfuerzo
  alto, 15 mensajes al día por jugador y **sin tope diario del servicio**, por decisión del usuario
  (como PlayGround). No se cambian sin preguntarle.
- **Cambiar un bot conserva su historial**: desde el próximo cierre, una vez al día, y su página dice
  en público cuándo cambió (no qué). Interruptores sí (pausar, excluir), órdenes no.

Convenciones:
- Hablar con el usuario en español. Código, comentarios y textos de la web en inglés.
- Python 3.12 con `uv`. Tests con `make test`; web con `make check`; todo en local con `make demo`.
- **El aspecto es el de The Market Hub** (lo pidió el usuario): `site/src/styles/global.css` es el
  del portal con lo propio de Bot League al final, sin color de marca (lo "signal" se dibuja en la
  tinta), con la cabecera y el pie del portal y "by The Market Hub" enlazando a la web.
- La web no explica cómo se calcula cada cifra; eso va aquí y en `docs/HANDOFF.md`.
- Al terminar una tarea relevante, actualizar "Dónde estamos" en `docs/HANDOFF.md`.
