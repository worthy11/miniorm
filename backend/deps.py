from fastapi import Request

def get_session(request: Request):
    return request.app.state.session
