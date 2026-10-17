# POST /analytics — authenticated event-batch aggregation

Stateless analytics endpoint. Every request is authenticated with the assigned
API key and answered from the batch in that request alone: nothing is stored
between calls, so a fresh randomized batch always produces fresh numbers.

## Deployed endpoint URL

**https://handling-dimension-wars-lady.trycloudflare.com/analytics**

> The URL is served by a Cloudflare quick tunnel in front of the FastAPI app
> running on this machine (`.\up.ps1` starts both and rewrites `.tunnel-url`;
> a restart of the tunnel issues a *new* URL — re-read `.tunnel-url`).

The same code is also pushed to `main` of this repository, where it is ready to
deploy on Vercel (project `vercel-latency-api` is already linked via
`.vercel/project.json`; `vercel deploy --token <token>` or a connected Git
integration will publish it at `https://vercel-latency-api.vercel.app/analytics`).

## Auth

`X-API-Key: ak_h609yeskd3fjyeyppukt11vx`

| Case                     | Result                |
| ------------------------ | --------------------- |
| Header missing           | `401 {"detail": ...}` |
| Key does not match       | `401 {"detail": ...}` |
| Key matches              | `200` + aggregates    |

`OPTIONS` preflights are answered by the CORS middleware (no key required, as
the browser cannot attach one before asking permission).

## Request / response

```json
POST /analytics
X-API-Key: ak_h609yeskd3fjyeyppukt11vx
Content-Type: application/json

{"events": [{"user": "alice", "amount": 42.5, "ts": 1700000000}, "..."]}
```

```json
{
  "email": "24f2005949@ds.study.iitm.ac.in",
  "total_events": 16,
  "unique_users": 4,
  "revenue": 2036.14,
  "top_user": "bob"
}
```

### Aggregation rules

- **total_events** — length of `events`.
- **unique_users** — distinct `user` values.
- **revenue** — sum of `amount` where `amount > 0` (zero and negative ignored).
- **top_user** — user with the highest positive-amount total (grader guarantees
  no ties; falls back to the first user seen only for an all-non-positive batch).
- **email** — the account's logged-in email address.

CORS is wide open (`Access-Control-Allow-Origin: *`, all methods and headers),
so the exam page can `fetch()` this endpoint cross-origin — including the
`X-API-Key` header, which forces a preflight.

## Layout

```
api/index.py          FastAPI app: /analytics + the original latency routes
vercel.json           Vercel build/route config for the same app
up.ps1                start uvicorn + cloudflared quick tunnel, write .tunnel-url
test_analytics_local.py  grader-style checks against any base URL
../analytics-page-test/  browser page that re-verifies all checks cross-origin
```

## Verify

```powershell
.\up.ps1                                                   # (re)start service + tunnel
python test_analytics_local.py                             # local
python test_analytics_local.py https://<tunnel-host>       # deployed URL
```

```powershell
curl -X POST https://handling-dimension-wars-lady.trycloudflare.com/analytics `
     -H "Content-Type: application/json" `
     -d '{\"events\": [{\"user\":\"alice\",\"amount\":42.5,\"ts\":1700000000}]}'
# 401 - key missing
curl -X POST https://handling-dimension-wars-lady.trycloudflare.com/analytics `
     -H "Content-Type: application/json" -H "X-API-Key: ak_h609yeskd3fjyeyppukt11vx" `
     -d '{\"events\": [{\"user\":\"alice\",\"amount\":42.5,\"ts\":1700000000},{\"user\":\"bob\",\"amount\":-5,\"ts\":1700000001}]}'
# 200 - {"email":"24f2005949@ds.study.iitm.ac.in","total_events":2,"unique_users":2,"revenue":42.5,"top_user":"alice"}
```
