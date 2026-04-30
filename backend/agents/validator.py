import tempfile
import subprocess
import os

def run_tests(patch, test_code):
    with tempfile.TemporaryDirectory() as tmp:
        code_path = os.path.join(tmp, "buggy_code.py")
        test_path = os.path.join(tmp, "test_buggy.py")

        with open(code_path, "w") as f:
            f.write(patch)

        with open(test_path, "w") as f:
            f.write(test_code)

        try:
            result = subprocess.run(
                ["pytest", test_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            return result.returncode == 0, result.stderr

        except Exception as e:
            return False, str(e)
