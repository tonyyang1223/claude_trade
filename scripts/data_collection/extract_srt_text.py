#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRT字幕提取脚本
遍历课程目录，提取所有srt字幕文件的文字内容，按课程章节合并输出
"""

import os
import re
from pathlib import Path
from collections import defaultdict


def extract_text_from_srt(srt_path):
    """从SRT文件中提取纯文本内容"""
    text_lines = []
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(srt_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(srt_path, 'r', encoding='gbk') as f:
                content = f.read()

    # SRT格式: 序号 -> 时间轴 -> 字幕文本 -> 空行
    # 匹配模式：跳过序号行和时间轴行，只保留文本
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        # 跳过序号行（纯数字）
        if line.isdigit():
            continue
        # 跳过时间轴行 (格式: 00:00:00,000 --> 00:00:00,000)
        if '-->' in line:
            continue
        # 跳过只包含数字和标点的行
        if re.match(r'^[\d\s\-\:\,\.\>]+$', line):
            continue
        # 这是字幕文本
        text_lines.append(line)

    return ' '.join(text_lines)


def find_all_srt_files(root_dir):
    """查找所有srt文件，按课程章节分组"""
    chapters = defaultdict(list)
    root_path = Path(root_dir)

    for srt_file in root_path.rglob('*.srt'):
        # 跳过目录（有些.srt结尾的是目录）
        if srt_file.is_dir():
            continue

        # 获取相对路径
        rel_path = srt_file.relative_to(root_path)
        parts = rel_path.parts

        # 确定章节名（第一级目录）
        if len(parts) >= 1:
            chapter = parts[0]
        else:
            chapter = "Unknown"

        # 获取文件名（不含扩展名）
        filename = srt_file.stem

        chapters[chapter].append({
            'path': srt_file,
            'name': filename,
            'sort_key': extract_sort_key(filename)
        })

    return chapters


def extract_sort_key(filename):
    """从文件名提取排序用的数字"""
    # 匹配开头的数字或translate后的数字
    match = re.match(r'(translate)?(\d+)', filename)
    if match:
        return int(match.group(2))
    return 999


def main():
    # 课程目录路径 - 使用环境变量或默认路径
    course_dir = os.environ.get('COURSE_DIR')
    if course_dir:
        course_dir = Path(course_dir)
    else:
        # 默认路径
        course_dir = Path(r'd:\gitpro\claude_trading\docs\courses\数字货币课程')

    print(f"正在扫描目录: {course_dir}")
    print("-" * 60)

    # 查找所有srt文件
    chapters = find_all_srt_files(course_dir)

    if not chapters:
        print("未找到任何srt文件")
        return

    # 输出目录
    output_dir = course_dir / "extracted_texts"
    output_dir.mkdir(exist_ok=True)

    # 按章节处理
    total_chapters = len(chapters)
    for idx, (chapter, files) in enumerate(sorted(chapters.items()), 1):
        print(f"[{idx}/{total_chapters}] 处理章节: {chapter}")

        # 按文件名排序
        files.sort(key=lambda x: x['sort_key'])

        # 合并该章节所有字幕
        chapter_text = []
        for file_info in files:
            text = extract_text_from_srt(file_info['path'])
            if text.strip():
                chapter_text.append(f"【{file_info['name']}】\n{text}")

        # 写入输出文件
        output_file = output_dir / f"{chapter}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(chapter_text))

        print(f"  -> 已提取 {len(files)} 个字幕文件")

    print("-" * 60)
    print(f"完成！输出目录: {output_dir}")
    print(f"共处理 {total_chapters} 个章节")


if __name__ == '__main__':
    main()
