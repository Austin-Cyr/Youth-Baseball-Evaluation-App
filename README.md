# Player Evaluation App

A mobile-friendly web app for evaluating players. Each division/sport combination
gets its own link (e.g. `/evaluate/12U/Baseball`). No login required.

## 1. Run the database migration

Before starting the app, run `migration.sql` once against your existing Postgres
database. It:
- Makes `id_player_reg` nullable on `eval_results` and adds an `evaluator_ip` column
- Turns `id_eval` into an auto-incrementing identity column (safe only because
  `eval_results` is currently empty)
- Creates a new `eval_results_manual_players` table for players an evaluator
  types in manually (not on the roster)

```bash
psql "$DATABASE_URL" -f migration.sql
```

## 2. Configure the database connection

```bash
cp .env.example .env
# then edit .env and set DATABASE_URL to your real Postgres connection string
```

## 3. Install dependencies and run

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

For production use, run behind a real ASGI server setup (e.g. uvicorn workers
behind Nginx, or deploy to a host like Render/Railway/Fly.io/an internal server).
If you deploy behind a reverse proxy or load balancer, the app already reads the
`X-Forwarded-For` header to capture the evaluator's real IP address.

## 4. Share links with evaluators

For each division/sport combination you want evaluators to use, share a link like:

```
https://yourdomain.com/evaluate/12U/Baseball
```

The division and sport values must match exactly (case-sensitive) what's stored
in your `DIVISIONS` and `sport` lookup tables and in the `REGISTRATIONS` table's
`DIVISION`/`SPORT` columns. If a division/sport combination doesn't exist in the
lookup tables, the app returns a 404.

Evaluators tapping that link will:
1. Pick the skill they're evaluating (from `eval_skill`)
2. See a list of players in that division/sport who haven't been evaluated yet
   for that specific skill
3. Tap a player, then tap a score (the score range comes from that skill's
   `min_score`/`max_score` in `eval_skill`)
4. Optionally tap "+ Add a player not on the list" to manually type in a
   first/last name and score a player who isn't on the roster yet

Every submission also silently records the evaluator's IP address and the
current date — no login or manual entry needed from the evaluator.

## Notes / things to double check

- **IP capture**: `request.client.host` is used directly unless an
  `X-Forwarded-For` header is present (typical when running behind a reverse
  proxy). If you deploy on a platform that uses a different header, let me
  know and I can adjust.
- **Manually-added players**: these go into `eval_results_manual_players`, a
  separate table from `eval_results`. They are not deduplicated against future
  submissions (e.g. someone could accidentally add "John Smith" twice for the
  same skill) — that table is meant as a raw capture log rather than a managed
  roster. If you want dedup logic later, that's straightforward to add.
- **Division/sport matching is case-sensitive** and must be an exact string
  match against `REGISTRATIONS."DIVISION"` / `REGISTRATIONS."SPORT"`.
