"use client";

import React, { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/* ---------------------------------------------------------------------------
   ErrorBoundary — Catches React render errors
   Displays a newspaper-style "Something went wrong" message.
   JetBrains Mono for error details, Playfair for the headline.
   --------------------------------------------------------------------------- */

export default class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  handleRefresh = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "var(--bg-primary)",
            padding: "var(--space-7)",
          }}
        >
          <div
            style={{
              maxWidth: 480,
              width: "100%",
              textAlign: "center",
            }}
          >
            {/* Thin top rule — newspaper tradition */}
            <div
              style={{
                borderTop: "2px solid var(--fg-primary)",
                marginBottom: "var(--space-5)",
              }}
            />

            {/* Headline */}
            <h1
              style={{
                fontFamily: "var(--font-editorial)",
                fontSize: "var(--text-xl)",
                fontWeight: 700,
                lineHeight: 1.15,
                color: "var(--fg-primary)",
                marginBottom: "var(--space-3)",
              }}
            >
              Something went wrong
            </h1>

            <p
              style={{
                fontFamily: "var(--font-structural)",
                fontSize: "var(--text-base)",
                color: "var(--fg-secondary)",
                lineHeight: 1.6,
                marginBottom: "var(--space-5)",
              }}
            >
              An unexpected error occurred while loading the page. Please try
              refreshing to continue reading.
            </p>

            {/* Error details in data voice */}
            {this.state.error && (
              <pre
                style={{
                  fontFamily: "var(--font-data)",
                  fontSize: "var(--text-xs)",
                  color: "var(--fg-tertiary)",
                  backgroundColor: "var(--bg-secondary)",
                  padding: "var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  textAlign: "left",
                  overflow: "auto",
                  maxHeight: 120,
                  marginBottom: "var(--space-5)",
                  border: "1px solid var(--border-subtle)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {this.state.error.message}
              </pre>
            )}

            {/* Refresh button */}
            <button
              onClick={this.handleRefresh}
              style={{
                fontFamily: "var(--font-structural)",
                fontSize: "var(--text-sm)",
                fontWeight: 600,
                color: "var(--bg-primary)",
                backgroundColor: "var(--fg-primary)",
                padding: "var(--space-3) var(--space-5)",
                borderRadius: "var(--radius-md)",
                minHeight: 44,
                minWidth: 44,
                cursor: "pointer",
                border: "none",
                transition: "opacity var(--dur-fast) var(--ease-out)",
              }}
            >
              Try refreshing
            </button>

            {/* Bottom rule */}
            <div
              style={{
                borderBottom: "1px solid var(--divider)",
                marginTop: "var(--space-5)",
              }}
            />

            <span
              style={{
                fontFamily: "var(--font-editorial)",
                fontSize: "var(--text-xs)",
                color: "var(--fg-muted)",
                letterSpacing: "0.01em",
                display: "block",
                marginTop: "var(--space-3)",
              }}
            >
              void --news
            </span>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
