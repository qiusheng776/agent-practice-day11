from email import message
from model import get_tool_call_from_model, get_final_answer_from_model, ask_local_model    
from json_tools import save_json
from run_tool import run_tool, list_tools
from pathlib import Path
from memory_store import read_memory, append_message,save_memory

import time
 

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / 'outputs'
# 记录一次对话的所有信息
session_file = OUTPUT_DIR / 'session.json'

user_text = input("请输入用户输入: ")
text_input = [user_text]

model_name = 'qwen3:8b'

def run_agent(text_input,model_name):
    tool_info = list_tools()
    # 记录全部用户输入的处理结果
    result = []
    # 统计每个状态的次数
    summary = {'need_tool_count': 0,
               'tool_failed_count': 0,
               'tool_success_count': 0,
               'no_tool_count': 0,
               'total': 0
               }
    
    # 遍历用户输入
    for user_input in text_input:

        timing = {
            'total_seconds': 0,
            'tool_decision_seconds': 0,
            'tool_execution_seconds': 0,
            'final_answer_seconds': 0
        }
        
        # 总读秒时间
        total_seconds = time.time()
        
        summary['total'] += 1
        status = ''
        # 记录单个用户的上下文
        message = []
        message.append({
            'role': 'user',
            'content': user_input
        })
        # 每个输入都先交给模型判断是否需要工具
        tool_decision_seconds = time.time()
        model_result = get_tool_call_from_model(user_input, model_name, tool_info)
        timing['tool_decision_seconds'] = round(time.time() - tool_decision_seconds, 2)

        if not model_result['success']:
            status = 'llm_json_failed'
            final_answer = '工具调用解析失败,无法安全执行工具'
            message.append({
                'role': 'assistant',
                'type': 'final_answer',
                'content': final_answer
            })
            timing['total_seconds'] = round(time.time() - total_seconds, 2)

        else:
            message.append({
                'role': 'assistant',
                'type': 'tool_call',
                'content': model_result
            })

            # 如果返回值为True，调用工具调用
            if model_result['need_tool'] == True:
                summary['need_tool_count'] += 1
                # 工具调用时间
                tool_execution_seconds = time.time()
                # 调用工具
                tool_result = run_tool(model_result['tool_name'], model_result['arguments'])
                timing['tool_execution_seconds'] = round(time.time() - tool_execution_seconds, 2)
                message.append({
                    'role': 'tool',
                    'tool_name': model_result['tool_name'],
                    'content': tool_result
                })

                # 如果工具调用失败，返回失败信息
                if not tool_result['success']:
                    status = 'tool_failed'
                    summary['tool_failed_count'] += 1
                    # llm返回最终结果的时间
                    final_answer_seconds = time.time()
                    final_answer = get_final_answer_from_model(user_input, tool_result, model_name)
                    timing['final_answer_seconds'] = round(time.time() - final_answer_seconds, 2)
                    message.append({
                        'role': 'assistant',
                        'type': 'final_answer',
                        'content': final_answer
                    })
                    timing['total_seconds'] = round(time.time() - total_seconds, 2)

                # 如果工具调用成功，调用llm获取最终答案
                else:
                    status = 'tool_success'
                    summary['tool_success_count'] += 1
                    # 大模型返回最终结果的时间
                    final_answer_seconds = time.time()
                    final_answer = get_final_answer_from_model(user_input, tool_result, model_name)
                    timing['final_answer_seconds'] = round(time.time() - final_answer_seconds, 2)
                    message.append({
                        'role': 'assistant',
                        'type': 'final_answer',
                        'content': final_answer
                    })
                    timing['total_seconds'] = round(time.time() - total_seconds, 2)

            if model_result['need_tool'] == False:
                status = 'no_tool'
                summary['no_tool_count'] += 1
                # final_answer = model_result['message']
                final_answer_seconds = time.time()
                memory_messages = read_memory()
                final_answer = ask_local_model(user_input, model_name, tool_info, memory_messages)
                # 追加记忆
                append_message(memory_messages, 'user', user_input)
                append_message(memory_messages, 'assistant', final_answer)
                # 保存记忆
                save_memory(memory_messages)
                timing['final_answer_seconds'] = round(time.time() - final_answer_seconds, 2)
                message.append({
                    'role': 'assistant',
                    'type': 'final_answer',
                    'content': final_answer
                })
                timing['total_seconds'] = round(time.time() - total_seconds, 2)
        result.append({
            'messages': message,
            'user_input': user_input,
            'status': status,
            'final_answer': final_answer,
            'timing': timing
        })
    return {
        'tools': tool_info,
        'summary': summary,
        'results': result
    }

result = run_agent(text_input,model_name)
save_json(result,session_file)

print(result['summary'])
