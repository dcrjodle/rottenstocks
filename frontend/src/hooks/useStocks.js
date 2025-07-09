/**
 * CONTEXT: useStocks
 * PURPOSE: Manages stock data fetching and state management
 * DEPENDENCIES: stockUtils for validation
 * TESTING: See useStocks.test.js for coverage
 */

import { useState, useEffect, useCallback } from 'react';
import { stockUtils } from '../utils/stockUtils';

const API_BASE_URL = 'http://localhost:8000';

export function useStocks() {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
      const validStocks = data.filter(stock => stockUtils.isValidStock(stock));
      
      setStocks(validStocks);
    } catch (err) {
      setError(err.message);
      setStocks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const createStock = useCallback(async (name, price) => {
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
      setError(err.message);
      throw err;
    }
  }, []);

  const updateStock = useCallback(async (id, name, price) => {
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
      setError(err.message);
      throw err;
    }
  }, []);

  const deleteStock = useCallback(async (id) => {
    try {
      const response = await fetch(`${API_BASE_URL}/stocks/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setStocks(prev => prev.filter(stock => stock.id !== id));
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

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
  };
}