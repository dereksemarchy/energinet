# Demo script — Creating and publishing a new data product (Grid Asset Data Product)

> **Use case** (`input/Demo use-cases.txt`): show how a data owner or data steward creates, governs, publishes and
> maintains a new data product based on existing operational data (SCADA / PMU measurements, substation and sensor
> data, asset information, context from an authoritative network model), for consumers such as control-centre
> applications, operational planning, analytics and Asset Management. For every capability, say whether it is
> **standard**, **configuration / custom development**, **third-party** or **roadmap**.
>
> **Data product**: `src/ENERGINET` (SEML 2.1), deployed on `https://valcon.eu.semarchy.net`, data location `ENERGINET`.
> **Dataset**: fictional, deterministic (`resources/data/`). Every number quoted below comes from `resources/data/README.md`.

**Duration**: 45 min of demo + 15 min Q&A. Acts can be dropped from the end if time runs short, except the
capability recap (Act 7), which the client explicitly asked for.

**Capability tags used throughout** — say the tag out loud when you show the feature:

| Tag | Meaning |
|---|---|
| 🟢 **STD** | Standard product functionality, used as shipped |
| 🔵 **CFG** | Standard product, configured for this data product (no code) |
| 🟠 **CUSTOM** | Custom development (scripts, upstream transformation) |
| 🟣 **3RD** | Depends on a third-party product |
| ⚪ **ROADMAP** | Not available in the current version |

---

## 0. Before the demo (T-1 day, then T-30 min)

| # | Check | How | ✓ |
|---|---|---|---|
| 1 | Data location is up | `sem dm data-locations get ENERGINET` → `DL_READY` | |
| 2 | Data is loaded and the counts match | `GET /dm/api/rest/count/ENERGINET/<Entity>/GD`: Substation **10**, Asset **87**, TransmissionLine **14**, MeasurementPoint **81**, Measurement **7 776** | |
| 3 | Demo users exist and are mapped | One user on `GridDataSteward`, one on `GridDataOwner`, one on `GridDataConsumer` (role mapping is **still to do** per `resources/DEPLOYMENT.md` §3). Two browser profiles: *Steward* and *Owner* | |
| 4 | Dashboards render | Open *Data product quality* and *Grid context* tiles; open a Substation → *Scorecard* tab shows only that substation. Check the *Schema check* tab: the two queries `SourceContribution` and `MatchBacklog` are still **unverified** | |
| 5 | The approval workflow has never been run on the asset you will use | Pick a fresh Asset (e.g. *CB Q112 Havrevang 132kV*) | |
| 6 | VS Code open on the workspace, `src/ENERGINET` builds green | `sem-design data-product build --data-product-folder "src/ENERGINET"` | |
| 7 | Terminal with an API token ready for the REST call (Act 5) | `sem auth token` (browser session) — **never show a key on screen** | |
| 8 | Fallback | Screenshots of each act in a folder, in case the tenant is slow. A deploy can answer `504` while it actually succeeds — never deploy live without a fallback | |

Tabs to have open, in order: (1) VS Code, (2) Data app — Steward, (3) Data app — Owner, (4) Terminal, (5) Dashboard.

---

## Act 1 — The business problem (3 min)

**Say**
> "A TSO has the data it needs already — a network model in the EMS modelling tool, an asset register in the EAM,
> a SCADA and PMU point list, and a historian with the measurements. What it does not have is **one trusted,
> governed product** that says *which* transformer this is, *where* it sits in the grid, *which* signals measure it
> and *how good* its data is — something a control-centre app, a planner, an analyst or an AI agent can consume
> without re-doing the reconciliation each time. That is the data product we will build, govern, publish and
> maintain in the next 40 minutes."

**Show** the data product diagram: data app → *Administration* → *Data product documentation*.
Five entities: Substation, Asset, Transmission line, Measurement point, Measurement.

**Key message — the MDM / time-series boundary** 🟣 **3RD**
> "We master the **context** and keep **15-minute aggregates** for analytics and the demo. Raw SCADA / PMU streams —
> seconds to sub-second — stay in the historian or the streaming platform, e.g. AVEVA PI or Kafka. Semarchy is the
> reference that tells those streams *what* they are measuring."

---

## Act 2 — Create the data product (8 min) — *Data owner, with the design team*

### 2.1 From the need to a specification 🔵 **CFG** (AI-assisted design)
**Show** `output/Specification-ENERGINET.md` briefly: source register (§1), roles (§2), quality rules (§4),
decision log (§10.3).

**Say**
> "We started from the one-paragraph use case. An AI design assistant produced the specification in Semarchy
> vocabulary, and **every** hypothesis it made — entity types, survivorship, matching thresholds — had to be
> validated by a person before anything was generated. That is the decision log."

### 2.2 The data product as code 🟢 **STD**
**Show** in VS Code:
- `src/ENERGINET/entities/Asset/Asset.Entity.seml` — the entity, its business descriptions.
- `src/ENERGINET/entities/Asset/` folder — enrichers, validations, survivorship rules, form, business view.
- `src/ENERGINET/list_of_values/VoltageLevel.LOVType.seml` — reference data (400 / 220 / 150 / 132 / 60 kV).

**Say**
> "A data product is a set of readable, versionable files: it goes into Git, gets reviewed in a pull request, and
> builds in CI like any other software."

### 2.3 Three entity types for three kinds of data 🟢 **STD**
| Entity | Type | Why — say this |
|---|---|---|
| Substation | ID-matched | Both sources share the substation code: consolidate on the key |
| Asset | Fuzzy-matched | Network model and EAM share **no key** on equipment: we need matching |
| Line, Measurement point, Measurement | Basic | One authoritative source each: no consolidation needed |

### 2.4 Build 🟢 **STD**
**Do** in the terminal:
```bash
sem-design data-product build --data-product-folder "src/ENERGINET"
```
**Expect** `Build successful`.
> "The build checks the whole product — every reference, every rule expression — before anything reaches the platform."

**Deploy**: do **not** run it live here (it takes minutes). Say it was deployed the same way with
`sem-design data-product deploy`, and come back to it in Act 6.

---

## Act 3 — Load the existing operational data (5 min) — *Integration*

**Show** `resources/data/` — one CSV per source system and entity:

| File | Source system | Publisher |
|---|---|---|
| `01/02_Substation_*` | Network model, Asset register | `NETMODEL`, `EAM` |
| `03_TransmissionLine_NETMODEL` | Network model | `NETMODEL` |
| `04/05_Asset_*` | Network model, Asset register | `NETMODEL`, `EAM` |
| `06_MeasurementPoint_SCADA` | SCADA / PMU point list | `SCADA` |
| `07_Measurement_HISTORIAN` | Historian, 15-min aggregates of 2026-10-14 | `HISTORIAN` |

**Say**
> "Each source system pushes its own data through the **REST loads API** under a technical integration role. The
> platform keeps every source record, then consolidates them into golden records."

**Do** (optional, only if rehearsed — otherwise just show the command):
```bash
python resources/data/load_datasets.py --url https://valcon.eu.semarchy.net --data-location ENERGINET --api-key <key> --dry-run
```

| Capability | Tag |
|---|---|
| REST loads API, integration role, batch per dependency level | 🟢 **STD** / 🔵 **CFG** |
| The CSV extraction from the EMS / EAM / SCADA / historian | 🟠 **CUSTOM** or 🟣 **3RD** ETL (or Semarchy Data Integration) |
| Reading CIM / CGMES (XML/RDF) natively | 🟠 **CUSTOM** / 🟣 **3RD** — an extract step upstream of the loads API |

---

## Act 4 — Govern the data (12 min) — *Data steward*

Switch to the **Steward** browser profile.

### 4.1 Consolidation of an ID-matched entity 🔵 **CFG**
**Do** *Grid* → *Substations* → open **Østerby** (`SUB-OST`).
**Point out**
- Name **Østerby** comes from the network model (the EAM spelled it *Osterby*); location comes from the network
  model too (the EAM has none).
- Commissioning date **1985-10-20** and the description come from the asset register.
- Lineage / history tabs: the two contributing source records.

> "20 source records became **10 golden substations**. Each attribute comes from the source that is authoritative
> for it — topology from the network model, lifecycle from the asset register. That is a survivorship rule, configured, not coded."

**Navigate** the tabs: *Assets*, *Measurement points*, *Outgoing lines*, *Incoming lines*, and the *Scorecard*
dashboard tab.
> "This is the context a control-centre engineer needs: everything that is at this substation, connected to it, and measured in it."

### 4.2 Automatic match & merge 🔵 **CFG**
**Do** *Grid* → *Assets* → search **Nordvig** → open **T1 400/150 kV transformer Nordvig**.
**Point out**
- Two sources: network model (`TR970981`, *Ampera SpA*) and EAM (`tr970981`, *AMPERA SPA*). Same serial and
  manufacturer, different case → **merged automatically** (rule *serial + manufacturer*, score 100).
- Name and network-model id from `NETMODEL`; EAM number, model `AMP-300`, commissioning **1999-02-12**,
  criticality **HIGH**, last inspection from `EAM`.
- *Age (years)* — computed after consolidation by an enricher.

> "98 asset source records, 1 rejected, **87 golden assets**: the 10 transformers known to both systems are now one record each."

### 4.3 Suggested matches — the human in the loop 🔵 **CFG**
**Do** *Data stewardship* → *Matching review* → *Assets — suggestions*.
**Show** the pair **CB Q11 Østerby 400kV** (network model) vs **CB-Q11 OSTERBY 400 KV** (EAM).
> "Same substation, same type, names 85 % similar after normalization — score 80, under the merge threshold of 90.
> The platform does **not** guess: it proposes, the steward decides. 28 pairs like this one."

**Do** confirm the merge for this one pair, and show the merged golden record.

### 4.4 Data quality — blocking rules and worklists 🔵 **CFG**
**Do** *Data stewardship* → *Records in error*:

| Worklist | Record | Rule |
|---|---|---|
| Transmission lines in error | `LN-150-LYN-LYN` | From substation = To substation |
| Assets in error | `EAM-NOID-1` | No mRID and no EAM asset number |
| Measurement points in error | `KRA.T1.AMB.TEMP` | Alarm low limit > high limit |
| Measurements in error | the last historian row | Min > Average |

> "Blocking rules keep bad records **out** of the published product. They stay visible here, with the reason, until a steward fixes the source."

**Do** *Data stewardship* → *Worklists* (warnings — published, but flagged):

| Worklist | Record |
|---|---|
| Location outside Denmark | `SUB-HAV` (latitude / longitude swapped in the network model) |
| In service, commissioned in the future | Shunt reactor R1 at Fjordby (2027) |
| Asset in another substation | `BAK.T1.TAP.TEMP` |

**Do** fix `SUB-HAV` in the form (swap the coordinates back), save, and show it leave the worklist.

### 4.5 Governance workflow — steward prepares, owner approves 🔵 **CFG**
**Do** (Steward) *Assets* → select **CB Q112 Havrevang 132kV** → **Submit asset for approval**.
- Task *Prepare the asset change*: set *Criticality* = HIGH, *Last inspection date* = today → **Submit to data owner**.

**Switch to the Owner profile** → *Quick access* → *My tasks* → *Approve the asset change*.
- First pass: **Reject — back to the data steward** (add a comment) → show the task back in the steward's inbox.
- Second pass: **Approve and publish** → the asset is certified and published.

> "Nothing reaches consumers without the owner's approval. Notifications by email need a notification server — that is platform configuration, not in this demo."

### 4.6 Who can do what 🔵 **CFG**
**Show** `src/ENERGINET/data_product_priv_grants/` — owner, steward, integration, consumer. The consumer is read-only;
the steward cannot write measurements.

---

## Act 5 — Publish and consume (8 min) — *Data consumers*

### 5.1 Business users — the data app 🟢 **STD**
**Switch to the Consumer profile**: same views, no edit buttons. Global search **"Kragholm"** → substation, its assets,
its points. Export a collection to Excel.

### 5.2 Analytics — dashboards 🔵 **CFG**
**Do** *Quick access* → **Data product quality**: tabs *Overview*, *Match and merge*, *Sources*, *Rejections and
warnings*. Then **Grid context**: assets by type, criticality, grid area, voltage level, age band; measurements tab —
*Non-good aggregates by hour (2026-10-14)*.
> "The data owner's quality cockpit and the asset manager's portfolio view come from the same governed golden records."

### 5.3 Applications — REST API 🟢 **STD**
**Do** in the terminal:
```bash
TOKEN=$(sem auth token)
curl -s -H "Authorization: Bearer $TOKEN" \
  https://valcon.eu.semarchy.net/dm/api/rest/count/ENERGINET/Asset/GD
```
> "Operational planning or a control-centre application reads the golden records — or the asset context of a SCADA tag — through the REST API, with the consumer role."

### 5.4 AI agents — MCP 🔵 **CFG**
**Show** an AI assistant connected to the data product's MCP server and ask:
*"Which high-criticality assets at Nordvig have a measurement point with suspect or missing aggregates on 2026-10-14?"*
> "Every entity, attribute and rule carries a business description — that is the semantic layer the agent reasons on.
> It answers from golden records, with units taken from the measurement point."

> ⚠ Rehearse this one: the MCP connection for this data location must be set up and tested before the demo. If not
> available, show the description layer in `Asset.Entity.seml` and describe the pattern instead.

---

## Act 6 — Maintain and evolve the data product (5 min)

### 6.1 History 🟢 **STD**
**Do** reopen `SUB-HAV` → history: the coordinate fix from Act 4.4, who made it and when.

### 6.2 Change the product 🟢 **STD** / 🔵 **CFG**
**Do** in VS Code: add a voltage level to `list_of_values/VoltageLevel.LOVType.seml` (e.g. `33` — "33 kV"), then build.

> "A new version of the product is a change to the files, a review, a build, a deploy. The deploy **upgrades** the data
> location in place: golden records, history and stewardship decisions are kept."

**Deploy** — only if rehearsed and the tenant is fast; otherwise show the runbook command and the last deployment
date in `sem dm data-locations get ENERGINET`:
```bash
sem-design data-product deploy --data-product-folder "src/ENERGINET" \
  --instance-url https://valcon.eu.semarchy.net --data-source datasource0 --data-location ENERGINET
```
> If it answers `504 Gateway Timeout`: do not retry — poll `sem dm data-locations get ENERGINET` until `DL_READY`.
> The deploy is asynchronous and usually succeeded.

**After the demo**: revert the LOV change (or fold it into `output/generate-ENERGINET.py`) so `src/` stays reproducible.

---

## Act 7 — Capability recap (4 min) — *the answer the client asked for*

Put this table on screen.

| Capability in the use case | Classification | Delivered by |
|---|---|---|
| Model a new data product (entities, references, LOVs, rules, views, application) | 🟢 STD — 🔵 CFG | Semarchy Design (VS Code extension / CLI), `.seml` files |
| AI-assisted specification and generation of the data product | 🔵 CFG (design accelerator) | AI design kit over the standard `.seml` format and CLI build |
| Load existing operational, asset and network-model extracts | 🟢 STD — 🔵 CFG | REST loads API, integration role |
| Govern: validations, enrichers, match & merge, survivorship | 🔵 CFG | Data quality rules |
| Steward review of suggested duplicates, error and warning worklists | 🟢 STD — 🔵 CFG | Data app, duplicate manager, business-view filters |
| Approval workflow, roles and privileges | 🔵 CFG | Workflows, privilege grants; users/groups mapped on the platform |
| Publish to consumers: data app, REST, dashboards, AI agents via MCP | 🟢 STD — 🔵 CFG | Deployment, REST query API, Dashboard Builder, MCP server |
| Maintain and version the data product, history of golden and master records | 🟢 STD | Redeploy (upgrade of the data location), history browsing, Git |
| Email notifications on workflow tasks | 🔵 CFG (platform) | Notification server — not configured for the demo |
| Extraction from EMS / EAM / SCADA / historian systems | 🔵 CFG or 🟣 3RD | Semarchy Data Integration or an external ETL calling the loads API |
| Native CIM / CGMES (XML/RDF) import | 🟠 CUSTOM / 🟣 3RD | Extract-to-CSV/JSON step upstream of the loads API |
| Real-time ingestion of raw SCADA / PMU streams | 🟣 3RD | Historian / streaming platform (e.g. AVEVA PI, Kafka); Semarchy holds context + aggregates |
| Semantic (vector) matching of assets | 🟢 STD on SaaS (2.1, AI preview) — not used here | `Vector` attributes + semantic match rules (SaaS only) |
| Multi-language user interface (e.g. English + Danish per user) | ⚪ ROADMAP | Not available in the current version |

**Close**
> "In under an hour we went from a one-paragraph need to a governed, published data product: two sources reconciled into
> one asset register, bad data stopped at the door, changes approved by the owner, and the result served to people,
> dashboards, applications and AI agents. Everything you saw except the source extraction and the raw streams is the
> standard product, configured."

---

## Likely questions

| Question | Answer |
|---|---|
| *Can we hold the raw PMU data in Semarchy?* | No — and you should not. Semarchy masters the context and keeps aggregates; raw streams stay in the historian or streaming platform, referenced by the measurement point tag. |
| *What if the network model and EAM disagree on the substation of an asset?* | Survivorship: the network model wins for the substation reference, with no manual override (spec §4.4). The disagreement stays visible in the source records. |
| *Why 90 as the merge threshold?* | So that exact serial matches (100) merge and name similarity (80) is only suggested. The threshold is exclusive: a score of exactly 90 would not merge. Tunable per rule. |
| *Who approves a brand-new asset?* | The same owner. Today the steward creates it with *Create*, then starts the approval workflow on it; a from-scratch workflow variant can be added. |
| *How do downstream systems get changes?* | REST query API on golden records today; continuous loads and data notifications are platform configuration (not shown). |
| *Self-hosted?* | The data product runs self-hosted on SDP Self-Hosted 1.3.0 or later; vector matching is SaaS-only. |
| *Is the logo theirs?* | The application uses public Energinet imagery for the demo only; replace with an approved asset before any external use. |

---

## Reset after the demo

1. Undo the `SUB-HAV` coordinate fix (or reload `01_Substation_NETMODEL.csv`) so the worklist demo works next time.
2. The merged *CB Q11* pair and the approved *CB Q112 Havrevang* asset stay changed — pick other records next time,
   or reload the dataset into a fresh data location.
3. Revert the `VoltageLevel` LOV change in `src/` if it was not folded back into the generator.
