# Global Instructions

## 1. Priority and Scope

- Follow the user’s latest explicit instruction first.
    
- Then follow the nearest project-level instructions such as `AGENTS.md`, `README`, environment notes, or task documents.
    
- Keep changes minimal, targeted, and compatible with the existing project structure.
    
- Do not remove useful existing comments, documentation, tests, or safeguards unless they are wrong or obsolete.
    

## 2. Code Quality and Comments

- Write clear, maintainable code that beginners can follow.
    
- Add helpful comments for important functions, classes, parameters, variables, calculations, and non-obvious logic.
    
- Explain the purpose of each major code block.
    
- Prefer readable structure over overly compact code.
    
- Preserve existing behavior unless the task explicitly asks for a change.
    

## 3. Python Environment and Execution

- Never assume the system default Python is suitable.
    
- Before running Python, identify the project-required environment from project files or environment notes.
    
- If a Conda environment is specified, always run Python through that environment:
    

```bash
conda run -n <env_name> python <script>.py
```

- Install Python packages through the same environment:
    

```bash
conda run -n <env_name> python -m pip install <package>
```

- Do not use bare `python`, `python3`, `py`, or `pip` when a project environment is specified.
    
- For this workstation, when working on PINN/GPU training projects and no stronger project-specific instruction exists, use the `geo_pinn` Conda environment.
    
- Before running any GPU training task, verify PyTorch and CUDA first:
    

```bash
conda run -n <env_name> python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA not available')"
```

- If CUDA is unavailable for a GPU training task, stop and report the environment problem instead of continuing.
    
- After writing or modifying code, run appropriate lightweight checks when practical, such as import checks, unit tests, smoke tests, formatting checks, or small plotting scripts.
    
- Do not start long-running training, large batch jobs, destructive commands, or expensive computations unless the user explicitly asks for them.
    
- If a full run is necessary but not authorized, provide the exact command for the user to run manually.
    

## 4. Scientific Plotting and Figure Style

When creating scientific figures, plots, or research images:

- Use English for titles, axis labels, legends, annotations, and other figure text unless the user requests otherwise.
    
- Use Times New Roman for English letters and numbers when practical.
    
- Use clear labels with units where applicable.
    
- Use readable font sizes, clean layouts, and clear legends.
    
- Save figures in both PNG and SVG formats unless the user gives different instructions.
    
- If Chinese text is necessary, use an appropriate Chinese font for Chinese characters while keeping English letters and numbers in Times New Roman when possible.
    

For Matplotlib, use this style when appropriate:

```python
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["axes.unicode_minus"] = False
```

## 5. Task Summary File

After each completed task in a writable project:

1. Create `./results` if it does not exist.
    
2. Save the task summary as `results/Result<N>.txt`.
    
3. Set `N` to the next available result number.
    
    - If no result file exists, create `Result1.txt`.
        
    - If `Result1.txt` to `Result3.txt` exist, create `Result4.txt`.
        
4. Include the same summary in the final chat response.
    

Use this format:

```text
Task:
Date:
Files Modified:
Commands Run:
Result:
Next Step:
```

Rules:

- `Files Modified` must list all files created, edited, or deleted.
    
- If no files were modified, write `- None`.
    
- `Commands Run` must list important commands executed.
    
- If no commands were run, write `- None`.
    
- `Next Step` should briefly tell the user what to review, run, test, or confirm next.
    

## 6. Final Response

- Be concise and beginner-friendly.
    
- Clearly state what was changed, what was checked, and what remains for the user.
    
- Mention any skipped checks, failed commands, missing dependencies, or risks honestly.