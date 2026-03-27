# Power BI Dashboard Specification (Week 1 v0.1)

**Target Completion:** End of Day 5 (March 31, 2026)  
**Owner:** Person E (with A, B, C, D reviews)  
**Input Data:** `data/processed/preprocessed_data.csv`  
**Output:** `dashboards/powerbi/starbucks_rewards.pbix`

---

## Overview: 3-Page Dashboard Structure

This Power BI workbook implements the Week 1 EDA findings and supports Week 2 modeling decisions.

**Minimum Requirements:**
- 3 distinct pages (Overview, Demographics, Offer Performance)
- 5+ interactive visuals total
- 1 slicer (for drilling into segments)
- All metrics sourced from Python EDA/insights_summary.md

---

## Page 1: Overview (KPI & Trends)

**Purpose:** Executive dashboard showing business health metrics.

### Visuals Required

1. **Card: Overall Completion Rate**
   - Value: 48.3%
   - Benchmark: 40%
   - Status: Green (exceeds)
   - Tooltip: "Based on 50,637 person-offer records"

2. **Card: Total Customers**
   - Value: 14,500
   - Tooltip: "Unique individuals in dataset"

3. **Card: Total Offers Sent**
   - Value: 50,637
   - Tooltip: "Person-offer interactions (viewed)"

4. **Card: Average Member Tenure**
   - Value: 314 days
   - Tooltip: "Average days since registration"

5. **Combo Chart: Completion Rate by Offer Type**
   - X-axis: Offer Type (BOGO, Discount)
   - Y-axis (line): Completion Rate (%)
   - Y-axis (column): Count of Offers
   - Data:
     - BOGO: 52% completion, 22,322 offers
     - Discount: 45% completion, 28,315 offers
   - Insight: "BOGO offers outperform by +7 percentage points"

---

## Page 2: Demographics Segmentation

**Purpose:** Highlight gender, income, age, and tenure patterns.

**Slicers (Filter Controls):**
- Income Group: [Low, Lower-Middle, Middle, Upper-Middle, High] — default all
- Age Group: [18-25, 26-35, 36-45, 46-55, 56-65, 66+] — default all

### Visuals Required

1. **Clustered Bar Chart: Completion Rate by Gender**
   - Categories: Female (58%), Male (46%), Unknown (51%)
   - Color code: Female green (highest), Male orange, Unknown gray
   - Include count labels (e.g., "Female: 5,847/10,089")
   - **Tooltip:** "Females show 20% uplift vs baseline"

2. **Line Chart: Completion Rate by Income Group**
   - X-axis: Income Group [Low, Lower-Middle, Middle, Upper, High]
   - Y-axis: Completion Rate (%)
   - Data: [37%, 42%, 48%, 54%, 61%]
   - Mark high end (61%) visually (e.g., red/gold point)
   - **Tooltip:** "High-income customers 65% more likely to complete"

3. **Line Chart: Completion Rate by Age Group**
   - X-axis: Age Groups
   - Y-axis: Completion Rate (%)
   - Data: [44%, 49%, 53%, 56%, 51%, 48%]
   - Highlight peak (age 46-55: 56%)
   - **Tooltip:** "Peak engagement in 46-55 age group"

4. **Stacked Column Chart: Completion by Tenure Bucket**
   - X-axis: Tenure Bin [New, Growing, Mature, Loyal]
   - Y-axis: Completion Count
   - Stacked by: Completed (green) vs Not Completed (red)
   - Data:
     - New (0-3mo): 1,344/3,200 completed (42%)
     - Growing (3-12mo): 4,032/8,400 (48%)
     - Mature (1-2yr): 8,112/15,600 (52%)
     - Loyal (2+yr): 6,696/12,400 (54%)
   - **Insight:** "Long-term loyalty drives +28% completion"

---

## Page 3: Channel & Offer Performance

**Purpose:** Show offer-level and channel-level effectiveness.

**Slicers:**
- Offer Type: [BOGO, Discount] — default all
- Channel: [Email, Web, Mobile, Social] — default all

### Visuals Required

1. **Table: Offer Performance Summary**
   - Columns:
     - Offer ID (text)
     - Offer Type (text)
     - Difficulty (int)
     - Reward (int)
     - Completion Rate (%)
     - Completed Count (int)
     - Total Sent (int)
   - Data: All 10 offers ranked by completion rate (descending)
   - **Conditional formatting:** Green for >50%, yellow for 40-50%, red for <40%
   - **Tooltip:** Click any row to filter other visuals to that offer

2. **Grouped Bar Chart: Completion Rate by Channel**
   - X-axis: Channel [Email, Web, Mobile, Social]
   - Y-axis: Completion Rate (%)
   - Data: [48%, 47%, 50%, 49%]
   - Highlight Mobile (50%) as highest
   - **Tooltip:** "Mobile shows +3pp advantage; Social underutilized"

3. **Scatter Plot: Difficulty vs Completion Rate (by Offer)**
   - X-axis: Difficulty Level [5, 10, 20]
   - Y-axis: Completion Rate (%)
   - Bubble size: Count of offers sent
   - Data:
     - (5, 58%, bubble size 3): Low difficulty, high completion
     - (10, 48%, bubble size 1): Medium difficulty
     - (20, 39%, bubble size 1): High difficulty, low completion
   - **Insight:** "Lower difficulty thresholds drive 49% higher completion"
   - **Tooltip:** Show offer names on hover

4. **Heatmap: Completion Rate by Gender × Channel**
   - Rows: Gender [Female, Male, Unknown]
   - Columns: Channel [Email, Web, Mobile, Social]
   - Values: Completion Rate (%) with color gradient (red=low, green=high)
   - Example cells:
     - Female + Mobile: 53% (dark green)
     - Female + Email: 52%
     - Male + Web: 45% (orange)
     - Social generally yellow/light (lower intensity)
   - **Insight:** Identifies best segment-channel combos (e.g., Female + Mobile)

---

## Cross-Page Features (Interactivity)

### Navigation
- Add page navigation buttons on each page (optional, Power BI auto-provides tabs)
- Consistent color scheme across all pages (Starbucks green + corporate grays)

### Slicers & Filtering
- **Global Slicer (all pages):** Date Range (if temporal trends added later) — currently **ignore**
- **Page 2 Slicers:** Income Group, Age Group (filters Page 2 visuals + updates Page 3 counts)
- **Page 3 Slicers:** Offer Type, Channel (filters Page 3 + highlights Page 1 benchmarks)

### Drillthrough (Optional - Week 2 enhancement)
- Clicking a visual detail → drill to customer-level transaction view
- **Not required for Week 1 v0.1**

---

## Data Source Configuration

### Connection
- **Type:** CSV file import
- **Path:** `data/processed/preprocessed_data.csv`
- **Refresh:** Manual (enable when notebook exports new data)

### Data Model
- **Table Name:** `preprocessed_data`
- **Record Count:** 39,826 (viewed offers only)
- **Key Measures to Create:**

| Measure Name | DAX Formula | Type |
|---|---|---|
| `Completion_Rate` | `DIVIDE(COUNTIF([offer_completed], 1), COUNTA([offer_completed]), 0)` | % |
| `Completed_Count` | `COUNTIF([offer_completed], 1)` | Count |
| `Total_Offers` | `COUNTA([offer])` | Count |
| `Unique_Customers` | `DISTINCTCOUNT([person])` | Count |
| `Avg_Income` | `AVERAGE([income])` | Currency |
| `Avg_Tenure_Days` | `AVERAGE([days_since_registration])` | Number |

### Calculated Columns
- **Age Group:** Use `SWITCH([age], <25, "18-25", <35, "26-35", ... )` if not already in CSV
- **Income Group:** Use binning logic matching Python features
- **Tenure Bin:** Segment `days_since_registration` into New/Growing/Mature/Loyal

---

## Formatting & Design Standards

### Color Palette
- **Primary:** Starbucks Green (#00704A) — use for positive/high metrics
- **Accent:** Gold (#D4AF37) — highlights/targets
- **Neutral:** Dark Gray (#333333) — labels, axes
- **Bad:** Red (#E73935) — low performance, warnings
- **Good:** Light Green (#A4DE6C) — successful metrics

### Typography
- **Title Font:** Segoe UI, 24pt, bold, dark gray
- **Axis Labels:** Segoe UI, 12pt, regular
- **Data Labels:** Segoe UI, 11pt, regular (on visuals)
- **Card Values:** Segoe UI, 36pt, bold, green

### Tooltips (All Visuals)
- Enabled by default
- Include: value, context, benchmark, recommendation

---

## Example Snapshot (Text Description)

```
┌─ STARBUCKS REWARDS PROGRAM DASHBOARD ─────────────────────┐
│                                                              │
│  [Overview] [Demographics] [Offer Performance]  [← ↓ →]    │
│                                                              │
│  ┌─ KEY METRICS ─────────────────────────────────────────┐ │
│  │ Completion Rate    Total Orders    Avg Tenure (days) │ │
│  │    48.3%  📈         50,637            314 days      │ │
│  │  vs 40% baseline                                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ Completion by Offer Type ────────────────────────────┐ │
│  │                    BOGO 52%                          ◆ │
│  │                    Discount 45%       ◆              │ │
│  │  ├─────────────────────────────────┤                 │ │
│  │  0%        25%        50%        75%        100%     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Page 2 Preview (Demographics):                             │
│  ├─ Completion by Gender: Female 58% ► Male 46%           │
│  ├─ Completion by Income: $100k+ 61% ► <$40k 37%          │
│  └─ Completion by Age: 46-55 years 56% (peak)             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Validation Checklist (Before Day 5 End)

- [ ] Data source connects to `data/processed/preprocessed_data.csv`
- [ ] Page 1 (Overview): 5 visuals displaying correctly
- [ ] Page 2 (Demographics): 4 visuals + 2 slicers functional
- [ ] Page 3 (Offer Performance): 4 visuals + 2 slicers functional
- [ ] All cards/visuals match values from `reports/week1/insights_summary.md`
- [ ] Tooltips populated (hover shows context)
- [ ] Cross-page filtering tested (Page 2 slicer affects Page 3)
- [ ] Export to PDF works without errors
- [ ] Design review by Person A (modeling lead)
- [ ] File saved as `dashboards/powerbi/starbucks_rewards.pbix`

---

## Notes for Week 2 Enhancements

- Add temporal analysis (trends over time) if time data added
- Integrate model predictions (Week 2 output) for before/after comparison
- Add RFM segmentation page
- Enable Q&A natural language queries (Power BI Premium feature)
- Schedule automatic refresh when Python notebooks run

---

**Assigned to:** Person E  
**Due:** March 31, 2026 (End of Day 5)  
**Review Meeting:** April 1, 2026 (Day 6 standup)  
**Git Branch:** `feature/e-powerbi-dashboard-v0.1`
