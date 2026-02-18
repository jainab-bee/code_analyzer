# 🧠 AI Code Quality Analyzer

AI Code Quality Analyzer is a Python-based tool that analyzes code quality, detects issues, calculates complexity, and provides AI-powered suggestions before committing code.

This project includes both frontend and backend in the same root folder.

---

## 📁 Project Structure

- **frontend.py**
  - Streamlit-based user interface
  - Allows users to upload Python files or paste code
  - Displays analysis results, warnings, and suggestions
  - Enables report download (CSV & HTML)

- **code_analyzer.py**
  - Backend engine of the project
  - Performs static code analysis using AST
  - Calculates complexity and maintainability
  - Detects issues like:
    - Missing docstrings
    - Poor variable names
    - Magic numbers
    - Debug prints
    - Unused variables
  - Generates AI suggestions using:
    - OpenRouter
    - Gemini
    - Ollama
  - Supports CLI commands & Git pre-commit hook

- **requirements.txt**
  - Contains all dependencies required to run the project

Both frontend and backend operate from the same folder.

---

## ⚙️ How the System Works

1. User uploads Python file OR pastes code in frontend.
2. Frontend sends code to backend.
3. Backend:
   - Parses code using AST
   - Detects issues
   - Calculates complexity & maintainability
   - Generates AI feedback
4. Results displayed in frontend.
5. Reports generated in CSV & HTML format.

---

## 🚀 How to Run the Project

### Step 1 — Install dependencies
pip install -r requirements.txt

### Step 2 — Run Backend (CLI mode optional)
python code_analyzer.py scan --path .

### Step 3 — Run Frontend
streamlit run frontend.py

---

## 🧠 Backend Capabilities

- Static code analysis
- Cyclomatic complexity detection
- Maintainability index calculation
- Rule-based issue detection
- AI-powered suggestions
- Auto-fix basic formatting
- Git pre-commit hook integration

---

## 💻 Frontend Features

- Upload multiple Python files
- Paste code manually
- View:
  - Project score
  - File-wise analysis
  - Complexity metrics
  - Warnings
  - AI suggestions
- Download reports (CSV & HTML)

---

## 🔧 CLI Commands (Backend)

| Command | Description |
|--------|-------------|
| scan | Analyze project |
| review | Show AI suggestions |
| apply | Apply auto-fixes |
| report | Show project score |
| diff | Show code changes |
| hook | Install Git pre-commit hook |

Example:
python code_analyzer.py scan --path .

---

## 📊 Metrics Used

- AST Complexity
- Cyclomatic Complexity
- Maintainability Index
- Code Quality Score
- Issue Detection

---

## ✨ Technologies Used

- Python
- Streamlit
- Pandas
- AST (Abstract Syntax Tree)
- Radon
- OpenRouter API
- Gemini API
- Ollama
- GitPython

---

## 🎯 Use Cases

- Code review before commit
- Learning clean coding practices
- Academic projects
- Developer productivity
- Git workflow automation

---

## 📜 License

This project is licensed under the MIT License.
