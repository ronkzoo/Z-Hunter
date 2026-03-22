import os
import shutil

# Create directories
for d in ['core', 'data', 'utils']:
    os.makedirs(d, exist_ok=True)
    with open(f"{d}/__init__.py", "w") as f:
        pass

# Move files
moves = {
    'indicators.py': 'core/indicators.py',
    'regime_risk_manager.py': 'core/regime_risk_manager.py',
    'data_loader.py': 'data/loader.py',
    'utils.py': 'utils/helpers.py'
}

for src, dst in moves.items():
    if os.path.exists(src):
        shutil.move(src, dst)

# Update imports in app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

app_code = app_code.replace('from utils import', 'from utils.helpers import')
app_code = app_code.replace('from data_loader import', 'from data.loader import')
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

# Update imports in data/loader.py
if os.path.exists('data/loader.py'):
    with open('data/loader.py', 'r', encoding='utf-8') as f:
        loader_code = f.read()
    
    loader_code = loader_code.replace('from utils import', 'from utils.helpers import')
    loader_code = loader_code.replace('from indicators import', 'from core.indicators import')
    loader_code = loader_code.replace('from regime_risk_manager import', 'from core.regime_risk_manager import')
    with open('data/loader.py', 'w', encoding='utf-8') as f:
        f.write(loader_code)

# Update imports in core/regime_risk_manager.py
if os.path.exists('core/regime_risk_manager.py'):
    with open('core/regime_risk_manager.py', 'r', encoding='utf-8') as f:
        regime_code = f.read()
    
    regime_code = regime_code.replace('from indicators import', 'from core.indicators import')
    with open('core/regime_risk_manager.py', 'w', encoding='utf-8') as f:
        f.write(regime_code)

print("Package organization complete.")
