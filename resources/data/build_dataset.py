#!/usr/bin/env python3
"""Build the ENERGINET demo dataset (FICTIONAL data) as CSV files, one per entity and source system.

Every substation, line, asset and signal below is invented: names are Danish-sounding but fictional,
coordinates are plausible points in Denmark, serial numbers are random. Deterministic (fixed seed).

Planted cases (what the demo shows) - see README.md for the expected counts:
  - Substation SUB-HAV: latitude/longitude swapped in the network model -> worklist "Location outside Denmark"
  - Line LN-150-LYN-LYN: same substation at both ends -> rejected (blocking validation)
  - Transformers: same serial + manufacturer in NETMODEL and EAM -> merged automatically (score 100)
  - Breakers: same bay, name spelled differently in each source -> suggested match for the steward (score 80)
  - EAM asset with neither mRID nor EAM number -> rejected
  - In-service EAM asset commissioned in the future -> worklist
  - Measurement point with alarm low > high -> rejected
  - Measurement point whose asset sits in another substation -> worklist
  - One measurement with min > avg -> rejected; a few SUSPECT / MISSING quality flags

  python resources/data/build_dataset.py
"""
import csv, math, os, random
from datetime import datetime, timedelta, timezone

random.seed(20261015)
OUT = os.path.dirname(os.path.abspath(__file__))

# code, NETMODEL name, EAM name, grid area, highest kV, lat, lon
SUBS = [
    ("SUB-NOR", "Nordvig", "NORDVIG", "DK1", "400", 57.2101, 9.9302),
    ("SUB-OST", "Østerby", "OSTERBY", "DK1", "400", 56.4512, 10.0124),
    ("SUB-KRA", "Kragholm", "KRAGHOLM", "DK1", "150", 55.8733, 9.1840),
    ("SUB-VES", "Vesterlund", "VESTERLUND", "DK1", "400", 55.4920, 8.6101),
    ("SUB-BAK", "Bakkedal", "BAKKEDAL", "DK1", "150", 55.3304, 10.3912),
    ("SUB-STR", "Strandhøj", "STRANDHOJ", "DK2", "400", 55.6402, 11.8125),
    ("SUB-LYN", "Lyngmose", "LYNGMOSE", "DK2", "132", 55.9015, 12.2733),
    ("SUB-FJO", "Fjordby", "FJORDBY", "DK2", "400", 55.7311, 12.1602),
    ("SUB-HAV", "Havrevang", "HAVREVANG", "DK2", "132", 55.4105, 12.0418),
    ("SUB-SKA", "Skærbæk Øst", "SKAERBAEK OEST", "DK2", "132", 55.2201, 11.7608),
]
SUBNAME = {s[0]: s[1] for s in SUBS}
# code, from, to, kV, type, km, MVA
LINES = [
    ("LN-400-NOR-OST", "SUB-NOR", "SUB-OST", "400", "OVERHEAD", 98.4, 1800),
    ("LN-400-OST-VES", "SUB-OST", "SUB-VES", "400", "OVERHEAD", 121.0, 1800),
    ("LN-150-OST-KRA", "SUB-OST", "SUB-KRA", "150", "OVERHEAD", 72.6, 400),
    ("LN-150-KRA-VES", "SUB-KRA", "SUB-VES", "150", "UNDERGROUND_CABLE", 54.2, 350),
    ("LN-150-KRA-BAK", "SUB-KRA", "SUB-BAK", "150", "OVERHEAD", 88.9, 400),
    ("LN-400-VES-BAK", "SUB-VES", "SUB-BAK", "400", "OVERHEAD", 112.3, 1800),
    ("LN-400-BAK-STR", "SUB-BAK", "SUB-STR", "400", "SUBMARINE_CABLE", 58.0, 600),
    ("LN-400-STR-FJO", "SUB-STR", "SUB-FJO", "400", "OVERHEAD", 31.7, 1800),
    ("LN-132-FJO-LYN", "SUB-FJO", "SUB-LYN", "132", "UNDERGROUND_CABLE", 19.8, 250),
    ("LN-132-STR-HAV", "SUB-STR", "SUB-HAV", "132", "OVERHEAD", 42.5, 250),
    ("LN-132-HAV-SKA", "SUB-HAV", "SUB-SKA", "132", "OVERHEAD", 27.3, 250),
    ("LN-132-SKA-STR", "SUB-SKA", "SUB-STR", "132", "UNDERGROUND_CABLE", 33.1, 250),
    ("LN-132-LYN-HAV", "SUB-LYN", "SUB-HAV", "132", "OVERHEAD", 61.0, 250),
    ("LN-400-NOR-VES", "SUB-NOR", "SUB-VES", "400", "OVERHEAD", 189.5, 1800),
]
BAD_LINE = ("LN-150-LYN-LYN", "SUB-LYN", "SUB-LYN", "132", "OVERHEAD", 4.2, 250)  # planted: same endpoints
MAKERS = ["Nordtrafo A/S", "Voltaro GmbH", "Hexagrid AB", "Ampera SpA"]
BREAKER_MAKERS = ["Voltaro GmbH", "Hexagrid AB"]

def w(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f); wr.writerow(header); wr.writerows(rows)
    print(f"{name}: {len(rows)} rows")

def mrid():
    return "_" + "".join(random.choice("0123456789abcdef") for _ in range(8)) + "-" + \
           "".join(random.choice("0123456789abcdef") for _ in range(4)) + "-4" + \
           "".join(random.choice("0123456789abcdef") for _ in range(3))

def sday(y0, y1):
    d = datetime(y0, 1, 1) + timedelta(days=random.randint(0, (y1 - y0) * 365))
    return d.strftime("%Y-%m-%d")

# ---------------- Substations ----------------
sub_nm, sub_eam = [], []
for code, nm, eam, area, kv, lat, lon in SUBS:
    la, lo = (lon, lat) if code == "SUB-HAV" else (lat, lon)       # planted swap in the network model
    sub_nm.append([code, nm, area, kv, la, lo, "IN_SERVICE", "", ""])
    sub_eam.append([code, eam.title(), area, kv, "", "", "IN_SERVICE", sday(1968, 2015),
                    f"{kv} kV substation {nm}, maintained by the regional asset team."])
SUBH = ["SubstationCode", "SubstationName", "GridArea", "HighestVoltageLevel", "Latitude", "Longitude",
        "OperatingStatus", "CommissioningDate", "Description"]
w("01_Substation_NETMODEL.csv", SUBH, sub_nm)
w("02_Substation_EAM.csv", SUBH, sub_eam)

# ---------------- Lines ----------------
w("03_TransmissionLine_NETMODEL.csv",
  ["LineCode", "LineName", "LineType", "VoltageLevel", "LengthKm", "RatedCapacityMva", "OperatingStatus",
   "FID_FromSubstation", "FID_ToSubstation"],
  [[c, f"{SUBNAME[f]} - {SUBNAME[t]} {kv} kV", typ, kv, km, mva, "IN_SERVICE", f, t]
   for c, f, t, kv, typ, km, mva in LINES + [BAD_LINE]])

# ---------------- Assets ----------------
AH = ["SourceID", "AssetName", "AssetType", "NetworkModelId", "EamAssetNumber", "Manufacturer", "Model",
      "SerialNumber", "VoltageLevel", "RatedPowerMva", "CommissioningDate", "OperatingStatus", "Criticality",
      "LastInspectionDate", "FID_Substation"]
a_nm, a_eam = [], []
nm_asset = {}            # (sub, key) -> NETMODEL SourceID, for the measurement points
eam_no = 100000
def next_eam():
    global eam_no; eam_no += 7; return f"EQ{eam_no}"

def translit(s):
    return (s.upper().replace("Ø", "O").replace("Æ", "AE").replace("Å", "AA"))

for code, nm, eam, area, kv, lat, lon in SUBS:
    low = {"400": "150", "150": "60", "132": "60"}[kv]
    # transformer: both sources know the nameplate -> exact merge on serial + manufacturer
    maker = random.choice(MAKERS); serial = f"TR{random.randint(100000, 999999)}"
    mva = random.choice([250, 300, 450, 500]) if kv == "400" else random.choice([60, 80, 100])
    m = mrid(); en = next_eam(); comm = sday(1975, 2018)
    a_nm.append([m, f"T1 {kv}/{low} kV transformer {nm}", "POWER_TRANSFORMER", m, "", maker, "", serial, kv, mva,
                 "", "IN_SERVICE", "", "", code])
    a_eam.append([en, f"Power transformer T1 {translit(nm)}", "POWER_TRANSFORMER", "", en, maker.upper(),
                  f"{maker.split()[0][:3].upper()}-{mva}", serial.lower(), kv, mva, comm, "IN_SERVICE", "HIGH",
                  sday(2023, 2026), code])
    nm_asset[(code, "T1")] = m
    # busbar: network model only
    m = mrid(); a_nm.append([m, f"BB1 {kv} kV busbar {nm}", "BUSBAR", m, "", "", "", "", kv, "", "", "IN_SERVICE", "", "", code])
    nm_asset[(code, "BB1")] = m
    # protection relay: asset register only
    en = next_eam()
    a_eam.append([en, f"Protection relay F1 {translit(nm)}", "PROTECTION_RELAY", "", en, "Relaytech ApS",
                  "RT-700", f"RL{random.randint(10000, 99999)}", kv, "", sday(2005, 2022), "IN_SERVICE", "MEDIUM",
                  sday(2024, 2026), code])
# breakers: one per line end; same bay, spelled differently in each source -> similarity match (review)
for i, (lc, f, t, kv, typ, km, mva) in enumerate(LINES):
    for q, (here, there) in enumerate(((f, t), (t, f)), 1):
        bay = f"Q{i + 1}{q}"
        m = mrid(); en = next_eam(); maker = random.choice(BREAKER_MAKERS)
        a_nm.append([m, f"CB {bay} {SUBNAME[there]} {kv}kV", "CIRCUIT_BREAKER", m, "", "", "", "", kv, "", "",
                     "IN_SERVICE", "", "", here])
        a_eam.append([en, f"CB-{bay} {translit(SUBNAME[there])} {kv} KV", "CIRCUIT_BREAKER", "", en, maker,
                      "HB-420" if kv == "400" else "HB-170", f"CB{random.randint(100000, 999999)}", kv, "",
                      sday(1990, 2020), "IN_SERVICE", "HIGH" if kv == "400" else "MEDIUM", sday(2023, 2026), here])
        nm_asset[(here, lc)] = m
# planted: no identifier at all (rejected) and a future commissioning date (worklist)
a_eam.append(["EAM-NOID-1", "Capacitor bank C1 LYNGMOSE", "CAPACITOR_BANK", "", "", "Ampera SpA", "CB-50",
              "CAP55120", "132", 50, "2014-05-01", "IN_SERVICE", "LOW", "2025-09-12", "SUB-LYN"])
en = next_eam()
a_eam.append([en, "Shunt reactor R1 FJORDBY", "SHUNT_REACTOR", "", en, "Nordtrafo A/S", "SR-120", "SR880211",
              "400", 120, "2027-03-01", "IN_SERVICE", "HIGH", "", "SUB-FJO"])
w("04_Asset_NETMODEL.csv", AH, a_nm)
w("05_Asset_EAM.csv", AH, a_eam)

# ---------------- Measurement points ----------------
PH = ["PointTag", "PointName", "MeasurementType", "Unit", "DeviceType", "Phase", "SamplingIntervalMs",
      "AlarmLowLimit", "AlarmHighLimit", "Active", "FID_Substation", "SourceID_Asset", "PublisherID_Asset",
      "FID_TransmissionLine"]
pts = []
prof = {}  # tag -> (type, base, amplitude, noise)
def pt(tag, name, mtype, unit, dev, phase, ms, lo, hi, sub, asset=None, line=None, base=0, amp=0, noise=0):
    pts.append([tag, name, mtype, unit, dev, phase, ms, lo, hi, "true", sub, asset or "",
                "NETMODEL" if asset else "", line or ""])
    prof[tag] = (mtype, base, amp, noise)

for code, nm, eam, area, kv, lat, lon in SUBS:
    k = code[4:]; t1 = nm_asset[(code, "T1")]; bb = nm_asset[(code, "BB1")]; kvf = float(kv)
    pt(f"{k}.T1.P.MW", f"{nm} T1 active power", "ACTIVE_POWER", "MW", "SCADA_RTU", "THREE_PHASE", 2000,
       -400, 400, code, t1, base=120 if kv == "400" else 40, amp=60 if kv == "400" else 20, noise=4)
    pt(f"{k}.T1.Q.MVAR", f"{nm} T1 reactive power", "REACTIVE_POWER", "MVAR", "SCADA_RTU", "THREE_PHASE", 2000,
       -150, 150, code, t1, base=15, amp=10, noise=2)
    pt(f"{k}.T1.OIL.TEMP", f"{nm} T1 top-oil temperature", "OIL_TEMPERATURE", "DEGC", "IOT_SENSOR", "", 60000,
       -20, 95, code, t1, base=48, amp=9, noise=0.6)
    pt(f"{k}.BB1.U.KV", f"{nm} busbar voltage", "VOLTAGE", "KV", "SCADA_RTU", "THREE_PHASE", 2000,
       round(kvf * 0.9, 1), round(kvf * 1.1, 1), code, bb, base=kvf * 1.01, amp=kvf * 0.01, noise=kvf * 0.002)
    pt(f"{k}.PMU.F.HZ", f"{nm} frequency (PMU)", "FREQUENCY", "HZ", "PMU", "POS_SEQ", 20,
       49.8, 50.2, code, base=50.0, amp=0.02, noise=0.008)
    pt(f"{k}.PQ.THD.PCT", f"{nm} voltage THD", "THD", "PCT", "PQ_METER", "THREE_PHASE", 200,
       0, 3, code, base=1.4, amp=0.4, noise=0.1)
for lc, f, t, kv, typ, km, mva in LINES:
    k = f[4:]
    pt(f"{k}.{lc}.P.MW", f"{SUBNAME[f]} line {lc} active power", "ACTIVE_POWER", "MW", "SCADA_RTU", "THREE_PHASE",
       2000, -mva, mva, f, nm_asset[(f, lc)], lc, base=mva * 0.35, amp=mva * 0.15, noise=mva * 0.01)
    if kv == "400":
        pt(f"{k}.{lc}.PMU.ANG", f"{SUBNAME[f]} line {lc} voltage angle (PMU)", "PHASE_ANGLE", "DEG", "PMU",
           "POS_SEQ", 20, -60, 60, f, None, lc, base=12, amp=6, noise=0.3)
# planted: inverted alarm limits (rejected - no measurements generated for it)
pts.append(["KRA.T1.AMB.TEMP", "Kragholm ambient temperature", "TEMPERATURE", "DEGC", "IOT_SENSOR", "",
            60000, 40, -25, "true", "SUB-KRA", "", "", ""])
# planted: asset in another substation (worklist) - a Bakkedal point pointing at the Kragholm transformer
pt("BAK.T1.TAP.TEMP", "Bakkedal T1 winding temperature", "TEMPERATURE", "DEGC", "IOT_SENSOR", "", 60000,
   -20, 110, "SUB-BAK", nm_asset[("SUB-KRA", "T1")], base=55, amp=8, noise=0.5)
w("06_MeasurementPoint_SCADA.csv", PH, pts)

# ---------------- Measurements (15-min aggregates, one day) ----------------
MH = ["PeriodStart", "AggregationInterval", "AvgValue", "MinValue", "MaxValue", "QualityFlag", "FID_MeasurementPoint"]
day = datetime(2026, 10, 14, tzinfo=timezone.utc)
rows = []
for tag, (mtype, base, amp, noise) in prof.items():
    for n in range(96):
        ts = day + timedelta(minutes=15 * n)
        load = math.sin((n / 96) * 2 * math.pi - math.pi / 2)        # night low, afternoon high
        avg = base + amp * load + random.gauss(0, noise)
        spread = abs(noise) * 2 + abs(amp) * 0.03
        mn, mx = avg - random.uniform(0, spread), avg + random.uniform(0, spread)
        q = "GOOD"
        if random.random() < 0.004: q = "SUSPECT"
        if random.random() < 0.002: q = "MISSING"
        rows.append([ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "PT15M", round(avg, 4), round(mn, 4), round(mx, 4), q, tag])
# planted: min greater than avg (rejected)
bad = rows[500][:]; bad[0] = (day + timedelta(minutes=15 * 96)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
bad[3] = round(float(bad[2]) + 5, 4); rows.append(bad)
w("07_Measurement_HISTORIAN.csv", MH, rows)
