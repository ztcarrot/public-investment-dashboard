"""
配置管理模块

用于管理投资组合的资产配置，包括默认配置、配置验证和计算功能。
"""

from typing import Dict, List, Optional, Union


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
        try:
            # 验证资产配置
            validated_asset = validate_asset(asset)
            parsed_assets.append(validated_asset)
        except ValueError as e:
            raise ValueError(f"第 {idx} 个资产配置无效: {str(e)}")

    return parsed_assets


def validate_asset(asset: Dict) -> Dict[str, Union[str, float, None]]:
    """
    验证单个资产配置的有效性。

    验证规则：
    - 代码和名称不能为空
    - 代码类型必须是：场内ETF、基金、股票、债券
    - 资产类别必须是：国债、股票、黄金、现金
    - 初始份额和初始金额互斥（只能输入其中一个）

    Args:
        asset: 待验证的资产配置字典

    Returns:
        验证通过后的资产配置字典

    Raises:
        ValueError: 如果资产配置不符合验证规则
    """
    # 检查必需字段
    required_fields = ['代码', '名称', '代码类型', '资产类别']
    for field in required_fields:
        if field not in asset:
            raise ValueError(f"缺少必需字段: {field}")

    # 验证代码和名称不为空
    if not asset['代码'] or not isinstance(asset['代码'], str) or not asset['代码'].strip():
        raise ValueError("代码不能为空")

    if not asset['名称'] or not isinstance(asset['名称'], str) or not asset['名称'].strip():
        raise ValueError("名称不能为空")

    # 验证代码类型
    valid_code_types = ['场内ETF', '基金', '股票', '债券']
    if asset['代码类型'] not in valid_code_types:
        raise ValueError(f"代码类型必须是以下之一: {', '.join(valid_code_types)}")

    # 验证资产类别
    valid_asset_categories = ['国债', '股票', '黄金', '现金']
    if asset['资产类别'] not in valid_asset_categories:
        raise ValueError(f"资产类别必须是以下之一: {', '.join(valid_asset_categories)}")

    # 验证初始份额和初始金额的互斥性
    initial_shares = asset.get('初始份额')
    initial_amount = asset.get('初始金额')

    # 如果两个都为 None，则设置初始份额为 0.0
    if initial_shares is None and initial_amount is None:
        asset['初始份额'] = 0.0
        asset['初始金额'] = None
    # 如果两个都有值，则报错
    elif initial_shares is not None and initial_amount is not None:
        raise ValueError("初始份额和初始金额只能输入其中一个")
    # 如果有值，验证是否为正数
    elif initial_shares is not None:
        try:
            shares = float(initial_shares)
            if shares < 0:
                raise ValueError("初始份额不能为负数")
            asset['初始份额'] = shares
            asset['初始金额'] = None
        except (TypeError, ValueError):
            raise ValueError("初始份额必须是有效的数字")
    elif initial_amount is not None:
        try:
            amount = float(initial_amount)
            if amount < 0:
                raise ValueError("初始金额不能为负数")
            asset['初始份额'] = None
            asset['初始金额'] = amount
        except (TypeError, ValueError):
            raise ValueError("初始金额必须是有效的数字")

    return asset


def calculate_shares_or_amount(asset: Dict, current_price: float) -> Dict[str, float]:
    """
    根据当前价格计算份额或金额。

    如果资产配置了初始份额，则计算对应的金额。
    如果资产配置了初始金额，则计算对应的份额。

    Args:
        asset: 资产配置字典
        current_price: 资产的当前价格

    Returns:
        包含计算结果的字典，格式为：
        {
            'shares': float,  # 份额
            'amount': float   # 金额
        }

    Raises:
        ValueError: 如果价格无效或无法计算
    """
    # 验证当前价格
    if current_price is None or current_price <= 0:
        raise ValueError("当前价格必须大于0")

    initial_shares = asset.get('初始份额')
    initial_amount = asset.get('初始金额')

    # 根据初始份额计算金额
    if initial_shares is not None:
        shares = float(initial_shares)
        amount = shares * current_price
        return {
            'shares': shares,
            'amount': amount
        }

    # 根据初始金额计算份额
    elif initial_amount is not None:
        amount = float(initial_amount)
        shares = amount / current_price
        return {
            'shares': shares,
            'amount': amount
        }

    # 如果两者都为 None，返回 0
    else:
        return {
            'shares': 0.0,
            'amount': 0.0
        }
