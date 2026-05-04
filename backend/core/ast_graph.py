import ast
from typing import Dict, List

class CallGraphBuilder(ast.NodeVisitor):
    def __init__(self):
        self.graph: Dict[str, List[str]] = {}
        self.current = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current = node.name
        self.graph.setdefault(self.current, [])
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and self.current:
            self.graph[self.current].append(node.func.id)
        self.generic_visit(node)

def build_graph(code: str):
    tree = ast.parse(code)
    b = CallGraphBuilder()
    b.visit(tree)
    return b.graph