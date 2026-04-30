def reflect_and_fix(context, error):
    context["last_error"] = error
    return context
