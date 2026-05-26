import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
import asyncio
import shlex


from langchain.tools import tool
from app.agent_mode.thought_interceptor import interceptor

# Root directory where agent-mode workspaces live. One subdirectory per chat_id.
BASE_AGENT_WORKDIR = os.environ.get("AGENT_MODE_WORKDIR", "/tmp/dish_chat_agent")

Path(BASE_AGENT_WORKDIR).mkdir(parents=True, exist_ok=True)


def _safe_workspace(chat_id: str) -> Path:
    """
    Return a per-chat workspace directory, creating it if needed.
    """
    ws = Path(BASE_AGENT_WORKDIR) / chat_id
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _venv_python(ws: Path) -> Path:
    """
    Resolve the Python executable inside the workspace virtualenv.
    """
    if os.name == "nt":
        return ws / ".venv" / "Scripts" / "python.exe"
    return ws / ".venv" / "bin" / "python"


@tool("agent_git_clone")
def agent_git_clone(chat_id: str, repo_url: str, branch: str = "main") -> str:
    """
    interceptor.tool_call("agent_git_clone", params={"repo_url": repo_url, "branch": branch})
    interceptor.thought(f"Cloning {repo_url}", "tool")
    Clone (or update) a Git repo into the agent workspace.

    - chat_id: Unique identifier for the current conversation.
    - repo_url: HTTPS or SSH URL for the repository.
    - branch: Branch to check out (default: main).

    The repo is placed under <BASE_AGENT_WORKDIR>/<chat_id>/repo.
    """
    interceptor.tool_call("agent_git_clone", params={"repo_url": repo_url, "branch": branch})
    interceptor.thought(f"Cloning {repo_url}", "tool")
    ws = _safe_workspace(chat_id)
    repo_dir = ws / "repo"

    if repo_dir.exists():
        # Try to update in-place instead of re-cloning.
        try:
            subprocess.run(
                ["git", "-C", str(repo_dir), "fetch", "--all"],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "checkout", branch],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "pull", "origin", branch],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return f"Updated existing repo at {repo_dir} on branch {branch}."
        except Exception as exc:
            # Fall back to a clean clone.
            shutil.rmtree(repo_dir, ignore_errors=True)

    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["git", "clone", "--branch", branch, repo_url, str(repo_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return f"""Cloned {repo_url} to {repo_dir} on branch {branch}.
STDOUT:
{result.stdout}
STDERR:
{result.stderr}"""
    except subprocess.CalledProcessError as exc:
        return f"""git clone failed: {exc}
STDOUT:
{exc.stdout}
STDERR:
{exc.stderr}"""
    except Exception as exc:  # pragma: no cover - defensive
        return f"git clone failed with unexpected error: {exc!r}"


@tool("agent_create_venv")
def agent_create_venv(chat_id: str, python_bin: Optional[str] = None) -> str:
    """
    interceptor.tool_call("agent_create_venv", params={"python_bin": python_bin})
    interceptor.thought("Creating virtual environment", "tool")
    Create (or recreate) a virtualenv inside the workspace.

    - chat_id: Workspace id.
    - python_bin: Which Python to use (default: current interpreter).
    """
    interceptor.tool_call("agent_create_venv", params={"python_bin": python_bin})
    interceptor.thought("Creating virtual environment", "tool")
    ws = _safe_workspace(chat_id)
    venv_dir = ws / ".venv"

    if python_bin is None:
        python_bin = os.environ.get("AGENT_MODE_PYTHON", None) or os.sys.executable

    if venv_dir.exists():
        # Keep it simple for now: reuse existing venv.
        return f"Virtualenv already exists at {venv_dir}."

    try:
        result = subprocess.run(
            [python_bin, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return f"""Created virtualenv at {venv_dir}.
STDOUT:
{result.stdout}
STDERR:
{result.stderr}"""
    except subprocess.CalledProcessError as exc:
        return f"""venv creation failed: {exc}
STDOUT:
{exc.stdout}
STDERR:
{exc.stderr}"""
    except Exception as exc:  # pragma: no cover
        return f"venv creation failed with unexpected error: {exc!r}"


@tool("agent_run_python")
def agent_run_python(
    chat_id: str,
    code: str,
    filename: str = "agent_script.py",
    workdir_subdir: Optional[str] = None,
    use_venv: bool = True,
) -> str:
    """
    Write Python code into the workspace and execute it.

    Parameters:
      - chat_id: Workspace id.
      - code: Python source code.
      - filename: Relative filename to write (default: agent_script.py).
      - workdir_subdir: Optional subdirectory under the workspace to use as CWD.
      - use_venv: If True, try to execute inside the workspace virtualenv.
    """
    interceptor.tool_call("agent_run_python", params={"filename": filename, "code_length": len(code)})
    interceptor.thought(f"Executing {filename}", "tool")
    
    ws = _safe_workspace(chat_id)
    if workdir_subdir:
        ws = ws / workdir_subdir
        ws.mkdir(parents=True, exist_ok=True)

    target = ws / filename
    target.write_text(code, encoding="utf-8")

    if use_venv and _venv_python(_safe_workspace(chat_id)).exists():
        python = str(_venv_python(_safe_workspace(chat_id)))
    else:
        python = os.sys.executable

    try:
        result = subprocess.run(
            [python, str(target)],
            cwd=str(ws),
            capture_output=True,
            text=True,
            timeout=600,
        )
        return (
            f"Executed {target} with python={python} (return code={result.returncode}).\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    except subprocess.TimeoutExpired as exc:
        return f"Execution of {target} timed out: {exc}"
    except Exception as exc:  # pragma: no cover
        return f"Execution of {target} failed with unexpected error: {exc!r}"


@tool("agent_list_artifacts")
def agent_list_artifacts(chat_id: str) -> str:
    """
    interceptor.tool_call("agent_list_artifacts", params={"chat_id": chat_id})
    List generated files in the workspace and return paths that can be exposed for download.
    """
    interceptor.tool_call("agent_list_artifacts", params={"chat_id": chat_id})
    ws = _safe_workspace(chat_id)
    paths = []
    for root, dirs, files in os.walk(ws):
        for f in files:
            full = Path(root) / f
            rel = full.relative_to(ws)
            paths.append(str(rel))
    # Keep output bounded.
    return "\n".join(sorted(paths)[:200])


# Allowed binaries for shell execution (security whitelist)
ALLOWED_BINARIES = {"aws", "kubectl", "helm", "bash", "git", "ls", "cat", "grep", "find"}


async def _run_shell_command(
    command: str,
    cwd: Optional[str] = None,
    timeout_seconds: int = 600,
) -> str:
    """
    Run a shell command on the host where dish-chat is running.

    Only allows commands whose first word is in ALLOWED_BINARIES.
    Returns combined stdout+stderr.
    """
    # Basic guardrail: only let it run a small whitelist
    parts = shlex.split(command)
    if not parts or parts[0] not in ALLOWED_BINARIES:
        return (
            f"Command rejected. First token {parts[0] if parts else '<empty>'!r} "
            f"is not in allowed list: {sorted(ALLOWED_BINARIES)}"
        )

    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        proc.kill()
        return f"Command timed out after {timeout_seconds} seconds: {command}"

    out = stdout.decode("utf-8", errors="replace")
    err = stderr.decode("utf-8", errors="replace")

    return (
        f"Exit code: {proc.returncode}\n"
        f"STDOUT:\n{out or '<empty>'}\n\n"
        f"STDERR:\n{err or '<empty>'}"
    )


@tool("agent_run_shell")
async def agent_run_shell(
    command: str,
    cwd: Optional[str] = None,
    timeout_seconds: int = 600,
) -> str:
    """
    Run shell commands on the ops host.
    
    Use this for aws/kubectl/helm/bash commands to inspect or change infrastructure state.
    Only allows commands starting with: aws, kubectl, helm, bash, git, ls, cat, grep, find.
    
    Parameters:
      - command: Shell command to execute
      - cwd: Working directory (optional)
      - timeout_seconds: Timeout in seconds (default: 600)
    
    Example: agent_run_shell(command="aws s3 ls", cwd="/tmp")
    """
    interceptor.tool_call("agent_run_shell", params={"command": command[:100], "cwd": cwd})
    interceptor.thought(f"Running shell command: {command[:50]}", "tool")
    
    result = await _run_shell_command(command, cwd, timeout_seconds)
    
    # Log completion
    if "Exit code: 0" in result:
        interceptor.tool_call("agent_run_shell", result="Command completed successfully")
    else:
        interceptor.tool_call("agent_run_shell", result="Command failed or returned error")
    
    return result
