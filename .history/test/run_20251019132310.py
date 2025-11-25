import argparse
import importlib.util
import json
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


def load_payload(module_path: str) -> dict:
    spec = importlib.util.spec_from_file_location("test_payload", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load data module from {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    if not hasattr(mod, "payload"):
        raise AttributeError(f"Data module {module_path} must define a 'payload' dict")
    payload = getattr(mod, "payload")
    if not isinstance(payload, dict):
        raise TypeError("'payload' must be a dict")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ulpiano tax engine for a model with sample data")
    parser.add_argument("model", choices=["650", "651"], help="Model code to generate")
    parser.add_argument("--data", dest="data_path", help="Path to a .py file exporting 'payload' dict")
    parser.add_argument("--output-dir", default=os.path.join(PROJECT_ROOT, "generated"), help="Output directory for artifacts")
    args = parser.parse_args()

    if args.data_path:
        data_path = os.path.abspath(args.data_path)
    else:
        data_path = os.path.join(PROJECT_ROOT, "test", f"data_{args.model}.py")

    payload = load_payload(data_path)

    from ulpiano_tax_engine import generate_model

    result = generate_model(args.model, payload, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


