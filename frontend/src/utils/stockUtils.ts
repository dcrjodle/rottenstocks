import { Stock } from '../types/stock';

export const stockUtils = {
  formatPrice(price: number): string {
    if (typeof price !== 'number' || isNaN(price)) {
      return '$0.00';
    }
    
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  },

  isValidStock(stock: any): stock is Stock {
    return (
      stock &&
      typeof stock.id === 'number' &&
      typeof stock.name === 'string' &&
      stock.name.length > 0 &&
      typeof stock.price === 'number' &&
      stock.price >= 0
    );
  },

  sortByName(stocks: Stock[]): Stock[] {
    if (!Array.isArray(stocks)) {
      return [];
    }
    
    return [...stocks].sort((a, b) => {
      if (!a.name || !b.name) return 0;
      return a.name.localeCompare(b.name);
    });
  },

  sortByPrice(stocks: Stock[]): Stock[] {
    if (!Array.isArray(stocks)) {
      return [];
    }
    
    return [...stocks].sort((a, b) => {
      if (typeof a.price !== 'number' || typeof b.price !== 'number') return 0;
      return b.price - a.price;
    });
  }
};