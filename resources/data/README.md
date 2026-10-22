# ENERGINET demo dataset (fictional)

All substations, lines, assets, signals and values are **invented** for the demo. Names look Danish on
purpose, so the matching rules are exercised on Danish letters (Æ, Ø, Å). Coordinates are plausible
points in Denmark, and serial numbers are random. The data is deterministic: `build_dataset.py` uses a
fixed seed.

| File | Entity | Source (publisher) | Rows |
|---|---|---|---|
| `01_Substation_NETMODEL.csv` | Substation (ID-matched) | Network model | 10 |
| `02_Substation_EAM.csv` | Substation | Asset register | 10 |
| `03_TransmissionLine_NETMODEL.csv` | TransmissionLine (basic) | Network model | 15 |
| `04_Asset_NETMODEL.csv` | Asset (fuzzy-matched) | Network model | 48 |
| `05_Asset_EAM.csv` | Asset | Asset register | 50 |
| `06_MeasurementPoint_SCADA.csv` | MeasurementPoint (basic) | SCADA / PMU point list | 82 |
| `07_Measurement_HISTORIAN.csv` | Measurement (basic) | Historian, 15-min aggregates of 2026-10-14 | 7 777 |

## Load

```bash
python resources/data/build_dataset.py        # regenerate the CSVs (optional)
python resources/data/load_datasets.py --url https://<tenant> --data-location <DL> --api-key <key> --dry-run
python resources/data/load_datasets.py --url https://<tenant> --data-location <DL> --api-key <key>
```

The loader runs one load per dependency level and waits for each integration batch before submitting
the next one: (1) substations, (2) lines and assets, (3) measurement points, (4) measurements.

The key's role must hold `integrationWsRole` in the data product grants. Both `semarchyAdmin` and
`GridIntegration` hold it.

## What the data demonstrates, and the expected result

| Case | Where | Expected outcome |
|---|---|---|
| Same substation code in both sources | Substation | 20 masters become **10 golden records**. Name and location come from the network model; status, commissioning date and description come from the asset register |
| Latitude/longitude swapped in the network model | `SUB-HAV` | 1 record in the *Location outside Denmark* worklist |
| Line with the same substation at both ends | `LN-150-LYN-LYN` | **Rejected**: 14 lines in the golden view, 1 in errors |
| Transformer with the same serial number and manufacturer in both sources | 10 transformers | **Merged automatically** (rule score 100) |
| Breaker in the same bay, spelled differently (`CB Q11 Østerby 400kV` vs `CB-Q11 OSTERBY 400 KV`) | 28 pairs | **Suggested matches** for the data steward (score 80, below the merge threshold of 90), not merged |
| Asset register asset with no mRID and no EAM number | `EAM-NOID-1` | **Rejected** |
| In-service asset with a 2027 commissioning date | Shunt reactor R1 at Fjordby | 1 record in the *In service, commissioned in the future* worklist |
| Asset totals | Asset | 98 masters, 1 rejected, 97 valid. **87 golden records**: 97 minus the 10 transformer merges |
| Measurement point with alarm low > high | `KRA.T1.AMB.TEMP` | **Rejected**: 81 points in the golden view |
| Measurement point whose asset is in another substation | `BAK.T1.TAP.TEMP` | 1 record in the *Asset in another substation* worklist |
| Measurement with min > avg | Last row | **Rejected**: 7 776 measurements in the golden view |
