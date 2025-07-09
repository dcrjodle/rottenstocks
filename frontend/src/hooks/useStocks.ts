/**
 * CONTEXT: useStocks
 * PURPOSE: Manages stock data fetching and state management
 * DEPENDENCIES: stockUtils for validation
 * TESTING: See useStocks.test.js for coverage
 */

import { useState, useEffect, useCallback } from 'react';
import { stockUtils } from '../utils/stockUtils';
import { Stock, UseStocksReturn } from '../types/stock';

const API_BASE_URL = 'http://localhost:8000';

export function useStocks(): UseStocksReturn {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStocks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/stocks`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Validate stock data
      const validStocks = data.filter((stock: any) => stockUtils.isValidStock(stock));
      
      setStocks(validStocks);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setStocks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const createStock = useCallback(async (name: string, price: number): Promise<Stock> => {
    try {
      const response = await fetch(`${API_BASE_URL}/stocks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, price }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const newStock = await response.json();
      
      if (stockUtils.isValidStock(newStock)) {
        setStocks(prev => [...prev, newStock]);
        return newStock;
      }
      
      throw new Error('Invalid stock data received');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    }
  }, []);

  const updateStock = useCallback(async (id: number, name: string, price: number): Promise<Stock> => {
    try {
      const response = await fetch(`${API_BASE_URL}/stocks/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, price }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const updatedStock = await response.json();
      
      if (stockUtils.isValidStock(updatedStock)) {
        setStocks(prev => 
          prev.map(stock => stock.id === id ? updatedStock : stock)
        );
        return updatedStock;
      }
      
      throw new Error('Invalid stock data received');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    }
  }, []);

  const deleteStock = useCallback(async (id: number): Promise<void> => {
    try {
      const response = await fetch(`${API_BASE_URL}/stocks/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setStocks(prev => prev.filter(stock => stock.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    }
  }, []);

  const syncStocks = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/stocks/sync/`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // After syncing, refetch the stocks to get the updated data
      await fetchStocks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      throw err;
    }
  }, [fetchStocks]);

  useEffect(() => {
    fetchStocks();
  }, [fetchStocks]);

  return {
    stocks,
    loading,
    error,
    refetch: fetchStocks,
    createStock,
    updateStock,
    deleteStock,
    syncStocks,
  };
}