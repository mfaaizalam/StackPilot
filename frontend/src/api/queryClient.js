import { QueryClient } from "@tanstack/react-query";

// Shared cache for the whole app.
// staleTime: data counts as fresh for 1 minute, so page/tab switches read from memory.
// refetchOnWindowFocus: false stops refetching when you return to the browser tab.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});