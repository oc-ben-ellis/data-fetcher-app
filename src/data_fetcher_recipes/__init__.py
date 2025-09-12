"""Auto-import every recipe module in this package.

Importing each module triggers its register_recipe(...) side-effects,
so new recipes are picked up automatically without editing this file.
"""

import pkgutil
from importlib import import_module

# Iterate over all top-level modules in this package and import them
for mod_info in pkgutil.iter_modules(__path__):
    if mod_info.name.startswith("_"):  # skip private helpers
        continue
    import_module(f"{__package__}.{mod_info.name}")
