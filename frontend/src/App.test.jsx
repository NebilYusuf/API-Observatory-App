import React from "react";
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { screen } from "@testing-library/dom";
import "@testing-library/jest-dom/vitest";
import userEvent from "@testing-library/user-event";
import { createRoot } from "react-dom/client";
import App from "./App";

let container = null;
let root = null;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  if (root) {
    root.unmount();
  }
  if (container) {
    container.remove();
    container = null;
  }
  vi.restoreAllMocks();
});

const render = async (ui) => {
  root.render(ui);
  await new Promise((resolve) => setTimeout(resolve, 0));
};

describe("App", () => {
  it("renders the main page and sample buttons", async () => {
    await render(<App />);

    expect(screen.getByRole("heading", { name: /api observatory/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/enter a url like api.github.com/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /check status/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /github api/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /jsonplaceholder/i })).toBeInTheDocument();
  });

  it("loads a sample URL when a sample button is clicked", async () => {
    await render(<App />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /github api/i }));
    expect(screen.getByPlaceholderText(/enter a url like api.github.com/i)).toHaveValue("api.github.com");

    await user.click(screen.getByRole("button", { name: /jsonplaceholder/i }));
    expect(screen.getByPlaceholderText(/enter a url like api.github.com/i)).toHaveValue("jsonplaceholder.typicode.com/posts");
  });

  it("submits the form and displays fetch results", async () => {
    await render(<App />);
    const fakeResult = {
      url: "https://example.com",
      status: "Up",
      status_code: 200,
      response_time_ms: 123.45,
      checked_at: "2026-06-17 10:00:00 AM",
      message: "Healthy response",
    };

    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve(fakeResult) })
    ));

    const user = userEvent.setup();
    const input = screen.getByPlaceholderText(/enter a url like api.github.com/i);

    await user.type(input, "example.com");
    await user.click(screen.getByRole("button", { name: /check status/i }));

    expect(global.fetch).toHaveBeenCalledWith("http://127.0.0.1:8000/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: "example.com" }),
    });

    expect(await screen.findByText(/check result/i)).toBeInTheDocument();
    expect(screen.getByText("Up")).toBeInTheDocument();
    expect(screen.getByText(/healthy response/i)).toBeInTheDocument();
  });

  it("shows an error message when the backend request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("Network error"))));

    await render(<App />);
    const user = userEvent.setup();
    const input = screen.getByPlaceholderText(/enter a url like api.github.com/i);

    await user.type(input, "example.com");
    await user.click(screen.getByRole("button", { name: /check status/i }));

    expect(await screen.findByText(/something went wrong while contacting the backend/i)).toBeInTheDocument();
  });
});
