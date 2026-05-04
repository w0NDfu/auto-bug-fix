import os

def load_repo_files(repo_dir: str):
    files = []
    for root, _, fs in os.walk(repo_dir):
        for f in fs:
            if f.endswith(".py"):
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8") as fh:
                        files.append((p, fh.read()))
                except Exception:
                    pass
    return files

def locate_bug(state, plan):
    # naive: pick files mentioning keywords
    repo_dir = "repo"
    files = load_repo_files(repo_dir)
    suspects = []
    for p, code in files:
        if "divide" in code or "ZeroDivisionError" in state.log:
            suspects.append((p, code))
    if not suspects:
        suspects = files[:2]
    state.context["suspects"] = suspects
    return {"suspects": suspects}