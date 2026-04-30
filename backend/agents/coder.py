def generate_patch(context):
    func = context["function"]

    patch = f"""
def {func}(a, b):
    if b == 0:
        return 0
    return a / b
"""

    test_code = """
from buggy_code import divide

def test_divide():
    assert divide(4,2) == 2
    assert divide(4,0) == 0
"""

    return patch, test_code
