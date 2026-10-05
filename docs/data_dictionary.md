# Data Dictionary — `data/warehouse/`

Star schema: 5 dimensions, 6 facts. All CSVs are UTF-8 with BOM (open correctly in Excel / Power BI).

## Dimensions

### dim_month
| column | type | description |
|---|---|---|
| month_key | int (YYYYMM01) | PK |
| year / year_be | int | ค.ศ. / พ.ศ. |
| month | int | 1–12 |
| month_label_th | text | เช่น "ก.ค. 67" |
| season_th | text | ฤดูฝน (พ.ค.–ต.ค.), ฤดูหนาว (พ.ย.–ก.พ.), ฤดูร้อน (มี.ค.–เม.ย.) |

### dim_province
| column | type | description |
|---|---|---|
| province_key | int | PK |
| province | text | ชื่อจังหวัด (ตัดคำว่า "จังหวัด" ออก) |
| region / region_key | text / int | 5 ภาค: กรุงเทพฯ, กลาง, เหนือ, ตะวันออกเฉียงเหนือ, ใต้ |
| province_code | int | รหัสจังหวัด |
| population_2568 | int | ประชากรกลางปี 2568 (กรมควบคุมโรค) |
| pharmacy_khy1 | int | ใบอนุญาตขายยาแผนปัจจุบัน (ข.ย.1) ที่คงอยู่ — อย. 2567 |
| pharmacy_khy2 | int | ใบอนุญาตขายยาบรรจุเสร็จที่ไม่ใช่ยาอันตราย (ข.ย.2) |
| pharmacies_total | int | khy1 + khy2 |
| pharmacies_per_10k | float | ร้านยาต่อประชากร 10,000 คน |

### dim_region
`region_key`, `region`

### dim_age_group
| column | description |
|---|---|
| age_group_key / age_group | 0-4, 5-14, 15-24, 25-44, 45-59, 60+ ปี |
| mediguide_segment | กลุ่มลูกค้าตาม Canvas (ผู้ซื้อยาให้ครอบครัว, นักศึกษา, คนทำงาน, ผู้สูงอายุ) |

### dim_occupation
`occupation_key`, `occupation_group` — 9 กลุ่ม จัดจากข้อความอาชีพในทะเบียนด้วย regex (ดู `OCC` ใน `etl_build_warehouse.py`)

## Facts

### fact_influenza_monthly  (grain: เดือนเริ่มป่วย × จังหวัด × กลุ่มอายุ × เพศ × กลุ่มอาชีพ)
| column | description |
|---|---|
| month_key, province_key, age_group_key, gender, occupation_key | FKs (gender = ชาย/หญิง/ไม่ระบุ) |
| cases | จำนวนผู้ป่วย |
| deaths | จำนวนผู้เสียชีวิต (มี death_date) |
| delay_days_sum | ผลรวมวันจากเริ่มป่วยถึงรักษา (เฉพาะ 0–30 วัน) |
| delay_n | จำนวนผู้ป่วยที่คำนวณ delay ได้ |
| delay_ge2_days | จำนวนผู้ป่วยที่รักษาหลังเริ่มป่วย ≥ 2 วัน |

### fact_population  (grain: จังหวัด × กลุ่มอายุ × เพศ)
`province_key`, `age_group_key`, `gender`, `population_2568`

### fact_outbreak  (grain: เหตุการณ์ระบาด)
`month_key`, `event_date`, `province_key`, `district`, `disease`, `setting`, `cases`, `deaths`

### fact_digital_adoption  (grain: ปี × ตัวชี้วัด × มิติ × สมาชิก)
| column | description |
|---|---|
| year_be, period | ปี พ.ศ. และงวดที่ สสช. เผยแพร่ (เลือกงวดล่าสุดของแต่ละปี) |
| metric | mobile / internet / household_smartphone |
| dimension | ทั่วประเทศ / เขตการปกครอง / ภาค / กลุ่มอายุ |
| member | ค่าของมิติ |
| pct | ร้อยละ |

### fact_illness_survey  (grain: ปี × ภาค × ประเภทการเจ็บป่วย)
`year_be`, `region`, `illness` (ไม่เจ็บป่วย / เจ็บป่วย / ป่วย-รู้สึกไม่สบาย / อุบัติเหตุ / โรคเรื้อรัง / รวม), `persons`

### fact_drug_market  (grain: ปี × กลุ่ม ATC)
`year_be`, `atc_code`, `atc_group`, `value_million_thb`, `mediguide_symptom_link` (กลุ่มยาที่ตรงอาการที่แอปดูแล)
