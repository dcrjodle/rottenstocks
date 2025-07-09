from database import get_all_stocks

stocks = get_all_stocks()
print(f'Database has {len(stocks)} stocks:')
for s in stocks:
    print(f'  {s["id"]}: {s["symbol"]} - {s["name"]} (${s["price"]})')