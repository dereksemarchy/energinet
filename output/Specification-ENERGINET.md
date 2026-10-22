# Implementation Specification File — ENERGINET (Grid Asset & Measurement data product)

> Produced by Module B (Semarchy discovery & specification) of the methodology, from the client inputs in `input/`.
> Business language only — no `.seml` is produced at this stage.
> Every row carries a status: **Confirmed** (client input or explicit user validation) · **AI suggestion — pending validation** · **Open**.
> Nothing is generated while a single line remains at `AI suggestion — pending validation` (§10.3).

---

## 0. Summary

| Item | Content | Status |
|---|---|---|
| Client / business domain | Energinet-type electricity Transmission System Operator (TSO): grid assets, substations, network topology and operational measurements (SCADA, PMU / power quality, sensors) | Confirmed (input: *Demo use-cases.txt*) |
| Business objectives and expected outcomes | Demonstrate how a **data owner / data steward creates, governs, publishes and maintains a new data product** built on existing operational data (SCADA measurements, PMU / power-quality measurements, substation or sensor data, asset information) enriched with context from an **authoritative network model**, for consumers such as control-centre applications, operational planning, analytics and Asset Management. For every capability shown, state whether it is **standard product functionality, configuration / custom development, third-party, or roadmap** (§10.5) | Confirmed (input) |
| Sources analyzed | `input/Demo use-cases.txt` (text, received 2026-10-15) — use-case statement only. **No data file (CSV / XLSX) was found in `input/`**, although the run request mentions "CSV for the Customer use-case" and "XLSX for the Product use-case" — see §10.1 Q1–Q2 | Confirmed (observed) |
| Scope covered by this document | **Included:** Substation, Asset (grid equipment), Transmission line, Measurement point (SCADA point / PMU channel / PQ meter / sensor), aggregated Measurement values, their reference data, quality rules, one governance workflow, business views and the application. **Excluded:** raw high-frequency time-series storage and streaming (see §10.5), Customer and Product domains (see §10.1 Q1) | Confirmed (user, 2026-10-15 — §10.1 Q1) |
| Overall status | **Validated** — hypothesis validation gate closed 2026-10-15 (§10.3) | Confirmed |

### 0.1 Structuring assumptions — to validate before design starts

| # | Structuring assumption | Decision | Consequence if changed later | Status |
|---|---|---|---|---|
| 1 | **Design language** | English | Rework of every label across the whole data product | Confirmed (run request: "Design language: English") |
| 2 | **One data product per workspace** | Single data product `src/ENERGINET/` | A second data product in `src/` breaks the build and the IDE | Confirmed (product constraint + run request) |
| 3 | **SEML dialect** | `2.1` (installed Design CLI 2.1.0; target tenant is SaaS) | Re-emission of the tree in another dialect | Confirmed (observed on the workstation) |
| 4 | **Business scope of the data product** | The energy-grid use case of `input/Demo use-cases.txt` — **not** the Customer / Product domains named in the run request | Wrong scope = a different data product altogether | Confirmed (user, 2026-10-15) |
| 5 | **Golden-record identifier strategy** | Basic and ID-matched entities keep the business key of their source (substation code, line code, SCADA point tag); the fuzzy-matched Asset gets a **platform-generated** golden id, source ids kept in `NetworkModelId` (CIM mRID) and `EamAssetNumber` | Migration of every identifier and every consumer integration | Confirmed (user, 2026-10-15) |
| 6 | **MDM vs. time-series boundary** | The data product **masters the context** (assets, topology, measurement-point catalogue) and holds only **aggregated measurement values** (e.g. 15-minute avg/min/max) for demonstration and analytics. Raw SCADA / PMU streams (seconds to sub-second) stay in the operational historian / streaming platform | Holding raw streams in MDM would not scale; omitting measurements entirely removes the "operational data" half of the demo | Confirmed (user, 2026-10-15) |

**Product limitation to state to the client:** no label-translation mechanism — a multi-language application (e.g. English + Danish served per user) is not implementable in the current version. The design language is a one-shot decision.

### 0.2 Design language

| Layer | What it covers | Rule | Decision | Status |
|---|---|---|---|---|
| **Technical names** | Entity / attribute / reference names, physical names, role names, SemQL | Always English, ASCII, unaccented | English (imposed) | Confirmed |
| **User-facing labels** | Labels, descriptions, LOV value labels, forms, tabs, actions, workflows, application, validation messages | 100 % in the design language | English | Confirmed (run request) |
| **Reference / LOV data values** | Stored codes and labels | Codes English/ASCII (or the industry code: `DK1`, `DK2`, kV values); labels in English | English | Confirmed |
| **This specification document** | Section wording | Same as design language | English | Confirmed |

- **Design language chosen:** English
- **Language of this document:** English
- **Reversibility:** none at reasonable cost (no translation layer)
- **Client-imposed terminology:** none supplied — industry terms (SCADA, PMU, mRID, CIM, bay, grid area DK1/DK2) used as-is
- **Status:** Confirmed

---

## 1. Source register

No source file was supplied; this register is the **assumed** source landscape of a TSO, derived from the use case wording ("existing operational data", "authoritative network model", "asset information").

| Source | Format | Producing system | Entities involved | Approx. volume | Authoritative source for... | Status |
|---|---|---|---|---|---|---|
| Network model export | CSV extract of a CIM / CGMES model (publisher code `NETMODEL`) | Network-model / EMS modelling tool | Substation, Asset, Transmission line | Demo: ~10 substations, ~60 assets, ~12 lines | Topology, CIM mRID, names, voltage levels, connectivity | Confirmed (user, 2026-10-15) |
| Asset register export | CSV (publisher code `EAM`) | Enterprise Asset Management (e.g. SAP PM / IBM Maximo) | Substation, Asset | Demo: ~10 substations, ~55 assets (overlap with the network model, no shared key on assets) | Asset lifecycle: manufacturer, model, serial number, commissioning date, operating status, criticality, inspections | Confirmed (user, 2026-10-15) |
| SCADA / PMU point list | CSV (publisher code `SCADA`) | SCADA / EMS and WAMS (PMU) point configuration | Measurement point | Demo: ~80 points | Point tag, measurement type, unit, device type, sampling rate, alarm limits | Confirmed (user, 2026-10-15) |
| Measurement aggregates | CSV (publisher code `HISTORIAN`) | Operational historian (e.g. AVEVA PI) — 15-minute aggregates | Measurement | Demo: ~1 day × 80 points × 96 = ~7 700 rows; **production volumes stay in the historian** | Aggregated values and quality flag | Confirmed (user, 2026-10-15) |
| Demo dataset | CSV per entity and per publisher, **fictional**, generated into `resources/data/` (the CSV / XLSX named in the run request do not exist) | — | All | As in the rows above | — | Confirmed (user, 2026-10-15) |

---

## 2. Roles (personas)

No role list was supplied → 4 roles proposed (within the 3–5 cap). The target platform currently declares only `semarchyAdmin`, `semarchyConnect`, `semarchySystemAdmin` (read on 2026-10-15), so every business role is **To create**.

| Role | Platform role name (`roleName`) | On the target platform | Functional description | Associated business personas | Intended access type | Record-level restriction | Field-level restriction | Status |
|---|---|---|---|---|---|---|---|---|
| Data administrator | `semarchyAdmin` | Exists (built-in) | Administers the data product, deployments and platform objects | Platform administrator | Full | None | None | Confirmed (user, 2026-10-15) |
| Grid data owner | `GridDataOwner` | To create | Accountable for the data product: approves new / changed assets, decides publication, owns quality targets | Data owner (named in the input) | Read/write on every entity; approver in the governance workflow; duplicate management | None | None | Confirmed (user, 2026-10-15) |
| Grid data steward | `GridDataSteward` | To create | Maintains substations, assets, lines and measurement points; reviews duplicates and data-quality errors; submits asset changes for approval | Data steward (named in the input) | Read/write on Substation, Asset, Transmission line, Measurement point; **read** on Measurement; duplicate management on Asset | None | None | Confirmed (user, 2026-10-15) |
| Integration service | `GridIntegration` | To create | Technical role used by the loads API (source feeds) — not a persona | Integration jobs (network model, EAM, SCADA, historian) | Write on every entity through the REST loads API (`integrationWsRole`) | None | None | Confirmed (user, 2026-10-15) |
| Data consumer | `GridDataConsumer` | To create | Read-only access for downstream consumers (control centre applications, operational planning, analytics, Asset Management) through the application, REST API and MCP server | Control-centre engineer, planner, analyst, asset manager | Read on every entity | None | None | Confirmed (user, 2026-10-15) |

---

## 3. Data model

### 3.1 Entities

| Entity | Type | Identifier generation logic | Historization | Deletion policy | Functional description | Status |
|---|---|---|---|---|---|---|
| Substation | **ID-matched** | Shared substation code (e.g. `SUB-KAS`), present in both the network model and the asset register | Golden: yes / Master: no | Logical; restrict while assets, points or lines reference it | Physical grid node (switchyard / station) with its grid area, highest voltage level and location | Confirmed (user, 2026-10-15) |
| Asset | **Fuzzy-matched** | Golden id generated by the platform (sequence); source ids kept in `NetworkModelId` (mRID) and `EamAssetNumber` | Golden: yes / Master: yes | Logical; restrict while measurement points reference it | Grid equipment (power transformer, circuit breaker, disconnector, busbar, instrument transformer, reactor, capacitor bank) consolidated from the network model and the asset register, which share no common key | Confirmed (user, 2026-10-15) |
| TransmissionLine | **Basic** | Line code from the network model (e.g. `LN-400-KAS-REV`) | Golden: yes | Logical | Overhead line or cable connecting two substations — the topology context from the authoritative network model | Confirmed (user, 2026-10-15) |
| MeasurementPoint | **Basic** | SCADA / PMU point tag from the point list (e.g. `KAS.T1.P.MW`) | Golden: yes | Logical; cascade to its measurements | Catalogue entry of one measured signal: what is measured, where, by which device, in which unit, at which rate — the link between the operational stream and its network context | Confirmed (user, 2026-10-15) |
| Measurement | **Basic** | Platform-generated sequence | No | Physical (aggregates can be reloaded from the historian) | One aggregated value window (avg / min / max / quality) of a measurement point | Confirmed (user, 2026-10-15) |

> No metadata entity (glossary, data-product catalogue, consumer register) is proposed: the data product's meaning and the AI-agent usage rules go into the `description` / `documentation` of the data product and of each object (exposed through the MCP server) — Confirmed (user, 2026-10-15).

### 3.2 Attributes

| Entity | Attribute | Type | Data type | Mandatory | Length / precision | Functional description | Status |
|---|---|---|---|---|---|---|---|
| Substation | Substation code | Simple (key) | Text | Yes | 30 | Shared business key | Confirmed (user, 2026-10-15) |
| Substation | Substation name | Simple | Text | Yes | 100 | Station name | Confirmed (user, 2026-10-15) |
| Substation | Grid area | Simple | LOV *Grid area* | Yes | — | DK1 (West Denmark) / DK2 (East Denmark) | Confirmed (user, 2026-10-15) |
| Substation | Highest voltage level | Simple | LOV *Voltage level* | Yes | — | 400 / 220 / 150 / 132 / 60 kV | Confirmed (user, 2026-10-15) |
| Substation | Latitude, Longitude | Simple ×2 | Decimal | No | 9,6 | WGS84 location | Confirmed (user, 2026-10-15) |
| Substation | Operating status | Simple | LOV *Operating status* | Yes | — | Planned / In service / Out of service / Decommissioned | Confirmed (user, 2026-10-15) |
| Substation | Commissioning date | Simple | Date | No | — | Date put into service | Confirmed (user, 2026-10-15) |
| Substation | Description | Simple | Text | No | 1000 | Free text | Confirmed (user, 2026-10-15) |
| Asset | Asset name | Simple | Text | Yes | 150 | Equipment designation (e.g. "T1 400/150 kV transformer") | Confirmed (user, 2026-10-15) |
| Asset | Asset type | Simple | LOV *Asset type* | Yes | — | Power transformer, circuit breaker, disconnector, busbar, current transformer, voltage transformer, shunt reactor, capacitor bank, protection relay | Confirmed (user, 2026-10-15) |
| Asset | Network model id (mRID) | Simple | Text | No | 64 | CIM mRID from the network model | Confirmed (user, 2026-10-15) |
| Asset | EAM asset number | Simple | Text | No | 30 | Equipment number in the asset register | Confirmed (user, 2026-10-15) |
| Asset | Manufacturer | Simple | Text | No | 100 | OEM | Confirmed (user, 2026-10-15) |
| Asset | Model | Simple | Text | No | 100 | OEM model reference | Confirmed (user, 2026-10-15) |
| Asset | Serial number | Simple | Text | No | 50 | OEM serial number | Confirmed (user, 2026-10-15) |
| Asset | Voltage level | Simple | LOV *Voltage level* | No | — | Rated voltage level | Confirmed (user, 2026-10-15) |
| Asset | Rated power (MVA) | Simple | Decimal | No | 10,2 | Rated apparent power (transformers, reactors) | Confirmed (user, 2026-10-15) |
| Asset | Commissioning date | Simple | Date | No | — | Date put into service | Confirmed (user, 2026-10-15) |
| Asset | Operating status | Simple | LOV *Operating status* | Yes | — | As for Substation | Confirmed (user, 2026-10-15) |
| Asset | Criticality | Simple | LOV *Criticality* | No | — | High / Medium / Low — drives maintenance priority | Confirmed (user, 2026-10-15) |
| Asset | Last inspection date | Simple | Date | No | — | From the asset register | Confirmed (user, 2026-10-15) |
| Asset | Age (years) | Simple, computed, read-only | Integer | No | — | Years since commissioning, computed on the golden record | Confirmed (user, 2026-10-15) |
| Asset | Normalized name (technical) | Simple, technical, not displayed | Text | No | 150 | Upper-case, punctuation-free name used for fuzzy matching | Confirmed (user, 2026-10-15) |
| TransmissionLine | Line code | Simple (key) | Text | Yes | 40 | Business key | Confirmed (user, 2026-10-15) |
| TransmissionLine | Line name | Simple | Text | Yes | 150 | e.g. "Kassø – Revsing 400 kV" | Confirmed (user, 2026-10-15) |
| TransmissionLine | Line type | Simple | LOV *Line type* | Yes | — | Overhead line / Underground cable / Submarine cable | Confirmed (user, 2026-10-15) |
| TransmissionLine | Voltage level | Simple | LOV *Voltage level* | Yes | — | Operating voltage | Confirmed (user, 2026-10-15) |
| TransmissionLine | Length (km) | Simple | Decimal | No | 8,2 | Circuit length | Confirmed (user, 2026-10-15) |
| TransmissionLine | Rated capacity (MVA) | Simple | Decimal | No | 10,2 | Thermal rating | Confirmed (user, 2026-10-15) |
| TransmissionLine | Operating status | Simple | LOV *Operating status* | Yes | — | — | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Point tag | Simple (key) | Text | Yes | 80 | SCADA / PMU tag | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Point name | Simple | Text | Yes | 150 | Human-readable signal name | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Measurement type | Simple | LOV *Measurement type* | Yes | — | Active power, reactive power, voltage magnitude, current, frequency, voltage phase angle, total harmonic distortion, temperature, oil temperature | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Unit | Simple | LOV *Unit* | Yes | — | MW, Mvar, kV, A, Hz, deg, %, °C | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Device type | Simple | LOV *Device type* | Yes | — | SCADA RTU, PMU, power-quality meter, IoT sensor | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Phase | Simple | LOV *Phase* | No | — | L1 / L2 / L3 / Three-phase / Positive sequence | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Sampling interval (ms) | Simple | Integer | No | — | e.g. 2 000 for SCADA, 20 for PMU (50 frames/s) | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Alarm low / high limit | Simple ×2 | Decimal | No | 14,4 | Operating limits | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Active | Simple | Boolean | Yes | — | Point currently scanned | Confirmed (user, 2026-10-15) |
| Measurement | Period start | Simple | Timestamp | Yes | — | Start of the aggregation window | Confirmed (user, 2026-10-15) |
| Measurement | Aggregation interval | Simple | LOV *Aggregation interval* | Yes | — | 15 min / 1 h | Confirmed (user, 2026-10-15) |
| Measurement | Average / Minimum / Maximum value | Simple ×3 | Decimal | Avg: Yes | 16,4 | Aggregated values over the window | Confirmed (user, 2026-10-15) |
| Measurement | Quality flag | Simple | LOV *Quality flag* | Yes | — | Good / Suspect / Bad / Missing | Confirmed (user, 2026-10-15) |

### 3.3 Relationships between entities

| Source entity (child) | Target entity (parent) | Cardinality | Nature | Functional description | Status |
|---|---|---|---|---|---|
| Asset | Substation | Many assets per substation; mandatory | Associative | An asset is installed in a substation | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Substation | Many points per substation; mandatory | Associative | Where the signal is measured | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Asset | Many points per asset; optional | Associative | The equipment the signal measures (empty for bus / station-level points) | Confirmed (user, 2026-10-15) |
| MeasurementPoint | TransmissionLine | Many points per line; optional | Associative | Line-end measurements (power flow, PMU phasors) | Confirmed (user, 2026-10-15) |
| Measurement | MeasurementPoint | Many values per point; mandatory | Associative | Aggregated values of a point | Confirmed (user, 2026-10-15) |

### 3.4 Relationship entities (many-to-many cardinalities)

| Relationship entity | Linked entity 1 | Linked entity 2 | Attributes specific to the relationship | Exposed in a business view? | Functional description | Status |
|---|---|---|---|---|---|---|
| TransmissionLine | Substation (*From substation*) | Substation (*To substation*) | Line code, type, voltage level, length, rated capacity, status | Yes — own view, and as "Outgoing / Incoming lines" tabs of the substation | The network topology: substations connected by lines | Confirmed (user, 2026-10-15) |

### 3.5 Reference data

| Reference dataset | Chosen mode | Justification | Estimated number of values | Maintenance owner | Status |
|---|---|---|---|---|---|
| Grid area | Native LOV | Closed, stable | 2 | N/A | Confirmed (user, 2026-10-15) |
| Voltage level | Native LOV | Closed, stable | 5 | N/A | Confirmed (user, 2026-10-15) |
| Operating status | Native LOV | Closed | 4 | N/A | Confirmed (user, 2026-10-15) |
| Asset type | Native LOV | Closed, < 1000 | 9 | N/A | Confirmed (user, 2026-10-15) |
| Criticality | Native LOV | Closed | 3 | N/A | Confirmed (user, 2026-10-15) |
| Line type | Native LOV | Closed | 3 | N/A | Confirmed (user, 2026-10-15) |
| Measurement type, Unit, Device type, Phase, Aggregation interval, Quality flag | Native LOVs | Closed, stable, small | 9 / 8 / 4 / 5 / 2 / 4 | N/A | Confirmed (user, 2026-10-15) |

---

## 4. Data quality rules

### 4.1 Enrichment

| Entity | Attribute(s) involved | Enrichment type | Scope | Functional description | Status |
|---|---|---|---|---|---|
| Asset | Normalized name | Technical generation (normalization) | Before consolidation | Upper-case, strip punctuation and spaces — preparation for fuzzy matching | Confirmed (user, 2026-10-15) |
| Asset, Substation, TransmissionLine, MeasurementPoint | Names | Standardization | Before consolidation | Trim surrounding spaces | Confirmed (user, 2026-10-15) |
| Asset | Age (years) | Derivation | After consolidation | Whole years between commissioning date and today | Confirmed (user, 2026-10-15) |

### 4.2 Validation

| Entity | Attribute(s) / rule | Business condition | Severity | Scope | Status |
|---|---|---|---|---|---|
| Asset | Source identifier | At least one of mRID or EAM asset number is filled | Blocking | Before consolidation | Confirmed (user, 2026-10-15) |
| Substation | Location | Latitude 54–58 and longitude 7.5–15.5 (Denmark) when filled | Warning | After consolidation | Confirmed (user, 2026-10-15) |
| TransmissionLine | Endpoints | From substation ≠ To substation | Blocking | Before consolidation | Confirmed (user, 2026-10-15) |
| TransmissionLine | Length | Length > 0 when filled | Blocking | Before consolidation | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Alarm limits | Low limit < High limit when both filled | Blocking | Before consolidation | Confirmed (user, 2026-10-15) |
| MeasurementPoint | Context consistency | When an asset is set, it belongs to the same substation as the point | Warning | After consolidation | Confirmed (user, 2026-10-15) |
| Measurement | Value range | Minimum ≤ Average ≤ Maximum | Blocking | Before consolidation | Confirmed (user, 2026-10-15) |
| Asset | Commissioning date | Not in the future for an *In service* asset | Warning | After consolidation | Confirmed (user, 2026-10-15) |

### 4.3 Matching rules

| Entity | Compared attributes | Comparison type | Tolerance / score | Human review required? | Responsible persona | Status |
|---|---|---|---|---|---|---|
| Substation | Substation code | Exact (ID-matched) | — | No | — | Confirmed (user, 2026-10-15) |
| Asset | Rule 1 — serial number + manufacturer | Exact (case-insensitive) | Score 100 → automatic merge | No | — | Confirmed (user, 2026-10-15) |
| Asset | Rule 2 — same substation + same asset type + normalized name similarity ≥ 85 % | Approximate (edit-distance similarity) | Score 80 → suggested match, **below** the automatic-merge threshold (90) | Yes | Grid data steward | Confirmed (user, 2026-10-15) |

### 4.4 Merge and survivorship rules

| Entity | Attribute(s) involved | Strategy | Detail | Manual override allowed? | Status |
|---|---|---|---|---|---|
| Asset | Asset name, Network model id, Voltage level, Asset type | `PREFERRED_PUBLISHER` | `NETMODEL` > `EAM` (the network model is authoritative for topology and naming) | Yes, until the next consolidated value change | Confirmed (user, 2026-10-15) |
| Asset | EAM asset number, Manufacturer, Model, Serial number, Rated power, Commissioning date, Operating status, Criticality, Last inspection date | `PREFERRED_PUBLISHER` | `EAM` > `NETMODEL` (the asset register is authoritative for lifecycle) | Yes, until the next consolidated value change | Confirmed (user, 2026-10-15) |
| Asset | Substation reference | `PREFERRED_PUBLISHER` | `NETMODEL` > `EAM` | No | Confirmed (user, 2026-10-15) |
| Substation | Name, grid area, voltage level, location | `PREFERRED_PUBLISHER` | `NETMODEL` > `EAM` | Yes | Confirmed (user, 2026-10-15) |
| Substation | Operating status, commissioning date, description | `PREFERRED_PUBLISHER` | `EAM` > `NETMODEL` | Yes | Confirmed (user, 2026-10-15) |

---

## 5. Processes and workflows

### 5.1 Persona × use case × process type matrix

| Persona | Use case | Entity/entities | Process type | Status |
|---|---|---|---|---|
| Integration service | Load the network model, asset register, SCADA point list and measurement aggregates | All | Batch load (REST loads API) | Confirmed (user, 2026-10-15) |
| Grid data steward | Maintain substations, lines, measurement points | Substation, TransmissionLine, MeasurementPoint | Simple entry | Confirmed (user, 2026-10-15) |
| Grid data steward → Grid data owner | Register or change an asset, then approve it | Asset | Collaborative workflow | Confirmed (user, 2026-10-15) |
| Grid data steward | Review suggested asset duplicates (network model vs. asset register) | Asset | Duplicate validation | Confirmed (user, 2026-10-15) |
| Data consumer | Browse the published data product, export, consume via REST / MCP | All | Read-only | Confirmed (user, 2026-10-15) |

### 5.2 Workflow descriptions

**Workflow: Asset change approval**
- **Trigger**: from scratch (new asset) or from an existing asset record
- **Entity/entities involved**: Asset
- **Steps**:
  1. *Prepare* — Grid data steward — user task (edit the asset form)
  2. *Approve* — Grid data owner — user task; approve → submit, reject → back to step 1 with a comment
- **Notifications**: none in this version (requires a notification server — platform-side)
- **Outcome**: on approval the record is submitted, certified and published to consumers
- **Disagreement handling**: rejection returns the task to the steward
- **Status**: Confirmed (user, 2026-10-15)

---

## 6. Business views

### 6.1 View catalog

| Business view | Root entity | Target persona(s) | Default filter | Status |
|---|---|---|---|---|
| Substations | Substation | Steward, owner, consumer | None | Confirmed (user, 2026-10-15) |
| Assets | Asset | Steward, owner, consumer | None | Confirmed (user, 2026-10-15) |
| Transmission lines | TransmissionLine | Steward, owner, consumer | None | Confirmed (user, 2026-10-15) |
| Measurement points | MeasurementPoint | Steward, owner, consumer | None | Confirmed (user, 2026-10-15) |

### 6.2 Navigation (transitions)

| Business view | Relationship used | Target entity | Presentation mode | Status |
|---|---|---|---|---|
| Substations | Substation → Asset | Asset | Tab "Assets" | Confirmed (user, 2026-10-15) |
| Substations | Substation → MeasurementPoint | MeasurementPoint | Tab "Measurement points" | Confirmed (user, 2026-10-15) |
| Substations | Substation → TransmissionLine (from / to) | TransmissionLine | Tabs "Outgoing lines" / "Incoming lines" | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Assets | Asset → MeasurementPoint | MeasurementPoint | Tab "Measurement points" | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Measurement points | MeasurementPoint → Measurement | Measurement | Tab "Measurements" | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Transmission lines | TransmissionLine → MeasurementPoint | MeasurementPoint | Tab "Measurement points" | Confirmed (user, 2026-10-15 — accepted without item-level review) |

### 6.3 Actions available per view

| Business view | Action | Type | Authorized persona(s) | Status |
|---|---|---|---|---|
| All views | Create / edit / delete / export | Entry / utility | Steward, owner (consumer: export only) | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Assets | Review suggested duplicates (match & merge) | Duplicate management | Steward, owner | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Assets | Start *Asset change approval* | Workflow | Steward | Confirmed (user, 2026-10-15 — accepted without item-level review) |

---

## 7. Management screens

### 7.1 Single-object screens

| Screen | Entity | Type | Attribute groups | Fields excluded from search | Status |
|---|---|---|---|---|---|
| Substation record | Substation | Form | Identification · Location · Lifecycle | — (no sensitive data) | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Asset record | Asset | Form | Identification · Technical data · Lifecycle · Source identifiers | — | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Transmission line record | TransmissionLine | Form | Identification · Topology · Technical data | — | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Measurement point record | MeasurementPoint | Form | Identification · Signal · Context · Limits | — | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Measurement record | Measurement | Form (read-mostly) | Single section | — | Confirmed (user, 2026-10-15 — accepted without item-level review) |

### 7.2 Multi-object screens

| Screen | Entities covered | Journey steps | Status |
|---|---|---|---|
| None in this version | — | — | Confirmed (user, 2026-10-15 — accepted without item-level review) |

---

## 8. Application personalization (branding)

| Element | Expected content | Source supplied | Status |
|---|---|---|---|
| Login page / application appearance / image library | Default Semarchy appearance with generic entity icons; no client logo (none supplied, and using a client's logo requires their authorisation) | None | Confirmed (user, 2026-10-15 — accepted without item-level review) |

---

## 9. Suggested dashboards

| Dashboard | Family | Proposed indicators | Target personas | Where the data app shows it | Parameters | Status |
|---|---|---|---|---|---|---|
| Grid data quality | Data quality | Errors per rule, suggested asset duplicates pending review, completeness of critical attributes | Grid data owner, steward | Navigation tile — **built in a later step with `/seml-dashboard`, out of this run** | — | Confirmed (user, 2026-10-15 — accepted without item-level review) |

---

## 10. Appendices

### 10.1 Open questions

| # | Question | Related phase | Blocking impact on implementation | Answer | Status |
|---|---|---|---|---|---|
| 1 | The run request mentions a **Customer use-case** (CSV) and a **Product use-case** (XLSX), but `input/` only contains the energy-grid "create and publish a new data product" use case. Which business scope should ENERGINET cover? | 0 — Sources | **Blocking** — decides the whole data model | Energy grid, as drafted from `input/Demo use-cases.txt` | Confirmed |
| 2 | No CSV or XLSX file exists in `input/`. Will you add them, or should a **fictional demo dataset** be generated for the chosen scope (`resources/data/`)? | 0 — Sources / load step | Blocking for the data load (step 6), not for generation | Generate a fictional demo dataset | Confirmed |

### 10.2 Glossary of Semarchy terms used in this document

See `mdm-semarchy-discovery-methodology.md` §1.

### 10.3 Decision log — hypothesis validation gate

**Gate outcome**

| Item | Value |
|---|---|
| Suggestions submitted (`N`) | 124 (+ 2 Open questions answered) |
| Mode used | Interactive (N > 5), grouped by theme |
| Groups reviewed | 16 — groups 1–14 and items 1–6 of group 15 item by item; the rest of group 15 and group 16 by user blanket acceptance |
| Accepted as recommended | 100 (item-level review) |
| Overridden by the user | 0 |
| Accepted without item-level review | 24 |
| Left `Open` | 0 |
| Gate closed on | 2026-10-15 |

**Decision log**

| Date | Group | # | Suggestion (what was assumed) | Decision | Decided by |
|---|---|---|---|---|---|
| 2026-10-15 | Open questions | Q1 | Business scope (energy grid vs. Customer / Product named in the run request) | Energy grid | User |
| 2026-10-15 | Open questions | Q2 | Demo data (no CSV / XLSX in `input/`) | Generate a fictional dataset | User |
| 2026-10-15 | Structuring assumptions | 1 | MDM masters context + 15-min aggregates; raw streams stay in the historian | Accepted as recommended | User |
| 2026-10-15 | Structuring assumptions | 2 | Source business keys; platform golden id for fuzzy-matched Asset (mRID + EAM no. kept) | Accepted as recommended | User |
| 2026-10-15 | Sources | 3 | Network model export (NETMODEL) authoritative for topology, mRID, names, voltage | Accepted as recommended | User |
| 2026-10-15 | Sources | 4 | EAM asset register authoritative for asset lifecycle; no shared key with the network model | Accepted as recommended | User |
| 2026-10-15 | Sources | 5 | SCADA/PMU point list feeds MeasurementPoint | Accepted as recommended | User |
| 2026-10-15 | Sources | 6 | Historian 15-min aggregates feed Measurement, ~1 day demo | Accepted as recommended | User |
| 2026-10-15 | Roles | 7 | GridDataOwner: read/write all, workflow approver, duplicates | Accepted as recommended | User |
| 2026-10-15 | Roles | 8 | GridDataSteward: write Substation/Asset/Line/Point, read Measurement, duplicates | Accepted as recommended | User |
| 2026-10-15 | Roles | 9 | GridIntegration: technical loads role, integrationWsRole, write all | Accepted as recommended | User |
| 2026-10-15 | Roles | 10 | GridDataConsumer: read-only all entities, export | Accepted as recommended | User |
| 2026-10-15 | Roles | 11 | Built-in semarchyAdmin as data administrator | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 12 | ID-matched on substation code, golden history, logical delete restrict | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 13 | Substation code Text(30) key | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 14 | Substation name Text(100) mandatory | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 15 | Grid area mandatory LOV DK1/DK2 | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 16 | Highest voltage level mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 17 | Latitude/Longitude decimal(9,6) | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 18 | Operating status mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 19 | Commissioning date optional | Accepted as recommended | User |
| 2026-10-15 | Entity Substation | 20 | Description optional Text(1000) | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 21 | Fuzzy-matched, platform golden id, golden+master history, logical delete restrict | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 22 | Asset name Text(150) mandatory | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 23 | Asset type mandatory LOV (9 values) | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 24 | Network model id (mRID) Text(64) | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 25 | EAM asset number Text(30) | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 26 | Manufacturer free Text(100) | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 27 | Model Text(100) | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 28 | Serial number Text(50) | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 29 | Voltage level optional LOV | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 30 | Rated power MVA Decimal(10,2) | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 31 | Commissioning date optional | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 32 | Operating status mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 33 | Criticality optional LOV | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 34 | Last inspection date optional | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 35 | Age (years) computed read-only | Accepted as recommended | User |
| 2026-10-15 | Entity Asset | 36 | Normalized name technical hidden | Accepted as recommended | User |
| 2026-10-15 | Entity TransmissionLine | 37 | Basic, NETMODEL only, key = line code, golden history, logical delete | Accepted as recommended | User |
| 2026-10-15 | Entity TransmissionLine | 38 | Line code Text(40) key | Accepted as recommended | User |
| 2026-10-15 | Entity TransmissionLine | 39 | Line name Text(150) mandatory | Accepted as recommended | User |
| 2026-10-15 | Entity TransmissionLine | 40 | Line type mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entity TransmissionLine | 41 | Voltage level mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entity TransmissionLine | 42 | Length km + rated capacity MVA | Accepted as recommended | User |
| 2026-10-15 | Entity TransmissionLine | 43 | Operating status mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 44 | Basic, SCADA list, key = point tag, cascade to measurements | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 45 | Point tag key + point name | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 46 | Measurement type mandatory LOV (9) | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 47 | Unit mandatory LOV, ASCII codes | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 48 | Device type mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 49 | Phase optional LOV | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 50 | Sampling interval ms integer | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 51 | Alarm low/high limits decimal | Accepted as recommended | User |
| 2026-10-15 | Entity MeasurementPoint | 52 | Active flag boolean mandatory | Accepted as recommended | User |
| 2026-10-15 | Entity Measurement | 53 | Basic, HISTORIAN, sequence id, no history, physical delete | Accepted as recommended | User |
| 2026-10-15 | Entity Measurement | 54 | Period start timestamp mandatory | Accepted as recommended | User |
| 2026-10-15 | Entity Measurement | 55 | Aggregation interval mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entity Measurement | 56 | Avg (mandatory)/min/max Decimal(16,4) | Accepted as recommended | User |
| 2026-10-15 | Entity Measurement | 57 | Quality flag mandatory LOV | Accepted as recommended | User |
| 2026-10-15 | Entities (metadata) | 58 | No metadata entities; semantics + AI-agent instructions embedded in documentation | Accepted as recommended | User |
| 2026-10-15 | Relationships | 59 | Asset -> Substation mandatory | Accepted as recommended | User |
| 2026-10-15 | Relationships | 60 | MeasurementPoint -> Substation mandatory | Accepted as recommended | User |
| 2026-10-15 | Relationships | 61 | MeasurementPoint -> Asset optional | Accepted as recommended | User |
| 2026-10-15 | Relationships | 62 | MeasurementPoint -> TransmissionLine optional | Accepted as recommended | User |
| 2026-10-15 | Relationships | 63 | Measurement -> MeasurementPoint mandatory, cascade | Accepted as recommended | User |
| 2026-10-15 | Relationships | 64 | TransmissionLine From/To Substation, both mandatory | Accepted as recommended | User |
| 2026-10-15 | Reference data | 65 | Grid area native LOV | Accepted as recommended | User |
| 2026-10-15 | Reference data | 66 | Voltage level native LOV | Accepted as recommended | User |
| 2026-10-15 | Reference data | 67 | Operating status native LOV | Accepted as recommended | User |
| 2026-10-15 | Reference data | 68 | Asset type native LOV | Accepted as recommended | User |
| 2026-10-15 | Reference data | 69 | Criticality native LOV | Accepted as recommended | User |
| 2026-10-15 | Reference data | 70 | Line type native LOV | Accepted as recommended | User |
| 2026-10-15 | Reference data | 71 | Six measurement-domain native LOVs | Accepted as recommended | User |
| 2026-10-15 | Enrichment | 72 | Asset normalized name, pre-consolidation | Accepted as recommended | User |
| 2026-10-15 | Enrichment | 73 | Trim names, pre-consolidation | Accepted as recommended | User |
| 2026-10-15 | Enrichment | 74 | Asset age, post-consolidation (computed at certification) | Accepted as recommended | User |
| 2026-10-15 | Validation | 75 | Asset mRID or EAM number required, blocking pre-conso | Accepted as recommended | User |
| 2026-10-15 | Validation | 76 | Substation location in DK bounds, warning post-conso | Accepted as recommended | User |
| 2026-10-15 | Validation | 77 | Line From != To, blocking pre-conso | Accepted as recommended | User |
| 2026-10-15 | Validation | 78 | Line length > 0, blocking pre-conso | Accepted as recommended | User |
| 2026-10-15 | Validation | 79 | Alarm low < high, blocking pre-conso | Accepted as recommended | User |
| 2026-10-15 | Validation | 80 | Point asset in same substation, warning post-conso | Accepted as recommended | User |
| 2026-10-15 | Validation | 81 | Min <= avg <= max, blocking pre-conso | Accepted as recommended | User |
| 2026-10-15 | Validation | 82 | In-service commissioning not in future, warning post-conso | Accepted as recommended | User |
| 2026-10-15 | Matching & survivorship | 83 | Substation exact match on code | Accepted as recommended | User |
| 2026-10-15 | Matching & survivorship | 84 | Asset rule 1 serial+manufacturer exact, score 100, auto-merge | Accepted as recommended | User |
| 2026-10-15 | Matching & survivorship | 85 | Asset rule 2 substation+type+name>=85%, score 80, steward review | Accepted as recommended | User |
| 2026-10-15 | Matching & survivorship | 86 | Asset topology attrs NETMODEL > EAM | Accepted as recommended | User |
| 2026-10-15 | Matching & survivorship | 87 | Asset lifecycle attrs EAM > NETMODEL | Accepted as recommended | User |
| 2026-10-15 | Matching & survivorship | 88 | Asset substation ref NETMODEL > EAM, no override | Accepted as recommended | User |
| 2026-10-15 | Matching & survivorship | 89 | Substation topology attrs NETMODEL > EAM | Accepted as recommended | User |
| 2026-10-15 | Matching & survivorship | 90 | Substation lifecycle attrs EAM > NETMODEL | Accepted as recommended | User |
| 2026-10-15 | Processes | 91 | Integration batch loads via REST loads API | Accepted as recommended | User |
| 2026-10-15 | Processes | 92 | Steward simple entry on Substation/Line/Point | Accepted as recommended | User |
| 2026-10-15 | Processes | 93 | Asset create/change via steward->owner workflow | Accepted as recommended | User |
| 2026-10-15 | Processes | 94 | Steward reviews suggested Asset duplicates | Accepted as recommended | User |
| 2026-10-15 | Processes | 95 | Consumer read-only browse/export/REST/MCP | Accepted as recommended | User |
| 2026-10-15 | Processes | 96 | Asset change approval workflow: Prepare->Approve, reject loops back, no notifications | Accepted as recommended | User |
| 2026-10-15 | Views & screens | 97 | Substations business view | Accepted as recommended | User |
| 2026-10-15 | Views & screens | 98 | Assets business view | Accepted as recommended | User |
| 2026-10-15 | Views & screens | 99 | Transmission lines business view | Accepted as recommended | User |
| 2026-10-15 | Views & screens | 100 | Measurement points business view | Accepted as recommended | User |
| 2026-10-15 | Views & screens | 101 | Substation -> Assets tab | Accepted as recommended | User |
| 2026-10-15 | Views & screens | 102 | Substation -> Measurement points tab | Accepted as recommended | User |
| 2026-10-15 | Views & screens | 103 | Substations / Substation → TransmissionLine (from / to) / TransmissionLine | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 104 | Assets / Asset → MeasurementPoint / MeasurementPoint | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 105 | Measurement points / MeasurementPoint → Measurement / Measurement | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 106 | Transmission lines / TransmissionLine → MeasurementPoint / MeasurementPoint | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 107 | All views / Create / edit / delete / export / Entry / utility | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 108 | Assets / Review suggested duplicates (match & merge) / Duplicate management | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 109 | Assets / Start *Asset change approval* / Workflow | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 110 | Substation record / Substation / Form | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 111 | Asset record / Asset / Form | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 112 | Transmission line record / TransmissionLine / Form | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 113 | Measurement point record / MeasurementPoint / Form | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 114 | Measurement record / Measurement / Form (read-mostly) | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 115 | None in this version / — / — | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 116 | Login page / application appearance / image library / Default Semarchy appearance with generic entity icons; n | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Views & screens | 117 | Grid data quality / Data quality / Errors per rule, suggested asset duplicates pending review, completeness of | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 118 | Model a new data product (entities, references, LOVs, rules, views, application) / Standard — configuration /  | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 119 | Load existing operational / asset / network-model extracts / Standard — configuration / REST loads API, integr | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 120 | Govern: validations, enrichers, match & merge, survivorship, approval workflow, roles & privileges / Standard  | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 121 | Publish to consumers (REST, application, AI agents via MCP) / Standard — configuration / Data product deployme | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 122 | Maintain / version the data product / Standard / Redeploy (upgrade of the data location), golden / master hist | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 123 | Ingest raw SCADA / PMU streams in real time / **Third-party** / Historian / streaming platform (e.g. AVEVA PI, | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 124 | Read the CIM / CGMES network model natively (XML/RDF) / **Custom development / third-party** / An extract-to-C | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 125 | Connect to SCADA / EMS / EAM systems directly / Configuration (integration) or third-party ETL / Semarchy Data | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Capability classification | 126 | Semantic (vector) matching of assets / Standard on SaaS (2.1, AI preview) — not used in this version / `Vector | Accepted without item-level review (user blanket acceptance of the recommended defaults) | User |
| 2026-10-15 | Implementation note | I1 | §4.4 survivorship: two source-ranked groups per entity | Implemented as one `PREFERRED_PUBLISHER` default rule + one `CUSTOM_RANKING` rule ordered on `PublisherID` (the platform allows a single `PREFERRED_PUBLISHER` rule per entity). Same source priorities as specified | Engine / build constraint |
| 2026-10-15 | Implementation note | I2 | §4.2 *Warning* rules (DK location, point/asset substation, future commissioning) | Implemented as stewardship worklists, not validations: a SemQL validation always rejects the record, so non-blocking rules are queues. *Blocking* rules are PRE_CONSO validations | Platform constraint |
| 2026-10-15 | Implementation note | I3 | §5.2 workflow trigger *from scratch* | Workflow starts from a selected Asset; new assets are created with the standard Create action, then submitted | Brief [MISSING] default, accepted by the user |

### 10.4 Validation history

| Date | Section reviewed | Validated by | Comment |
|---|---|---|---|
| 2026-10-15 | Whole document | — | Draft produced by Module B |
| 2026-10-15 | Whole document | User | Gate closed; 24 items accepted without item-level review |

### 10.5 Capability classification (requested by the client)

How each capability of the use case maps to the Semarchy Data Platform. Product claims are flagged for confirmation rather than asserted.

| Capability in the use case | Classification | How it is delivered | Status |
|---|---|---|---|
| Model a new data product (entities, references, LOVs, rules, views, application) | Standard — configuration | Semarchy Design (VS Code extension / CLI), `.seml` data product | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Load existing operational / asset / network-model extracts | Standard — configuration | REST loads API, integration role | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Govern: validations, enrichers, match & merge, survivorship, approval workflow, roles & privileges | Standard — configuration | Data quality rules, workflows, privilege grants | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Publish to consumers (REST, application, AI agents via MCP) | Standard — configuration | Data product deployment, REST query API, MCP server, data app | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Maintain / version the data product | Standard | Redeploy (upgrade of the data location), golden / master history | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Ingest raw SCADA / PMU streams in real time | **Third-party** | Historian / streaming platform (e.g. AVEVA PI, Kafka); Semarchy holds context + aggregates | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Read the CIM / CGMES network model natively (XML/RDF) | **Custom development / third-party** | An extract-to-CSV / JSON step upstream of the loads API | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Connect to SCADA / EMS / EAM systems directly | Configuration (integration) or third-party ETL | Semarchy Data Integration or an external ETL tool calling the loads API | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Semantic (vector) matching of assets | Standard on SaaS (2.1, AI preview) — not used in this version | `Vector` attributes + semantic match rules | Confirmed (user, 2026-10-15 — accepted without item-level review) |
| Multi-language user interface | **Roadmap** | Not available in the current version | Confirmed (methodology §5) |
