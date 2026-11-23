"""解析日报目录内的展示文件，保留相对层级并检查目录边界。"""
from pathlib import Path

if __package__:
    from .page_renderer import daily_source_status
else:
    from page_renderer import daily_source_status


def resolve_daily_show_source(directory, source):
    directory = Path(directory)
    source = str(source)
    status = daily_source_status(directory, source)
    if status == 0:
        return directory / source
    if status == 1:
        raise ValueError('show_source 必须是日报目录内的HTML相对路径')
    if status == 2:
        raise ValueError('show_source 超出日报目录')
    # 原解析器保留文件系统错误及未安装 C++ 构建时的行为。
    if (not source.endswith('.html') or '\\' in source or ':' in source
            or any(part in ('', '.', '..') for part in source.split('/'))):
        raise ValueError('show_source 必须是日报目录内的HTML相对路径')
    target = directory / source
    if not target.resolve().is_relative_to(directory.resolve()):
        raise ValueError('show_source 超出日报目录')
    return target
