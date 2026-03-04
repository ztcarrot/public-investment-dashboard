#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产配置管理模块

使用 URL 查询参数存储配置，实现真正的多用户隔离。
"""

import streamlit as st
import json
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class AssetsConfigManager:
    """资产配置管理器"""

    def __init__(self):
        self.storage_key = "investment_user_assets"

    def load(self, secrets_assets=None, default_assets=None) -> List[Dict]:
        """
        加载资产配置

        优先级：session_state > URL参数 > secrets > 默认

        Args:
            secrets_assets: 从 secrets.toml 加载的资产
            default_assets: 默认资产配置

        Returns:
            资产列表
        """
        # 1. 优先从 session_state 加载（当前会话，最新修改）
        if 'assets' in st.session_state:
            assets = st.session_state.assets
            if assets and len(assets) > 0:
                logger.debug(f"从 session_state 加载资产配置: {len(assets)} 个")
                return assets

        # 2. 尝试从 URL 参数加载（多用户独立）
        from utils.url_config import url_config_manager
        url_assets = url_config_manager.load_assets()
        if url_assets and len(url_assets) > 0:
            logger.info(f"从 URL 加载资产配置: {len(url_assets)} 个")
            st.session_state.assets = url_assets
            return url_assets

        # 3. 使用 secrets.toml 的配置（部署者配置的默认资产）
        if secrets_assets and len(secrets_assets) > 0:
            logger.info(f"使用 secrets.toml 资产配置: {len(secrets_assets)} 个")
            st.session_state.assets = secrets_assets
            return secrets_assets

        # 4. 使用默认配置
        if default_assets:
            logger.info(f"使用默认资产配置: {len(default_assets)} 个")
            st.session_state.assets = default_assets
            return default_assets

        # 都没有，返回空列表
        logger.warning("没有找到任何资产配置")
        return []

    def save(self, assets: List[Dict]) -> bool:
        """
        保存资产配置

        Args:
            assets: 资产列表

        Returns:
            是否保存成功
        """
        try:
            if not assets or len(assets) == 0:
                logger.warning("尝试保存空的资产列表，跳过")
                return False

            # 保存到 session_state（当前会话）
            st.session_state.assets = assets

            # 保存到 URL 参数（多用户独立，主要存储）
            from utils.url_config import url_config_manager
            url_config_manager.save_assets(assets)

            # 保存到 localStorage（浏览器存储，辅助）
            self._save_to_localstorage(assets)

            logger.info(f"资产配置已保存: {len(assets)} 个资产")
            return True
        except Exception as e:
            logger.error(f"保存资产配置失败: {e}")
            return False

    def _save_to_localstorage(self, assets: List[Dict]):
        """保存到浏览器 localStorage（辅助存储）"""
        try:
            data = {
                'assets': assets,
                'count': len(assets),
                'updated_at': st.session_state.get('last_update', 'unknown')
            }

            # 使用 JavaScript 保存到 localStorage
            json_str = json.dumps(data, ensure_ascii=False)
            # 转义单引号
            json_str = json_str.replace("'", "\\'")

            js_code = f"""
            <script>
            try {{
                localStorage.setItem('{self.storage_key}', '{json_str}');
                console.log('资产配置已保存到 localStorage: {len(assets)} 个资产');
            }} catch(e) {{
                console.error('保存失败:', e);
            }}
            </script>
            """
            st.components.v1.html(js_code, height=0, width=0)
        except Exception as e:
            logger.warning(f"保存资产配置到 localStorage 失败: {e}")


# 全局实例
assets_config_manager = AssetsConfigManager()
