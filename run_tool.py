from github_tools import get_github_user
from tool_registry import TOOLS

def run_tool(tool_name, arguments):
    if tool_name in TOOLS:
        function = TOOLS[tool_name]['function']
        return function(arguments['username'])
    if tool_name not in TOOLS:
        return {
                'success': False,
                'message': '工具不存在',
                'data': None
        }
        
def list_tools(tool_name=None):
    if tool_name == None:
        return {
            'success': True,
            'message': '工具列表',
            'data': {
                'get_github_user': {
                'description': '查询GitHub用户信息',
                'arguments': {
                    'username': {
                        'type': 'string',
                        'description': 'GitHub用户名'
                    }
                }
            }
        }
    }
    if tool_name in TOOLS:
        return {
            'success': True,
            'message': '工具详情',
            'data': TOOLS[tool_name]
        }
    if tool_name not in TOOLS:
        return {
                'success': False,
                'message': '工具不存在',
                'data': None
        }