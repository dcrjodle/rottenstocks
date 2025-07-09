/**
 * CONTEXT: AppHeader
 * PURPOSE: Header component displaying app title, stock count, and sync button
 * DEPENDENCIES: None (receives props from parent)
 * TESTING: See AppHeader.test.js for coverage
 */

import React from 'react';
import './AppHeader.css';

interface AppHeaderProps {
  stockCount: number;
  onSync: () => void;
  loading: boolean;
}

function AppHeader({ stockCount, onSync, loading }: AppHeaderProps): React.JSX.Element {
  return (
    <header className="app-header">
      <h1>Stock Portfolio</h1>
      <div className="header-info">
        <p>Total stocks: {stockCount}</p>
        <button onClick={onSync} className="sync-button" disabled={loading}>
          {loading ? 'Syncing...' : 'Sync Fresh Data'}
        </button>
      </div>
    </header>
  );
}

export default AppHeader;