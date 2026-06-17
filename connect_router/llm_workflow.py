from model import check_llm_workflow_completion_from_model,get_llm_workflow_next_step_from_model,get_llm_workflow_step_from_model
from create_context import create_context
from memory_store import  save_turn

def llm_workflow(user_input, router_result, model_name='deepseek-chat'):
    context = create_context(user_input, model_name)
    context['router_result'] = router_result
    context['route'] = router_result['route']
    # last_topic =

    while context['step'] < context['max_steps']:
        context['step'] += 1
        # 获取下一步执行的步骤
        llm_response = get_llm_workflow_next_step_from_model(user_input,workflow_steps=context['workflow_steps'],model_name=model_name)
        context['current_step_name'] = llm_response['step_name']
        context['workflow_next_step'] = llm_response['step_name']
        context['messages'].append({
            "role": "assistant",
            "type": "workflow_step",
            "step": context['step'],
            "content": llm_response
        })

        # 执行当前步骤
        step_input = context['previous_result']
        llm_action = get_llm_workflow_step_from_model(llm_response['step_name'],user_input,step_input,model_name)
        context['messages'].append({
            "role": "assistant",
            "type": "workflow_step_result",
            "step": context['step'],
            "content": llm_action
        })

        # 记录步骤执行结果
        context["workflow_steps"].append({
            "step": context['step'],
            "step_name": context["current_step_name"],
            "input": step_input,
            "result": llm_action,
            "success": True
        })
        context['previous_result'] = llm_action
        context['messages'].append({
            "role": "assistant",
            "type": "workflow_step_result",
            "step": context['step'],
            "content": llm_action
        })

        # 检查工作流是否完成
        check_result = check_llm_workflow_completion_from_model(user_input, context['workflow_steps'], model_name)
        context['workflow_completion_result'] = check_result['is_complete']
        context['messages'].append({
            "role": "assistant",
            "type": "workflow_completion_result",
            "step": context['step'],
            "content": check_result
        })

        # 如果工作流完成，停止执行
        if check_result['is_complete']:
            context['status'] = 'finished'
            context['stop_reason'] = 'workflow_completed'
            save_turn(context['user_input'], context['final_answer'], context['last_tool_call'])
            break

        # 如果达到最大步骤数，停止执行
        if context['step'] >= context['max_steps']:
            context['status'] = 'stopped'
            context['stop_reason'] = 'workflow_max_steps_reached'
            save_turn(context['user_input'], context['final_answer'], context['last_tool_call'])
            break

    return {
        "workflow_completion_result": context['workflow_completion_result'],
        "step": context['step'],
        "current_step_name": context['current_step_name'],
        "workflow_steps": context['workflow_steps'],
        "workflow_next_step": context['workflow_next_step'],
        "status": context['status'],
        "max_steps": context['max_steps'],
        "stop_reason": context['stop_reason'],
        "final_answer": context['previous_result'],
        "route": context['route'],
        "router_result": context['router_result']
    }



            
    