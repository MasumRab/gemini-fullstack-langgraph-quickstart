
import sys
import os
import pkgutil
import importlib

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), 'src'))

print("Searching for modules in backend/src...")
package_path = os.path.join(os.getcwd(), 'src')

modules = []
for root, dirs, files in os.walk(package_path):
    for file in files:
        if file.endswith(".py") and not file.startswith("__"):
            # Convert path to module name
            rel_path = os.path.relpath(os.path.join(root, file), package_path)
            module_name = rel_path.replace(os.path.sep, ".")[:-3]
            modules.append(module_name)

print(f"Found {len(modules)} modules. Attempting import...")
failed = []
for mod in modules:
    try:
        importlib.import_module(mod)
        # print(f"PASS: {mod}")
    except Exception as e:
        print(f"FAIL: {mod} -> {e}")
        failed.append(mod)

if failed:
    print(f"\n{len(failed)} modules failed to import.")
    sys.exit(1)
else:
    print("\nAll modules imported successfully.")
