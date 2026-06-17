# 导入记忆
from memory_store import read_memory
from model import get_direct_answer_from_model
from create_context import create_context
from memory_store import  save_turn

def run_direct_agent(user_input, router_result, model_name='deepseek-chat'):
    memory = read_memory()
    context = create_context(user_input, model_name)
    context['router_result'] = router_result
    context['route'] = router_result['route']
    # last_topic

    context['final_answer'] = get_direct_answer_from_model(
        user_input=user_input,
        available_tools=[],
        messages=[],
        model_name=model_name,
        memory=memory
    )
    context['messages'].append({
        "role": "assistant",
        "type": "final_answer",
        "content": context['final_answer']
    })
    context['status'] = 'finished'
    context['stop_reason'] = 'direct_answer_finished'
    save_turn(context['user_input'], context['final_answer'], context['last_tool_call'])

    return {
        'messages': context['messages'],
        'user_input': context['user_input'],
        'final_answer': context['final_answer'],
        'status': context['status'],
        'memory': memory,
        'route': context['route'],
        'router_result': context['router_result'],
        'stop_reason': context['stop_reason'],

    }


    


    