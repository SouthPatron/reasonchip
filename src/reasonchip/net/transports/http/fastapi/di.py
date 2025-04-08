from fastapi import Request

from ..common import CallbackHooks


# ************* Dependency injections ****************************************

# Get the callbacks
def get_callbacks(request: Request) -> CallbackHooks:
    hooks: CallbackHooks = request.app.state.callback_hooks
    return hooks

