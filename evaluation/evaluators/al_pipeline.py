"""
Fully automated AL compile pipeline stage. No VS Code, no dotnet SDK,
no altool/MCP server — just nuget.exe (a single standalone binary) to
pull symbols, then alc.exe to compile.

One-time setup:
    Invoke-WebRequest -Uri "https://dist.nuget.org/win-x86-commandline/latest/nuget.exe" -OutFile "nuget.exe"

Then everything below is automatic.
"""

import subprocess
import glob
import json
from pathlib import Path

MSSYMBOLS_FEED = (
    "https://dynamicssmb2.pkgs.visualstudio.com/DynamicsBCPublicFeeds/"
    "_packaging/MSSymbols/nuget/v3/index.json"
)


def resolve_alc_path(vscode_extensions_dir: str = None) -> Path:
    if vscode_extensions_dir is None:
        vscode_extensions_dir = str(Path.home() / ".vscode" / "extensions")
    matches = glob.glob(f"{vscode_extensions_dir}/ms-dynamics-smb.al-*/bin/win32/alc.exe")
    if not matches:
        raise FileNotFoundError(f"alc.exe not found under {vscode_extensions_dir}")
    matches.sort(key=lambda p: Path(p).stat().st_mtime, reverse=True)
    return Path(matches[0])


def resolve_analyzer_dlls(alc_path: Path, analyzer_names: list[str] = None) -> list[str]:
    """
    Finds the built-in AL code analyzer DLLs (CodeCop, UICop, PerTenantExtensionCop,
    AppSourceCop) shipped inside the same VS Code AL extension that alc.exe came from.
    Skips AppSourceCop by default since it's for App Source dev, not per-tenant.
    """
    if analyzer_names is None:
        analyzer_names = ["CodeCop", "UICop", "PerTenantExtensionCop"]

    dll_map = {
        "CodeCop": "Microsoft.Dynamics.Nav.CodeCop.dll",
        "UICop": "Microsoft.Dynamics.Nav.UICop.dll",
        "AppSourceCop": "Microsoft.Dynamics.Nav.AppSourceCop.dll",
        "PerTenantExtensionCop": "Microsoft.Dynamics.Nav.PerTenantExtensionCop.dll",
    }

    # alc.exe lives at .../ms-dynamics-smb.al-X.Y.Z/bin/win32/alc.exe
    # Analyzers live at .../ms-dynamics-smb.al-X.Y.Z/bin/Analyzers/*.dll
    # Walk up from alc.exe until we find the extension root, then glob for Analyzers/
    extension_root = Path(alc_path)
    for _ in range(4):  # bin/win32/alc.exe -> bin/win32 -> bin -> extension root
        extension_root = extension_root.parent
        analyzers_dir = extension_root / "bin" / "Analyzers"
        if analyzers_dir.exists():
            break
    else:
        return []

    found = []
    for name in analyzer_names:
        dll_name = dll_map.get(name)
        if not dll_name:
            continue
        candidate = analyzers_dir / dll_name
        if candidate.exists():
            found.append(str(candidate))
    return found


def read_app_manifest(project_dir: Path) -> dict:
    app_json = project_dir / "app.json"
    if not app_json.exists():
        raise FileNotFoundError(f"app.json not found in {project_dir}")
    with open(app_json, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def find_best_version(pkg_name: str, requested_version: str, nuget_exe: str) -> str:
    """
    Query the feed for all available versions of pkg_name and pick the
    highest version whose major matches requested_version's major.
    Falls back to the absolute latest version if no major match exists.
    """
    cmd = [nuget_exe, "list", pkg_name, "-Source", MSSYMBOLS_FEED, "-AllVersions", "-PreRelease"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    versions = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(" ")
        if len(parts) == 2 and parts[0].lower() == pkg_name.lower():
            versions.append(parts[1])

    if not versions:
        return requested_version  # nothing found; let nuget install fail with a clear error

    requested_major = requested_version.split(".")[0]
    same_major = [v for v in versions if v.split(".")[0] == requested_major]

    def version_key(v):
        return [int(x) if x.isdigit() else 0 for x in v.replace("-", ".").split(".")]

    if same_major:
        return sorted(same_major, key=version_key)[-1]
    return sorted(versions, key=version_key)[-1]


def default_symbols_dir(project_dir: Path) -> Path:
    """
    A short, shared cache path (e.g. C:\\bcsym\\<project_name>) instead of
    nesting .alpackages inside a long project path — avoids Windows'
    260-char MAX_PATH limit, which NuGet's long GUID-based package
    folder names can easily exceed.
    """
    drive = Path(project_dir).resolve().drive or "C:"
    return Path(drive + "\\") / "bcsym" / Path(project_dir).name


def download_symbols(project_dir: Path, nuget_exe: str = "nuget.exe", symbols_dir: Path = None) -> dict:
    """
    Download BC platform + base app + dependency symbols using the
    public MSSymbols NuGet feed. Versions come from app.json but are
    resolved against what the feed actually publishes (exact app.json
    versions rarely exist verbatim). Downloads to a short symbols_dir
    to dodge Windows path-length limits, not directly under project_dir.
    """
    project_dir = Path(project_dir)
    if symbols_dir is None:
        symbols_dir = default_symbols_dir(project_dir)
    symbols_dir = Path(symbols_dir)
    symbols_dir.mkdir(parents=True, exist_ok=True)

    manifest = read_app_manifest(project_dir)

    packages = []
    if manifest.get("application"):
        packages.append(("Microsoft.Application.symbols", manifest["application"]))
    if manifest.get("platform"):
        packages.append(("Microsoft.Platform.symbols", manifest["platform"]))
    for dep in manifest.get("dependencies", []):
        pkg_name = f"{dep['publisher']}.{dep['name']}.symbols"
        packages.append((pkg_name, dep["version"]))

    if not packages:
        return {"success": False, "logs": [], "symbols_dir": str(symbols_dir),
                "error": "No 'application', 'platform', or 'dependencies' found in app.json"}

    logs = []
    for pkg_name, requested_version in packages:
        resolved_version = find_best_version(pkg_name, requested_version, nuget_exe)
        cmd = [nuget_exe, "install", pkg_name, "-version", resolved_version,
               "-Source", MSSYMBOLS_FEED, "-OutputDirectory", str(symbols_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        logs.append({"package": pkg_name, "requested_version": requested_version,
                     "resolved_version": resolved_version, "returncode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 0:
            return {"success": False, "logs": logs, "symbols_dir": str(symbols_dir)}

    return {"success": True, "logs": logs, "symbols_dir": str(symbols_dir)}


def compile_al_project(project_dir: Path, symbols_dir: Path, alc_path: Path = None,
                        out_name: str = None, analyzer_paths: list[str] = None) -> dict:
    project_dir = Path(project_dir)
    symbols_dir = Path(symbols_dir)
    if alc_path is None:
        alc_path = resolve_alc_path()

    if out_name is None:
        out_name = f"{project_dir.name}.app"
    out_file = project_dir / out_name

    cmd = [str(alc_path), f"/project:{project_dir}",
           f"/packagecachepath:{symbols_dir}", f"/out:{out_file}"]

    # One /analyzer:<dll> flag per requested analyzer (CodeCop, UICop, etc.)
    if analyzer_paths:
        for dll_path in analyzer_paths:
            cmd.append(f"/analyzer:{dll_path}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "out_file": str(out_file) if result.returncode == 0 else None,
        "returncode": result.returncode,
    }


def run_full_pipeline(project_dir: Path, nuget_exe: str = "nuget.exe", alc_path: Path = None,
                       symbols_dir: Path = None) -> dict:
    """Call this immediately after your agent generates AL code."""
    project_dir = Path(project_dir)
    if symbols_dir is None:
        symbols_dir = default_symbols_dir(project_dir)
    result = {"project_dir": str(project_dir), "symbols_dir": str(symbols_dir),
              "download": None, "compile": None, "success": False}

    dl = download_symbols(project_dir, nuget_exe, symbols_dir)
    result["download"] = dl
    if not dl["success"]:
        return result

    compile_result = compile_al_project(project_dir, symbols_dir, alc_path)
    result["compile"] = compile_result
    result["success"] = compile_result["success"]
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python al_pipeline.py <project_dir> [nuget_exe_path]")
        sys.exit(1)
    project_dir = Path(sys.argv[1])
    nuget_exe = sys.argv[2] if len(sys.argv) > 2 else "nuget.exe"
    result = run_full_pipeline(project_dir, nuget_exe)
    print(json.dumps(result, indent=2)) 