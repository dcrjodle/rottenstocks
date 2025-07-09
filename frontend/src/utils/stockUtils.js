/**
 * Utility functions for stock data manipulation and formatting
 */

export const stockUtils = {
  /**
   * Format price as currency string
   * @param {number} price - The price to format
   * @returns {string} Formatted price string
   */
  formatPrice(price) {
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

  /**
   * Validate stock data structure
   * @param {object} stock - Stock object to validate
   * @returns {boolean} True if valid stock object
   */
  isValidStock(stock) {
    return (
      stock &&
      typeof stock.id === 'number' &&
      typeof stock.name === 'string' &&
      stock.name.length > 0 &&
      typeof stock.price === 'number' &&
      stock.price >= 0
    );
  },

  /**
   * Sort stocks by name alphabetically
   * @param {Array} stocks - Array of stock objects
   * @returns {Array} Sorted array of stocks
   */
  sortByName(stocks) {
    if (!Array.isArray(stocks)) {
      return [];
    }
    
    return [...stocks].sort((a, b) => {
      if (!a.name || !b.name) return 0;
      return a.name.localeCompare(b.name);
    });
  },

  /**
   * Sort stocks by price (descending)
   * @param {Array} stocks - Array of stock objects
   * @returns {Array} Sorted array of stocks
   */
  sortByPrice(stocks) {
    if (!Array.isArray(stocks)) {
      return [];
    }
    
    return [...stocks].sort((a, b) => {
      if (typeof a.price !== 'number' || typeof b.price !== 'number') return 0;
      return b.price - a.price;
    });
  }
};