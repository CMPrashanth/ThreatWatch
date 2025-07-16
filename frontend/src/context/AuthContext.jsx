import { createContext, useContext } from 'react';

/**
 * This file creates and exports the authentication context and hook.
 * By keeping it separate, we avoid circular dependencies between App.jsx
 * and the components that need authentication info.
 */

export const AuthContext = createContext(null);

export const useAuth = () => {
  return useContext(AuthContext);
};
