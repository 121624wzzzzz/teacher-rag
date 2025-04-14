# 专业样式配置
STYLES = {
    "default": {
        "font": "微软雅黑",
        "size": 14,
        "color": (89, 89, 89),  # 深灰色
        "align": "left"
    },
    "cover_title": {
        "font": "微软雅黑 Light",
        "size": 44,
        "color": (0, 84, 149),  # 主题主色
        "bold": True,
        "align": "center"
    },
    "cover_subtitle": {
        "font": "微软雅黑",
        "size": 24,
        "color": (118, 118, 118),  # 次色灰
        "align": "center"
    },
    "section_title": {
        "font": "微软雅黑",
        "size": 32,
        "color": (0, 84, 149),  # 主色蓝
        "bold": True,
        "align": "left"
    },
    "content_title": {
        "font": "微软雅黑",
        "size": 28,
        "color": (0, 84, 149),  # 主色蓝
        "bold": True,
        "align": "left"
    },
    "content_text": {
        "font": "微软雅黑",
        "size": 14,
        "color": (89, 89, 89),  # 深灰色
        "align": "left"
    },
    "footer": {
        "font": "微软雅黑",
        "size": 12,
        "color": (118, 118, 118),  # 次色灰
        "align": "right"
    },
    # 更多样式...
}

# 颜色主题配置
COLORS = {
    "default": {
        "background": (255, 255, 255),  # 白色背景
        "primary": (0, 84, 149),       # 主色蓝
        "secondary": (118, 118, 118),  # 次色灰
        "accent": (255, 153, 0),       # 强调色橙
        "chart_colors": [
            (0, 84, 149), (255, 153, 0), (100, 181, 64)
        ]
    },
    "blue": {
        "background": (240, 248, 255),  # 浅蓝色背景
        "primary": (0, 120, 215),       # 主色深蓝
        "secondary": (96, 125, 139),    # 次色灰蓝
        "accent": (0, 188, 212),        # 强调色青蓝
        "chart_colors": [
            (0, 120, 215), (0, 188, 212), (96, 125, 139)
        ]
    },
    # 更多主题...
}

# 布局配置
LAYOUTS = {
    "cover": 0,
    "toc": 1,
    "section": 2,
    "content_text": 3,
    "content_image": 4,
    "chart": 5,
    # 更多布局...
}