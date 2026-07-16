# VCF Automation 9 — getting a tenant token (and the /iaas 3-state)

The single most common surprise when moving vRA 8 IaaS automation to VCF
Automation 9: **the old `POST /csp/gateway/am/api/login` is gone (404), and a
`provider` token returns `500` on `/iaas/api/*`.** You need a *tenant-scoped*
token, and even that isn't enough for `/iaas`. Everything below is live-verified
against home.lab (2026-07-06); reproduce with
`samples/vcf_automation/02_tenant_token_two_paths.py`.

## Two ways to get a tenant token (both are API — no browser needed at call time)

### Path A — VCD session login (just needs the org user's password)
```
POST /cloudapi/1.0.0/sessions
Host: <vcfa-fqdn>
Accept: application/json;version=9.1.0
Authorization: Basic base64("<user>@<org>:<password>")
```
The tenant access token comes back in the **`X-VMWARE-VCLOUD-ACCESS-TOKEN`**
response header (a ~1.3 KB JWT, short-lived; re-login when it expires).
Verified against a freshly-created tenant org: `200`, 1337-char token.

### Path B — persistent API (refresh) token
The refresh token itself must be **minted once in the VCFA UI** (My Account →
API Tokens, *while switched into the tenant org*). `POST /cloudapi/1.0.0/tokens`
is system-gated in this build — it returns `403`/`400` for tenant *and*
provider callers, independent of role rights, so the API cannot mint it.
Once you have the refresh token, exchanging it is pure API:
```
POST /oauth/tenant/<org>/token
Content-Type: application/x-www-form-urlencoded
grant_type=refresh_token&refresh_token=<the-UI-minted-token>
```
→ `{"access_token": "..."}`. Note the token must be minted **inside a tenant
org**; a provider-scoped token (from `/oauth/provider/token`) will 500 on
`/iaas` just like a provider session.

## The `/iaas/api/*` 3-state (same request, token scope decides)

| Token | `/iaas/api/*` | `/deployment` · `/catalog` · `/blueprint` |
|---|---|---|
| provider (admin@system) | **500** — gateway can't route to IaaS | 500 |
| tenant, no Cloud Assembly rights | **403** — reaches IaaS, permission denied | **200** |
| tenant + Cloud Assembly rights + org onboarded to Automation | **200** | **200** |

So a script that used to hit `/iaas` on vRA 8 needs, on VCFA 9:
1. a **tenant** token (Path A or B), **not** provider;
2. the tenant user's role to include **Cloud Assembly / IaaS rights**;
3. the org to be **onboarded to Automation** (region / cloud account assigned) —
   otherwise even a correct tenant token returns `403` (rights) or an empty
   `200` (no resources).

The VCFA-native surfaces (`/deployment`, `/catalog`, `/blueprint`) answer `200`
with any tenant token, so migrate those first.

## Old → new auth, at a glance

| Old (vRA 8) | New (VCF Automation 9) |
|---|---|
| `POST /csp/gateway/am/api/login {username,password}` → `cspAuthToken` | `POST /cloudapi/1.0.0/sessions` (Basic `user@org:pw`) → `X-VMWARE-VCLOUD-ACCESS-TOKEN`, **or** `POST /oauth/tenant/<org>/token` (UI-minted refresh token) |
| single flat token | provider vs **tenant** scope matters; `/iaas` needs tenant + rights |
| `/identity/api/*` | removed → VCF Identity Broker (OIDC) |
