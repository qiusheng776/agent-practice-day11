# 从router包中导入各个agent
from connect_router.tool_agent import tool_agent
from connect_router.llm_workflow import llm_workflow
from connect_router.direct_runner import run_direct_agent

def run_agent(user_input, router_result, model_name='deepseek-chat'):
    if router_result['route'] == 'tool_agent':
        return tool_agent(user_input, router_result, model_name)
    elif router_result['route'] == 'llm_workflow':
        return llm_workflow(user_input, router_result, model_name)
    elif router_result['route'] == 'memory_query' or router_result['route'] == 'llm_only':
        return run_direct_agent(user_input, router_result, model_name)
    else:
        raise ValueError(f"Unknown route: {router_result['route']}")