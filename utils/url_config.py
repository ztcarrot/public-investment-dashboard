#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL 配置管理模块

使用 Streamlit 的 URL 查询参数来存储配置，实现真正的多用户隔离。
每个用户有独立的 URL，配置保存在 URL 中。

优势：
- 每个用户完全独立的配置
- 可以分享配置 URL
- 配置不会丢失
- 不需要文件系统或数据库
"""

import streamlit as st
import json
import base64
import logging
from datetime import datetime
from typing import Optional, List, Dict
import zlib

logger = logging.getLogger(__name__)


def compress_json(data: any) -> str:
    """压缩并编码 JSON 数据为 URL 安全的字符串"""
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        # 压缩
        compressed = zlib.compress(json_str.encode('utf-8'))
        # Base64 编码
        encoded = base64.b64encode(compressed).decode('utf-8')
        # URL 安全
        return encoded.replace('+', '-').replace('/', '_').replace('=', '')
    except Exception as e:
        logger.warning(f"压缩数据失败: {e}")
        return ""


def decompress_json(encoded_str: str) -> any:
    """解压缩并解码 URL 字符串为 JSON 数据"""
    try:
        if not encoded_str:
            return None
        # URL 安全还原
        encoded = encoded_str.replace('-', '+').replace('_', '/')
        # 补齐 padding
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += '=' * padding
        # Base64 解码
        compressed = base64.b64decode(encoded)
        # 解压
        json_str = zlib.decompress(compressed).decode('utf-8')
        return json.loads(json_str)
    except Exception as e:
        logger.warning(f"解压数据失败: {e}")
        return None


class URLConfigManager:
    """基于 URL 的配置管理器"""

    def __init__(self):
        self.query_params = st.query_params

    def load_date(self) -> Optional[datetime.date]:
        """从 URL 加载日期配置"""
        try:
            if 'date' in self.query_params:
                date_str = self.query_params['date']
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                logger.info(f"从 URL 加载日期: {date}")
                return date
        except Exception as e:
            logger.warning(f"从 URL 加载日期失败: {e}")
        return None

    def save_date(self, date: datetime.date):
        """保存日期配置到 URL"""
        try:
            self.query_params['date'] = date.strftime('%Y-%m-%d')
            logger.info(f"日期已保存到 URL: {date}")
        except Exception as e:
            logger.error(f"保存日期到 URL 失败: {e}")

    def load_assets(self) -> Optional[List[Dict]]:
        """从 URL 加载资产配置"""
        try:
            if 'assets' in self.query_params:
                encoded = self.query_params['assets']
                assets = decompress_json(encoded)
                if assets and isinstance(assets, list):
                    logger.info(f"从 URL 加载资产配置: {len(assets)} 个")
                    return assets
        except Exception as e:
            logger.warning(f"从 URL 加载资产配置失败: {e}")
        return None

    def save_assets(self, assets: List[Dict]):
        """保存资产配置到 URL"""
        try:
            if not assets:
                # 如果资产为空，删除参数
                if 'assets' in self.query_params:
                    del self.query_params['assets']
                return

            encoded = compress_json(assets)
            if encoded:
                self.query_params['assets'] = encoded
                logger.info(f"资产配置已保存到 URL: {len(assets)} 个资产")
        except Exception as e:
            logger.error(f"保存资产配置到 URL 失败: {e}")


# 全局实例
url_config_manager = URLConfigManager()
