"use client";

import React, { Component, type ReactNode } from "react";
import LogoWordmark from "./LogoWordmark";
import LogoIcon from "./LogoIcon";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/* ---------------------------------------------------------------------------
   ErrorBoundary — Catches React render errors
   Shows the void circle in "balanced" state (settling after disruption)
   with the wordmark beneath.
   --------------------------------------------------------------------------- */

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
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
        <div className="error-page">
          <div className="error-content">
            <div className="error-rule-top" />
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-5)" }}>
              <LogoIcon size={48} animation="balanced" />
              <LogoWordmark height={16} />
            </div>
            <h1 className="text-xl" style={{ color: "var(--fg-primary)", marginBottom: "var(--space-3)" }}>
              Something went wrong
            </h1>
            <p className="text-base" style={{ color: "var(--fg-secondary)", marginBottom: "var(--space-5)" }}>
              An unexpected error occurred while loading the page. Please try
              refreshing to continue reading.
            </p>
            {this.state.error && (
              <pre className="error-details">{this.state.error.message}</pre>
            )}
            <button onClick={this.handleRefresh} className="btn-primary">
              Try refreshing
            </button>
            <div className="error-rule-bottom" />
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
