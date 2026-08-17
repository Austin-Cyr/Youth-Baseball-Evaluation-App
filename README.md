# Youth Baseball Player Evaluation App

A mobile-friendly web app for evaluating youth baseball players' skills for use in the season wide draft.

## 1. Why this exists?

Before the start of the season, players are rated on a scale between 1-5 in a number of baseball skill areas. Previously, the league rated the players on paper
and the scores were later transcribed to an excel file to be used in the draft. This method required a person to transcribe the ratings, leading to data input
errors, delays in when the draft could occur and lack of history for the players. The paper method also required additional supplies, including paper, pencils
and clipboards. By transferring the data collection from a paper method, removed the need for supplies, allowed users to use their own mobile phones and doesn't
require supplies to be returned to the league, minimizing the risk of data loss. 

## 2. What it does?

Provides an enhanced skill rating intake method that is durable, flexible and enjoyable to the users. 

## 3. Architecture



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
