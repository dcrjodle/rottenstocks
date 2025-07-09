/**
 * CONTEXT: App
 * PURPOSE: Main application component that displays stock cards
 * DEPENDENCIES: useStocks hook, StockCard component, stockUtils
 * TESTING: See App.test.js for coverage
 */

import React from 'react';
import StockCard from './components/StockCard';
import { useStocks } from './hooks/useStocks';
import { stockUtils } from './utils/stockUtils';
import './App.css';

function App(): React.JSX.Element {
  const { stocks, loading, error, refetch } = useStocks();

  if (loading) {
    return (
      <div className="app">
        <header className="app-header">
          <h1>Stock Portfolio</h1>
        </header>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading stocks...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app">
        <header className="app-header">
          <h1>Stock Portfolio</h1>
        </header>
        <div className="error-container">
          <p className="error-message">Error: {error}</p>
          <button onClick={refetch} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const sortedStocks = stockUtils.sortByName(stocks);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Stock Portfolio</h1>
        <p>Total stocks: {stocks.length}</p>
      </header>
      
      <main className="app-main">
        {sortedStocks.length === 0 ? (
          <div className="empty-state">
            <p>No stocks available</p>
            <button onClick={refetch} className="refresh-button">
              Refresh
            </button>
          </div>
        ) : (
          <div className="stocks-grid" data-testid="stocks-grid">
            {sortedStocks.map(stock => (
              <StockCard key={stock.id} stock={stock} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;