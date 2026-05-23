from json_tools import load_json, save_json
from pathlib import Path
import os

MEMORY_FILE = Path(__file__).parent / "outputs" / "memory.json"

# 读取内存
def read_memory():
    # 如果文件不存在，返回空列表
    if not os.path.exists(MEMORY_FILE):
        return []
    # 读取文件内容
    data = load_json(MEMORY_FILE)
    return data.get("messages", [])

# 保存内存
def save_memory(messages):
    # 保存消息到文件
    data = {
        "messages": messages
    }
    save_json(data, MEMORY_FILE)

# 添加消息到内存
def append_message(messages,role,content):
    # 添加消息到列表
    message = {
        "role": role,
        "content": content
    }
    messages.append(message)
