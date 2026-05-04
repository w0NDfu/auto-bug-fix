import tempfile
import subprocess
import os

def run_pytest(patch: str, tests: str):
    with tempfile.TemporaryDirectory() as tmp:
        code_path = os.path.join(tmp, "buggy_code.py")
        test_path = os.path.join(tmp, "test_buggy.py")

        with open(code_path, "w", encoding="utf-8") as f:
            f.write(patch)

        with open(test_path, "w", encoding="utf-8") as f:
            f.write(tests)

        try:
            res = subprocess.run(
                ["pytest", "-q", test_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            ok = (res.returncode == 0)
            return ok, res.stdout + "\n" + res.stderr
        except Exception as e:
            return False, str(e)