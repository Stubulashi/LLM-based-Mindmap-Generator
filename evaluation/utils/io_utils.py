"""
E: IO utilities — JSON read/write, result persistence
C: IO 工具 — JSON 读写、结果持久化
"""
import json
import os
from datetime import datetime
from typing import Any, Optional


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
"""
C: IO 工具 — JSON 读写、结果持久化
E: IO utilities — JSON read/write, result persistence
"""
import json
import os
from datetime import datetime
from typing import Any, Optional


def read_json(filepath: str) -> Optional[dict]:
    """C: 安全读取 JSON 文件 / E: Safely read JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"[IO] 读取失败 / Read failed {filepath}: {e}")
        return None


def write_json(filepath: str, data: Any, indent: int = 2) -> bool:
    """C: 写入 JSON 文件 / E: Write JSON file"""
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
    C: 保存中间评估结果到 JSON 文件
    E: Save intermediate evaluation result to JSON file
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"{tag}_{ts}.json")
    write_json(path, results)
    return path


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
