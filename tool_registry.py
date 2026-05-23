from github_tools import get_github_user

TOOLS = {
    'get_github_user': {
        'function': get_github_user,
        'description': '查询GitHub用户信息',
        'arguments': {
            'username': {
                'type': 'string',
                'description': 'GitHub用户名'
            }
        }
    }
}