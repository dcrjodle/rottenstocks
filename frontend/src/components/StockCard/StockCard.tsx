/**
 * CONTEXT: StockCard
 * PURPOSE: Displays individual stock information with name and price
 * DEPENDENCIES: stockUtils for price formatting
 * TESTING: See StockCard.test.js for coverage
 */

import React from 'react';
import { stockUtils } from '../../utils/stockUtils';
import { Stock } from '../../types/stock';
import './StockCard.css';

interface StockCardProps {
  stock?: Stock;
}

function StockCard({ stock }: StockCardProps) {
  if (!stock) {
    return (
      <div className="stock-card stock-card--loading">
        <div className="stock-card__name">Loading...</div>
        <div className="stock-card__price">--</div>
      </div>
    );
  }

  const formattedPrice = stockUtils.formatPrice(stock.price);

  return (
    <div className="stock-card" data-testid="stock-card">
      <div className="stock-card__name" data-testid="stock-name">
        {stock.name}
      </div>
      <div className="stock-card__price" data-testid="stock-price">
        {formattedPrice}
      </div>
    </div>
  );
}

export default StockCard;