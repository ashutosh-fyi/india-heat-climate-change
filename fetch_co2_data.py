"""
Fetch CO2 emissions data for India from Global Carbon Budget and Our World in Data.
Produces co2_data_var.js for the web visualization.
"""
import json
import requests
import csv
import io

# ── 1. Global Carbon Budget (GCB) - Fuel breakdown 1858-2023 ──────────
print("Downloading Global Carbon Budget data...")
gcb_url = "https://zenodo.org/records/13981696/files/GCB2024v17_MtCO2_flat.csv?download=1"
resp = requests.get(gcb_url, timeout=120)
resp.raise_for_status()
print(f"  Downloaded {len(resp.content)//1024} KB")

reader = csv.DictReader(io.StringIO(resp.text))
india_rows = []
global_rows = []
for row in reader:
    if row["Country"] == "India":
        india_rows.append(row)
    if row["Country"] == "Global":
        global_rows.append(row)

print(f"  India rows: {len(india_rows)}, Global rows: {len(global_rows)}")
if india_rows:
    print(f"  Columns: {list(india_rows[0].keys())}")
    print(f"  Year range: {india_rows[0]['Year']}-{india_rows[-1]['Year']}")
    print(f"  Sample: {india_rows[-1]}")

# Process India fuel breakdown
india_by_year = {}
for row in india_rows:
    yr = int(row["Year"])
    india_by_year[yr] = {
        "total": float(row["Total"]) if row["Total"] else 0,
        "coal": float(row["Coal"]) if row["Coal"] else 0,
        "oil": float(row["Oil"]) if row["Oil"] else 0,
        "gas": float(row["Gas"]) if row["Gas"] else 0,
        "cement": float(row["Cement"]) if row["Cement"] else 0,
        "flaring": float(row["Flaring"]) if row["Flaring"] else 0,
        "other": float(row["Other"]) if row["Other"] else 0,
        "perCapita": float(row["Per Capita"]) if row["Per Capita"] else 0,
    }

# Process Global totals for India's share
global_by_year = {}
for row in global_rows:
    yr = int(row["Year"])
    global_by_year[yr] = float(row["Total"]) if row["Total"] else 0

# ── 2. Our World in Data - Additional metrics ─────────────────────────
print("\nDownloading Our World in Data CO2 dataset...")
owid_url = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
resp2 = requests.get(owid_url, timeout=120)
resp2.raise_for_status()
print(f"  Downloaded {len(resp2.content)//1024} KB")

reader2 = csv.DictReader(io.StringIO(resp2.text))
india_owid = []
world_owid = []
for row in reader2:
    if row["country"] == "India":
        india_owid.append(row)
    elif row["country"] == "World":
        world_owid.append(row)

print(f"  India OWID rows: {len(india_owid)}")
if india_owid:
    # Get relevant columns
    sample = india_owid[-1]
    relevant_keys = ["year", "co2", "co2_per_capita", "share_global_co2",
                     "cumulative_co2", "co2_per_gdp", "population",
                     "coal_co2", "oil_co2", "gas_co2", "cement_co2",
                     "co2_growth_prct", "co2_growth_abs"]
    print(f"  Sample latest: {{{', '.join(k+': '+str(sample.get(k,'')) for k in relevant_keys)}}}")

# Build per-capita comparison data (India vs World)
world_percapita = {}
for row in world_owid:
    yr = row.get("year", "")
    pc = row.get("co2_per_capita", "")
    if yr and pc:
        try:
            world_percapita[int(yr)] = round(float(pc), 3)
        except:
            pass

india_percapita = {}
india_share = {}
india_cumulative = {}
for row in india_owid:
    yr = row.get("year", "")
    if not yr:
        continue
    yr = int(yr)
    pc = row.get("co2_per_capita", "")
    if pc:
        try:
            india_percapita[yr] = round(float(pc), 3)
        except:
            pass
    sh = row.get("share_global_co2", "")
    if sh:
        try:
            india_share[yr] = round(float(sh), 2)
        except:
            pass
    cu = row.get("cumulative_co2", "")
    if cu:
        try:
            india_cumulative[yr] = round(float(cu), 1)
        except:
            pass

# ── 3. Get top emitter countries for comparison ───────────────────────
print("\nExtracting top emitter comparisons...")
# Read OWID data again for top countries
resp3 = requests.get(owid_url, timeout=120)
reader3 = csv.DictReader(io.StringIO(resp3.text))

# Collect latest year data for major emitters
countries_of_interest = ["India", "China", "United States", "European Union (27)",
                         "Russia", "Japan", "World"]
country_data = {c: {} for c in countries_of_interest}

for row in reader3:
    c = row.get("country", "")
    if c in countries_of_interest:
        yr = row.get("year", "")
        if not yr:
            continue
        yr = int(yr)
        entry = {}
        for key in ["co2", "co2_per_capita", "cumulative_co2", "share_global_co2", "population"]:
            val = row.get(key, "")
            if val:
                try:
                    entry[key] = float(val)
                except:
                    pass
        if entry:
            country_data[c][yr] = entry

# Get latest year comparison
latest_comparison = {}
for c, ydata in country_data.items():
    if c == "World":
        continue
    # Find latest year with co2 data
    for yr in sorted(ydata.keys(), reverse=True):
        if "co2" in ydata[yr]:
            latest_comparison[c] = {
                "year": yr,
                "co2": round(ydata[yr].get("co2", 0), 1),
                "perCapita": round(ydata[yr].get("co2_per_capita", 0), 2),
                "cumulative": round(ydata[yr].get("cumulative_co2", 0), 1),
                "share": round(ydata[yr].get("share_global_co2", 0), 2),
            }
            break

print(f"  Latest comparison: {json.dumps(latest_comparison, indent=2)}")

# ── 4. Build final output ─────────────────────────────────────────────
# Filter to years with actual data
years_with_data = sorted(yr for yr, d in india_by_year.items() if d["total"] > 0)
print(f"\nYears with CO2 data: {years_with_data[0]}-{years_with_data[-1]} ({len(years_with_data)} years)")

output = {
    "india": {
        str(yr): {
            "total": round(india_by_year[yr]["total"], 2),
            "coal": round(india_by_year[yr]["coal"], 2),
            "oil": round(india_by_year[yr]["oil"], 2),
            "gas": round(india_by_year[yr]["gas"], 2),
            "cement": round(india_by_year[yr]["cement"], 2),
            "flaring": round(india_by_year[yr]["flaring"], 2),
            "other": round(india_by_year[yr]["other"], 2),
            "perCapita": round(india_by_year[yr]["perCapita"], 3),
        }
        for yr in years_with_data
    },
    "globalTotal": {str(yr): round(global_by_year[yr], 2) for yr in years_with_data if yr in global_by_year},
    "indiaShare": {str(yr): v for yr, v in india_share.items() if yr >= years_with_data[0]},
    "indiaCumulative": {str(yr): v for yr, v in india_cumulative.items() if yr >= years_with_data[0]},
    "worldPerCapita": {str(yr): v for yr, v in world_percapita.items() if yr >= years_with_data[0]},
    "indiaPerCapita": {str(yr): v for yr, v in india_percapita.items() if yr >= years_with_data[0]},
    "comparison": latest_comparison,
    "years": years_with_data,
    "sources": {
        "gcb": "Global Carbon Budget 2024 (Friedlingstein et al.)",
        "owid": "Our World in Data",
    },
}

# Write JSON
json_path = "/Users/ash-19027/claudecode/india/heat-climate-change/co2_data.json"
with open(json_path, "w") as f:
    json.dump(output, f, separators=(",", ":"))
print(f"\nWrote JSON → {json_path} ({len(json.dumps(output))//1024} KB)")

# Write JS var
js_path = "/Users/ash-19027/claudecode/india/heat-climate-change/co2_data_var.js"
with open(js_path, "w") as f:
    f.write("var CO2_DATA = ")
    json.dump(output, f, separators=(",", ":"))
    f.write(";\n")
print(f"Wrote JS  → {js_path}")

# Summary
print("\n── Summary ──")
latest_yr = years_with_data[-1]
d = india_by_year[latest_yr]
print(f"India {latest_yr}: {d['total']:.1f} MtCO2 total")
print(f"  Coal: {d['coal']:.1f}, Oil: {d['oil']:.1f}, Gas: {d['gas']:.1f}, Cement: {d['cement']:.1f}")
print(f"  Per capita: {d['perCapita']:.2f} tCO2")
print(f"  Global share: {india_share.get(latest_yr, 'N/A')}%")
