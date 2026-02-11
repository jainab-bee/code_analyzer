from ai_code_review_core import (
    parse_python_file,
    ai_review_engine,
    calculate_metrics,
    export_report
)

import sys

file_path = sys.argv[1]

analysis = parse_python_file(file_path)
feedback = ai_review_engine(analysis["issues"])
metrics = calculate_metrics(analysis)

export_report(feedback, metrics)

print("✅ Review completed. Check review_report.txt")
