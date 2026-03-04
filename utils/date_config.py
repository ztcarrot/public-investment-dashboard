#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日期配置管理模块

支持多种存储方式：
1. URL 查询参数（Streamlit Cloud 多用户部署，每个用户独立）
2. 本地文件存储（用于本地开发）
3. 浏览器 localStorage（补充存储，刷新时恢复）
"""

import streamlit as st
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DateConfigManager:
    """日期配置管理器"""

    def __init__(self):
        self.file_path = Path(__file__).parent.parent / "data" / "date_config.json"
        self.storage_key = "investment_start_date"

    def load(self) -> Optional[datetime]:
        """
        加载日期配置

        优先级：session_state > URL参数 > 文件 > 默认值
        """
        # 1. 优先从 session_state 加载（当前会话）
        if 'start_date' in st.session_state:
            logger.debug(f"从 session_state 加载日期: {st.session_state.start_date}")
            return st.session_state.start_date

        # 2. 尝试从 URL 参数加载（多用户独立）
        from utils.url_config import url_config_manager
        url_result = url_config_manager.load_date()
        if url_result:
            logger.info(f"从 URL 加载日期: {url_result}")
            st.session_state.start_date = url_result
            return url_result

        # 3. 尝试从文件加载（本地开发）
        file_result = self._load_from_file()
        if file_result:
            logger.info(f"从文件加载日期: {file_result}")
            st.session_state.start_date = file_result
            return file_result

        # 4. 使用默认值
        default_date = datetime(2025, 1, 1).date()
        logger.info(f"使用默认日期: {default_date}")
        st.session_state.start_date = default_date
        return default_date

    def save(self, date: datetime.date) -> bool:
        """
        保存日期配置

        Args:
            date: 要保存的日期

        Returns:
            是否保存成功
        """
        try:
            # 保存到 session_state（当前会话）
            st.session_state.start_date = date

            # 保存到 URL 参数（多用户独立，主要存储）
            from utils.url_config import url_config_manager
            url_config_manager.save_date(date)

            # 保存到 localStorage（浏览器存储，辅助）
            self._save_to_localstorage(date)

            # 保存到文件（本地开发，后备存储）
            self._save_to_file(date)

            logger.info(f"日期配置已保存: {date}")
            return True
        except Exception as e:
            logger.error(f"保存日期配置失败: {e}")
            return False

    def _load_from_localstorage(self) -> Optional[datetime.date]:
        """从浏览器 localStorage 加载"""
        try:
            # 注意：由于 Streamlit 安全限制，无法直接从 localStorage 读取
            # 这里返回 None，依赖 session_state 或文件
            return None
        except Exception as e:
            logger.warning(f"从 localStorage 加载失败: {e}")
            return None

    def _save_to_localstorage(self, date: datetime.date):
        """保存到浏览器 localStorage"""
        try:
            config = {
                'start_date': date.strftime('%Y-%m-%d'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 使用 JavaScript 保存到 localStorage
            json_str = json.dumps(config, ensure_ascii=False)
            js_code = f"""
            <script>
            try {{
                localStorage.setItem('{self.storage_key}', '{json_str}');
                console.log('日期配置已保存到 localStorage: {date}');
            }} catch(e) {{
                console.error('保存失败:', e);
            }}
            </script>
            """
            st.components.v1.html(js_code, height=0, width=0)
        except Exception as e:
            logger.warning(f"保存到 localStorage 失败: {e}")

    def _load_from_file(self) -> Optional[datetime.date]:
        """从文件加载"""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    date_str = config.get('start_date')
                    if date_str:
                        return datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception as e:
            logger.warning(f"从文件加载失败: {e}")
        return None

    def _save_to_file(self, date: datetime.date):
        """保存到文件"""
        try:
            # 确保目录存在
            self.file_path.parent.mkdir(exist_ok=True)

            config = {
                'start_date': date.strftime('%Y-%m-%d'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.debug(f"日期配置已保存到文件: {self.file_path}")
        except Exception as e:
            logger.warning(f"保存到文件失败: {e}")


# 全局实例
date_config_manager = DateConfigManager()
