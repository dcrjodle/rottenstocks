# CLAUDE Development Rules

## Code Generation and Project Structure Guidelines

When generating code and structuring projects, follow these core principles:

---

## Component Structure Rules

### 100-Line Component Limit
- Components should not exceed ~100 lines
- If approaching limit, extract logic to hooks or split component
- Components handle only rendering and user interaction

### Logic Separation
```javascript
// ✅ Component: Only rendering and events
function UserProfile({ userId }) {
  const { user, loading, error, updateUser } = useUserProfile(userId);
  
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return (
    <div>
      <h1>{user.name}</h1>
      <button onClick={() => updateUser(user.id, newData)}>
        Update
      </button>
    </div>
  );
}

// ✅ Hook: State management and side effects
function useUserProfile(userId) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const updateUser = useCallback(async (id, data) => {
    const result = await userService.update(id, data);
    setUser(result);
  }, []);
  
  return { user, loading, error, updateUser };
}

// ✅ Utils: Pure business logic
export const userService = {
  async update(id, data) {
    const validated = validateUserData(data);
    return api.put(`/users/${id}`, validated);
  }
};
```

---

## Context Comments

Every component must start with context documentation:

```javascript
/**
 * CONTEXT: ComponentName
 * PURPOSE: Brief description of what this component does
 * DEPENDENCIES: List key dependencies (hooks, utils, APIs)
 * TESTING: Reference to test file location
 */
```

Example:
```javascript
/**
 * CONTEXT: ProductCard
 * PURPOSE: Displays product information with add-to-cart functionality
 * DEPENDENCIES: useCart hook, priceUtils, productAPI
 * TESTING: See ProductCard.test.js for coverage
 */
function ProductCard({ product }) {
  // Component implementation
}
```

---

## File Organization

### Utils-First Approach
- Extract all business logic to testable utility functions
- Utils should be pure functions when possible
- Group related utilities in dedicated files

```
src/
├── components/
│   ├── ProductCard/
│   │   ├── ProductCard.jsx
│   │   ├── ProductCard.test.js
│   │   └── index.js
├── hooks/
│   ├── useCart.js
│   ├── useProducts.js
│   └── __tests__/
├── utils/
│   ├── priceUtils.js
│   ├── validationUtils.js
│   ├── dateUtils.js
│   └── __tests__/
```

### Testability Requirements
- Every utility function has unit tests
- Hooks have dedicated test files
- Components have integration tests

---

## Development Approach

### Small, Incremental Changes
- Make minimal changes that add value
- Test immediately after each change
- Commit working state frequently

### Horizontal Slice Development
Build features across all layers simultaneously:

1. **Start with UI component** (minimal, with mock data)
2. **Add hook for state management**
3. **Create utility functions for business logic**
4. **Add API integration**
5. **Write comprehensive tests**

```javascript
// Phase 1: Component with mock data
function UserList() {
  const mockUsers = [{ id: 1, name: 'John' }];
  return <ul>{mockUsers.map(user => <li key={user.id}>{user.name}</li>)}</ul>;
}

// Phase 2: Add hook
function UserList() {
  const { users } = useUsers();
  return <ul>{users.map(user => <li key={user.id}>{user.name}</li>)}</ul>;
}

// Phase 3: Add business logic utils
const userUtils = {
  sortByName: (users) => users.sort((a, b) => a.name.localeCompare(b.name)),
  filterActive: (users) => users.filter(user => user.active)
};

// Phase 4: Complete with API and tests
```

---

## Testing Strategy

### Required Test Coverage
- **Utils**: Unit tests for all functions
- **Hooks**: Test state management and side effects
- **Components**: Integration tests for user interactions
- **E2E**: Critical user journeys

### Test File Structure
```javascript
// utils/priceUtils.test.js
describe('priceUtils', () => {
  describe('calculateDiscount', () => {
    it('should calculate percentage discount correctly', () => {
      expect(calculateDiscount(100, 0.1)).toBe(10);
    });
    
    it('should handle edge cases', () => {
      expect(calculateDiscount(0, 0.1)).toBe(0);
      expect(calculateDiscount(100, 0)).toBe(0);
    });
  });
});
```

---

## Code Generation Guidelines

When generating code, always:

1. **Start with context comment**
2. **Keep components under 100 lines**
3. **Extract logic to hooks and utils**
4. **Create accompanying test files**
5. **Use descriptive, self-documenting names**
6. **Follow horizontal slice pattern**

### Example Generated Structure
```javascript
/**
 * CONTEXT: ShoppingCart
 * PURPOSE: Manages cart items with add/remove functionality
 * DEPENDENCIES: useCart hook, cartUtils, productAPI
 * TESTING: See ShoppingCart.test.js
 */
function ShoppingCart() {
  const { items, addItem, removeItem, total } = useCart();
  
  return (
    <div className="shopping-cart">
      <h2>Cart ({cartUtils.getItemCount(items)} items)</h2>
      {items.map(item => (
        <CartItem 
          key={item.id} 
          item={item} 
          onRemove={() => removeItem(item.id)} 
        />
      ))}
      <div className="total">Total: {cartUtils.formatPrice(total)}</div>
    </div>
  );
}
```

---

## Error Handling Pattern

Always include proper error handling:

```javascript
// Hook with error handling
function useData(id) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const result = await dataService.fetch(id);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, [id]);
  
  return { data, loading, error };
}
```

These rules ensure maintainable, testable, and scalable code generation that follows established patterns and best practices.