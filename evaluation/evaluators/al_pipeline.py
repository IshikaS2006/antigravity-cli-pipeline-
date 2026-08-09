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
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

MSSYMBOLS_FEED = (
    "https://dynamicssmb2.pkgs.visualstudio.com/DynamicsBCPublicFeeds/"
    "_packaging/MSSymbols/nuget/v3/index.json"
)

TEST_SYMBOL_PACKAGES = [
    "Microsoft.LibraryAssert.symbols.dd0be2ea-f733-4d65-bb34-a28f4624fb14",
    "Microsoft.Tests-TestLibraries.symbols.5d86850b-0d76-4eca-bd7b-951ad998e997",
]
# Known Microsoft test-library codeunits, mapped to the app.json dependency
# entry they require. Generated test code frequently references these by
# type (e.g. `Assert: Codeunit "Assert"`) without the generation agent also
# declaring the matching dependency — symbols get downloaded, but alc.exe
# still fails to link because app.json never lists it. This table lets us
# detect that usage and auto-patch the dependency in before compile.
KNOWN_TEST_LIBRARY_DEPENDENCIES = {
    "assert": {
        "id": "dd0be2ea-f733-4d65-bb34-a28f4624fb14",
        "name": "Library Assert",
        "publisher": "Microsoft",
    },
    "any": {
        "id": "5d86850b-0d76-4eca-bd7b-951ad998e997",
        "name": "Tests-TestLibraries",
        "publisher": "Microsoft",
    },
    "library random": {
        "id": "5d86850b-0d76-4eca-bd7b-951ad998e997",
        "name": "Tests-TestLibraries",
        "publisher": "Microsoft",
    },
    "library utility": {
        "id": "5d86850b-0d76-4eca-bd7b-951ad998e997",
        "name": "Tests-TestLibraries",
        "publisher": "Microsoft",
    },
}

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

@lru_cache(maxsize=1)
def _registration_base_url() -> str:
    with urlopen(MSSYMBOLS_FEED, timeout=30) as response:
        service_index = json.load(response)

    for resource in service_index.get("resources", []):
        resource_type = resource.get("@type", "")
        if "RegistrationsBaseUrl/3.6.0" in resource_type or "RegistrationsBaseUrl/Versioned" in resource_type:
            return resource["@id"].rstrip("/") + "/"

    raise RuntimeError("Could not locate a NuGet registrations base URL in the MSSymbols feed index")


@lru_cache(maxsize=128)
def _feed_versions(pkg_name: str) -> list[str]:
    registration_url = _registration_base_url() + quote(pkg_name.lower()) + "/index.json"
    with urlopen(registration_url, timeout=30) as response:
        registration = json.load(response)

    versions = []
    for page in registration.get("items", []):
        if "@id" in page:
            with urlopen(page["@id"], timeout=30) as response:
                page_data = json.load(response)
            items = page_data.get("items", [])
        else:
            items = page.get("items", [])

        for item in items:
            catalog_entry = item.get("catalogEntry", {})
            version = catalog_entry.get("version")
            if version:
                versions.append(version)

    return versions


def _version_key(version: str) -> list[int]:
    return [int(part) if part.isdigit() else 0 for part in version.replace("-", ".").split(".")]


def find_best_version(pkg_name: str, requested_version: str, nuget_exe: str) -> str:
    try:
        versions = _feed_versions(pkg_name)
    except Exception:
        cmd = [nuget_exe, "list", pkg_name, "-Source", MSSYMBOLS_FEED, "-AllVersions", "-PreRelease"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT resolving version for {pkg_name} — falling back to requested version {requested_version}", flush=True)
            return requested_version

        versions = []
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) == 2 and parts[0].lower() == pkg_name.lower():
                versions.append(parts[1])

    if not versions:
        return requested_version

    requested_parts = requested_version.split(".")
    requested_major_minor = ".".join(requested_parts[:2]) if len(requested_parts) >= 2 else requested_parts[0]
    same_major_minor = [v for v in versions if v == requested_major_minor or v.startswith(requested_major_minor + ".")]

    if same_major_minor:
        return sorted(same_major_minor, key=_version_key)[-1]

    requested_major = requested_parts[0]
    same_major = [v for v in versions if v.split(".")[0] == requested_major]

    if same_major:
        return sorted(same_major, key=_version_key)[-1]

    return sorted(versions, key=_version_key)[-1]

def default_symbols_dir(project_dir: Path) -> Path:
    """
    A short, shared cache path (e.g. C:\\bcsym\\<project_name>) instead of
    nesting .alpackages inside a long project path — avoids Windows'
    260-char MAX_PATH limit, which NuGet's long GUID-based package
    folder names can easily exceed.
    """
    drive = Path(project_dir).resolve().drive or "C:"
    return Path(drive + "\\") / "bcsym" / Path(project_dir).name


def project_has_test_codeunits(project_dir: Path) -> bool:
    """
    Detect whether the generated AL source contains test codeunits.
    This is intentionally heuristic and fast: if test symbols are needed,
    we should try to fetch them before compile.
    """
    codeunit_decl = re.compile(r"\bcodeunit\s+\d+\b", re.IGNORECASE)
    test_markers = re.compile(r"\bSubtype\s*=\s*Test\b|\[\s*Test\s*\]", re.IGNORECASE)

    for al_file in Path(project_dir).rglob("*.al"):
        try:
            content = al_file.read_text(encoding="utf-8")
        except Exception:
            continue
        if codeunit_decl.search(content) and test_markers.search(content):
            return True
    return False

def find_used_test_library_codeunits(project_dir: Path) -> set[str]:
    """
    Scans generated AL for references to known Microsoft test-library
    codeunit types (e.g. `Codeunit "Assert"`), regardless of whether the
    reference is a variable declaration, a parameter type, or inline usage.
    Returns the lowercase set of matched keys from KNOWN_TEST_LIBRARY_DEPENDENCIES.
    """
    found = set()
    pattern = re.compile(
    r'\bcodeunit\s+"?([^";]+)"?\s*;',
    re.IGNORECASE
    )

    for al_file in Path(project_dir).rglob("*.al"):
        try:
            content = al_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in pattern.finditer(content):
            name = match.group(1).strip().lower()
            if name in KNOWN_TEST_LIBRARY_DEPENDENCIES:
                found.add(name)
    return found

def ensure_test_dependencies(project_dir: Path) -> dict:
    """
    Auto-patches app.json to add any missing dependency entries for known
    Microsoft test-library codeunits (Assert, Any, etc.) that generated
    test code references but the generation agent forgot to declare.
    Idempotent — safe to call every run; only writes if something's missing.
    """
    project_dir = Path(project_dir)
    app_json_path = project_dir / "app.json"

    used = find_used_test_library_codeunits(project_dir)
    if not used:
        return {"patched": False, "added": [], "reason": "no known test-library codeunits referenced"}

    manifest = read_app_manifest(project_dir)
    existing_ids = {dep.get("id", "").lower() for dep in manifest.get("dependencies", [])}

    to_add = []
    for key in used:
        dep = KNOWN_TEST_LIBRARY_DEPENDENCIES[key]
        if dep["id"].lower() in existing_ids:
            continue
        # app.json dependency entries need a version too — reuse the
        # project's own application/platform version as a reasonable default;
        # find_best_version() during download_symbols will still resolve
        # against what the feed actually has.
        version = manifest.get("application") or manifest.get("platform") or "24.0.0.0"
        to_add.append({
            "id": dep["id"],
            "name": dep["name"],
            "publisher": dep["publisher"],
            "version": version,
        })
        existing_ids.add(dep["id"].lower())

    if not to_add:
        return {"patched": False, "added": [], "reason": "all required dependencies already present"}

    manifest.setdefault("dependencies", []).extend(to_add)
    with open(app_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {"patched": True, "added": [d["name"] for d in to_add]}

def ensure_namespaces(project_dir: Path) -> dict:
    """
    Adds a namespace derived from app.json to AL files that don't
    already declare one. Safe to run repeatedly.
    """
    project_dir = Path(project_dir)

    manifest = read_app_manifest(project_dir)

    publisher = manifest.get("publisher", "").strip()
    app_name = manifest.get("name", "").strip()

    if not publisher or not app_name:
        return {
            "patched": False,
            "files_touched": [],
            "reason": "publisher or name missing from app.json",
        }

    namespace = (
        f"{re.sub(r'[^A-Za-z0-9_]', '', publisher)}."
        f"{re.sub(r'[^A-Za-z0-9_]', '', app_name)}"
    )

    touched = []

    for al_file in project_dir.rglob("*.al"):
        try:
            content = al_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Skip files that already have a namespace
        if re.search(
            r"^\s*namespace\s+[\w.]+\s*;",
            content,
            re.IGNORECASE | re.MULTILINE,
        ):
            continue

        content = f"namespace {namespace};\n\n{content}"

        al_file.write_text(content, encoding="utf-8")
        touched.append(str(al_file.relative_to(project_dir)))

    return {
        "patched": bool(touched),
        "files_touched": touched,
        "namespace": namespace,
    }

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
        dep_id = dep.get("id", "").lower()

        known_package = next(
            (
                pkg for pkg in TEST_SYMBOL_PACKAGES
                if pkg.lower().endswith(f".{dep_id}")
            ),
            None,
        )

        pkg_name = known_package or f"{dep['publisher']}.{dep['name']}.symbols"
        packages.append((pkg_name, dep["version"]))

    include_test_symbols = project_has_test_codeunits(project_dir)
    optional_test_packages = set()
    if include_test_symbols:
        test_version = manifest.get("application") or manifest.get("platform")
        if test_version:
            existing = {p[0].lower() for p in packages}
            for pkg_name in TEST_SYMBOL_PACKAGES:
                if pkg_name.lower() in existing:
                    continue
                packages.append((pkg_name, test_version))
                optional_test_packages.add(pkg_name.lower())

    if not packages:
        return {"success": False, "logs": [], "symbols_dir": str(symbols_dir),
                "error": "No 'application', 'platform', or 'dependencies' found in app.json"}

    logs = []
    for pkg_name, requested_version in packages:
        resolved_version = find_best_version(pkg_name, requested_version, nuget_exe)
        print(f"RESOLVED: {pkg_name} -> {resolved_version}", flush=True)
        cmd = [nuget_exe, "install", pkg_name, "-version", resolved_version,
               "-Source", MSSYMBOLS_FEED, "-OutputDirectory", str(symbols_dir)]
        print("RUNNING NUGet:", cmd, flush=True)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        print(f"FINISHED INSTALL: {pkg_name}", flush=True)
        print("NUGet RETURN CODE:", result.returncode, flush=True)
        print("NUGet STDOUT:", result.stdout, flush=True)
        print("NUGet STDERR:", result.stderr, flush=True)
        logs.append({"package": pkg_name, "requested_version": requested_version,
                     "resolved_version": resolved_version, "returncode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 0:
            if pkg_name.lower() in optional_test_packages:
                continue
            return {"success": False, "logs": logs, "symbols_dir": str(symbols_dir)}
    print("DOWNLOAD_SYMBOLS FINISHED", flush=True)
    return {
        "success": True,
        "logs": logs,
        "symbols_dir": str(symbols_dir),
        "test_symbols_requested": include_test_symbols,
    }


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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

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
    result = {
    "project_dir": str(project_dir),
    "symbols_dir": str(symbols_dir),
    "dependency_patch": None,
    "namespace_patch": None,
    "download": None,
    "compile": None,
    "success": False,
    }

    result["dependency_patch"] = ensure_test_dependencies(project_dir)
    result["namespace_patch"] = ensure_namespaces(project_dir)

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