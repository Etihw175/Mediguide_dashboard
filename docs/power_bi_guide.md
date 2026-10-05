# ทำเวอร์ชัน Power BI จาก Warehouse ชุดเดียวกัน

`dashboard/index.html` ทำงานแบบ Power BI อยู่แล้ว แต่ถ้าต้องส่งเป็นไฟล์ `.pbix` ทำตามนี้ (~20 นาที)

## 1. โหลดข้อมูล
Power BI Desktop → **Get data → Text/CSV** → เลือกไฟล์ทั้งหมดใน `data/warehouse/` (File origin: 65001 UTF-8)

## 2. Relationships (Model view)
| from (many) | to (one) |
|---|---|
| fact_influenza_monthly[month_key] | dim_month[month_key] |
| fact_influenza_monthly[province_key] | dim_province[province_key] |
| fact_influenza_monthly[age_group_key] | dim_age_group[age_group_key] |
| fact_influenza_monthly[occupation_key] | dim_occupation[occupation_key] |
| fact_population[province_key] | dim_province[province_key] |
| fact_population[age_group_key] | dim_age_group[age_group_key] |
| fact_outbreak[province_key] | dim_province[province_key] |
| dim_province[region_key] | dim_region[region_key] |

ตั้ง `dim_month[month_label_th]` → Sort by column = `month_key`

## 3. DAX measures
```DAX
Flu Cases = SUM(fact_influenza_monthly[cases])
Flu Deaths = SUM(fact_influenza_monthly[deaths])
Population = SUM(fact_population[population_2568])
Flu Rate per 100k = DIVIDE([Flu Cases], [Population]) * 100000
Avg Days to Treatment = DIVIDE(SUM(fact_influenza_monthly[delay_days_sum]), SUM(fact_influenza_monthly[delay_n]))
% Delayed >= 2 Days = DIVIDE(SUM(fact_influenza_monthly[delay_ge2_days]), SUM(fact_influenza_monthly[delay_n]))
Pharmacies = SUM(dim_province[pharmacies_total])
Pharmacies per 10k = DIVIDE([Pharmacies], SUM(dim_province[population_2568])) * 10000
Mobile Use % (latest) =
    VAR y = CALCULATE(MAX(fact_digital_adoption[year_be]), fact_digital_adoption[metric] = "mobile", fact_digital_adoption[dimension] = "ทั่วประเทศ")
    RETURN CALCULATE(MAX(fact_digital_adoption[pct]), fact_digital_adoption[metric] = "mobile", fact_digital_adoption[dimension] = "ทั่วประเทศ", fact_digital_adoption[year_be] = y)
```

## 4. หน้ารายงาน (ให้ตรงกับเวอร์ชัน HTML)
1. **เรื่องเล่า** — Card: Flu Cases, Flu Rate per 100k, % Delayed, Pharmacies, Mobile Use · Column chart: Flu Cases by month (legend = season_th) · Text box 5 บท (ปัญหา → หลักฐาน → ช่องว่าง → ความพร้อม → โอกาส)
2. **โรค & กลุ่มผู้ป่วย** — Line: Flu Cases by month (legend = year_be) · Bar: Flu Rate per 100k by age_group · Bar: Flu Cases by occupation_group · Bar: % Delayed by age_group
3. **พื้นที่ & การเข้าถึงยา** — Scatter: X = Pharmacies per 10k, Y = Flu Rate per 100k, Details = province, Size = Population · Bar: Pharmacies per 10k by region · Table Top 15
4. **ความพร้อมดิจิทัล** — Line: pct by year_be (legend = metric, filter dimension = ทั่วประเทศ) · Clustered bar by กลุ่มอายุ
5. **ตลาดยา** — Stacked column: value_million_thb by year_be, legend = atc_group · Line: persons by year_be (fact_illness_survey)

Slicers: dim_month[month_label_th], dim_region[region], dim_province[province], dim_age_group[age_group], dim_occupation[occupation_group], gender
