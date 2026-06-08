import os
import sys
import importlib
import traceback

def audit_modules():
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    print("Starting module import audit under: ", src_dir)
    errors = []
    successes = []

    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                rel_path = os.path.relpath(os.path.join(root, file), src_dir)
                module_parts = rel_path[:-3].replace(os.sep, ".")
                module_name = f"src.{module_parts}"
                
                try:
                    importlib.import_module(module_name)
                    successes.append(module_name)
                except Exception as e:
                    errors.append((module_name, str(e), traceback.format_exc()))
                    
    print(f"\nImport Summary: Successfully imported {len(successes)} modules.")
    if errors:
        print(f"Failed to import {len(errors)} modules:\n")
        for mod, err, tb in errors:
            print(f"--- ERROR IN {mod} ---")
            print(f"Reason: {err}")
            print(tb)
            print("-" * 40)
        sys.exit(1)
    else:
        print("All modules imported successfully without any runtime errors!")
        sys.exit(0)

if __name__ == "__main__":
    audit_modules()
