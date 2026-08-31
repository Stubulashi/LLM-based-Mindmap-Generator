"""
E: IO utilities — JSON read/write, result persistence
C: IO 工具 — JSON 读写、结果持久化
"""
import json
import glob
import os
from datetime import datetime
from typing import Any, Optional

# E: Supported audio extensions (shared by all audio-discovery call sites)
# C: 支持的音频扩展名（所有音频发现调用点共享）
AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".ogg", ".flac")


def discover_audio_files(dir_path: str) -> list[str]:
    """
    E: Return sorted, de-duplicated audio file paths under a directory.
        Returns [] when the directory is missing or contains no audio files.
    C: 返回目录下排序、去重后的音频文件路径列表；
        目录不存在或无音频文件时返回空列表。
    """
    if not dir_path or not os.path.isdir(dir_path):
        return []
    found: list[str] = []
    for ext in AUDIO_EXTS:
        found.extend(glob.glob(os.path.join(dir_path, f"*{ext}")))
    return sorted(set(found))


def read_json(filepath: str) -> Optional[dict]:
    """E: Safely read JSON file / C: 安全读取 JSON 文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"[IO] 读取失败 / Read failed {filepath}: {e}")
        return None


def write_json(filepath: str, data: Any, indent: int = 2) -> bool:
    """E: Write JSON file / C: 写入 JSON 文件"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        print(f"[IO] 写入失败 / Write failed {filepath}: {e}")
        return False


def save_intermediate_result(results: dict, tag: str, output_dir: str = "evaluation/data") -> str:
    """
    E: Save intermediate evaluation result to JSON file
    C: 保存中间评估结果到 JSON 文件
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"{tag}_{ts}.json")
    write_json(path, results)
    return path


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
