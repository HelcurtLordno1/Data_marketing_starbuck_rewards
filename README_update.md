# Power BI Project - Data Explore And Process

## Muc tieu
Notebook `Data_explore_and_process.ipynb` duoc dung de hop nhat du lieu tu 3 file JSON va tao bo du lieu san sang cho phan tich/modeling.

## File nay da lam duoc gi
1. Doc du lieu tu 3 nguon:
- `Data/portfolio.json`
- `Data/profile.json`
- `Data/transcript.json`

2. Merge transcript + profile + portfolio thanh mot dataframe duy nhat: `merged_df`.

3. Tao nhan ket qua offer:
- `offer_completed_event`: su kien hoan thanh goc tu transcript
- `offer_completed`: nhan thanh cong cuoi cung theo logic:
  - offer phai duoc viewed
  - va offer phai duoc completed

4. Xu ly missing values:
- `age`: doi gia tri 118 thanh missing, sau do dien median
- `income`: dien median
- `gender`: dien gia tri `U`
- `days_since_registration`: dien median (neu co missing)

5. One-hot cot channels thanh cac cot nhi phan:
- `web`, `email`, `mobile`, `social`

6. In ket qua kiem tra chat luong:
- kich thuoc dataframe
- ty le `offer_completed`
- so cot con null

## Nguyen tac co ban duoc ap dung
1. Reproducible:
- Pipeline co the chay lai tu dau theo thu tu Section 1 -> Section 2.

2. Defensive coding:
- Co check ton tai cot truoc khi thao tac (`became_member_on`, `channels`) de tranh vo cell khi rerun.

3. Data quality first:
- Xu ly missing values ro rang truoc khi tinh toan/so sanh.
- Tach bien nhan (`offer_completed`) minh bach theo business rule.

4. Compatibility:
- Dung option pandas an toan (`display.max_columns`).
- Tranh cac loi do kieu du lieu khi tinh toan thong ke/tuong quan.

## Huong dan chay nhanh
1. Mo `Data_explore_and_process.ipynb`.
2. Chay Cell 3 (Section 1) de tao `merged_df` co ban.
3. Chay Cell 5 (Section 2) de tao `offer_completed` va xu ly missing.
4. Chay Cell 8 de xem bang so sanh output.

## Output mong doi (tham chieu)
- `merged_df` shape: `(50637, 18)`
- `offer_completed` rate: `0.483`
- Null columns count: `0`
