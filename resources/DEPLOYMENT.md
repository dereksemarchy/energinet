# ENERGINET deployment runbook

| Item | Value |
|---|---|
| Tenant | `https://valcon.eu.semarchy.net` (no trailing slash) |
| Data location | `ENERGINET`, type DEV, created by the first deploy on 2026-10-15 |
| Datasource | `datasource0`. It was free before the first deploy (no data location used it, and it had no alias warning) |
| Data product | `src/ENERGINET`, SEML 2.1, no `Vector` attribute, so `--enable-ai-preview` is not needed |

## 1. Build

```bash
python output/generate-ENERGINET.py
sem-design data-product build --data-product-folder "src/ENERGINET"
python ai-model-development/scripts/audit-model.py src/ENERGINET
```

## 2. Deploy

The 2.x deploy command does not accept an API key: the legacy `dm data-location deploy --api-key`
answered **401** on this tenant. Use the browser session instead.

```bash
sem-design auth login --url https://valcon.eu.semarchy.net     # approve the device link in the browser
sem profiles                                                   # the default profile must name this tenant
sem-design data-product deploy --data-product-folder "src/ENERGINET" \
  --instance-url https://valcon.eu.semarchy.net --data-source datasource0 --data-location ENERGINET
sem dm data-locations get ENERGINET                            # status DL_READY, deploymentDate advanced
```

- No `--overwrite-deployment-url`: the tenant's `/.well-known/sem-api` publishes `apis.deploy.v1.baseUrl`.
- After a `504` or `502`, poll the status for `DL_READY` before retrying. Never deploy while an
  integration batch or an un-submitted load is running.

## 3. Roles (once per tenant)

```bash
for r in GridDataOwner GridDataSteward GridIntegration GridDataConsumer; do
  sem dm admin roles set $r -i resources/platform-administration/roles/$r.json --url https://valcon.eu.semarchy.net --api-key <key>
done
```

Done on 2026-10-15. `semarchyAdmin` is built in.

Still to do platform-side: map users or identity-provider groups to these roles (role mapping), and
create a dedicated integration API key on `GridIntegration` for production feeds.

## 4. Demo data

```bash
python resources/data/load_datasets.py --url https://valcon.eu.semarchy.net --data-location ENERGINET --api-key <key> --dry-run
python resources/data/load_datasets.py --url https://valcon.eu.semarchy.net --data-location ENERGINET --api-key <key>
```

Expected counts are in `resources/data/README.md`. Check them with
`GET /dm/api/rest/count/ENERGINET/<Entity>/GD` (golden records) and `.../SAWE` or `.../SDWE` (records in error).

## 5. Dashboard application `ENERGINETAnalytics`

Source: `output/dashboards/ENERGINETAnalytics.spec.yaml` → built into `resources/dashboards/ENERGINETAnalytics/` + `.zip`.

```bash
python .claude/skills/seml-dashboard/scripts/build_dashboard.py output/dashboards/ENERGINETAnalytics.spec.yaml \
  --out resources/dashboards --catalog output/dashboards/ENERGINET-catalog.json
sem dm dashboards applications import ENERGINETAnalytics -i resources/dashboards/ENERGINETAnalytics.zip
```

Import it BEFORE deploying a data product that links to it.

- 2026-10-16: imported as a NEW application (the tenant had none), then the data product was redeployed
  (upgrade, data kept, `DL_READY`, deploymentDate 2026-10-16T14:06Z). That deploy carries two Quick access tiles
  (*Data product quality*, *Grid context*) and a *Scorecard* tab on the Substation form (FormDashboard
  `SubstationScorecard`/`Scorecard`, parameter `SubstationCode`).
- Still to verify on render: the Issues report (`/dm/dashboard-builder/ENERGINETAnalytics/issues`), the two UNVERIFIED
  queries (`SourceContribution` → `md_*.b_pubid`, `MatchBacklog` → `du_asset`, settled by the *Schema check* tab), and
  that the Substation scorecard shows only that substation.
