#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用户关心的债券数据获取
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_fetcher import DataFetcher
from datetime import datetime, timedelta

def test_user_bond(code, name):
    """测试单个债券"""
    print(f"\n{'='*60}")
    print(f"测试: {name} ({code})")
    print(f"{'='*60}")

    fetcher = DataFetcher()

    # 计算测试日期范围（最近30天）
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    print(f"日期范围: {start_date} 至 {end_date}")

    # 构造资产配置
    asset = {
        '代码': code,
        '名称': name,
        '代码类型': '债券',
        '资产类别': '国债',
        '初始份额': 1000
    }

    # 获取数据
    df = fetcher.fetch_asset_data(asset, start_date, end_date)

    if df is not None and not df.empty:
        print(f"✅ 成功获取 {len(df)} 条数据")
        print(f"\n最新数据:")
        print(df.tail(3))
        return True
    else:
        print(f"❌ 未获取到数据")
        return False


def main():
    """主测试函数"""
    print("测试用户关心的债券数据获取")
    print("="*60)

    # 用户关心的债券
    test_cases = [
        ("511130", "国债30年ETF"),
        ("19789", "25特国06"),
        ("019789", "25特国06（完整代码）"),
    ]

    results = {
        '成功': [],
        '失败': []
    }

    for code, name in test_cases:
        success = test_user_bond(code, name)
        if success:
            results['成功'].append((code, name))
        else:
            results['失败'].append((code, name))

    # 打印汇总
    print(f"\n\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    print(f"\n✅ 成功 ({len(results['成功'])} 个):")
    for code, desc in results['成功']:
        print(f"   {code}: {desc}")

    print(f"\n❌ 失败 ({len(results['失败'])} 个):")
    for code, desc in results['失败']:
        print(f"   {code}: {desc}")


if __name__ == "__main__":
    main()
