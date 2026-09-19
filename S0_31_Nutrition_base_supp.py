import pandas as pd

# 读取原始文件
# 请确保文件名与您本地的文件名一致
# df_profile = pd.read_excel("../../input/Driver/retired_unused_raw/Nutrition_profile.xlsx", sheet_name='select')
df_profile = pd.read_csv("../../input/Driver/retired_unused_raw/Nutrition_profile_updated.csv")
df_missing = pd.read_csv("../../input/Driver/retired_unused_raw/nutrition_missing_report.csv")

# 1. 建立映射关系 (从现有数据中获取 Area Code 和 Item Code)
area_mapping = df_profile[['M49_Country_Code', 'Area']].drop_duplicates('M49_Country_Code').set_index('M49_Country_Code')
item_mapping = df_profile[['Item', 'Item Code', 'Item Code (FBS)']].drop_duplicates('Item').set_index('Item')

# 2. 定义需要添加的营养元素标准
elements_defaults = [
    {'Element Code': 664, 'Element': 'Food supply (kcal/capita/day)', 'Unit': 'kcal/cap/d'},
    {'Element Code': 674, 'Element': 'Protein supply quantity (g/capita/day)', 'Unit': 'g/cap/d'},
    {'Element Code': 684, 'Element': 'Fat supply quantity (g/capita/day)', 'Unit': 'g/cap/d'}
]

# 3. 提取缺失条目
missing_entries = df_missing[['M49_Country_Code', 'country_name', 'item_nutrition_map']].drop_duplicates()

new_rows = []

# 4. 遍历并构造新数据
for _, row in missing_entries.iterrows():
    m49 = row['M49_Country_Code']
    item = row['item_nutrition_map']
    
    # 查找或使用默认的国家/地区信息
    if m49 in area_mapping.index:
        area_name = area_mapping.loc[m49, 'Area']
    else:
        area_name = row['country_name']
        
    # 查找或使用默认的商品代码
    if item in item_mapping.index:
        item_code = item_mapping.loc[item, 'Item Code']
        item_fbs = item_mapping.loc[item, 'Item Code (FBS)']
    else:
        item_code = None
        item_fbs = None
        
    # 为每个营养元素添加一行
    for elem in elements_defaults:
        new_row = {
            'Area Code (M49)': m49,
            'M49_Country_Code': m49,
            'Area': area_name,
            'Item Code': item_code,
            'Item Code (FBS)': item_fbs,
            'Item': item,
            'Element Code': elem['Element Code'],
            'Element': elem['Element'],
            'Unit': elem['Unit'],
            'Y2020': 0.01  # 按要求填充 2020 年数据
        }
        new_rows.append(new_row)

# 5. 合并并保存
df_new = pd.DataFrame(new_rows)
df_final = pd.concat([df_profile, df_new], ignore_index=True)

df_final.to_csv("../../input/Driver/retired_unused_raw/Nutrition_profile_updated2.csv", index=False)
print("处理完成，文件已保存为 Nutrition_profile_updated2.csv")
