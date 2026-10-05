"""
Download the REAL public source files into data/raw/.

All sources are Thai government open data (data.go.th catalogue):
  - กรมควบคุมโรค (DDC)  : influenza case register, mid-year population, food-poisoning/diarrhea outbreaks
  - สำนักงานคณะกรรมการอาหารและยา (อย./FDA): drug-premises licences 2024, drug production+import value
  - สำนักงานสถิติแห่งชาติ (NSO): mobile/internet use, household smartphones, illness in past month

The NSO API sits behind a WAF that rejects default clients, so a browser
User-Agent is sent. Run:  python scripts/fetch_raw_data.py
"""
from pathlib import Path
import urllib.request

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

DDC = "https://opendata.ddc.moph.go.th/dataset"
FLU = f"{DDC}/c2fc9128-12d5-44f4-a800-36b7a99b23b7/resource"
POP = f"{DDC}/5e7d68c8-8652-4ca2-9931-2e2699357b68/resource"
FDA = "https://catalog.fda.moph.go.th/dataset"
NSO = "https://catalogapi.nso.go.th/api/index?format=json&table="

SOURCES = {
    # DDC influenza case register (one row per reported case), by quarter
    "flu_2567_q1.csv": f"{FLU}/1b9227a7-c04f-4b29-ab0d-0f797c71395f/download/influenza__-_2567.csv",
    "flu_2567_q2.csv": f"{FLU}/3c8aef4c-e16c-4982-b7b2-bea13dffbaac/download/influenza__-_2567.csv",
    "flu_2567_q3.csv": f"{FLU}/34bd3851-aecc-4299-a463-da07100b3a58/download/influenza__-_2567.csv",
    "flu_2567_q4.csv": f"{FLU}/35af91a9-152a-4ab8-87be-9208c4408e92/download/influenza__-_2567.csv",
    "flu_2568_q1.csv": f"{FLU}/cadda43d-4f09-4076-80c3-4361e4e589b0/download/untitled.csv",
    "flu_2568_q2.csv": f"{FLU}/ed1ba0a6-2fbd-4ef2-90b0-c766f48b0c77/download/untitled.csv",
    "flu_2568_q3.csv": f"{FLU}/ba310df9-e797-4593-87f2-8bb0c72c8f8c/download/untitled.csv",
    "flu_datadict.csv": f"{FLU}/623054d6-c074-4265-844f-68afb5e82707/download/datadict_.csv",
    # DDC mid-year population by province x age x sex
    "pop_2567.csv": f"{POP}/b455f65c-de32-4509-b327-d85c1aef45ad/download/untitled.csv",
    "pop_2568.csv": f"{POP}/e34f7a4a-6e51-49c2-b50a-fd3e2edb8b13/download/untitled.csv",
    # DDC food poisoning / diarrhea outbreak events
    "food_diarrhea_outbreak.csv": f"{DDC}/2a698098-c758-4680-898c-53a292680f5b/resource/91ae5208-51bd-4039-ad21-cd13a8757fe0/download/untitled.csv",
    # FDA drug-premises licences (pharmacies etc.) 2024
    "fda_drug_location_license_2024.xlsx": f"{FDA}/cf621463-524a-4bc0-8a92-62f32e2650d4/resource/00789601-1313-4d28-86e7-cf9afbc457e8/download/drug_location_license-2024-final.xlsx",
    # FDA value of modern-drug production + import 2557-2566
    "fda_drug_production_import_2557_2566.xlsx": f"{FDA}/b5ce12d3-2e02-402c-b52d-0bd56052e348/resource/021dd806-e363-4c9f-870e-68fd5e8ff917/download/untitled.xlsx",
    # NSO ICT household survey + health & welfare survey
    "nso_mobile_use_by_region.json": NSO + "ICTH_37_11_Table_02per",
    "nso_mobile_use_by_age.json": NSO + "ICTH_37_11_Table_03per",
    "nso_internet_use_by_region.json": NSO + "ICTH_37_5_Table_02per",
    "nso_internet_use_by_age.json": NSO + "ICTH_37_5_Table_03per",
    "nso_hh_smartphone.json": NSO + "Per_HH_Smartphone",
    "nso_illness_outpatient_by_area.json": NSO + "HWS_ADD_0704_06_0004_01",
    "nso_illness_outpatient_by_region.json": NSO + "HWS_ADD_0704_06_0004_03",
    "nso_clinic_satisfaction.json": NSO + "POS_ADD_01_0602_00_0007_01",
}

if __name__ == "__main__":
    for name, url in SOURCES.items():
        dest = RAW / name
        if dest.exists() and dest.stat().st_size > 5000:
            print(f"skip  {name}")
            continue
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=300) as r:
            dest.write_bytes(r.read())
        print(f"saved {name} ({dest.stat().st_size / 1e6:.1f} MB)")
