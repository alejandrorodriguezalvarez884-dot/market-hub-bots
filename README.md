# Bot League

Market Hub's bot competition, on its own site. A member builds a bot of rules by talking to Claude on
their page ("Your bot"), sees what it would hold, backtests it and sends it in. Bot League runs every bot on paper, from the close after it was sent in, and ranks them over the day,
the week, the month, the year and since each started, against the S&P 500.

No money, no broker, no orders. Sign-in is the Market Hub account; the data is Market Hub's own
(Firestore database `market-hub`, collections `bots`, `bot_keys` and `bot_meta`), shared with the
portal's Community section.

- `src/botleague/`: the API (FastAPI). `engine.py` is the portal's engine, `league.py` this site's own.
- `src/botleague/kit/`: the kit for a member's own agent. Since 2026-11-04 the site no longer offers
  it; the API behind it (`/api/bots/kit`, `/api/bots/key`, `/api/bot/*`) is still there.
- `site/`: the website (Astro).

```bash
make install
make demo      # the whole site on made-up figures at http://localhost:8080
make test
```

See `CLAUDE.md` and `docs/HANDOFF.md`.
