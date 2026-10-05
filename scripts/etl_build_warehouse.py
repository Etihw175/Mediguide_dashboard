"""
ETL: real public data (data/raw) -> star schema CSVs (data/warehouse).

Run:  python scripts/etl_build_warehouse.py
"""
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
WH = ROOT / "data" / "warehouse"
WH.mkdir(parents=True, exist_ok=True)

REGIONS = ["กรุงเทพมหานคร", "ภาคกลาง", "ภาคเหนือ", "ภาคตะวันออกเฉียงเหนือ", "ภาคใต้"]


def clean_prov(s):
    return re.sub(r"^จังหวัด", "", str(s).strip()).strip()


# ------------------------------------------------------------------ dim_province (+ population, pharmacies)
pop = pd.read_csv(RAW / "pop_2568.csv", encoding="utf-8-sig")
pop["province"] = pop.province_name.map(clean_prov)
pop = pop[pop.province != ""]
pop["region5"] = np.where(pop.province == "กรุงเทพมหานคร", "กรุงเทพมหานคร", pop.region.str.strip())
prov_pop = pop.groupby(["province", "region5", "province_code"], as_index=False).popuration.sum() \
    .rename(columns={"popuration": "population_2568"})

lic = pd.read_excel(RAW / "fda_drug_location_license_2024.xlsx")
lic["province"] = lic.thachngwtnm.map(clean_prov)
khy1 = lic[lic.lcntpcd == "ขายยาแผนปัจจุบัน"].groupby("province").size()
khy2 = lic[lic.lcntpcd.str.startswith("ขายยาแผนปัจจุบันเฉพาะยาบรรจุเสร็จที่ไม่ใช่", na=False)].groupby("province").size()

dim_province = prov_pop.sort_values("province_code").reset_index(drop=True)
dim_province.insert(0, "province_key", range(1, len(dim_province) + 1))
dim_province["region_key"] = dim_province.region5.map({r: i + 1 for i, r in enumerate(REGIONS)})
dim_province["pharmacy_khy1"] = dim_province.province.map(khy1).fillna(0).astype(int)
dim_province["pharmacy_khy2"] = dim_province.province.map(khy2).fillna(0).astype(int)
dim_province["pharmacies_total"] = dim_province.pharmacy_khy1 + dim_province.pharmacy_khy2
dim_province["pharmacies_per_10k"] = (dim_province.pharmacies_total / dim_province.population_2568 * 1e4).round(3)
dim_province = dim_province.rename(columns={"region5": "region"})
pkey = dict(zip(dim_province.province, dim_province.province_key))
unmatched_lic = sorted(set(lic.province) - set(pkey) - {"-"})

dim_region = pd.DataFrame({"region_key": range(1, 6), "region": REGIONS})

# ------------------------------------------------------------------ dim_age_group / dim_occupation
AGE_BINS = [-1, 4, 14, 24, 44, 59, 200]
AGE_LABELS = ["0-4 ปี", "5-14 ปี", "15-24 ปี", "25-44 ปี", "45-59 ปี", "60+ ปี"]
dim_age = pd.DataFrame({"age_group_key": range(1, 7), "age_group": AGE_LABELS,
                        "mediguide_segment": ["ผู้ซื้อยาให้ครอบครัว (เด็กเล็ก)", "ผู้ซื้อยาให้ครอบครัว (เด็ก)",
                                              "นักเรียน/นักศึกษา", "คนทำงาน", "คนทำงาน", "ผู้สูงอายุ"]})

OCC = [  # (group, regex) - first match wins
    ("นักเรียน/นักศึกษา", r"นักเรียน|นักศึกษา"),
    ("เด็ก/ในปกครอง", r"ในปกครอง|ในความปกครอง|เด็ก"),
    ("เกษตรกร", r"เกษตร|ปลูก|ทำสวน|ทำนา|ทำไร่|ประมง|เลี้ยงสัตว์"),
    ("ข้าราชการ/บุคลากรรัฐ", r"ข้าราชการ|รับราชการ|ทหาร|ตำรวจ|พยาบาล|แพทย์|ครู|รัฐวิสาหกิจ"),
    ("พนักงาน/รับจ้าง", r"รับจ้าง|พนักงาน|คนงาน|ลูกจ้าง|ผู้ประกอบวิชาชีพ|ช่าง|ขับรถ|เสมียน"),
    ("ค้าขาย/ธุรกิจส่วนตัว", r"ค้าขาย|ธุรกิจ|ค้า"),
    ("ไม่มีงาน/แม่บ้าน/ผู้สูงอายุ", r"ไม่มีงาน|ไม่มีอาชีพ|แม่บ้าน|พ่อบ้าน|ผู้สูงอายุ|บำนาญ|นักบวช|พระ"),
]
OCC_GROUPS = [g for g, _ in OCC] + ["อื่น ๆ", "ไม่ระบุ"]
dim_occ = pd.DataFrame({"occupation_key": range(1, len(OCC_GROUPS) + 1), "occupation_group": OCC_GROUPS})


def occ_group(s):
    if not isinstance(s, str) or re.search(r"ไม่ทราบ|ไม่ระบุ", s):
        return "ไม่ระบุ"
    for g, rx in OCC:
        if re.search(rx, s):
            return g
    return "อื่น ๆ"


# ------------------------------------------------------------------ fact_influenza_monthly (from 1.36M real case rows)
frames = []
for f in sorted(RAW.glob("flu_25*.csv")):
    df = pd.read_csv(f, encoding="utf-8-sig", low_memory=False,
                     usecols=["gender", "age_y", "occupation", "province", "onset_date", "treated_date", "death_date"])
    iso = df.onset_date.astype(str).str.match(r"\d{4}-")
    for c in ["onset_date", "treated_date"]:
        df[c] = pd.to_datetime(df[c], format="%Y-%m-%d" if iso.all() else "%d/%m/%Y", errors="coerce")
    df["source_file"] = f.name
    frames.append(df)
flu = pd.concat(frames, ignore_index=True)
n_raw = len(flu)
flu["province"] = flu.province.map(clean_prov)
flu = flu[flu.onset_date.between("2024-01-01", "2025-09-30")]
flu["province_key"] = flu.province.map(pkey)
flu = flu[flu.province_key.notna()]
flu["age_group_key"] = pd.cut(flu.age_y.clip(0, 120), AGE_BINS, labels=range(1, 7)).astype(int)
flu["gender"] = flu.gender.where(flu.gender.isin(["ชาย", "หญิง"]), "ไม่ระบุ")
occ_map = {o: occ_group(o) for o in flu.occupation.dropna().unique()}
flu["occupation_key"] = flu.occupation.map(occ_map).fillna("ไม่ระบุ").map(dict(zip(OCC_GROUPS, range(1, 99))))
delay = (flu.treated_date - flu.onset_date).dt.days
flu["delay_days"] = delay.where(delay.between(0, 30))
flu["month_key"] = flu.onset_date.dt.strftime("%Y%m01").astype(int)
flu["is_death"] = flu.death_date.notna().astype(int)
flu["delay_ge2"] = (flu.delay_days >= 2).astype(int)
flu["has_delay"] = flu.delay_days.notna().astype(int)
fact_flu = flu.groupby(["month_key", "province_key", "age_group_key", "gender", "occupation_key"], as_index=False).agg(
    cases=("is_death", "size"), deaths=("is_death", "sum"),
    delay_days_sum=("delay_days", "sum"), delay_n=("has_delay", "sum"), delay_ge2_days=("delay_ge2", "sum"))
fact_flu["province_key"] = fact_flu.province_key.astype(int)
print(f"influenza raw rows {n_raw:,} -> kept {len(flu):,} -> fact rows {len(fact_flu):,}")

# ------------------------------------------------------------------ dim_month
months = pd.date_range("2024-01-01", "2025-09-01", freq="MS")
TH_M = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
dim_month = pd.DataFrame({
    "month_key": months.strftime("%Y%m01").astype(int), "year": months.year, "month": months.month,
    "year_be": months.year + 543, "month_label_th": [f"{TH_M[m.month - 1]} {str(m.year + 543)[2:]}" for m in months],
    "season_th": ["ฤดูฝน" if 5 <= m.month <= 10 else "ฤดูหนาว" if m.month in (11, 12, 1, 2) else "ฤดูร้อน" for m in months],
})

# ------------------------------------------------------------------ fact_population (age x sex x province)
POP_AGE = {" 0-4 ปี": 1, " 5-9 ปี": 2, "10-14 ปี": 2, "15-19 ปี": 3, "20-24 ปี": 3, "25-29 ปี": 4, "30-34 ปี": 4,
           "35-39 ปี": 4, "40-44 ปี": 4, "45-49 ปี": 5, "50-54 ปี": 5, "55-59 ปี": 5, "60-64 ปี": 6,
           "65-69 ปี": 6, "70 ปี +": 6}
p2 = pop[pop.age_group.isin(POP_AGE)].copy()
p2["age_group_key"] = p2.age_group.map(POP_AGE)
p2["province_key"] = p2.province.map(pkey)
fact_population = p2.groupby(["province_key", "age_group_key", "gender"], as_index=False).popuration.sum() \
    .rename(columns={"popuration": "population_2568"})

# ------------------------------------------------------------------ fact_outbreak (food poisoning / diarrhea events 2025)
ob = pd.read_csv(RAW / "food_diarrhea_outbreak.csv", encoding="utf-8-sig")
ob["event_date"] = pd.to_datetime(ob.month, format="%d-%b-%y", errors="coerce")
ob["province_key"] = ob.province.map(clean_prov).map(pkey)
fact_outbreak = ob.assign(month_key=ob.event_date.dt.strftime("%Y%m01").astype("Int64"))[
    ["month_key", "event_date", "province_key", "district", "disease", "setting", "cases", "deaths"]]

# ------------------------------------------------------------------ NSO: ICT use (mobile / internet)
def nso(name):
    return pd.DataFrame(json.load(open(RAW / f"{name}.json", encoding="utf-8")))


def latest_q(df):  # keep annual-ish points: plain year or the last quarter of each year
    df = df.copy()
    df["y"] = df.year.str[:4].astype(int)
    df["q"] = df.year.str[5:].replace("", "Q4")
    last = df.groupby("y").q.transform("max")
    return df[df.q == last]


rows = []
for kind, col in [("mobile", "Per_use_Mo"), ("internet", "Per_use_In")]:
    r = latest_q(nso(f"nso_{kind}_use_by_region"))
    tot = r[(r.region.str.contains("ทั่วราช")) & (r.area == "รวม") & (r.sex == "รวม")]
    rows += [dict(year_be=y, period=p, metric=kind, dimension="ทั่วประเทศ", member="รวม", pct=v)
             for y, p, v in zip(tot.y, tot.year, tot[col])]
    area = r[(r.region.str.contains("ทั่วราช")) & (r.area != "รวม") & (r.sex == "รวม")]
    rows += [dict(year_be=y, period=p, metric=kind, dimension="เขตการปกครอง", member=a.split(") ")[-1], pct=v)
             for y, p, a, v in zip(area.y, area.year, area.area, area[col])]
    reg = r[~r.region.str.contains("ทั่วราช")]
    reg = reg.assign(member=reg.region.str.split(") ", regex=False).str[-1].map(
        {"กรุงเทพมหานคร": "กรุงเทพมหานคร", "ภาคกลาง": "ภาคกลาง", "ภาคเหนือ": "ภาคเหนือ",
         "ภาคตะวันออกเฉียงเหนือ": "ภาคตะวันออกเฉียงเหนือ", "ภาคใต้": "ภาคใต้"}))
    reg = reg.groupby(["y", "year", "member"], as_index=False)[col].mean()  # simple mean of area x sex cells
    rows += [dict(year_be=y, period=p, metric=kind, dimension="ภาค", member=m, pct=round(v, 1))
             for y, p, m, v in zip(reg.y, reg.year, reg.member, reg[col])]
    a = latest_q(nso(f"nso_{kind}_use_by_age"))
    a = a[(a.area == "รวม") & (a.age_group != "รวม")]
    rows += [dict(year_be=y, period=p, metric=kind, dimension="กลุ่มอายุ", member=g.split(". ")[-1], pct=v)
             for y, p, g, v in zip(a.y, a.year, a.age_group, a[col])]
hh = nso("nso_hh_smartphone")
rows += [dict(year_be=int(p[:4]), period=p, metric="household_smartphone", dimension="เขตการปกครอง" if a != "รวม" else "ทั่วประเทศ",
              member=a, pct=v) for p, a, v in zip(hh.year, hh.area, hh.Per_HH_Smartphone)]
fact_digital = pd.DataFrame(rows)

# ------------------------------------------------------------------ NSO: illness in the past month (persons)
ill = nso("nso_illness_outpatient_by_region")
ill["region"] = ill.region.replace({"กลาง": "ภาคกลาง", "เหนือ": "ภาคเหนือ", "ตะวันออกเฉียงเหนือ": "ภาคตะวันออกเฉียงเหนือ",
                                    "ใต้": "ภาคใต้", "รวม": "ทั่วประเทศ"})
fact_illness = ill.rename(columns={"year": "year_be", "value": "persons"})[["year_be", "region", "illness", "persons"]]
fact_illness["year_be"] = fact_illness.year_be.astype(int)

# ------------------------------------------------------------------ FDA: drug production + import value
m = pd.read_excel(RAW / "fda_drug_production_import_2557_2566.xlsx", sheet_name="แยกตามฤทธิ์ทางเภสัชวิทยา")
m = m.rename(columns={m.columns[0]: "atc_code", m.columns[1]: "atc_group"})
fact_drug_market = m.melt(id_vars=["atc_code", "atc_group"], var_name="year_be", value_name="value_million_thb")
fact_drug_market["year_be"] = fact_drug_market.year_be.astype(float).astype(int)
fact_drug_market = fact_drug_market.dropna(subset=["value_million_thb"])
OTC_RELEVANT = {"R": "ระบบทางเดินหายใจ (หวัด/ภูมิแพ้)", "A": "ทางเดินอาหาร (ท้องเสีย/กรดไหลย้อน)",
                "M": "กล้ามเนื้อ-กระดูก (ปวดเมื่อย)", "N": "ระบบประสาท (ปวดหัว/ลดไข้)", "D": "ผิวหนัง (ผื่นคัน)"}
fact_drug_market["mediguide_symptom_link"] = fact_drug_market.atc_code.map(OTC_RELEVANT).fillna("")

# ------------------------------------------------------------------ write
tables = {
    "dim_region": dim_region, "dim_province": dim_province, "dim_month": dim_month,
    "dim_age_group": dim_age, "dim_occupation": dim_occ,
    "fact_influenza_monthly": fact_flu, "fact_population": fact_population,
    "fact_outbreak": fact_outbreak, "fact_digital_adoption": fact_digital,
    "fact_illness_survey": fact_illness, "fact_drug_market": fact_drug_market,
}
for name, df in tables.items():
    df.to_csv(WH / f"{name}.csv", index=False, encoding="utf-8-sig")
    print(f"{name:26s} {len(df):>8,d} rows")
if unmatched_lic:
    print("licence provinces not matched:", unmatched_lic)
