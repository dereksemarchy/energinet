#!/usr/bin/env python3
"""Load the ENERGINET demo dataset (CSV, fictional) into a data location through the REST loads API.

CREATE_LOAD -> PERSIST_DATA (per file, chunked) -> SUBMIT (INGEST_ALL), one load per dependency level,
each one waited for (loadStatus terminal) before the next is submitted:

  level 1  Substation (ID-matched: NETMODEL + EAM masters)
  level 2  TransmissionLine (basic) + Asset (fuzzy: NETMODEL + EAM masters)
  level 3  MeasurementPoint (basic; asset referenced by its SOURCE key SourceID_Asset + PublisherID_Asset)
  level 4  Measurement (basic, 15-min aggregates)

Separate levels avoid the "parent certified in the same batch is not visible yet" trap.
File name convention: NN_<Entity>_<PUBLISHER>.csv. Empty CSV cells are omitted from the payload.

Auth: --api-key (a key whose role holds integrationWsRole in the data product grants) or a bearer token
(`sem auth token | head -1`); a value shaped like a JWT is sent as a Bearer. Stdlib only.

  python resources/data/load_datasets.py --url https://<tenant> --data-location <DL> --api-key <key> [--dry-run]
"""
import argparse, csv, glob, json, os, sys, time, urllib.error, urllib.request

PROGRAM = "energinet-demo-data"
JOB = "INGEST_ALL"
LEVEL = {"Substation": 1, "TransmissionLine": 2, "Asset": 2, "MeasurementPoint": 3, "Measurement": 4}
MATCHED = {"Substation", "Asset"}
NUMERIC = {"Latitude", "Longitude", "RatedPowerMva", "LengthKm", "RatedCapacityMva", "SamplingIntervalMs",
           "AlarmLowLimit", "AlarmHighLimit", "AvgValue", "MinValue", "MaxValue"}
BOOLEAN = {"Active"}
CHUNK = 2000
TERMINAL = ("DONE", "WARNING", "ERROR", "FINISHED", "CANCELED")

def req(url, key, body=None):
    auth = {"Authorization": f"Bearer {key}"} if key.startswith("ey") and key.count(".") == 2 else {"Api-Key": key}
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                               method="POST" if body is not None else "GET",
                               headers={"Content-Type": "application/json", "Accept": "application/json", **auth})
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} on {r.method} {url}\n{e.read().decode('utf-8', 'replace')[:2000]}")

def typed(k, v):
    if k in NUMERIC: return float(v) if "." in v else int(v)
    if k in BOOLEAN: return v.lower() == "true"
    return v

def read(path):
    ent, pub = os.path.basename(path)[3:-4].rsplit("_", 1)
    with open(path, encoding="utf-8") as f:
        recs = [{k: typed(k, v) for k, v in row.items() if v != ""} for row in csv.DictReader(f)]
    if ent in MATCHED:
        for r in recs: r["PublisherID"] = pub
    return {"entity": ent, "publisher": pub, "records": recs, "file": os.path.basename(path)}

def load(base, dl, key, specs, dry):
    lid = req(f"{base}/dm/api/rest/loads/{dl}", key,
              {"action": "CREATE_LOAD", "programName": PROGRAM, "loadDescription": "ENERGINET demo dataset"})["loadId"]
    print(f"  load {lid}")
    try:
        for s in specs:
            recs = s["records"]
            for i in range(0, len(recs), CHUNK):
                body = {"action": "PERSIST_DATA",
                        "persistOptions": {"defaultPublisherId": s["publisher"], "missingIdBehavior": "GENERATE",
                                           "persistMode": "NEVER" if dry else "ALWAYS",
                                           "optionsPerEntity": {s["entity"]: {"enrichers": [], "validations": [],
                                                                              "queryPotentialMatches": False}},
                                           "responsePayload": "SUMMARY"},
                        "persistRecords": {s["entity"]: recs[i:i + CHUNK]}}
                r = req(f"{base}/dm/api/rest/loads/{dl}/{lid}", key, body)
                print(f"    {s['file']:34} [{i}:{i + len(recs[i:i + CHUNK])}] -> {r.get('status')} "
                      f"{json.dumps(r.get('persistSummary') or {})[:140]}")
    except Exception:
        req(f"{base}/dm/api/rest/loads/{dl}/{lid}", key, {"action": "CANCEL"})   # never leave a load RUNNING
        print(f"  load {lid} cancelled after error")
        raise
    if dry:
        req(f"{base}/dm/api/rest/loads/{dl}/{lid}", key, {"action": "CANCEL"})
        print(f"  dry run: load {lid} cancelled")
        return None
    req(f"{base}/dm/api/rest/loads/{dl}/{lid}", key, {"action": "SUBMIT", "jobName": JOB})
    return lid

def wait(base, dl, key, lid, timeout=1800):
    end = time.time() + timeout
    while True:
        st = req(f"{base}/dm/api/rest/loads/{dl}/{lid}", key)
        if str(st.get("loadStatus", "")).upper() in TERMINAL:
            job = st.get("integrationJob") or {}
            print(f"  batch {st.get('batchId')} -> {st.get('loadStatus')} ({(job.get('duration') or 0) / 1000:.0f} s)")
            return st
        if time.time() > end: sys.exit(f"timeout waiting for load {lid}")
        time.sleep(5)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True); ap.add_argument("--data-location", required=True)
    ap.add_argument("--api-key", default=os.environ.get("SEM_API_KEY"))
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--dry-run", action="store_true", help="persistMode NEVER for every level, then cancel")
    a = ap.parse_args()
    if not a.api_key: sys.exit("Provide --api-key or SEM_API_KEY")
    base = a.url.rstrip("/")
    specs = [read(p) for p in sorted(glob.glob(os.path.join(a.dir, "[0-9][0-9]_*.csv")))]
    for lvl in sorted({LEVEL[s["entity"]] for s in specs}):
        group = [s for s in specs if LEVEL[s["entity"]] == lvl]
        print(f"Level {lvl}: {', '.join(s['file'] for s in group)}")
        lid = load(base, a.data_location, a.api_key, group, a.dry_run)
        if lid: wait(base, a.data_location, a.api_key, lid)
    print("Done.")

if __name__ == "__main__":
    main()
