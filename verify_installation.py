"""Installation verification script for Construct Cost AI."""

import sys
from pathlib import Path


def check_python_version():
    """Check Python version."""
    required = (3, 11)
    current = sys.version_info[:2]
    
    print(f"✓ Python version: {current[0]}.{current[1]}")
    
    if current < required:
        print(f"✗ ERROR: Python {required[0]}.{required[1]}+ required")
        return False
    return True


def check_imports():
    """Check that all required packages can be imported."""
    packages = [
        ("fastapi", "FastAPI"),
        ("pydantic", "Pydantic"),
        ("dynaconf", "Dynaconf"),
        ("loguru", "Loguru"),
        ("streamlit", "Streamlit"),
        ("rich", "Rich"),
        ("typer", "Typer"),
        ("httpx", "httpx"),
        ("pytest", "pytest"),
    ]
    
    all_ok = True
    for module, name in packages:
        try:
            __import__(module)
            print(f"✓ {name} installed")
        except ImportError:
            print(f"✗ {name} NOT installed")
            all_ok = False
    
    return all_ok


def check_project_structure():
    """Check that project structure is correct."""
    base_dir = Path(__file__).parent
    
    required_paths = [
        "src/construct_cost_ai/__init__.py",
        "src/construct_cost_ai/api/app.py",
        "src/construct_cost_ai/domain/models.py",
        "src/construct_cost_ai/domain/orchestrator.py",
        "src/construct_cost_ai/infra/ai/stackspot_client.py",
        "app/streamlit_app.py",
        "cli/main.py",
        "tests/conftest.py",
        "settings.toml",
        ".env.example",
    ]
    
    all_ok = True
    for path in required_paths:
        full_path = base_dir / path
        if full_path.exists():
            print(f"✓ {path}")
        else:
            print(f"✗ {path} NOT FOUND")
            all_ok = False
    
    return all_ok


def check_package_installation():
    """Check if the package can be imported."""
    try:
        import construct_cost_ai
        print(f"✓ construct_cost_ai package installed (v{construct_cost_ai.__version__})")
        return True
    except ImportError:
        print("✗ construct_cost_ai package NOT installed")
        print("  Run: pip install -e .")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Construct Cost AI - Installation Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_imports),
        ("Project Structure", check_project_structure),
        ("Package Installation", check_package_installation),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        print("-" * 40)
        result = check_func()
        results.append(result)
        print()
    
    print("=" * 60)
    if all(results):
        print("✓ ALL CHECKS PASSED - Installation verified!")
        print()
        print("Next steps:")
        print("  1. Copy .env.example to .env")
        print("  2. Run the API: python run_api.py")
        print("  3. Run Streamlit: streamlit run app/streamlit_app.py")
        print("  4. Run tests: pytest")
    else:
        print("✗ SOME CHECKS FAILED - Please fix the issues above")
        print()
        print("Common fixes:")
        print("  - Install dependencies: pip install -e .[dev]")
        print("  - Check Python version: python --version")
    print("=" * 60)


if __name__ == "__main__":
    main()
