from create_context import create_context
from model import get_tool_call_from_model, get_final_answer_from_model, check_task_completion_from_model
from run_tool import  run_tool
from memory_store import  save_turn
from parse_tool_call_result import parse_tool_call_result
from model import get_direct_answer_from_model
from create_context import create_context


def tool_agent(user_input, router_result, model_name='deepseek-chat'):
    # context 是本次 tool_agent 运行的总容器
    # 里面保存：用户输入、工具列表、messages 轨迹、step、status、最终回答等
    context = create_context(user_input, model_name)
    context['router_result'] = router_result
    context['route'] = router_result['route']

    # 工具 Agent 循环：每一轮最多让模型决定并执行一个工具
    # step 用来限制最多执行多少轮，避免 Agent 无限调用工具
    while context['step'] < context['max_steps']:
        context['step'] += 1

        # 第一步：让 LLM 根据用户输入、已有消息轨迹、可用工具，决定当前这一步要不要调用工具
        # model_text 是模型原始输出，通常应该是一段 JSON 字符串
        model_text = get_tool_call_from_model(
            user_input=context['user_input'],
            available_tools=context['tools'],
            messages=context['messages'],
            step=context['step'],
            max_steps=context['max_steps'],
            model_name=context['model_name'],
        )

        # 第二步：解析并校验模型输出
        # model_result 是结构化结果，后面 run_tool 只能相信这个解析后的结果，不直接相信 model_text
        model_result = parse_tool_call_result(model_text)

        # 把“模型决定调用什么工具”也记录进 messages
        # 这只是 assistant 的 tool_call 决策，不代表工具已经真的执行成功
        context['messages'].append({
            'role': 'assistant',
            'type': 'tool_call',
            'step': context['step'],
            'content': model_result
        })
        
        # 如果模型输出不是合法工具调用 JSON，记录错误并停止当前工具链路
        # 这里的失败属于“模型/解析失败”，不是具体工具执行失败
        if model_result['success'] is False:
            context['messages'].append({
                'role': 'assistant',
                'type': 'error',
                'step': context['step'],
                'content': model_result['error']
            })
            context['status'] = 'failed'
            context['stop_reason'] = 'llm_json_failed'
            continue    
        
        # 如果模型判断当前不需要继续调用工具，就退出工具循环
        # 注意：这里表示“工具链路没有下一步工具”，不一定等于整个用户任务已经完成
        if model_result['need_tool'] is False:
            context['status'] = 'finished'
            context['stop_reason'] = 'no_tool_needed'
            break
            
        # 第三步：真正执行工具
        # run_tool 只接收解析后的 tool_name 和 arguments，不直接接收模型原始文本
        tool_result = run_tool(
            model_result['tool_name'],
            model_result['arguments']
        )
        
        # 记录最后一次工具调用，方便后面保存 memory 或判断 last_topic
        context['last_tool_call'] = {
            'tool_name': model_result['tool_name'],
            'arguments': model_result['arguments'],
            'success': tool_result['success']
        }

        # 把真实工具执行结果写进 messages
        # 只有 role='tool' 的消息才代表工具真的运行过
        context['messages'].append({
            'role': 'tool',
            'step': context['step'],
            'name': model_result['tool_name'],
            'content': tool_result
        })

        # 如果工具本身执行失败，停止工具循环
        # 后面 final_answer 应该基于这个失败的 tool_result 诚实总结
        if tool_result['success'] is False:
            context['status'] = 'tool_failed'
            context['stop_reason'] = 'tool_failed'
            continue

    # 如果循环是因为达到 max_steps 才结束，并且状态还没有被其他分支改掉，
    # 就让模型根据 messages 检查用户任务是否真的完成
    if context['step'] >= context['max_steps'] and context['status'] == 'running':
        completion_result = check_task_completion_from_model(
            user_input=context['user_input'],
            messages=context['messages'],
            model_name=context['model_name']
        )
    
        # completion_result 保存“任务完成度判断”的结构化结果
        context['completion_result'] = completion_result
        
        # 完成度检查本身失败：说明模型没有返回可用的完成度 JSON
        if completion_result['success'] is False:
            context['status'] = 'stopped'
            context['stop_reason'] = 'completion_check_failed'

        # 达到最大步数时，任务刚好已经全部完成
        elif completion_result['is_complete'] is True:
            context['status'] = 'finished'
            context['stop_reason'] = 'completed_at_max_steps'

        # 达到最大步数后，模型判断还有工具任务没完成
        elif completion_result['need_more_tool'] is True:
            context['status'] = 'stopped'
            context['stop_reason'] = 'max_steps_reached_need_more_tool'
        
        # 兜底：达到最大步数，但完成度结果不属于上面几类
        else:
            context['status'] = 'stopped'
            context['stop_reason'] = 'max_steps_reached'

    # 生成最终回答：模型工具调用 JSON 解析失败时，直接告诉用户解析失败原因
    if context['stop_reason'] == "llm_json_failed":
        context['final_answer'] = "模型工具调用解析失败：" + str(model_result["error"])
        
    # 达到最大步数但没有明确完成时，先用直接回答模型基于 messages 生成回复
    elif context['stop_reason'] == 'max_steps_reached':
        context['final_answer'] = get_direct_answer_from_model(
            user_input=context['user_input'],
            available_tools=context['tools'],
            messages=context['messages'],
            model_name=context['model_name'],
            memory=None
        )

    # 默认情况：根据完整 messages 轨迹生成最终回答
    # 如果有工具结果，get_final_answer_from_model 应该只相信 role='tool' 的真实结果
    else:
        context['final_answer'] = get_final_answer_from_model(
            user_input=context['user_input'],
            messages=context['messages'],
            model_name=context['model_name']
        )
    
    # last_topic 用来给 memory_store 保存一个粗略主题
    # 有工具调用时，主题优先记为最后一次工具名
    last_topic = None

    if context['stop_reason'] == 'llm_json_failed':
        last_topic = None

    elif context['last_tool_call'] is not None:
        last_topic = {
            'role': 'topic',
            'content': context['last_tool_call']['tool_name']
        }

    elif '工具' in context['user_input']:
        last_topic = 'tools'

    # 保存一轮简化记忆：用户输入、最终回答、最后一次工具调用、主题
    save_turn(context['user_input'], context['final_answer'], context['last_tool_call'], last_topic)

    # 最终回答也写进 messages，形成完整轨迹：user -> tool_call -> tool -> final_answer
    context['messages'].append({
        "role": "assistant",
        "type": "final_answer",
        "content": context['final_answer']
    })

    # 返回本次 tool_agent 的核心运行结果，供 main.py 保存 session.json 或打印
    return {
        'messages': context['messages'],
        'user_input': context['user_input'],
        'final_answer': context['final_answer'],
        'status': context['status'],
        'step': context['step'],
        'stop_reason': context['stop_reason'],
        'completion_result': context['completion_result'],
        'route': context['route'],
        'router_result': context['router_result']
    }
