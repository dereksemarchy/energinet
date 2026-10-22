#!/usr/bin/env python3
"""Data product definition - ENERGINET (grid asset & measurement context data product).

Source of truth: output/Specification-ENERGINET.md (Validated 2026-10-15) and
output/GenerationBrief-ENERGINET.md. All .seml emission logic lives in the shared engine.

Usage:  python output/generate-ENERGINET.py
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
while ROOT != os.path.dirname(ROOT) and not os.path.isdir(os.path.join(ROOT, "ai-model-development")):
    ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "ai-model-development", "scripts"))
import seml_engine as engine

PKG = "ENERGINET"
SRC = os.path.join(ROOT, "src", PKG)
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_sources")

def eqn(e): return f"{PKG}.entities.{e}.{e}"
lov = lambda n: f"{PKG}.list_of_values.{n}"
AI = engine.with_ai_instructions

def A(name, dt, length=None, mand=False, is_lov=False, prec=None, scale=None, phys=None, label=None, desc=None):
    a = {"qualifiedName": f"__.{name}", "_type": "AtomicAttribute", "abstractAtomicType": dt,
         "physicalColName": phys or name.upper()[:25], "label": label or name,
         "description": desc or (label or name), "searchable": True, "mandatory": mand}
    if length is not None: a["length"] = length
    if prec is not None: a["precision"] = prec
    if scale is not None: a["scale"] = scale
    if mand: a["mandatoryValidationScope"] = "PRE_CONSO"
    if is_lov: a["lovValidationScope"] = "PRE_CONSO"
    return a

def PK(name, dt, mode, prec=None, length=None, label=None, desc=None):
    p = {"qualifiedName": f"__.{name}", "abstractAtomicType": dt, "physicalColName": name.upper()[:25],
         "idGenerationType": mode, "label": label or name, "description": desc or (label or name)}
    if prec is not None: p["precision"] = prec
    if length is not None: p["length"] = length
    return p

def LOV(name, label, length, values, desc):
    return {"qualifiedName": lov(name), "label": label, "length": length, "description": desc,
            "lovValues": [{"code": c, "label": l, "description": d} for c, l, d in values]}

def E(name, label, plural, icon, desc, etype, pk, atoms, enrichers=None, validations=None,
      survivorship=None, histG=False, histM=False):
    for a in atoms: a["qualifiedName"] = f"{eqn(name)}.{a['qualifiedName'].split('.')[-1]}"
    pk["qualifiedName"] = f"{eqn(name)}.{pk['qualifiedName'].split('.')[-1]}"
    return {"qualifiedName": eqn(name), "label": label, "pluralLabel": plural, "iconUrl": icon,
            "description": desc, "documentation": desc, "entityType": etype,
            "physicalTableName": name.upper()[:25], "historizeGolden": histG, "historizeMaster": histM,
            "enableDelete": True, "pkAttributes": [pk], "atomicAttributes": atoms,
            "enrichers": enrichers or [], "validations": validations or [], "survivorship": survivorship or []}

def R(name, fromE, toE, fromRole, fromLabel, toRole, toLabel, toPhys, label, desc, mand=False, delete="RESTRICT"):
    r = {"qualifiedName": f"{PKG}.references.{name}", "fromEntity": eqn(fromE), "toEntity": eqn(toE),
         "fromRoleName": fromRole, "fromRoleLabel": fromLabel, "fromRolePluralLabel": fromLabel,
         "toRoleName": toRole, "toRoleLabel": toLabel, "toRolePhysicalName": toPhys,
         "physicalName": name.upper()[:25], "deletePropagation": delete, "validationScope": "PRE_CONSO",
         "oneToMany": True, "label": label, "description": desc}
    if mand: r["mandatory"] = True
    return r

def V(name, label, cond, msg, desc):
    return {"_name": name, "_type": "SemQLValidation", "label": label, "validationScope": "PRE_CONSO",
            "condition": cond, "validationLabel": msg, "description": desc}

def trim(ent, attr):
    return {"qualifiedName": f"{PKG}.entities.{ent}.enrichers.Trim{attr}", "_type": "SemQLEnricher",
            "label": "Trim name", "enricherExecutionScope": "PRE_CONSO",
            "description": f"Removes leading and trailing spaces from {attr}.",
            "semQlEnricherExpressions": [{"attributeName": attr, "expression": f"RTRIM(LTRIM({attr}))"}]}

# Source-ranking expression used by the CUSTOM_RANKING survivorship rules (only one PREFERRED_PUBLISHER
# rule - the default one - is allowed per entity, so the second source-ranked group ranks on PublisherID).
def rank(*pubs):
    whens = " ".join(f"WHEN '{p}' THEN {i}" for i, p in enumerate(pubs, 1))
    return f"CASE PublisherID {whens} ELSE {len(pubs) + 1} END"

NORMALIZE = ("REGEXP_REPLACE(UPPER(SEM_NORMALIZE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(AssetName, "
             "'[Ææ]', 'AE', 'g'), '[Øø]', 'O', 'g'), '[Åå]', 'AA', 'g'))), '[^A-Z0-9]', '', 'g')")

def build_model():
    lovTypes = [
        LOV("GridArea", "Grid area", 3, [
            ("DK1", "DK1 - West Denmark", "Western Danish grid area (Jutland and Funen), synchronous with Continental Europe."),
            ("DK2", "DK2 - East Denmark", "Eastern Danish grid area (Zealand and islands), synchronous with the Nordic system.")],
            "Danish bidding and synchronous area the asset belongs to."),
        LOV("VoltageLevel", "Voltage level", 3, [
            ("400", "400 kV", "Transmission backbone."), ("220", "220 kV", "Transmission level."),
            ("150", "150 kV", "Regional transmission (West Denmark)."), ("132", "132 kV", "Regional transmission (East Denmark)."),
            ("60", "60 kV", "Sub-transmission / distribution interface.")],
            AI("Nominal voltage level of a grid element.",
               "The code is the nominal voltage in kV: compare and sort numerically on the code, never on the label.")),
        LOV("OperatingStatus", "Operating status", 20, [
            ("PLANNED", "Planned", "Approved but not yet in service."),
            ("IN_SERVICE", "In service", "Energized and operated."),
            ("OUT_OF_SERVICE", "Out of service", "Temporarily disconnected (maintenance, fault)."),
            ("DECOMMISSIONED", "Decommissioned", "Permanently removed from operation.")],
            AI("Operating status of a grid element.",
               "Only IN_SERVICE elements belong to the operated grid; exclude PLANNED and DECOMMISSIONED from topology and capacity questions.")),
        LOV("AssetType", "Asset type", 30, [
            ("POWER_TRANSFORMER", "Power transformer", "Transforms power between two voltage levels."),
            ("CIRCUIT_BREAKER", "Circuit breaker", "Switches load and fault currents."),
            ("DISCONNECTOR", "Disconnector", "Provides a visible isolation point, operated off-load."),
            ("BUSBAR", "Busbar", "Collects and distributes power inside a substation."),
            ("CURRENT_TRANSFORMER", "Current transformer", "Instrument transformer for current measurement."),
            ("VOLTAGE_TRANSFORMER", "Voltage transformer", "Instrument transformer for voltage measurement."),
            ("SHUNT_REACTOR", "Shunt reactor", "Absorbs reactive power for voltage control."),
            ("CAPACITOR_BANK", "Capacitor bank", "Supplies reactive power for voltage control."),
            ("PROTECTION_RELAY", "Protection relay", "Detects faults and trips the circuit breakers.")],
            "Kind of grid equipment."),
        LOV("Criticality", "Criticality", 10, [
            ("HIGH", "High", "Failure has system-wide consequences."), ("MEDIUM", "Medium", "Failure has local consequences."),
            ("LOW", "Low", "Failure has limited consequences.")],
            "Business criticality used to prioritise maintenance."),
        LOV("LineType", "Line type", 20, [
            ("OVERHEAD", "Overhead line", "Conductors carried by towers."),
            ("UNDERGROUND_CABLE", "Underground cable", "Buried land cable."),
            ("SUBMARINE_CABLE", "Submarine cable", "Sea cable, including interconnectors.")],
            "Construction type of a transmission line."),
        LOV("MeasurementType", "Measurement type", 20, [
            ("ACTIVE_POWER", "Active power", "Real power flow (SCADA)."),
            ("REACTIVE_POWER", "Reactive power", "Reactive power flow (SCADA)."),
            ("VOLTAGE", "Voltage magnitude", "Voltage magnitude (SCADA or PMU)."),
            ("CURRENT", "Current", "Current magnitude (SCADA or PMU)."),
            ("FREQUENCY", "Frequency", "System frequency (PMU)."),
            ("PHASE_ANGLE", "Voltage phase angle", "Synchrophasor angle (PMU)."),
            ("THD", "Total harmonic distortion", "Power-quality indicator (PQ meter)."),
            ("TEMPERATURE", "Temperature", "Ambient or equipment temperature (sensor)."),
            ("OIL_TEMPERATURE", "Oil temperature", "Transformer top-oil temperature (sensor).")],
            "Physical quantity a measurement point captures."),
        LOV("Unit", "Unit", 5, [
            ("MW", "MW", "Megawatt."), ("MVAR", "Mvar", "Megavolt-ampere reactive."), ("KV", "kV", "Kilovolt."),
            ("A", "A", "Ampere."), ("HZ", "Hz", "Hertz."), ("DEG", "deg", "Angle in degrees."),
            ("PCT", "%", "Percentage."), ("DEGC", "°C", "Degree Celsius.")],
            "Engineering unit of the measured values."),
        LOV("DeviceType", "Device type", 15, [
            ("SCADA_RTU", "SCADA RTU", "Remote terminal unit scanned by SCADA (seconds)."),
            ("PMU", "PMU", "Phasor measurement unit, time-synchronised (50 frames per second)."),
            ("PQ_METER", "Power-quality meter", "Power-quality analyser (harmonics, flicker)."),
            ("IOT_SENSOR", "IoT sensor", "Condition-monitoring sensor.")],
            "Device family producing the signal."),
        LOV("Phase", "Phase", 15, [
            ("L1", "L1", "Phase 1."), ("L2", "L2", "Phase 2."), ("L3", "L3", "Phase 3."),
            ("THREE_PHASE", "Three-phase", "Aggregated over the three phases."),
            ("POS_SEQ", "Positive sequence", "Positive-sequence component, as published by PMUs.")],
            "Electrical phase of the signal."),
        LOV("AggregationInterval", "Aggregation interval", 5, [
            ("PT15M", "15 minutes", "15-minute aggregation window."), ("PT1H", "1 hour", "Hourly aggregation window.")],
            "Length of the aggregation window (ISO 8601 duration code)."),
        LOV("QualityFlag", "Quality flag", 10, [
            ("GOOD", "Good", "Value is valid."), ("SUSPECT", "Suspect", "Value may be wrong (stale, out of range)."),
            ("BAD", "Bad", "Value is invalid."), ("MISSING", "Missing", "No data for the window.")],
            AI("Historian quality of an aggregated measurement.",
               "Use only GOOD values in calculations unless the question is about data quality itself.")),
    ]

    substation = E("Substation", "Substation", "Substations", "images://mdi/office-building-cog.svg",
        AI("Physical grid node (switchyard or station) of the transmission grid, consolidated from the network "
           "model and the asset register, which share the substation code.",
           "Reason on golden records; the network model is authoritative for name, grid area, voltage and location, "
           "the asset register for status and commissioning."),
        "ID_MATCHED",
        PK("SubstationCode", "String", "MANUAL", length=30, label="Substation code",
           desc="Business key of the substation, shared by the network model and the asset register."),
        [A("SubstationName", "String", 100, True, label="Substation name", desc="Name of the substation."),
         A("GridArea", lov("GridArea"), mand=True, is_lov=True, label="Grid area", desc="Danish grid area (DK1 / DK2)."),
         A("HighestVoltageLevel", lov("VoltageLevel"), mand=True, is_lov=True, label="Highest voltage level",
           desc="Highest nominal voltage present in the substation."),
         A("Latitude", "Decimal", prec=9, scale=6, label="Latitude", desc="WGS84 latitude of the substation."),
         A("Longitude", "Decimal", prec=9, scale=6, label="Longitude", desc="WGS84 longitude of the substation."),
         A("OperatingStatus", lov("OperatingStatus"), mand=True, is_lov=True, label="Operating status",
           desc="Operating status of the substation."),
         A("CommissioningDate", "Date", label="Commissioning date", desc="Date the substation was put into service."),
         A("Description", "String", 1000, label="Description", desc="Free-text description of the substation.")],
        enrichers=[trim("Substation", "SubstationName")],
        survivorship=[
            {"_name": "TopologyFromNetworkModel", "kind": "STANDARD", "label": "Topology and naming (network model first)",
             "description": "Name, grid area, voltage level and location come from the network model first.",
             "strategy": "PREFERRED_PUBLISHER", "defaultRule": True, "publishers": ["NETMODEL", "EAM", "UI"],
             "attributes": ["SubstationName", "GridArea", "HighestVoltageLevel", "Latitude", "Longitude"],
             "override": "UNTIL_CONSOLIDATED_VAL_CHANGE"},
            {"_name": "LifecycleFromAssetRegister", "kind": "STANDARD", "label": "Lifecycle (asset register first)",
             "description": "Status, commissioning date and description come from the asset register first.",
             "strategy": "CUSTOM_RANKING", "orderBy": rank("EAM", "NETMODEL", "UI"),
             "attributes": ["OperatingStatus", "CommissioningDate", "Description"],
             "override": "UNTIL_CONSOLIDATED_VAL_CHANGE"},
            {"_name": "IdRule", "kind": "ID", "label": "Identity", "strategy": "PREFERRED_PUBLISHER",
             "publishers": ["NETMODEL", "EAM", "UI"]}],
        histG=True)

    asset = E("Asset", "Asset", "Assets", "images://mdi/flash.svg",
        AI("Grid equipment (transformer, breaker, disconnector, busbar, instrument transformer, reactor, capacitor bank, "
           "protection relay), consolidated from the network model and the asset register, which share no equipment key.",
           "Reason on golden records; master records are source contributions and are not distinct assets. "
           "NetworkModelId and EamAssetNumber trace the golden record back to each system."),
        "FUZZY_MATCHED",
        PK("AssetId", "LongInteger", "SEQUENCE", prec=18, label="Asset id", desc="Identifier generated by the platform."),
        [A("AssetName", "String", 150, True, label="Asset name", desc="Equipment designation."),
         A("AssetType", lov("AssetType"), mand=True, is_lov=True, label="Asset type", desc="Kind of equipment."),
         A("NetworkModelId", "String", 64, label="Network model id (mRID)", desc="CIM mRID of the equipment in the network model."),
         A("EamAssetNumber", "String", 30, label="EAM asset number", desc="Equipment number in the asset register."),
         A("Manufacturer", "String", 100, label="Manufacturer", desc="Original equipment manufacturer."),
         A("Model", "String", 100, label="Model", desc="Manufacturer model reference."),
         A("SerialNumber", "String", 50, label="Serial number", desc="Manufacturer serial number."),
         A("VoltageLevel", lov("VoltageLevel"), is_lov=True, label="Voltage level", desc="Rated voltage level."),
         A("RatedPowerMva", "Decimal", prec=10, scale=2, label="Rated power (MVA)",
           desc="Rated apparent power in MVA (transformers, reactors)."),
         A("CommissioningDate", "Date", label="Commissioning date", desc="Date the asset was put into service."),
         A("OperatingStatus", lov("OperatingStatus"), mand=True, is_lov=True, label="Operating status",
           desc="Operating status of the asset."),
         A("Criticality", lov("Criticality"), is_lov=True, label="Criticality", desc="Maintenance priority."),
         A("LastInspectionDate", "Date", label="Last inspection date", desc="Date of the last inspection (asset register)."),
         A("AgeYears", "Integer", prec=4, label="Age (years)",
           desc=AI("Whole years since commissioning, computed when the record is certified.",
                   "Computed at certification time, so it can lag up to a year until the record is next certified; "
                   "recompute from CommissioningDate for exact ages.")),
         A("NormalizedName", "String", 150, label="Normalized name",
           desc=AI("Upper-case name without punctuation or spaces, used to match the two sources.",
                   "Technical matching key: never display it or reason on it; use AssetName."))],
        enrichers=[
            trim("Asset", "AssetName"),
            {"qualifiedName": f"{PKG}.entities.Asset.enrichers.NormalizeName", "_type": "SemQLEnricher",
             "label": "Normalize name for matching", "enricherExecutionScope": "PRE_CONSO",
             "description": "Builds the matching key: Danish letters transliterated, accents folded, upper case, "
                            "everything but letters and digits removed.",
             "semQlEnricherExpressions": [{"attributeName": "NormalizedName", "expression": NORMALIZE}]},
            {"qualifiedName": f"{PKG}.entities.Asset.enrichers.ComputeAge", "_type": "SemQLEnricher",
             "label": "Compute age", "enricherExecutionScope": "POST_CONSO",
             "description": "Whole years between the commissioning date and the certification date.",
             "semQlEnricherExpressions": [{"attributeName": "AgeYears",
                 "expression": "SEM_CAST_INTEGER(DATE_PART('year', AGE(NOW(), CommissioningDate)))"}]}],
        validations=[V("SourceIdentifier", "Source identifier required",
                       "NetworkModelId IS NOT NULL OR EamAssetNumber IS NOT NULL",
                       "An asset needs a network model id (mRID) or an EAM asset number.",
                       "Every asset must be traceable to at least one source system.")],
        survivorship=[
            {"_name": "LifecycleFromAssetRegister", "kind": "STANDARD", "label": "Lifecycle (asset register first)",
             "description": "Lifecycle and technical attributes come from the asset register first.",
             "strategy": "PREFERRED_PUBLISHER", "defaultRule": True, "publishers": ["EAM", "NETMODEL", "UI"],
             "attributes": ["EamAssetNumber", "Manufacturer", "Model", "SerialNumber", "RatedPowerMva",
                            "CommissioningDate", "OperatingStatus", "Criticality", "LastInspectionDate"],
             "override": "UNTIL_CONSOLIDATED_VAL_CHANGE"},
            {"_name": "TopologyFromNetworkModel", "kind": "STANDARD", "label": "Topology and naming (network model first)",
             "description": "Name, mRID, voltage level and type come from the network model first.",
             "strategy": "CUSTOM_RANKING", "orderBy": rank("NETMODEL", "EAM", "UI"),
             "attributes": ["AssetName", "NetworkModelId", "VoltageLevel", "AssetType"],
             "override": "UNTIL_CONSOLIDATED_VAL_CHANGE"},
            {"_name": "SubstationFromNetworkModel", "kind": "STANDARD", "label": "Substation (network model first)",
             "description": "The substation an asset belongs to is owned by the network model and cannot be overridden.",
             "strategy": "CUSTOM_RANKING", "orderBy": rank("NETMODEL", "EAM", "UI"),
             "attributes": ["Substation"], "override": "NO_OVERRIDE"},
            {"_name": "IdRule", "kind": "ID", "label": "Identity", "strategy": "PREFERRED_PUBLISHER",
             "publishers": ["NETMODEL", "EAM", "UI"]}],
        histG=True, histM=True)

    line = E("TransmissionLine", "Transmission line", "Transmission lines", "images://mdi/transmission-tower.svg",
        AI("Overhead line or cable connecting two substations, from the authoritative network model.",
           "A line is undirected electrically: From and To only record the modelling direction, so look at both "
           "sides when asking which lines connect a substation."),
        "BASIC",
        PK("LineCode", "String", "MANUAL", length=40, label="Line code", desc="Business key of the line in the network model."),
        [A("LineName", "String", 150, True, label="Line name", desc="Name of the line."),
         A("LineType", lov("LineType"), mand=True, is_lov=True, label="Line type", desc="Overhead line or cable."),
         A("VoltageLevel", lov("VoltageLevel"), mand=True, is_lov=True, label="Voltage level", desc="Operating voltage of the line."),
         A("LengthKm", "Decimal", prec=8, scale=2, label="Length (km)", desc="Circuit length in kilometres."),
         A("RatedCapacityMva", "Decimal", prec=10, scale=2, label="Rated capacity (MVA)", desc="Thermal rating in MVA."),
         A("OperatingStatus", lov("OperatingStatus"), mand=True, is_lov=True, label="Operating status",
           desc="Operating status of the line.")],
        enrichers=[trim("TransmissionLine", "LineName")],
        validations=[
            V("DistinctEndpoints", "Distinct endpoints",
              "FID_FromSubstation IS NULL OR FID_ToSubstation IS NULL OR FID_FromSubstation <> FID_ToSubstation",
              "A line must connect two different substations.", "A line cannot start and end in the same substation."),
            V("PositiveLength", "Positive length", "LengthKm IS NULL OR LengthKm > 0",
              "The line length must be greater than zero.", "The circuit length, when known, is positive.")],
        histG=True)

    point = E("MeasurementPoint", "Measurement point", "Measurement points", "images://mdi/gauge.svg",
        AI("Catalogue entry of one measured signal (SCADA point, PMU channel, power-quality meter or sensor): what is "
           "measured, where, by which device, in which unit and at which rate. It links an operational data stream "
           "to its network context.",
           "The raw stream stays in the historian under the same PointTag; this record describes it. The unit of every "
           "value of the point is the Unit attribute."),
        "BASIC",
        PK("PointTag", "String", "MANUAL", length=80, label="Point tag", desc="SCADA / PMU tag of the signal."),
        [A("PointName", "String", 150, True, label="Point name", desc="Human-readable signal name."),
         A("MeasurementType", lov("MeasurementType"), mand=True, is_lov=True, label="Measurement type", desc="Measured quantity."),
         A("Unit", lov("Unit"), mand=True, is_lov=True, label="Unit", desc="Engineering unit."),
         A("DeviceType", lov("DeviceType"), mand=True, is_lov=True, label="Device type", desc="Device producing the signal."),
         A("Phase", lov("Phase"), is_lov=True, label="Phase", desc="Electrical phase of the signal."),
         A("SamplingIntervalMs", "Integer", prec=9, label="Sampling interval (ms)",
           desc="Interval between two raw samples in milliseconds (e.g. 2000 for SCADA, 20 for PMU)."),
         A("AlarmLowLimit", "Decimal", prec=14, scale=4, label="Alarm low limit", desc="Lower operating limit, in the point's unit."),
         A("AlarmHighLimit", "Decimal", prec=14, scale=4, label="Alarm high limit", desc="Upper operating limit, in the point's unit."),
         A("Active", "Boolean", mand=True, label="Active", desc="The point is currently scanned.")],
        enrichers=[trim("MeasurementPoint", "PointName")],
        validations=[V("AlarmLimitsOrdered", "Alarm limits ordered",
                       "AlarmLowLimit IS NULL OR AlarmHighLimit IS NULL OR AlarmLowLimit < AlarmHighLimit",
                       "The alarm low limit must be lower than the high limit.",
                       "Operating limits must define a non-empty range.")],
        histG=True)

    meas = E("Measurement", "Measurement", "Measurements", "images://mdi/chart-line.svg",
        AI("Aggregated value window (average, minimum, maximum, quality) of a measurement point, loaded from the "
           "operational historian.",
           "These are aggregates, not raw samples: never sum averages across windows; weight by window length. "
           "Read the unit from the measurement point."),
        "BASIC",
        PK("MeasurementId", "LongInteger", "SEQUENCE", prec=18, label="Measurement id", desc="Identifier generated by the platform."),
        [A("PeriodStart", "Timestamp", mand=True, prec=6, label="Period start", desc="Start of the aggregation window (UTC)."),
         A("AggregationInterval", lov("AggregationInterval"), mand=True, is_lov=True, label="Aggregation interval",
           desc="Length of the aggregation window."),
         A("AvgValue", "Decimal", prec=16, scale=4, mand=True, label="Average value", desc="Average over the window."),
         A("MinValue", "Decimal", prec=16, scale=4, label="Minimum value", desc="Minimum over the window."),
         A("MaxValue", "Decimal", prec=16, scale=4, label="Maximum value", desc="Maximum over the window."),
         A("QualityFlag", lov("QualityFlag"), mand=True, is_lov=True, label="Quality flag", desc="Historian quality of the window.")],
        validations=[V("ValueRange", "Consistent value range",
                       "(MinValue IS NULL OR MinValue <= AvgValue) AND (MaxValue IS NULL OR AvgValue <= MaxValue)",
                       "Minimum <= average <= maximum must hold.", "Aggregates that break min <= avg <= max are corrupt.")])

    refs = [
        R("AssetInSubstation", "Asset", "Substation", "Assets", "Assets", "Substation", "Substation", "SUBSTATION_REF",
          "Asset - Substation", "The substation an asset is installed in.", mand=True),
        R("PointInSubstation", "MeasurementPoint", "Substation", "MeasurementPoints", "Measurement points",
          "Substation", "Substation", "SUBSTATION_REF", "Measurement point - Substation", "Where the signal is measured.", mand=True),
        R("PointMeasuresAsset", "MeasurementPoint", "Asset", "MeasurementPoints", "Measurement points",
          "Asset", "Asset", "ASSET_REF", "Measurement point - Asset", "The equipment the signal measures (empty for station-level points)."),
        R("PointOnLine", "MeasurementPoint", "TransmissionLine", "MeasurementPoints", "Measurement points",
          "TransmissionLine", "Transmission line", "LINE_REF", "Measurement point - Line", "Line-end measurement (power flow, phasors)."),
        R("MeasurementOfPoint", "Measurement", "MeasurementPoint", "Measurements", "Measurements",
          "MeasurementPoint", "Measurement point", "POINT_REF", "Measurement - Measurement point",
          "The measurement point an aggregated value belongs to.", mand=True, delete="CASCADE"),
        R("LineFromSubstation", "TransmissionLine", "Substation", "OutgoingLines", "Outgoing lines",
          "FromSubstation", "From substation", "FROM_SUBST_REF", "Line - From substation", "Modelling start of the line.", mand=True),
        R("LineToSubstation", "TransmissionLine", "Substation", "IncomingLines", "Incoming lines",
          "ToSubstation", "To substation", "TO_SUBST_REF", "Line - To substation", "Modelling end of the line.", mand=True),
    ]
    return {"entities": [substation, asset, line, point, meas], "referenceRels": refs, "lovTypes": lovTypes}

def T(name, label, path, target):
    return {"_name": name, "label": label, "path": path, "type": "FULLY_QUALIFIED", "target": eqn(target)}

CFG = {
    "pkg": PKG, "src": SRC, "seml_version": "2.1", "design_language": "en", "databaseType": "POSTGRESQL",
    "description": AI(
        "Grid asset and measurement context data product of a transmission system operator: substations, grid "
        "equipment, transmission lines (topology from the network model), the catalogue of measurement points "
        "(SCADA, PMU, power-quality and sensor signals) and their 15-minute aggregates. Consumers: control-centre "
        "applications, operational planning, analytics and asset management.",
        "Reason on golden records. Measurements are aggregates; raw streams stay in the operational historian "
        "under the measurement point tag. Units come from the measurement point."),
    "fuzzy": {"Asset": {
        "rules": [
            {"_name": "SerialAndManufacturer", "label": "Same serial number and manufacturer", "color": "md:green 800",
             "matchScore": 100,
             "condition": ("Record1.SerialNumber IS NOT NULL AND Record1.Manufacturer IS NOT NULL AND "
                           "UPPER(Record1.SerialNumber) = UPPER(Record2.SerialNumber) AND "
                           "UPPER(Record1.Manufacturer) = UPPER(Record2.Manufacturer)"),
             "binning": ["UPPER(SerialNumber)"],
             "description": "Same manufacturer serial number from the same manufacturer: the same physical equipment. Merged automatically."},
            {"_name": "SameBayNameClose", "label": "Same substation and type, similar name", "color": "md:amber 700",
             "matchScore": 80,
             "condition": ("Record1.FID_Substation = Record2.FID_Substation AND Record1.AssetType = Record2.AssetType AND "
                           "SEM_EDIT_DISTANCE_SIMILARITY(Record1.NormalizedName, Record2.NormalizedName) >= 85"),
             "binning": ["FID_Substation", "AssetType"],
             "description": "Same substation, same equipment type and a close name: suggested to the data steward, never merged automatically."}],
        "mergeThreshold": 90, "transitive": True, "multiIteration": True}},
    "publishers": [("NETMODEL", "Network model"), ("EAM", "Asset register (EAM)"), ("SCADA", "SCADA / PMU point list"),
                   ("HISTORIAN", "Measurement historian"), ("UI", "Manual entry (data steward)")],
    "workflow_entities": [],
    "workflow_actions": {"Asset": [{"_name": "StartApproval", "label": "Submit for approval",
                                    "startEvent": f"{PKG}.workflows.AssetChangeApproval.Start"}]},
    "core": ["Substation", "Asset", "TransmissionLine", "MeasurementPoint", "Measurement"],
    "reference_ent": [],
    "job_order": ["Substation", "TransmissionLine", "Asset", "MeasurementPoint", "Measurement"],
    "lineage_views": ["Substation", "Asset"],
    "id_columns": ["Substation", "Asset"],
    "bv_transitions": {
        "Substation": [T("AssetsTab", "Assets", "Assets", "Asset"),
                       T("PointsTab", "Measurement points", "MeasurementPoints", "MeasurementPoint"),
                       T("OutgoingLinesTab", "Outgoing lines", "OutgoingLines", "TransmissionLine"),
                       T("IncomingLinesTab", "Incoming lines", "IncomingLines", "TransmissionLine")],
        "Asset": [T("PointsTab", "Measurement points", "MeasurementPoints", "MeasurementPoint")],
        "TransmissionLine": [T("PointsTab", "Measurement points", "MeasurementPoints", "MeasurementPoint")],
        "MeasurementPoint": [T("MeasurementsTab", "Measurements", "Measurements", "Measurement")]},
    "display_text": {"Measurement": "FID_MeasurementPoint || ' @ ' || SEM_CAST_STRING(PeriodStart)"},
    "form_layout_strict": True,
    "form_layout": {
        "Substation": [("Identification", ["SubstationCode", "SubstationName", "GridArea", "HighestVoltageLevel"]),
                       ("Location", ["Latitude", "Longitude"]),
                       ("Lifecycle", ["OperatingStatus", "CommissioningDate", "Description"])],
        "Asset": [("Identification", ["AssetName", "AssetType", "FDN_Substation", "Criticality"]),
                  ("Technical data", ["Manufacturer", "Model", "SerialNumber", "VoltageLevel", "RatedPowerMva"]),
                  ("Lifecycle", ["OperatingStatus", "CommissioningDate", "AgeYears", "LastInspectionDate"]),
                  ("Source identifiers", ["NetworkModelId", "EamAssetNumber"])],
        "TransmissionLine": [("Identification", ["LineCode", "LineName", "LineType"]),
                             ("Topology", ["FDN_FromSubstation", "FDN_ToSubstation"]),
                             ("Technical data", ["VoltageLevel", "LengthKm", "RatedCapacityMva", "OperatingStatus"])],
        "MeasurementPoint": [("Identification", ["PointTag", "PointName", "Active"]),
                             ("Signal", ["MeasurementType", "Unit", "DeviceType", "Phase", "SamplingIntervalMs"]),
                             ("Context", ["FDN_Substation", "FDN_Asset", "FDN_TransmissionLine"]),
                             ("Limits", ["AlarmLowLimit", "AlarmHighLimit"])],
        "Measurement": [("Measurement", ["FDN_MeasurementPoint", "PeriodStart", "AggregationInterval",
                                         "AvgValue", "MinValue", "MaxValue", "QualityFlag"])]},
    # Dashboard application ENERGINETAnalytics (resources/dashboards/, spec output/dashboards/) - import it BEFORE
    # deploying a data product that links to it. Embed names end in "Dashboard" so they never collide with a transition.
    "form_embeds": {"Substation": [
        {"_name": "ScorecardDashboard", "application": "ENERGINETAnalytics", "dashboard": "SubstationScorecard",
         "tab": "Scorecard", "parameters": [{"name": "SubstationCode", "value": "SubstationCode"}],
         "form_tab": "Scorecard", "icon": "images://mdi/card-account-details.svg", "height": 1100}]},
    "diagram": {"label": "Grid asset data product", "description": "Entities and relationships of the ENERGINET data product."},
    "diagram_colors": {"Substation": "#1565c0", "Asset": "#6a1b9a", "TransmissionLine": "#00838f",
                       "MeasurementPoint": "#2e7d32", "Measurement": "#ef6c00"},
    "app": {"name": PKG, "label": "Grid Asset Data Product", "title": "Grid Asset Data Product",
            "documentation": "Application of the grid asset and measurement context data product: maintain, govern and consume "
                             "substations, assets, lines and measurement points.",
            "browsers": ["Substation", "Asset", "TransmissionLine", "MeasurementPoint"],
            "dashboards": [
                {"_name": "DataProductQualityDashboard", "label": "Data product quality",
                 "application": "ENERGINETAnalytics", "dashboard": "GridDataQuality",
                 "description": "Consolidation, match and merge, sources, rejections and warnings of the data product",
                 "icon": "images://mdi/check-decagram.svg", "iconColor": "md:indigo"},
                {"_name": "GridContextDashboard", "label": "Grid context",
                 "application": "ENERGINETAnalytics", "dashboard": "GridContext",
                 "description": "Assets, measurement points and measurement quality across the grid",
                 "icon": "images://mdi/transmission-tower.svg", "iconColor": "md:blue"}],
            "nav_labels_visible": True, "history_browsing": True,
            "error_views": ["Substation", "Asset", "TransmissionLine", "MeasurementPoint", "Measurement"],
            "matching_review": ["Asset"],
            # Warning-level rules of the specification (§4.2): non-blocking, so they are stewardship queues.
            "worklists": [
                {"entity": "Substation", "_name": "SubstationOutsideDenmark", "label": "Location outside Denmark",
                 "condition": "Latitude < 54 OR Latitude > 58 OR Longitude < 7.5 OR Longitude > 15.5",
                 "description": "Substations whose coordinates fall outside Denmark: swapped or wrongly projected coordinates.",
                 "icon": "images://mdi/map-marker-alert.svg", "color": "md:orange"},
                {"entity": "Asset", "_name": "AssetFutureCommissioning", "label": "In service, commissioned in the future",
                 "condition": "OperatingStatus = 'IN_SERVICE' AND CommissioningDate > NOW()",
                 "description": "In-service assets whose commissioning date lies in the future.",
                 "icon": "images://mdi/calendar-alert.svg", "color": "md:orange"},
                {"entity": "MeasurementPoint", "_name": "PointAssetElsewhere", "label": "Asset in another substation",
                 "condition": "FID_Asset IS NOT NULL AND Asset.FID_Substation <> FID_Substation",
                 "description": "Measurement points whose measured asset sits in a different substation than the point.",
                 "icon": "images://mdi/link-variant-off.svg", "color": "md:orange"}],
            "quick_links_label": "Quick access", "search_desc": "Search the data product", "mytasks_desc": "My tasks",
            "core_group": {"label": "Grid", "icon": "images://mdi/transmission-tower.svg", "color": "md:blue"},
            "ref_group": {"label": "Reference data", "icon": "images://mdi/folder.svg", "color": "md:teal"},
            "stewardship_label": "Data stewardship", "errors_label": "Records in error",
            "admin_label": "Administration", "admin_desc": "Administrative tasks", "model_doc_label": "Data product documentation",
            "import_folder_label": "Data import", "import_label": "Import", "browse_desc_prefix": "Browse"},
    "grants": [
        {"role": "SemAdmin", "roleName": "semarchyAdmin", "label": "Semarchy administrator",
         "desc": "Platform administrators: full access, data administration and loads.",
         "entities": "ALL", "access": "READ_WRITE", "integrationWsRole": True, "dataAdminRole": True},
        {"role": "GridDataOwner", "label": "Grid data owner",
         "desc": "Accountable for the data product: approves asset changes, full read/write access.",
         "entities": "ALL", "access": "READ_WRITE", "dataAdminRole": True},
        {"role": "GridDataSteward", "label": "Grid data steward",
         "desc": "Maintains substations, assets, lines and measurement points; reviews duplicates; reads measurements.",
         "entities": "ALL", "access": "READ_WRITE", "entity_access": {"Measurement": "READ"}},
        {"role": "GridIntegration", "label": "Grid integration service",
         "desc": "Technical role of the source feeds calling the loads API.",
         "entities": "ALL", "access": "READ_WRITE", "integrationWsRole": True},
        {"role": "GridDataConsumer", "label": "Grid data consumer",
         "desc": "Read-only access for control-centre, planning, analytics and asset-management consumers.",
         "entities": "ALL", "access": "READ"}],
}

def load_source(*rel):
    import yaml
    with open(os.path.join(SOURCES, *rel), encoding="utf-8") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    engine.generate(build_model(), CFG,
                    extra_workflows=[load_source("workflows", "AssetChangeApproval.Workflow.seml")])
