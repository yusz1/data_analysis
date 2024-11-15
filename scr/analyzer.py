import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from .data_processing import clean_data, get_data_columns, preprocess_data
from .distribution_plots import plot_distributions, plot_single_distribution, export_statistics_to_excel
from .box_plots import plot_boxplots, plot_group_boxplots, plot_all_columns_by_group
from .utils import get_output_dir
from .correlation_plots import plot_correlations    

def setup_matplotlib():
    """设置matplotlib的基本配置"""
    # 设置中文字体为微软雅黑
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
    # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False

def create_output_dirs(data_path):
    """创建输出目录结构
    Args:
        data_path: 数据文件路径
    Returns:
        output_dir: 主输出目录
        single_dist_dir: 单个分布图目录
    """
    # 获取当前时间戳
    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    
    # 获取基础输出目录路径
    base_output_dir = get_output_dir(data_path)
    
    # 添加时间戳到目录名
    output_dir = f"{base_output_dir}_{timestamp}"
    
    # 创建单个分布图的子目录
    single_dist_dir = os.path.join(output_dir, 'single_distributions')
    
    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(single_dist_dir, exist_ok=True)
    
    return output_dir, single_dist_dir

def generate_plots(df, data_columns, data_df, lsl_values, usl_values, output_dir, single_dist_dir, config, is_group_data=False):
    """生成所有基本图表"""
    # 导出统计数据到Excel
    export_statistics_to_excel(df, config, output_dir, is_group_data)
    
    # 生成并保存总体分布图
    if config.PLOT.get('enable_distribution', True):
        print("\n生成分布图...")
        plot_distributions(df, config)
        plt.savefig(os.path.join(output_dir, 'distribution_plots.png'))
        plt.close()
        
        # 为每个数据列生成单独的分布图
        for col in data_columns:
            fig = plot_single_distribution(data_df, col, lsl_values, usl_values, config)
            plt.savefig(os.path.join(single_dist_dir, f'{col}.png'))
            plt.close(fig)
    
    # 生成并保存箱线图
    if config.PLOT.get('enable_boxplot', True):
        print("\n生成箱线图...")
        plot_boxplots(df, config)
        plt.savefig(os.path.join(output_dir, 'boxplot.png'))
        plt.close()
    
    # 生成相关性分析图
    if config.PLOT.get('enable_correlation', True):
        print("\n生成相关性分析图...")
        plot_correlations(df, config)

def analyze_data(data_path: str, config: object) -> str:
    """执行完整的数据分析流程
    Args:
        data_path: 数据文件路径
        config: 配置对象
    Returns:
        output_dir: 输出目录路径
    """
    # 设置matplotlib基本配置
    setup_matplotlib()
    
    # 关闭交互模式
    plt.ioff()
    try:
        # 读取Excel数据文件
        print("读取数据文件...")
        df = pd.read_excel(data_path)
        print(f"数据加载成功！从: {data_path}")
        
        # 数据检查阶段
        print("\n=== 数据检查阶段 ===")
        print("数据形状:", df.shape)
        print("\n检查数据中的无效值...")
        # 获取所有数值类型的列
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        print("数值列:", numeric_columns.tolist())
        
        # 检查每列是否存在无效值
        has_invalid_data = False
        for col in numeric_columns:
            mask = ~np.isfinite(df[col])  # 检查非有限值（NaN或inf）
            if mask.any():
                has_invalid_data = True
                print(f"在列 {col} 中发现无效值，无效值总数: {mask.sum()}")
        
        if not has_invalid_data:
            print("未发现无效值")
        
        # 数据处理阶段
        print("\n=== 开始数据处理 ===")
        print("正在清理数据...")
        df = clean_data(df, config)
        
        # 创建输出目录结构
        output_dir, single_dist_dir = create_output_dirs(data_path)
        # 获取需要分析的数据列
        data_columns = get_data_columns(df, config)
        
        # 首先生成整体分析图
        print("\n=== 生成整体分析图 ===")
        data_df, lsl_values, usl_values = preprocess_data(df)
        generate_plots(df, data_columns, data_df, lsl_values, usl_values,
                      output_dir, single_dist_dir, config)
        
        # 然后检查是否需要生成分组分析图
        group_config = config.DATA_PROCESSING.get('group_analysis', {})
        print("\n=== 检查分组分析配置 ===")
        print(f"group_config: {group_config}")
        
        # 检查是否启用分组分析功能
        if group_config.get('enabled', False):
            print("分组分析已启用")
            group_by = group_config.get('group_by')
            
            if group_by and group_by in df.columns:
                print(f"找到分组列: {group_by}")
                spec_mask = df['SN'].isin(['LSL', 'USL'])
                spec_data = df[spec_mask]
                actual_data = df[~spec_mask]
                groups = actual_data[group_by].unique()
                print(f"发现的{group_by}组: {groups}")
                
                # 1. 生成分组分布图
                if config.PLOT.get('enable_distribution', True):
                    print(f"\n=== 生成{group_by}分组分布图 ===")
                    for group_name in groups:
                        # 合并当前组的数据和规格数据
                        group_data = pd.concat([
                            spec_data,
                            actual_data[actual_data[group_by] == group_name]
                        ])
                        # 创建当前组的输出目录
                        group_output_dir = os.path.join(output_dir, f"{group_by}_{group_name}")
                        group_single_dist_dir = os.path.join(group_output_dir, 'single_distributions')
                        os.makedirs(group_output_dir, exist_ok=True)
                        os.makedirs(group_single_dist_dir, exist_ok=True)
                        
                        print(f"\n处理 {group_by}: {group_name}")
                        # 预处理数据并生成图表
                        data_df, lsl_values, usl_values = preprocess_data(group_data)
                        generate_plots(group_data, data_columns, data_df, lsl_values, usl_values,
                                    group_output_dir, group_single_dist_dir, config, is_group_data=True)
                
                # 2. 生成分组箱线图
                if config.PLOT.get('enable_group_boxplot', True):
                    print(f"\n=== 生成{group_by}分组箱线图 ===")
                    for group_name in groups:
                        # 合并当前组的数据和规格数据
                        group_data = pd.concat([
                            spec_data,
                            actual_data[actual_data[group_by] == group_name]
                        ])
                        # 创建输出目录
                        group_output_dir = os.path.join(output_dir, f"{group_by}_{group_name}")
                        os.makedirs(group_output_dir, exist_ok=True)
                        
                        print(f"\n处理 {group_by}: {group_name}")
                        # 预处理数据并生成箱线图
                        data_df, lsl_values, usl_values = preprocess_data(group_data)
                        fig, ax = plot_boxplots(group_data, config)
                        plt.savefig(os.path.join(group_output_dir, 'boxplot.png'))
                        plt.close(fig)
                
                # 3. 生成分组对比图（每列单独的分组对比）
                if config.PLOT.get('enable_group_boxplot', True):
                    print(f"\n=== 生成{group_by}分组对比图 ===")
                    # 创建分组对比图的专用目录
                    group_plots_dir = os.path.join(output_dir, f'{group_by}_comparison')
                    os.makedirs(group_plots_dir, exist_ok=True)
                    
                    # 为每个数据列生成分组对比图
                    for col in data_columns:
                        print(f"\n处理列: {col}")
                        fig, ax = plot_group_boxplots(df[['SN', group_by, col]], group_by, config)
                        output_path = os.path.join(group_plots_dir, f'{col}_group_comparison.png')
                        fig.savefig(output_path)
                        plt.close(fig)
                        print(f"已保存分组对比图: {output_path}")
                
                # 4. 生成整体分组对比图
                if config.PLOT.get('enable_all_columns_compare', True):
                    print(f"\n=== 生成{group_by}整体分组对比图 ===")
                    group_plots_dir = os.path.join(output_dir, f'{group_by}_comparison')
                    os.makedirs(group_plots_dir, exist_ok=True)
                    
                    print("\n生成整体分组对比图...")
                    fig, ax = plot_all_columns_by_group(df, group_by, config)
                    output_path = os.path.join(group_plots_dir, 'all_columns_comparison.png')
                    fig.savefig(output_path)
                    plt.close(fig)
                    print(f"已保存整体分组对比图: {output_path}")
            else:
                print(f"警告: 未找到分组列 {group_by}")
        else:
            print("分组分析未启用")
            
        return output_dir
            
    except Exception as e:
        print(f"分析过程中出现错误: {str(e)}")
        raise
    finally:
        # 恢复交互模式
        plt.ion()
        print("分组分析未启用")
    
    return output_dir 