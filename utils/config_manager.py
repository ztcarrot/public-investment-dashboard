"""
配置管理模块

用于管理投资组合的资产配置，包括默认配置、配置验证和计算功能。
"""

from typing import Dict, List, Optional, Union, Tuple


def get_default_assets() -> List[Dict[str, Union[str, float, None]]]:
    """
    返回默认的资产配置。

    Returns:
        包含4个默认资产的列表：
        - 国债30年 (511130)
        - 300ETF (510300)
        - 工银黄金 (518660)
        - 短债基金 (005350)
    """
    return [
        {
            '代码': '511130',
            '名称': '国债30年',
            '代码类型': '场内ETF',
            '资产类别': '国债',
            '初始份额': 1000.0,
            '初始金额': None
        },
        {
            '代码': '510300',
            '名称': '300ETF',
            '代码类型': '场内ETF',
            '资产类别': '股票',
            '初始份额': 22000.0,
            '初始金额': None
        },
        {
            '代码': '518660',
            '名称': '工银黄金',
            '代码类型': '场内ETF',
            '资产类别': '黄金',
            '初始份额': 8700.0,
            '初始金额': None
        },
        {
            '代码': '005350',
            '名称': '短债基金',
            '代码类型': '债券',
            '资产类别': '现金',
            '初始份额': 90000.0,
            '初始金额': None
        }
    ]


def parse_secrets_assets(assets_data: List[Dict]) -> List[Dict[str, Union[str, float, None]]]:
    """
    解析 secrets.toml 中的资产配置数据。

    Args:
        assets_data: 从 secrets.toml 读取的原始资产配置数据

    Returns:
        解析后的资产配置列表

    Raises:
        ValueError: 如果资产数据格式不正确或验证失败
    """
    if not isinstance(assets_data, list):
        raise ValueError("资产配置必须是一个列表")

    parsed_assets = []
    for idx, asset in enumerate(assets_data, start=1):
        # 验证资产配置
        is_valid, error_msg = validate_asset(asset)
        if not is_valid:
            raise ValueError(f"第 {idx} 个资产配置无效: {error_msg}")

        # 复制资产并移除额外字段（如 '备注'）
        clean_asset = {
            '代码': asset.get('代码', ''),
            '名称': asset.get('名称', ''),
            '代码类型': asset.get('代码类型', ''),
            '资产类别': asset.get('资产类别', ''),
            '初始份额': asset.get('初始份额'),
            '初始金额': None  # 统一使用初始份额
        }
        parsed_assets.append(clean_asset)

    return parsed_assets


def validate_asset(asset: Dict) -> Tuple[bool, str]:
    """
    验证单个资产配置的有效性。

    验证规则：
    - 代码和名称不能为空
    - 代码类型必须是：场内ETF、基金、股票、债券
    - 资产类别必须是：国债、股票、黄金、现金
    - 必须输入初始份额

    Args:
        asset: 待验证的资产配置字典

    Returns:
        (is_valid, error_message 或 '')
        is_valid: 验证是否通过
        error_message: 错误信息，验证通过时为空字符串
    """
    try:
        # 检查必需字段
        required_fields = ['代码', '名称', '代码类型', '资产类别']
        for field in required_fields:
            if field not in asset:
                return False, f"缺少必需字段: {field}"

        # 验证代码和名称不为空
        if not asset['代码'] or not isinstance(asset['代码'], str) or not asset['代码'].strip():
            return False, "代码不能为空"

        if not asset['名称'] or not isinstance(asset['名称'], str) or not asset['名称'].strip():
            return False, "名称不能为空"

        # 验证代码类型
        valid_code_types = ['场内ETF', '基金', '股票', '债券']
        if asset['代码类型'] not in valid_code_types:
            return False, f"代码类型必须是以下之一: {', '.join(valid_code_types)}"

        # 验证资产类别
        valid_asset_categories = ['国债', '股票', '黄金', '现金']
        if asset['资产类别'] not in valid_asset_categories:
            return False, f"资产类别必须是以下之一: {', '.join(valid_asset_categories)}"

        # 验证初始份额
        initial_shares = asset.get('初始份额')

        # 必须输入初始份额
        if initial_shares is None or initial_shares == 0:
            return False, "必须输入初始份额"

        # 验证数值
        try:
            shares = float(initial_shares)
            if shares < 0:
                return False, "初始份额不能为负数"
        except (TypeError, ValueError):
            return False, "初始份额必须是有效的数字"

        # 所有验证通过
        return True, ""

    except Exception as e:
        return False, f"验证过程中发生错误: {str(e)}"
