#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalStorage 组件 - 支持浏览器端配置持久化
"""

import streamlit.components.v1 as components
import os

# 声明组件
_release = True
_local_storage_component = components.declare_component(
    "local_storage",
    path=os.path.dirname(__file__) + "/local_storage"
)


def local_storage_component(key, value=None, get=True):
    """
    LocalStorage 组件的底层接口

    Args:
        key: localStorage 的键
        value: 要保存的值（当 get=False 时使用）
        get: True=读取, False=写入

    Returns:
        读取时返回存储的值，写入时返回 None
    """
    return _local_storage_component(key=key, value=value, get=get)


def save_to_localstorage(key, data):
    """
    保存数据到 LocalStorage

    Args:
        key: 存储键名
        data: 要保存的数据（字典，会自动JSON序列化）

    Returns:
        None
    """
    try:
        import json
        json_str = json.dumps(data)
        local_storage_component(key=key, value=json_str, get=False)
    except Exception as e:
        import streamlit as st
        st.error(f"保存到 LocalStorage 失败: {str(e)}")


def load_from_localstorage(key):
    """
    从 LocalStorage 加载数据

    Args:
        key: 存储键名

    Returns:
        存储的数据（字典），如果不存在或出错则返回 None
    """
    try:
        import json
        json_str = local_storage_component(key=key, get=True)
        if json_str:
            return json.loads(json_str)
        return None
    except Exception as e:
        import streamlit as st
        st.error(f"从 LocalStorage 加载失败: {str(e)}")
        return None
