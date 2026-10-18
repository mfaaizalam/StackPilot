import { QueryClient } from "@tanstack/react-query";

// Single shared client. Imported by main.jsx (provider) and axios.js
// (cache invalidation after writes). It imports nothing from the app, so
// there is no circular import with axios.js.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,          // lists (boards) don't refetch on every mount
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});