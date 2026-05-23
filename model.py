import json
import requests
from parse_tool_call_result import parse_tool_call_result



# 调用模型生成文本
def ask_local_model(user_input, model_name, tool_info=None, memory_messages=None):
    memory_text = ""

    if memory_messages:
        memory_text = json.dumps(memory_messages[-10:], ensure_ascii=False, indent=2)

    if tool_info is not None:
        prompt = f"""
你是一个 Agent 助手。

历史对话记忆：
{memory_text}

用户问题：
{user_input}

当前可用工具：
{tool_info}

回答规则：
1. 如果用户询问你有什么工具、能使用哪些工具、工具列表，请根据“当前可用工具”回答。
2. 如果用户是普通聊天或普通问题，请结合“历史对话记忆”和当前问题正常回答。
3. 不要编造当前工具列表之外的工具。
4. 不要输出 JSON，直接用自然语言回答。
"""
    else:
        prompt = f"""
历史对话记忆：
{memory_text}

用户问题：
{user_input}

请结合历史对话记忆回答用户。
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]

# 调用模型生成JSON数据是否要调用工具函数
def get_tool_call_from_model(user_input,model_name,tools_info):
    prompt = f"""
你是一个工具调用决策器。

用户问题是：
{user_input}

工具列表是：
{tools_info}

你只能返回 JSON，不要返回解释，不要返回 markdown。

如果用户要查询 GitHub 用户，返回这个格式：
{{
  "need_tool": true,
  "success": true,
  "tool_name": "get_github_user",
  "message": "查询 GitHub 用户 octocat 的信息",
  "arguments": {{
    "username": "octocat"
  }}
}}

如果不需要工具，返回这个格式：
{{
  "need_tool": false,
  "success": true,
  "tool_name": null,
  "message": "这个问题不需要调用工具",
  "arguments": null,
}}
"""
    model_text = ask_local_model(prompt,model_name)
    model_result = parse_tool_call_result(model_text)
    return model_result


# 调用模型生成最终结果
def get_final_answer_from_model(user_input,tool_result,model_name):
    prompt = f"""
用户问题是：
{user_input}

工具执行结果是：
{json.dumps(tool_result, ensure_ascii=False, indent=2)}

请根据工具结果生成最终回答。

要求：
1. 如果 success 是 true，回答里必须包含 login、public_repos、followers、html_url。
2. 如果 success 是 false，不能说查询成功，要说明失败原因。
3. 直接回答，不要输出 JSON。
"""
    model_text = ask_local_model(prompt,model_name)
    return model_text
