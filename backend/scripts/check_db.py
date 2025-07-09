import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from models.database import get_all_stocks

stocks = get_all_stocks()
print(f'Database has {len(stocks)} stocks:')
for s in stocks:
    print(f'  {s["id"]}: {s["symbol"]} - {s["name"]} (${s["price"]})')