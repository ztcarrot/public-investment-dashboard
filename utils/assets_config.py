#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产配置管理模块

支持多种存储方式：
1. URL 查询参数（Streamlit Cloud 多用户部署，每个用户独立）
2. 本地文件存储（用于本地开发，用户自定义的资产）
3. Streamlit Secrets（用于部署者配置的默认资产）
4. 默认配置（后备方案）
"""

import streamlit as st
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Union

logger = logging.getLogger(__name__)


class AssetsConfigManager:
    """资产配置管理器"""

    def __init__(self):
        self.file_path = Path(__file__).parent.parent / "data" / "user_assets.json"
        self.storage_key = "investment_user_assets"

    def load(self, secrets_assets=None, default_assets=None) -> List[Dict]:
        """
        加载资产配置

        优先级：session_state > URL参数 > 文件 > secrets > 默认

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

        # 3. 尝试从文件加载（用户自定义的持久化配置）
        file_assets = self._load_from_file()
        if file_assets and len(file_assets) > 0:
            logger.info(f"从文件加载用户资产配置: {len(file_assets)} 个")
            st.session_state.assets = file_assets
            return file_assets

        # 4. 使用 secrets.toml 的配置（部署者配置的默认资产）
        if secrets_assets and len(secrets_assets) > 0:
            logger.info(f"使用 secrets.toml 资产配置: {len(secrets_assets)} 个")
            st.session_state.assets = secrets_assets
            return secrets_assets

        # 5. 使用默认配置
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

            # 保存到文件（持久化，后备存储）
            self._save_to_file(assets)

            # 保存到 localStorage（浏览器存储，辅助）
            self._save_to_localstorage(assets)

            logger.info(f"资产配置已保存: {len(assets)} 个资产")
            return True
        except Exception as e:
            logger.error(f"保存资产配置失败: {e}")
            return False

    def _load_from_file(self) -> Optional[List[Dict]]:
        """从文件加载"""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    assets = data.get('assets', [])
                    if assets and len(assets) > 0:
                        return assets
        except Exception as e:
            logger.warning(f"从文件加载资产配置失败: {e}")
        return None

    def _save_to_file(self, assets: List[Dict]):
        """保存到文件"""
        try:
            # 确保目录存在
            self.file_path.parent.mkdir(exist_ok=True)

            data = {
                'assets': assets,
                'updated_at': st.session_state.get('last_update', 'unknown'),
                'count': len(assets)
            }

            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"资产配置已保存到文件: {self.file_path}")
        except Exception as e:
            logger.warning(f"保存资产配置到文件失败: {e}")

    def _save_to_localstorage(self, assets: List[Dict]):
        """保存到浏览器 localStorage"""
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
