/**
 * Shared render helpers for component and page tests.
 *
 * Most of the app's screens lean on three providers: the MUI theme, the
 * react-router context, and the react-query client. These helpers wrap a
 * subject in whatever combination it needs so individual tests stay short.
 */

import type { ReactElement, ReactNode } from "react";
import { render } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { darkTheme } from "@/theme/theme";

/**
 * Fresh query client per render. Retries are off so failed mutations surface
 * their error state immediately instead of being retried on a timer.
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

interface ProvidersProps {
  children: ReactNode;
  client?: QueryClient;
  route?: string;
}

export function AllProviders({ children, client, route = "/" }: ProvidersProps) {
  const queryClient = client ?? makeQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={darkTheme}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

/** Render a full page/screen with theme + router + query providers. */
export function renderWithProviders(ui: ReactElement, route = "/") {
  const client = makeQueryClient();
  return render(
    <AllProviders client={client} route={route}>
      {ui}
    </AllProviders>
  );
}

/** Render a leaf component that only needs the MUI theme. */
export function renderWithTheme(ui: ReactElement) {
  return render(<ThemeProvider theme={darkTheme}>{ui}</ThemeProvider>);
}
