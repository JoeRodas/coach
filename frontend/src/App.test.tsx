import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App shell", () => {
  it("renders the analyze page stub at /", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: /analyze a game/i })).toBeInTheDocument();
  });

  it("renders the metrics page stub at /admin/metrics", () => {
    renderAt("/admin/metrics");
    expect(screen.getByRole("heading", { name: /admin · metrics/i })).toBeInTheDocument();
  });

  it("shows a not-found stub for unknown routes", () => {
    renderAt("/nope");
    expect(screen.getByText(/not found/i)).toBeInTheDocument();
  });
});
