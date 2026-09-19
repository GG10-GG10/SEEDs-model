import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as c
import matplotlib as mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import os


# 1. 文件路径配置

emissions_path = '../../output/BASE/Emis/emissions_summary.xlsx'
pop_path = '../../input/Driver/Population/WPP/Population_E_All_Data_NOFLAG.csv'
dict_path = '../../src/dict_v3.xlsx'
shp_map_path = '../../src/World_map/polygon/World_polygon.shp'

output_dir = '../../output/BASE/Plot/'
if not os.path.exists(output_dir):
    try:
        os.makedirs(output_dir)
    except:
        pass

img_name_total = 'Global_GHG_2020_Total_Optimized_Gt.png'
img_name_percapita = 'Global_GHG_2020_PerCapita_Optimized.png'

path_total = os.path.join(output_dir, img_name_total)
path_percapita = os.path.join(output_dir, img_name_percapita)


# 2. 读取数据

print("正在读取数据...")
try:
    df_emissions = pd.read_excel(emissions_path, engine='openpyxl')
except:
    try:
        df_emissions = pd.read_csv(emissions_path, encoding='latin1')
    except:
        df_emissions = pd.read_csv(emissions_path)

try:
    df_pop = pd.read_csv(pop_path, encoding='latin1')
except:
    try:
        df_pop = pd.read_csv(pop_path, encoding='ISO-8859-1')
    except:
        df_pop = pd.read_csv(pop_path)

df_dict = pd.read_excel(dict_path, sheet_name='region')
gdf_world = gpd.read_file(shp_map_path)


# 3. 数据处理

print("正在处理数据...")

# 3.1 排放
df_emissions['M49_Country_Code'] = df_emissions['M49_Country_Code'].astype(str).str.replace("'", "")
df_ghg = df_emissions[df_emissions['GHG'] == 'CO2eq'].copy()
df_ghg = df_ghg.groupby(['M49_Country_Code'], as_index=False)['Y2020'].sum()
df_ghg.rename(columns={'Y2020': 'GHG_2020_Kt'}, inplace=True)

# ：单位转换 Kt -> Gt
df_ghg['GHG_2020_Gt'] = df_ghg['GHG_2020_Kt'] / 1_000_000

# 3.2 人口
df_pop['M49_Country_Code'] = df_pop['M49_Country_Code'].astype(str).str.replace("'", "")
df_pop_total = df_pop[df_pop['Element'] == 'Total Population - Both sexes'].copy()
df_pop_total = df_pop_total[['M49_Country_Code', 'Y2020']]
df_pop_total.rename(columns={'Y2020': 'Pop_2020_1000s'}, inplace=True)

# 3.3 合并
df_data = pd.merge(df_ghg, df_pop_total, on='M49_Country_Code', how='inner')
df_data['Per_Capita_GHG_2020'] = df_data['GHG_2020_Kt'] / df_data['Pop_2020_1000s']


# 4. 映射 (M49 -> NAME -> SHP)

df_dict['M49_Country_Code'] = df_dict['M49_Country_Code'].astype(str).str.replace("'", "")
df_map = df_dict[['M49_Country_Code', 'NAME']].drop_duplicates()
df_data_mapped = pd.merge(df_data, df_map, on='M49_Country_Code', how='left')
df_data_mapped = df_data_mapped.dropna(subset=['NAME'])

# 匹配 SHP
shp_columns = gdf_world.columns.tolist()
join_col = 'NAME' if 'NAME' in shp_columns else shp_columns[0]
gdf_world[join_col] = gdf_world[join_col].astype(str).str.strip()
df_data_mapped['NAME'] = df_data_mapped['NAME'].astype(str).str.strip()

gdf_plot = gdf_world.merge(df_data_mapped, left_on=join_col, right_on='NAME', how='left')


# 5. 可视化优化函数 (配色与分级)

def get_optimized_norm_cmap(data_series):
    """
    针对单边分布(主要是正数)数据优化，使用单色渐变系 (YlOrRd)
    """
    values = data_series.dropna().values
    
    # 过滤掉 0 值以计算更有意义的分位数
    val_positive = values[values > 0]
    
    breaks = []
    
    # 使用分位数来确定颜色分界点，增强对比度
    # 0, 20%, 40%, 60%, 80%, 90%, 95%, 99%, 100%
    if len(val_positive) > 0:
        percentiles = [0, 20, 40, 60, 80, 90, 95, 99, 100]
        breaks = np.nanpercentile(val_positive, percentiles, method='midpoint').tolist()
    else:
        breaks = np.linspace(values.min(), values.max(), 9).tolist()

    # 如果数据中有负值（极少情况），把负值范围加进去，或者简单从0开始
    if values.min() < 0:
        breaks.insert(0, values.min())
    
    # 确保 breaks 唯一且排序
    breaks = sorted(list(set(breaks)))
    
    # 如果 min break > 0，手动插入一个 0 作为起点
    if breaks[0] > 0:
        breaks.insert(0, 0)

    # 配色设置
    # 使用 Matplotlib 内置的 Yellow-Orange-Red 渐变色
    # 这种颜色对于展示 "强度/数量" 非常直观
    # 我们根据 breaks 的数量从 colormap 中取样
    cmap_base = plt.get_cmap('YlOrRd')
    
    # 创建一个离散的 colormap
    # 颜色数量应该等于 区间数量 (len(breaks) - 1)
    n_bins = len(breaks) - 1
    colors = [cmap_base(i/n_bins) for i in range(n_bins)]
    
    cmap_plot = c.ListedColormap(colors)
    norm = mpl.colors.BoundaryNorm(breaks, cmap_plot.N)
    
    return norm, cmap_plot


# 6. 绘图主程序

def plot_map(data_col, output_path, label_text):
    print(f"正在绘制: {output_path} ...")
    
    # 获取优化后的 Norm 和 Cmap
    norm, cmap = get_optimized_norm_cmap(gdf_plot[data_col])
    
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # 绘制底图
    gdf_world.plot(ax=ax, color='#f0f0f0', edgecolor='white', linewidth=0.2)
    
    # 准备 Colorbar 的位置
    divider = make_axes_locatable(ax)
    # size="2%" 使图例变窄
    cax = divider.append_axes("right", size="2%", pad=0.1) 
    
    gdf_plot.plot(column=data_col, 
                  ax=ax,
                  cmap=cmap,
                  norm=norm,
                  linewidth=0.3,
                  edgecolor='black',
                  legend=True,
                  cax=cax, 
                  legend_kwds={
                      'label': label_text, 
                      'orientation': "vertical",
                      'format': "%.3f" # 核心修改：强制显示3位小数
                  },
                  missing_kwds={'color': '#d9d9d9', 'label': 'No Data'})

    # 调整图例字体
    cax.tick_params(labelsize=12)
    cax.set_ylabel(label_text, fontsize=14, labelpad=15)

    ax.set_axis_off()
    
    plt.savefig(output_path, dpi=600, bbox_inches='tight')
    plt.close(fig)
    print(f"保存成功: {output_path}")

# 执行绘图
# 图1：总量 (单位改为 Gt)
plot_map('GHG_2020_Gt', path_total, "Total GHG Emissions 2020 (Gt CO2eq)")

# 图2：人均 (保持原单位，但应用新的配色和显示格式)
plot_map('Per_Capita_GHG_2020', path_percapita, "Per Capita GHG 2020 (Tonnes/capita)")

print("全部绘图完成！")