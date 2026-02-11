from ai_code_review_core import parse_python_file

file_path = "sample_test.py"  # file to check before commit

analysis = parse_python_file(file_path)

critical = [i for i in analysis["issues"] if i["severity"] == "critical"]

if critical:
    print("❌ Commit blocked due to critical issues")
    exit(1)
else:
    print("✅ Code is safe to commit")
    exit(0)
