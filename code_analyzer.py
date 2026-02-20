import argparse
import os
import sys
import ast
import time
import requests
import pandas as pd
import toml
import difflib
from radon.complexity import cc_visit
from radon.metrics import mi_visit

def load_config():
    config_path = "pyproject.toml"

    default_config = {
        "exclude_dirs": ["venv", ".venv", "__pycache__", "anaconda3", "site-packages"],
        "complexity_threshold": 10,
        "maintainability_threshold": 65
    }

    if os.path.exists(config_path):
        try:
            data = toml.load(config_path)
            return data.get("tool", {}).get("ai_code_review", default_config)
        except:
            return default_config

    return default_config


def get_python_files(path):
    python_files = []

    if os.path.isfile(path) and path.endswith(".py"):
        return [path]
    config = load_config()
    ignore_dirs = config["exclude_dirs"]

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    return python_files


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def safe_parse(code):
    try:
        tree = ast.parse(code)
        return tree, None
    except SyntaxError as e:
        return None, f"Syntax Error: {e}"

def extract_structure(tree):
    structure = {
        "imports": [],
        "functions": [],
        "classes": [],
        "loops": 0,
        "conditionals": 0
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                structure["imports"].append(name.name)

        elif isinstance(node, ast.ImportFrom):
            structure["imports"].append(node.module)

        elif isinstance(node, ast.FunctionDef):
            structure["functions"].append(node.name)

        elif isinstance(node, ast.ClassDef):
            structure["classes"].append(node.name)

        elif isinstance(node, (ast.For, ast.While)):
            structure["loops"] += 1

        elif isinstance(node, ast.If):
            structure["conditionals"] += 1

    return structure


def cyclomatic_complexity_ast(tree):
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp)):
            complexity += 1
    return complexity


def detect_issues(code):
    raw_issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [{"type": "Syntax Error", "detail": str(e), "context": None, "level": "CRITICAL"}]

    assigned = {}
    used = set()
    parameters = {}
    current_function = None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            current_function = node.name

            if len(node.name) < 4:
                raw_issues.append({"type": "Poor function name", "detail": node.name, "context": node.name, "level": "INFO"})

            if ast.get_docstring(node) is None:
                raw_issues.append({"type": "Missing docstring", "detail": node.name, "context": node.name, "level": "INFO"})

            if len(node.args.args) > 4:
                raw_issues.append({"type": "Too many parameters", "detail": node.name, "context": node.name, "level": "WARNING"})

            for arg in node.args.args:
                parameters[arg.arg] = current_function
                if len(arg.arg) < 3:
                    raw_issues.append({
                        "type": "Poor parameter name",
                        "detail": arg.arg,
                        "context": current_function,
                        "level": "INFO"
                    })

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned[target.id] = current_function
                    if len(target.id) < 3:
                        raw_issues.append({
                            "type": "Poor variable name",
                            "detail": target.id,
                            "context": current_function,
                            "level": "INFO"
                        })

        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if node.value not in (0, 1):
                raw_issues.append({
                    "type": "Magic number used",
                    "detail": node.value,
                    "context": current_function,
                    "level": "WARNING"
                })

        if isinstance(node, ast.ExceptHandler):
            if not node.body:
                raw_issues.append({
                    "type": "Empty except block",
                    "detail": "",
                    "context": current_function,
                    "level": "CRITICAL"
                })

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                raw_issues.append({
                    "type": "Debug print found",
                    "detail": "",
                    "context": current_function,
                    "level": "INFO"
                })

    for var, func in assigned.items():
        if var not in used and var not in parameters:
            raw_issues.append({
                "type": "Unused variable",
                "detail": var,
                "context": func,
                "level": "WARNING"
            })

    seen = set()
    issues = []
    for i in raw_issues:
        key = (i["type"], i["detail"], i["context"])
        if key not in seen:
            issues.append(i)
            seen.add(key)

    return issues

def _rule_based_feedback(issues):
    feedback = []
    for issue in issues:
        t = issue["type"]
        ctx = issue["context"]
        if t == "Missing docstring":
            feedback.append(f"Add a proper docstring to '{ctx}' explaining its purpose.")
        elif t == "Too many parameters":
            feedback.append(f"Refactor '{ctx}' to reduce parameters using objects.")
        elif t == "Magic number used":
            feedback.append("Replace magic numbers with constants.")
        elif t == "Unused variable":
            feedback.append(f"Remove unused variable '{issue['detail']}'.")
        elif t == "Debug print found":
            feedback.append("Remove debug print statements.")
        elif t == "Poor variable name":
            feedback.append(f"Rename variable '{issue['detail']}' meaningfully.")
    return feedback


def _build_prompt(issues, code):
    issues_text = "\n".join(
        f"- [{i['level']}] {i['type']}: {i['detail']} (in {i['context']})"
        for i in issues
    )
    return f"""You are a senior Python code reviewer. Analyze the following code and its detected issues, then provide clear, actionable feedback.

DETECTED ISSUES:
{issues_text}

SOURCE CODE:
```python
{code[:3000]}
```

Provide 3-7 concise, actionable suggestions to improve this code. Focus on the most impactful improvements. Return ONLY the suggestions as a numbered list, one per line. Do not include any other text."""


def _parse_ai_response(raw):
    suggestions = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if line:
            cleaned = line.lstrip("0123456789.-) ").strip()
            if cleaned:
                suggestions.append(cleaned)
    return suggestions


def _call_gemini(prompt, api_key):
    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response.text


def _call_openrouter(prompt, api_key):
    model = os.getenv("OPENROUTER_MODEL", "google/gemma-3-4b-it:free")
    for attempt in range(3):
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )
        if response.status_code == 429:
            wait = 10 * (attempt + 1)
            print(f"[WARN] OpenRouter rate limited. Waiting {wait}s...")
            time.sleep(wait)
            continue
        if response.status_code != 200:
            error_msg = response.json().get("error", {}).get("message", response.text[:200])
            raise Exception(f"OpenRouter {response.status_code}: {error_msg}")
        return response.json()["choices"][0]["message"]["content"]
    raise Exception("OpenRouter rate limited after 3 retries")


def _call_ollama(prompt):
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    response = requests.post(
        f"{ollama_url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120
    )
    response.raise_for_status()
    return response.json()["response"]


def generate_ai_feedback(issues, code=""):
    if not issues:
        return ["No issues detected. Code looks good!"]

    prompt = _build_prompt(issues, code)

    engines = []

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        engines.append(("OpenRouter", lambda: _call_openrouter(prompt, openrouter_key)))

    engines.append(("Ollama", lambda: _call_ollama(prompt)))

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        engines.append(("Gemini", lambda: _call_gemini(prompt, gemini_key)))

    for engine_name, call_fn in engines:
        try:
            print(f"[INFO] Trying {engine_name}...")
            raw = call_fn()
            suggestions = _parse_ai_response(raw)
            if suggestions:
                print(f"[INFO] {engine_name} succeeded.")
                return suggestions
        except Exception as e:
            print(f"[WARN] {engine_name} failed: {e}")

    print("[INFO] All AI engines failed. Using rule-based feedback.")
    return _rule_based_feedback(issues)

def auto_fix_code(code):
    lines = code.split("\n")
    fixed_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("print(") and (
            "debug" in stripped.lower()
            or "test" in stripped.lower()
        ):
            continue

        if "print(" in line:
            line = line.replace("print(", "print(")
            line = line.replace(" )", ")")
            line = line.replace("+", " + ")

        fixed_lines.append(line.rstrip())

    return "\n".join(fixed_lines)


def analyze_metrics(code):
    try:
        complexity_results = cc_visit(code)
        maintainability = mi_visit(code, True)
    except:
        return 0, 0, 0, "Error", []

    total_complexity = 0
    warnings = []

    for func in complexity_results:
        total_complexity += func.complexity

        if func.complexity > 10:
            warnings.append(f"CRITICAL: {func.name} highly complex")
        elif func.complexity > 5:
            warnings.append(f"WARNING: {func.name} moderate complexity")

    avg_complexity = total_complexity / len(complexity_results) if complexity_results else 0

    score = 100
    if avg_complexity > 10:
        score -= 20
    elif avg_complexity > 5:
        score -= 10

    if maintainability < 65:
        score -= 20
    elif maintainability < 80:
        score -= 10

    grade = (
        "Excellent" if score >= 90
        else "Good" if score >= 75
        else "Moderate" if score >= 60
        else "Poor"
    )

    return round(avg_complexity, 2), round(maintainability, 2), score, grade, warnings

def generate_diff(original, fixed):
    return "\n".join(difflib.unified_diff(
        original.splitlines(),
        fixed.splitlines(),
        lineterm=""
    ))

import os

def create_git_hook():
    project_root = os.getcwd()
    git_dir = os.path.join(project_root, ".git")

    if not os.path.exists(git_dir):
        print("Git not initialized.")
        return

    hook_path = os.path.join(git_dir, "hooks", "pre-commit")
    hook_script_path = os.path.join(git_dir, "hooks", "pre-commit-script.py")

    python_script = """import subprocess
import os
import sys

print("Running AI Code Review on staged files...")

result = subprocess.run(
    ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
    capture_output=True,
    text=True,
    cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

files = [f for f in result.stdout.strip().split("\\n") if f.endswith(".py") and f]

if not files:
    print("No Python files to check.")
    sys.exit(0)

failed = False
for file in files:
    proc = subprocess.run(
        [sys.executable, "code_analyzer.py", "scan", "--path", file],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    if proc.returncode != 0:
        failed = True

if failed:
    print("Commit blocked: Code issues found.")
    sys.exit(1)

print("Code review passed. Commit successful.")
sys.exit(0)
"""
    wrapper_script = f"""#!/bin/sh
python "{hook_script_path}" "$@"
exit $?
"""

    try:
        with open(hook_script_path, "w", encoding="utf-8") as f:
            f.write(python_script)
            
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(wrapper_script)

        try:
            os.chmod(hook_path, 0o775)
            os.chmod(hook_script_path, 0o775)
        except:
            pass

        print("Git pre-commit hook installed successfully.")
        print("Location:", hook_path)

    except Exception as e:
        print("Error installing hook:", e)


def analyze_project(project_path):

    files = get_python_files(project_path)

    if not files:
        return None, None, "No Python files found"

    results = []

    for file in files:
        code = read_file(file)

        tree, error = safe_parse(code)
        if error:
            results.append({
                "file": file,
                "functions": 0,
                "classes": 0,
                "loops": 0,
                "conditionals": 0,
                "ast_complexity": 0,
                "issues": [("Syntax error in file", "CRITICAL")],
                "ai_feedback": "Fix syntax errors before analysis",
                "avg_complexity": 0,
                "maintainability": 0,
                "score": 0,
                "grade": "Error",
                "warnings": error
            })
            continue

        structure = extract_structure(tree)
        ast_complexity = cyclomatic_complexity_ast(tree)
        issues = detect_issues(code)
        ai_feedback = generate_ai_feedback(issues, code)

        avg_complexity, mi, score, grade, warnings = analyze_metrics(code)

        results.append({
            "file": file,
            "functions": len(structure["functions"]),
            "classes": len(structure["classes"]),
            "loops": structure["loops"],
            "conditionals": structure["conditionals"],
            "ast_complexity": ast_complexity,
            "issues": issues,
            "ai_feedback": "; ".join(ai_feedback),
            "avg_complexity": avg_complexity,
            "maintainability": mi,
            "score": score,
            "grade": grade,
            "warnings": "; ".join(warnings)
        })

    df = pd.DataFrame(results)

    project_score = round(df["score"].mean(), 2)

    save_dir = os.path.dirname(project_path) if os.path.isfile(project_path) else project_path

    csv_path = os.path.join(save_dir, "report.csv")
    html_path = os.path.join(save_dir, "report.html")

    df.to_csv(csv_path, index=False)
    df.to_html(html_path, index=False)


    return df, project_score, "Analysis completed successfully"

def run_cli():
    parser = argparse.ArgumentParser(description="AI Code Quality Analyzer")
    parser.add_argument("command", choices=["scan", "review", "apply", "report","diff","hook"])
    parser.add_argument("--path", required=True)

    args = parser.parse_args()

    df, score, msg = analyze_project(args.path)

    if args.command == "scan":
        print(df)

        critical_found = False

        for _, row in df.iterrows():
            if row["grade"] == "Error":
                critical_found = True

            if "CRITICAL" in str(row["warnings"]):
                critical_found = True

        if critical_found:
            print("❌ Critical issues found. Fix before commit.")
            sys.exit(1)
        else:
            sys.exit(0)


    elif args.command == "review":
        for _, row in df.iterrows():
            print("\nFile:", row["file"])
            print(row["ai_feedback"])

    elif args.command == "apply":
        for file in get_python_files(args.path):
            code = read_file(file)
            fixed = auto_fix_code(code)
            with open(file, "w", encoding="utf-8") as f:
                f.write(fixed)
        print("Auto fixes applied.")

    elif args.command == "report":
        print("Project Score:", score)

    elif args.command == "diff":
        for file in get_python_files(args.path):
            original = read_file(file)
            fixed = auto_fix_code(original)
            print(generate_diff(original, fixed))

    elif args.command == "hook":
        create_git_hook()


if __name__ == "__main__":
    run_cli()