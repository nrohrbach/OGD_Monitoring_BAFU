import requests
import json
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
%matplotlib inline

# Abfrage aller CKAN Packages des BAFU
Packages = "https://ckan.opendata.swiss/api/3/action/organization_show?id=bundesamt-fur-umwelt-bafu&include_datasets=True"
Packages = requests.get(Packages).json()

# Alle Bezeichungen und Publisher extrahieren
Title = [s['title_for_slug'] for s in Packages['result']['packages']]
Maintainer = [s['maintainer'] for s in Packages['result']['packages']]
Email = [s['maintainer_email'] for s in Packages['result']['packages']]
LastModified = [s['modified'] for s in Packages['result']['packages']]

# Dataframe für Packages erstellen
dict = {'Publisher': Maintainer, 'Mail': Email, 'Package': Title, 'LastModified': LastModified}
dfPackages = pd.DataFrame(dict)

# Mit folgender BaseURL können Details aller Packages abgerufen werden
DatasetBaseURL = 'https://ckan.opendata.swiss/api/3/action/package_show?id='

# Alle Datasets aller Packages abfragen
Datasets = []

for package in Title:
    try:
        DataSet = requests.get(DatasetBaseURL + package).json()
        # Alle Bezeichungen und Publisher extrahieren
        Format = [s['format'] for s in DataSet['result']['resources']]
        PackageId = [s['package_id'] for s in DataSet['result']['resources']]
        Datasets.append({'Package': package, 'Format': Format})
        
    except:
        Datasets.append({'Package': package, 'Format': 'Unbekannt'})

# Dataframe der Datasets erstellen und mit dem Dataframe der Packages mergen
dfDatasets = pd.DataFrame(Datasets)
dfDatasets = dfDatasets.explode('Format', ignore_index=False)
dfDatasets = pd.merge(dfDatasets, dfPackages, how='left', on=['Package'])
dfDatasets['Date'] = datetime.today().strftime("%Y-%m-%d")

# Übersicht Packages speichern
dfPackagesCSV = dfPackages.groupby(['Mail'])['Package'].count().reset_index()
dfPackagesCSV['Date'] = datetime.today().strftime("%Y-%m-%d")
dfPackagesCSV.to_csv("data/BAFU_OGD_Monitoring_Packages.csv", header=False, index=False, mode='a')

# Übersicht Datasets speichern
dfDatasetsCSV = dfDatasets.groupby(['Mail'])['Package'].count().reset_index()
dfDatasetsCSV['Date'] = datetime.today().strftime("%Y-%m-%d")
dfDatasetsCSV.to_csv("data/BAFU_OGD_Monitoring_Datasets.csv", header=False, index=False, mode='a')

# Übersicht Formate speichern
dfFormats = dfDatasets.groupby(['Format'])['Mail'].count().reset_index()
dfFormats.replace("","Fehlt",inplace=True)
dfFormats['Date'] = datetime.today().strftime("%Y-%m-%d")
dfFormats.to_csv("data/BAFU_OGD_Monitoring_Formats.csv", header=False, index=False, mode='a')

# Übersicht Last Update speichern
dfPackages['LastModified'] = dfPackages['LastModified'].str.slice(0,7)
dfLastUpdateCSV = dfPackages.groupby(['LastModified'])['Mail'].count().reset_index()
dfLastUpdateCSV.replace("","1999-01",inplace=True) #Fehlende Werte werden 1999 dargestellt.
dfLastUpdateCSV['LastModified'] = pd.to_datetime(dfLastUpdateCSV['LastModified'])
dfLastUpdateCSV['Date'] = datetime.today().strftime("%Y-%m-%d")
dfLastUpdateCSV.to_csv("data/BAFU_OGD_Monitoring_LastUpdate.csv", header=False, index=False, mode='a')

#Packages - Daten reinladen
dfPackages = pd.read_csv("data/BAFU_OGD_Monitoring_Packages.csv", parse_dates=['Date'])

#Packages Barchart
dfPackagesBar = dfPackages.loc[dfPackages['Date']==datetime.today().strftime("%Y-%m-%d")]
dfPackagesBar = dfPackagesBar.sort_values('Package',ascending=False)

fig, ax = plt.subplots()
ax.bar(dfPackagesBar['Mail'], dfPackagesBar['Package'])
ax.set_title('Anzahl OGD Publikationen')
plt.xticks(rotation = 90)
plt.ylabel("Anzahl Masten")
plt.rcParams["figure.figsize"] = (10,5)
ax.bar_label(ax.containers[0], label_type='edge')
plt.savefig('plots/PackagesBarchart.png',bbox_inches='tight')
plt.close()

#Packages - Linechart
dfPackagesLine = dfPackages.pivot(index="Date", columns=['Mail'],values="Package")

dfPackagesLine.plot(figsize=(15,10))
plt.legend(loc='lower left')
plt.title("Anzahl OGD Publikationen")
plt.savefig('plots/PackagesLinechart.png')
plt.close()

#Datasets - Daten reinladen
dfDatasets = pd.read_csv("data/BAFU_OGD_Monitoring_Datasets.csv", parse_dates=['Date'])

#Datasets Barchart
dfDatasetsBar = dfDatasets.loc[dfDatasets['Date']==datetime.today().strftime("%Y-%m-%d")]
dfDatasetsBar = dfDatasetsBar.sort_values('Package',ascending=False)

fig, ax = plt.subplots()
ax.bar(dfDatasetsBar['Mail'], dfDatasetsBar['Package'])
ax.set_title('Anzahl OGD Datensätze')
plt.xticks(rotation = 90)
plt.ylabel("Anzahl Masten")
plt.rcParams["figure.figsize"] = (10,5)
ax.bar_label(ax.containers[0], label_type='edge')
plt.savefig('plots/DatasetsBarchart.png',bbox_inches='tight')
plt.close()

#Datsets - Linechart
dfDatasetsLine = dfDatasets.pivot(index="Date", columns=['Mail'],values="Package")

dfDatasetsLine.plot(figsize=(15,10))
plt.legend(loc='lower left')
plt.title("Anzahl OGD Datensätze")
plt.savefig('plots/DatasetsLinechart.png')
plt.close()

#Formate - Daten reinladen
dfFormats = pd.read_csv("data/BAFU_OGD_Monitoring_Formats.csv", parse_dates=['Date'])

#Formats Barchart
dfFormatsBar = dfFormats.loc[dfFormats['Date']==datetime.today().strftime("%Y-%m-%d")]
dfFormatsBar = dfFormatsBar.sort_values('Mail',ascending=False)

fig, ax = plt.subplots()
ax.bar(dfFormatsBar['Format'], dfFormatsBar['Mail'])
ax.set_title('Anzahl OGD Datensätze nach Format')
plt.xticks(rotation = 90)
plt.ylabel("Anzahl Datensätze")
plt.rcParams["figure.figsize"] = (10,5)
ax.bar_label(ax.containers[0], label_type='edge')
plt.savefig('plots/FormatssBarchart.png',bbox_inches='tight')
plt.close()

#Formats - Linechart
dfFormatsLine = dfFormats.pivot(index="Date", columns=['Format'],values="Mail")

dfFormatsLine.plot(figsize=(15,10))
plt.legend(loc='lower left')
plt.title("Anzahl OGD Datensätze nach Format")
plt.savefig('plots/FormatssLinechart.png')
plt.close()

#Last Update - Daten reinladen
dfLastUpdate = pd.read_csv("data/BAFU_OGD_Monitoring_LastUpdate.csv", parse_dates=['Date'])
dfLastUpdate = dfLastUpdate.loc[dfLastUpdate['Date']==datetime.today().strftime("%Y-%m-%d")]
dfLastUpdate['LastModified'] = pd.to_datetime(dfLastUpdate['LastModified'])
dfLastUpdate['Mail']=pd.to_numeric(dfLastUpdate['Mail'])

#Last Update - Barchart
fig, ax = plt.subplots()
plt.rcParams["figure.figsize"] = (4,2)
plt.bar(x=dfLastUpdate['LastModified'], height=dfLastUpdate['Mail'], width=20)
ax.set_title('Anzahl Publikationen')
plt.xticks(rotation = 90)
plt.ylabel("Anzahl Publikationen")
ax.bar_label(ax.containers[0], label_type='edge')
plt.rcParams["figure.figsize"] = (10,5)
plt.savefig('plots/LastUpdate.png',bbox_inches='tight')
plt.close()
  
