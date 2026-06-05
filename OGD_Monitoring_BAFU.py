# -*- coding: utf-8 -*-
"""
OGD Monitoring BAFU
Tägliche Abfrage aller BAFU-Packages auf opendata.swiss via CKAN API.
Datenquelle: package_search (vollständige Ergebnisse, paginiert),
Details: package_show (direkt aus CKAN DB, vollständige Metadaten).
"""

import requests
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

CKAN_BASE = "https://ckan.opendata.swiss/api/3/action"
ORG = "bundesamt-fur-umwelt-bafu"
TODAY = datetime.today().strftime("%Y-%m-%d")

BAFU_THEMEN = [
    'abfall', 'altlasten', 'bildung', 'forschung', 'innovation',
    'biodiversitat', 'biotechnologie', 'boden', 'chemikalien',
    'elektrosmog', 'licht', 'ernahrung', 'wohnen', 'mobilitat',
    'gesundheit', 'internationales', 'klima', 'landschaft', 'larm',
    'luft', 'naturgefahr', 'recht', 'storfallvorsorge',
    'umweltvertraglichkeitsprufung', 'wald', 'holz', 'wasser',
    'wirtschaft', 'konsum',
]

# ---------------------------------------------------------------------------
# 1. Alle Package-Namen via package_search laden (paginiert)
# ---------------------------------------------------------------------------

all_package_names = []
rows = 500
start = 0

while True:
    url = (f"{CKAN_BASE}/package_search"
           f"?fq=organization:{ORG}&rows={rows}&start={start}")
    resp = requests.get(url).json()
    results = resp["result"]["results"]
    all_package_names.extend(s["name"] for s in results)
    if len(all_package_names) >= resp["result"]["count"] or not results:
        break
    start += rows

print(f"Gefundene Packages: {len(all_package_names)}")

# ---------------------------------------------------------------------------
# 2. Detaildaten via package_show laden (einmal pro Package)
#    package_show liefert vollständige Metadaten direkt aus der CKAN DB.
# ---------------------------------------------------------------------------

packages = []
datasets = []

for name in all_package_names:
    try:
        data = requests.get(f"{CKAN_BASE}/package_show?id={name}").json()["result"]

        maintainer = data.get("maintainer") or "Unbekannt"
        email      = data.get("maintainer_email") or "Unbekannt"
        modified   = data.get("modified") or ""
        issued     = data.get("issued") or ""
        resources  = data.get("resources") or []
        license_   = resources[0].get("license", "") if resources else ""

        # Keywords: dict {"de": [...], "fr": [...]} -> flache Liste
        kw_raw = data.get("keywords") or {}
        if isinstance(kw_raw, dict):
            kw_flat = [k for vals in kw_raw.values() for k in (vals or [])]
        elif isinstance(kw_raw, list):
            kw_flat = kw_raw
        else:
            kw_flat = []

        last_modified = modified if modified else issued

        packages.append({
            "Package":      name,
            "Publisher":    maintainer,
            "Mail":         email,
            "LastModified": last_modified,
            "Issued":       issued,
            "License":      license_,
            "Keywords":     str(kw_flat).lower(),
        })

        for res in resources:
            datasets.append({
                "Package":      name,
                "Mail":         email,
                "Format":       res.get("format") or "Fehlt",
                "Display_Name": res.get("url") or "",
            })

    except Exception as e:
        print(f"Fehler bei {name}: {e}")
        packages.append({
            "Package": name, "Publisher": "Unbekannt", "Mail": "Unbekannt",
            "LastModified": "", "Issued": "", "License": "", "Keywords": "[]",
        })

dfPackages = pd.DataFrame(packages)
dfDatasets = pd.DataFrame(datasets)

# ---------------------------------------------------------------------------
# 3. Lizenz kürzen (Teil nach #)
# ---------------------------------------------------------------------------

dfPackages["License"] = dfPackages["License"].str.split("#").str[-1]

# ---------------------------------------------------------------------------
# 4. STAC-Markierung
# ---------------------------------------------------------------------------

dfDatasets["STAC"] = "nein"
dfDatasets.loc[
    dfDatasets["Display_Name"].str.contains("data.geo.admin.ch/browser/index.html", na=False),
    "STAC"
] = "ja"

dfGeodaten = dfDatasets[
    dfDatasets["Display_Name"].str.contains("map.geo.admin.ch", na=False) &
    (dfDatasets["Format"] == "SERVICE")
].copy()

# ---------------------------------------------------------------------------
# 5. BAFU-Themen auswerten
# ---------------------------------------------------------------------------

thema_counts = []
for thema in BAFU_THEMEN:
    count = dfPackages["Keywords"].str.contains(f"'{thema}'", na=False).sum()
    thema_counts.append({"Thema": thema, "Anzahl": int(count)})

dfBafuThemen = pd.DataFrame(thema_counts)

# ---------------------------------------------------------------------------
# 6. CSV speichern (append)
# ---------------------------------------------------------------------------

dfPackagesCSV = dfPackages.groupby("Mail")["Package"].count().reset_index()
dfPackagesCSV["Date"] = TODAY
dfPackagesCSV.to_csv("data/BAFU_OGD_Monitoring_Packages.csv",
                     header=False, index=False, mode="a")

dfDatasetsCSV = dfDatasets.groupby("Mail")["Package"].count().reset_index()
dfDatasetsCSV["Date"] = TODAY
dfDatasetsCSV.to_csv("data/BAFU_OGD_Monitoring_Datasets.csv",
                     header=False, index=False, mode="a")

dfFormatsCSV = dfDatasets.groupby("Format")["Mail"].count().reset_index()
dfFormatsCSV["Date"] = TODAY
dfFormatsCSV.to_csv("data/BAFU_OGD_Monitoring_Formats.csv",
                    header=False, index=False, mode="a")

dfPackages["LastModifiedMonth"] = dfPackages["LastModified"].str.slice(0, 7)
dfLastUpdateCSV = dfPackages.groupby("LastModifiedMonth")["Mail"].count().reset_index()
dfLastUpdateCSV.columns = ["LastModified", "Mail"]
dfLastUpdateCSV["LastModified"].replace("", "1999-01", inplace=True)
dfLastUpdateCSV["LastModified"] = pd.to_datetime(dfLastUpdateCSV["LastModified"])
dfLastUpdateCSV["Date"] = TODAY
dfLastUpdateCSV.to_csv("data/BAFU_OGD_Monitoring_LastUpdate.csv",
                       header=False, index=False, mode="a")

dfLicenseCSV = dfPackages.groupby("License")["Package"].count().reset_index()
dfLicenseCSV["Date"] = TODAY
dfLicenseCSV.to_csv("data/BAFU_OGD_Monitoring_License.csv",
                    header=False, index=False, mode="a")

dfGeodatenCSV = dfGeodaten.groupby(["Mail", "STAC"])["Package"].count().reset_index()
dfGeodatenCSV["Date"] = TODAY
dfGeodatenCSV.to_csv("data/BAFU_OGD_Monitoring_STAC.csv",
                     header=False, index=False, mode="a")

dfBafuThemenCSV = dfBafuThemen.copy()
dfBafuThemenCSV["Date"] = TODAY
dfBafuThemenCSV.to_csv("data/BAFU_OGD_Monitoring_BafuThemen.csv",
                       header=False, index=False, mode="a")

print("CSV-Dateien aktualisiert.")

# ---------------------------------------------------------------------------
# 7. Visualisierungen
# ---------------------------------------------------------------------------

# Packages – Linechart gesamt
dfP = pd.read_csv("data/BAFU_OGD_Monitoring_Packages.csv",
                  names=["Mail", "Package", "Date"], parse_dates=["Date"])
dfPtotal = dfP.groupby("Date")["Package"].sum()
dfPtotal.plot(figsize=(15, 10))
plt.title("Anzahl OGD Publikationen (total)")
plt.ylabel("Anzahl Packages")
plt.savefig("plots/PackagesBAFULinechart.png")
plt.close()

# Packages – Barchart heute
dfPbar = dfP[dfP["Date"] == TODAY].sort_values("Package", ascending=False)
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(dfPbar["Mail"], dfPbar["Package"])
ax.set_title("Anzahl OGD Publikationen")
plt.xticks(rotation=90)
plt.ylabel("Anzahl Packages")
ax.bar_label(ax.containers[0], label_type="edge")
plt.savefig("plots/PackagesBarchart.png", bbox_inches="tight")
plt.close()

# Packages – Linechart pro Maintainer
dfPline = dfP.pivot(index="Date", columns="Mail", values="Package")
dfPline.plot(figsize=(15, 10))
plt.legend(loc="lower left")
plt.title("Anzahl OGD Publikationen pro Maintainer")
plt.savefig("plots/PackagesLinechart.png")
plt.close()

# Datasets – Barchart heute
dfD = pd.read_csv("data/BAFU_OGD_Monitoring_Datasets.csv",
                  names=["Mail", "Package", "Date"], parse_dates=["Date"])
dfDbar = dfD[dfD["Date"] == TODAY].sort_values("Package", ascending=False)
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(dfDbar["Mail"], dfDbar["Package"])
ax.set_title("Anzahl OGD Datensätze")
plt.xticks(rotation=90)
plt.ylabel("Anzahl Datasets")
ax.bar_label(ax.containers[0], label_type="edge")
plt.savefig("plots/DatasetsBarchart.png", bbox_inches="tight")
plt.close()

# Datasets – Linechart pro Maintainer
dfDline = dfD.pivot(index="Date", columns="Mail", values="Package")
dfDline.plot(figsize=(15, 10))
plt.legend(loc="lower left")
plt.title("Anzahl OGD Datensätze pro Maintainer")
plt.savefig("plots/DatasetsLinechart.png")
plt.close()

# Formate – Barchart heute
dfF = pd.read_csv("data/BAFU_OGD_Monitoring_Formats.csv",
                  names=["Format", "Mail", "Date"], parse_dates=["Date"])
dfFbar = dfF[dfF["Date"] == TODAY].sort_values("Mail", ascending=False)
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(dfFbar["Format"], dfFbar["Mail"])
ax.set_title("Anzahl OGD Datensätze nach Format")
plt.xticks(rotation=90)
plt.ylabel("Anzahl Datensätze")
ax.bar_label(ax.containers[0], label_type="edge")
plt.savefig("plots/FormatssBarchart.png", bbox_inches="tight")
plt.close()

# Formate – Linechart
dfFline = dfF.pivot(index="Date", columns="Format", values="Mail")
dfFline.plot(figsize=(15, 10))
plt.legend(loc="lower left")
plt.title("Anzahl OGD Datensätze nach Format")
plt.savefig("plots/FormatssLinechart.png")
plt.close()

# Last Update – Barchart heute
dfLU = pd.read_csv("data/BAFU_OGD_Monitoring_LastUpdate.csv",
                   names=["LastModified", "Mail", "Date"], parse_dates=["Date"])
dfLUbar = dfLU[dfLU["Date"] == TODAY].copy()
dfLUbar["LastModified"] = pd.to_datetime(dfLUbar["LastModified"])
dfLUbar["Mail"] = pd.to_numeric(dfLUbar["Mail"])
fig, ax = plt.subplots(figsize=(12, 5))
plt.bar(x=dfLUbar["LastModified"], height=dfLUbar["Mail"], width=20)
ax.set_title("Letzte Änderung der Packages")
plt.xticks(rotation=90)
plt.ylabel("Anzahl Packages")
ax.bar_label(ax.containers[0], label_type="edge")
plt.savefig("plots/LastUpdate.png", bbox_inches="tight")
plt.close()

# Lizenz – Linechart
dfL = pd.read_csv("data/BAFU_OGD_Monitoring_License.csv",
                  names=["License", "Package", "Date"], parse_dates=["Date"])
dfL.pivot(index="Date", columns="License", values="Package").plot(figsize=(15, 10))
plt.title("Anzahl OGD Datensätze nach Lizenz")
plt.savefig("plots/LizenzLinechart.png")
plt.close()

# STAC – Linechart (noch nicht migriert)
dfG = pd.read_csv("data/BAFU_OGD_Monitoring_STAC.csv",
                  names=["Mail", "STAC", "Package", "Date"], parse_dates=["Date"])
dfGnein = dfG[dfG["STAC"] == "nein"]
if not dfGnein.empty:
    dfGnein.pivot(index="Date", columns="Mail", values="Package").plot(figsize=(15, 10))
    plt.title("Geo-Datensätze noch nicht auf STAC")
    plt.savefig("plots/StacLinechart.png")
    plt.close()

# STAC – Barchart heute
dfGbar = dfG[dfG["Date"] == TODAY]
if not dfGbar.empty:
    dfGbar.groupby(["Mail", "STAC"])["Package"].sum().unstack(fill_value=0).plot(
        kind="bar", stacked=True, figsize=(10, 6), color=["green", "red"]
    )
    plt.title("Geodatensätze über STAC-API verfügbar")
    plt.xlabel("Mail")
    plt.ylabel("Anzahl Geodatensätze")
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="STAC")
    plt.tight_layout()
    plt.savefig("plots/StacBarchart.png")
    plt.close()

# BAFU Themen – Linechart
dfT = pd.read_csv("data/BAFU_OGD_Monitoring_BafuThemen.csv",
                  names=["Thema", "Anzahl", "Date"], parse_dates=["Date"])
dfTpos = dfT[dfT["Anzahl"] > 0]
if not dfTpos.empty:
    dfTpos.pivot(index="Date", columns="Thema", values="Anzahl").plot(figsize=(15, 10))
    plt.title("Anzahl OGD Datensätze nach Thema")
    plt.savefig("plots/BafuThemenLinechart.png")
    plt.close()

# BAFU Themen – Barchart heute
dfTbar = dfT[(dfT["Date"] == TODAY) & (dfT["Anzahl"] > 0)].sort_values(
    "Anzahl", ascending=False
)
if not dfTbar.empty:
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(dfTbar["Thema"], dfTbar["Anzahl"])
    ax.set_title("Anzahl OGD Datensätze nach Thema")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Anzahl Datensätze")
    ax.bar_label(ax.containers[0], label_type="edge")
    plt.tight_layout()
    plt.savefig("plots/BafuThemenBarchart.png", bbox_inches="tight")
    plt.close()

print("Visualisierungen erstellt.")
