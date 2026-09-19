import pandas as pd
import numpy as np
import os
import warnings

# 忽略可能的切片警告
warnings.filterwarnings('ignore')

def run():
    
    # 1. 定义文件路径
    
    # 输入路径
    path_nutrition = r"..\..\input\Driver\retired_unused_raw\FoodBalanceSheets_E_All_Data_NOFLAG.csv"
    path_production = r"..\..\input\Production_Trade\Production_Crops_Livestock_E_All_Data_NOFLAG_yield_refilled_baseYearFilled.csv"
    
    # 输出路径
    output_dir = r"..\..\input\Driver\Nutrition"
    output_file = os.path.join(output_dir, "Nutrition_profile.xlsx")

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("正在初始化...")

    
    # 2. 读取并处理营养供给数据 (Nutrition)
    
    print(f"读取营养数据: {path_nutrition}")
    # FAO数据常含有Latin-1字符，读取时不进行任何M49格式清洗，保留原始格式
    df_nut = pd.read_csv(path_nutrition, encoding='latin-1', dtype={'M49_Country_Code': str})
    
    # 筛选 Element
    target_elements = [
        'Food supply (kcal/capita/day)', 
        'Protein supply quantity (g/capita/day)', 
        'Fat supply quantity (g/capita/day)'
    ]
    df_nut = df_nut[df_nut['Element'].isin(target_elements)]
    
    # 修改点2：不再对国家进行筛选，保留所有国家/区域数据
    
    # 识别年份列 (Yxxxx)
    year_cols = [c for c in df_nut.columns if c.startswith('Y') and c[1:].isdigit()]
    
    
    # 3. 读取并处理产量数据 (Production)
    
    print(f"读取产量数据: {path_production}")
    # 同样保留M49原始格式
    df_prod = pd.read_csv(path_production, encoding='latin-1', dtype={'M49_Country_Code': str})
    
    # 筛选 Element = Production
    df_prod = df_prod[df_prod['Element'] == 'Production']

    
    # 4. 定义拆分规则
    
    split_rules = [
        {
            'target_item': 'Sugar (Raw Equivalent)',
            'ref_items': ['Sugar cane', 'Sugar beet'],
            'suffixes': ['-Sugar cane', '-Sugar beet']
        },
        {
            'target_item': 'Meat, Other',
            'ref_items': [
                'Meat of asses, fresh or chilled', 
                'Meat of camels, fresh or chilled', 
                'Horse meat, fresh or chilled', 
                'Meat of other domestic camelids, fresh or chilled', 
                'Meat of mules, fresh or chilled'
            ],
            'suffixes': ['-asses', '-camels', '-horse', '-other domestic camelids', '-mules']
        },
        {
            'target_item': 'Milk - Excluding Butter',
            'ref_items': [
                'Raw milk of buffalo', 
                'Raw milk of camel', 
                'Raw milk of cattle', 
                'Raw milk of goats', 
                'Raw milk of sheep'
            ],
            'suffixes': ['-buffalo', '-camel', '-cattle', '-goats', '-sheep']
        },
        {
            'target_item': 'Bovine Meat',
            'ref_items': [
                'Meat of buffalo, fresh or chilled', 
                'Meat of cattle with the bone, fresh or chilled'
            ],
            'suffixes': ['-buffalo', '-cattle']
        },
        {
            'target_item': 'Poultry Meat',
            'ref_items': [
                'Meat of chickens, fresh or chilled', 
                'Meat of ducks, fresh or chilled', 
                'Meat of turkeys, fresh or chilled'
            ],
            'suffixes': ['-chickens', '-ducks', '-turkeys']
        },
        {
            'target_item': 'Mutton & Goat Meat',
            'ref_items': [
                'Meat of goat, fresh or chilled', 
                'Meat of sheep, fresh or chilled'
            ],
            'suffixes': ['-goat', '-sheep']
        }
    ]

    new_rows_list = []

    print("开始进行数据拆分与填充...")

    for rule in split_rules:
        target_item = rule['target_item']
        ref_items = rule['ref_items']
        suffixes = rule['suffixes']
        
        print(f"  处理项目: {target_item}")
        
        # 1. 获取该项目的营养数据
        nut_subset = df_nut[df_nut['Item'] == target_item].copy()
        if nut_subset.empty:
            continue
            
        # 2. 获取对应的产量数据
        prod_subset = df_prod[df_prod['Item'].isin(ref_items)].copy()
        
        # 3. 构建产量比例矩阵 (Pivot)
        # 仅保留年份列交集
        prod_years = [y for y in year_cols if y in df_prod.columns]
        
        # 转换为长格式以便处理
        prod_long = prod_subset.melt(
            id_vars=['M49_Country_Code', 'Item'], 
            value_vars=prod_years, 
            var_name='Year', 
            value_name='Production'
        )
        
        # Pivot: Index=[Country, Year], Columns=Item
        prod_pivot = prod_long.pivot_table(
            index=['M49_Country_Code', 'Year'], 
            columns='Item', 
            values='Production', 
            fill_value=0
        )
        
        # 确保所有参考项都在列中（防止某项在所有国家都无数据）
        for item in ref_items:
            if item not in prod_pivot.columns:
                prod_pivot[item] = 0
                
        # 计算总产量
        prod_pivot['Total_Prod'] = prod_pivot[ref_items].sum(axis=1)
        
        # 计算比例 (Avoid division by zero)
        ratios = pd.DataFrame(index=prod_pivot.index)
        for item in ref_items:
            # 如果总产量>0，则计算比例，否则为0
            ratios[item] = np.where(
                prod_pivot['Total_Prod'] > 0, 
                prod_pivot[item] / prod_pivot['Total_Prod'], 
                0
            )
        
        # 将比例表重置索引，以便 merge
        ratios = ratios.reset_index()
        
        # 4. 将营养数据转换为长格式并合并比例
        # 识别 id_vars (除了年份以外的所有列)
        id_vars_nut = [c for c in nut_subset.columns if c not in year_cols]
        nut_long = nut_subset.melt(
            id_vars=id_vars_nut, 
            value_vars=year_cols, 
            var_name='Year', 
            value_name='Value'
        )
        
        # 合并 (Left join, 保留所有营养数据行)
        # 这里的 M49_Country_Code 格式必须一致（都是 'xxx 或 都是 xxx）
        # 由于我们都未做处理且原文件格式一致，所以可以直接合并
        merged = pd.merge(nut_long, ratios, on=['M49_Country_Code', 'Year'], how='left')
        
        # 对于匹配不上的（没有产量数据的），比例设为0
        for item in ref_items:
            merged[item] = merged[item].fillna(0)
            
        # 5. 生成新行
        for i, ref_item in enumerate(ref_items):
            suffix = suffixes[i]
            new_item_name = f"{target_item}{suffix}"
            
            # 计算拆分后的值
            # 复制一份 merged 数据用于当前子项计算
            temp_df = merged.copy()
            temp_df['Value'] = temp_df['Value'] * temp_df[ref_item]
            
            # 更新 Item 名称
            temp_df['Item'] = new_item_name
            
            # 这里的 Unit, Area, Element 等列已经在 temp_df 中保留了原值
            
            # 转换回宽格式 (Pivot)
            # 需要保留所有 id_vars (此时 Item 已变)
            # Pivot table index 必须唯一
            pivot_index = [c for c in id_vars_nut if c != 'Item'] + ['Item']
            
            # ：某些列可能包含 NaN，pivot_table 默认会 dropna=True
            temp_wide = temp_df.pivot_table(
                index=pivot_index, 
                columns='Year', 
                values='Value'
            ).reset_index()
            
            new_rows_list.append(temp_wide)

    
    # 5. 合并结果并排序
    
    print("正在合并数据...")
    if new_rows_list:
        df_new_rows = pd.concat(new_rows_list, ignore_index=True)
        # 确保列顺序与原始 df_nut 一致（如果 pivot 改变了顺序）
        # 补充可能缺失的列（如果有的话）并对齐
        df_new_rows = df_new_rows.reindex(columns=df_nut.columns)
        
        # 将新行添加到原始数据中
        df_final = pd.concat([df_nut, df_new_rows], ignore_index=True)
    else:
        df_final = df_nut

    print("正在排序...")
    # 按照 M49_Country_Code, Item, Element 升序排列
    df_final.sort_values(
        by=['M49_Country_Code', 'Item', 'Element'], 
        ascending=[True, True, True], 
        inplace=True
    )

    
    # 6. 保存文件
    
    print(f"保存文件至: {output_file}")
    df_final.to_excel(output_file, index=False)
    print("脚本执行完毕。")

if __name__ == "__main__":
    run()