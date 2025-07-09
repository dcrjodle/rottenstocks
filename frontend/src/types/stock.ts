export interface Stock {
  id: number;
  name: string;
  price: number;
}

export interface StockCreate {
  name: string;
  price: number;
}

export interface StockUpdate {
  name: string;
  price: number;
}

export interface UseStocksReturn {
  stocks: Stock[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  createStock: (name: string, price: number) => Promise<Stock>;
  updateStock: (id: number, name: string, price: number) => Promise<Stock>;
  deleteStock: (id: number) => Promise<void>;
  syncStocks: () => Promise<void>;
}