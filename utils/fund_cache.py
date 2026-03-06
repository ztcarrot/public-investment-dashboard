#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金数据缓存管理模块

使用本地 JSON 文件缓存基金筛选结果，减少 API 调用。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class FundCacheManager:
    """基金数据缓存管理器"""

    def __init__(self, cache_file: str = "cache/fund_screening.json"):
        """
        初始化缓存管理器

        Args:
            cache_file: 缓存文件路径
        """
        self.cache_file = cache_file
        self.cache_dir = os.path.dirname(cache_file)

        # 确保缓存目录存在
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"创建缓存目录: {self.cache_dir}")

    def load(self) -> Optional[Dict]:
        """
        从文件加载缓存数据

        Returns:
            缓存数据字典，如果不存在或已损坏返回 None
        """
        try:
            if not os.path.exists(self.cache_file):
                logger.debug(f"缓存文件不存在: {self.cache_file}")
                return None

            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"成功加载缓存: {self.cache_file}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"缓存文件损坏，将重新获取数据: {e}")
            # 删除损坏的缓存文件
            try:
                os.remove(self.cache_file)
                logger.info(f"已删除损坏的缓存文件: {self.cache_file}")
            except Exception as remove_error:
                logger.error(f"删除损坏缓存文件失败: {remove_error}")
            return None
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return None

    def save(self, data: Dict) -> bool:
        """
        保存数据到缓存文件

        Args:
            data: 要缓存的数据字典

        Returns:
            是否保存成功
        """
        try:
            # 添加更新时间戳
            data['update_time'] = datetime.now().strftime('%Y-%m-%d')

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"缓存已保存: {self.cache_file}")
            return True

        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
            return False

    def is_expired(self, days: int = 7) -> bool:
        """
        检查缓存是否过期

        Args:
            days: 过期天数阈值，默认7天

        Returns:
            是否过期
        """
        data = self.load()
        if not data:
            return True

        try:
            update_time_str = data.get('update_time')
            if not update_time_str:
                return True

            update_time = datetime.strptime(update_time_str, '%Y-%m-%d')
            expire_time = datetime.now() - timedelta(days=days)

            is_expired = update_time < expire_time

            if is_expired:
                logger.info(f"缓存已过期: {update_time_str}")
            else:
                age_days = (datetime.now() - update_time).days
                logger.debug(f"缓存未过期，已使用 {age_days} 天")

            return is_expired

        except Exception as e:
            logger.error(f"检查缓存过期失败: {e}")
            return True

    def get_cache_age_days(self) -> int:
        """
        获取缓存年龄（天数）

        Returns:
            缓存年龄天数，如果无法获取返回 -1
        """
        data = self.load()
        if not data:
            return -1

        try:
            update_time_str = data.get('update_time')
            if not update_time_str:
                return -1

            update_time = datetime.strptime(update_time_str, '%Y-%m-%d')
            age = (datetime.now() - update_time).days
            return age

        except Exception as e:
            logger.error(f"获取缓存年龄失败: {e}")
            return -1

    def clear(self) -> bool:
        """
        清除缓存文件

        Returns:
            是否清除成功
        """
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info(f"缓存已清除: {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False


# 全局实例
fund_cache_manager = FundCacheManager()
