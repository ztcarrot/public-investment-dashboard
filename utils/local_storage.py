#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalStorage 管理 - 使用纯 JavaScript 实现浏览器端持久化
"""

import streamlit as st
import json


def save_to_localstorage(key, data):
    """
    保存数据到 LocalStorage

    Args:
        key: 存储键名
        data: 要保存的数据（字典，会自动JSON序列化）

    Returns:
        bool: 是否成功
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False)

        # 使用 JavaScript 直接操作 localStorage
        js_code = f"""
        <script>
        try {{
            localStorage.setItem('{key}', '{json_str}');
            console.log('数据已保存到 LocalStorage: {key}');
        }} catch(e) {{
            console.error('保存失败:', e);
        }}
        </script>
        """
        st.components.v1.html(js_code, height=0, width=0)
        return True
    except Exception as e:
        st.error(f"保存到 LocalStorage 失败: {str(e)}")
        return False


def load_from_localstorage(key):
    """
    从 LocalStorage 加载数据

    注意：由于浏览器安全限制，JavaScript 无法直接将数据返回给 Python
    此函数主要用于记录读取意图，实际加载需要通过其他方式实现

    Args:
        key: 存储键名

    Returns:
        dict: 存储的数据，如果不存在则返回 None
    """
    # Streamlit 的安全限制使得直接从 localStorage 读取变得困难
    # 我们暂时返回 None，依赖 session_state
    return None


def init_session_state():
    """
    初始化 session state 中的配置缓存
    """
    if 'assets_config' not in st.session_state:
        st.session_state.assets_config = None

    if 'config_loaded' not in st.session_state:
        st.session_state.config_loaded = False


def save_to_session(key, data):
    """
    保存数据到 session state（作为 LocalStorage 的备选方案）

    Args:
        key: 存储键名
        data: 要保存的数据
    """
    st.session_state[key] = data


def load_from_session(key):
    """
    从 session state 加载数据

    Args:
        key: 存储键名

    Returns:
        存储的数据，如果不存在则返回 None
    """
    return st.session_state.get(key, None)
