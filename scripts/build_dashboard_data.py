"""
Pack the warehouse CSVs (data/warehouse) into dashboard/data.js
so the HTML dashboard opens offline by double-click.

Run:  python scripts/build_dashboard_data.py
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
W = ROOT / "data" / "warehouse"
read = lambda n: pd.read_csv(W / f"{n}.csv", encoding="utf-8-sig")

month = read("dim_month")
prov = read("dim_province").sort_values("province_key")
age = read("dim_age_group")
occ = read("dim_occupation")
region = read("dim_region")
flu = read("fact_influenza_monthly")
pop = read("fact_population")
ob = read("fact_outbreak")
dig = read("fact_digital_adoption")
ill = read("fact_illness_survey")
mkt = read("fact_drug_market")

m_idx = {k: i for i, k in enumerate(month.month_key)}
GENDER = ["ชาย", "หญิง", "ไม่ระบุ"]

data = {
    "months": month.month_key.tolist(),
    "monthLabels": month.month_label_th.tolist(),
    "monthYear": month.year_be.tolist(),
    "monthNo": month.month.tolist(),
    "dim": {
        "region": region.region.tolist(),
        "age": age.age_group.tolist(), "ageSegment": age.mediguide_segment.tolist(),
        "occupation": occ.occupation_group.tolist(), "gender": GENDER,
    },
    "province": {
        "name": prov.province.tolist(), "region": (prov.region_key - 1).tolist(),
        "pop": prov.population_2568.tolist(), "pharm": prov.pharmacies_total.tolist(),
        "khy1": prov.pharmacy_khy1.tolist(),
    },
    # population by province x age group (both sexes) for rates
    "popAge": pop.groupby(["province_key", "age_group_key"]).population_2568.sum()
                 .unstack(fill_value=0).reindex(prov.province_key, fill_value=0).values.tolist(),
    "popGender": pop[pop.gender.isin(["ชาย", "หญิง"])].groupby(["province_key", "gender"]).population_2568.sum()
                 .unstack(fill_value=0).reindex(prov.province_key, fill_value=0)[["ชาย", "หญิง"]].values.tolist(),
    "flu": {
        "m": flu.month_key.map(m_idx).tolist(), "p": (flu.province_key - 1).tolist(),
        "a": (flu.age_group_key - 1).tolist(), "g": flu.gender.map({g: i for i, g in enumerate(GENDER)}).tolist(),
        "o": (flu.occupation_key - 1).tolist(), "c": flu.cases.tolist(), "d": flu.deaths.tolist(),
        "ds": flu.delay_days_sum.round(0).astype(int).tolist(), "dn": flu.delay_n.tolist(), "d2": flu.delay_ge2_days.tolist(),
    },
    "outbreak": ob.assign(m=ob.month_key.map(m_idx), p=ob.province_key - 1)[["m", "p", "disease", "setting", "cases", "deaths"]]
                  .fillna({"m": -1, "p": -1}).astype({"m": int, "p": int}).to_dict("records"),
    "digital": dig.sort_values(["metric", "dimension", "year_be"]).to_dict("records"),
    "illness": ill.to_dict("records"),
    "market": mkt.to_dict("records"),
}
out = ROOT / "dashboard" / "data.js"
out.write_text("window.MG_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";", encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
