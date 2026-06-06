import os
import ast
from pathlib import Path

def parse_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        node = ast.parse(f.read(), filename=file_path)
    
    routes = []
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.FunctionDef):
            for decorator in subnode.decorator_list:
                is_router = False
                decorator_str = ""
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "router":
                        is_router = True
                        decorator_str = f"@{func.value.id}.{func.attr}"
                        args = [ast.unparse(arg) for arg in decorator.args]
                        kwargs = [f"{kw.arg}={ast.unparse(kw.value)}" for kw in decorator.keywords]
                        decorator_str += f"({', '.join(args + kwargs)})"
                
                if is_router:
                    docstring = ast.get_docstring(subnode) or "No docstring"
                    routes.append({
                        "decorator": decorator_str,
                        "func_name": subnode.name,
                        "args": [arg.arg for arg in subnode.args.args],
                        "docstring": docstring.split('\n')[0] if docstring else "No description"
                    })
    return routes

def main():
    routes_dir = Path("src/api/routes")
    all_routes = {}
    for path in routes_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        all_routes[path.name] = parse_file(path)
    
    output_lines = []
    for filename, routes in sorted(all_routes.items()):
        output_lines.append(f"\n### {filename}")
        for r in routes:
            output_lines.append(f"- **{r['decorator']}** -> `{r['func_name']}`")
            output_lines.append(f"  *Args:* `{', '.join(r['args'])}`")
            output_lines.append(f"  *Description:* {r['docstring']}")
    
    with open("scratch/routes_list.txt", "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(output_lines))

if __name__ == "__main__":
    main()
