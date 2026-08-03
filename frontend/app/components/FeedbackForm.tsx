"use client";

import { useEffect, useRef, useState } from "react";
import { submitShipRequest, generateFingerprint } from "../lib/supabase";
import type { ShipCategory } from "../lib/types";
import "../styles/feedback.css";

/* ---------------------------------------------------------------------------
   FeedbackForm — the whole of the retired void --ship, reduced to a calm note.
   Reuses submitShipRequest + generateFingerprint + the same localStorage rate
   limit, so a note lands in the same ship_requests table with no new migration.
   No board, no votes, no replies, no status.
   --------------------------------------------------------------------------- */

const CATEGORY_OPTIONS: { value: ShipCategory; label: string }[] = [
  { value: "feature", label: "An idea or request" },
  { value: "bug", label: "Something is broken" },
];

/* Same key + window as ShipBoard, so the limit is shared across both surfaces. */
const RATE_LIMIT_KEY = "void-ship-submissions";
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW = 3600000;

function checkRateLimit(): boolean {
  try {
    const raw = localStorage.getItem(RATE_LIMIT_KEY);
    if (!raw) return true;
    const timestamps: number[] = JSON.parse(raw);
    const now = Date.now();
    return timestamps.filter((t) => now - t < RATE_LIMIT_WINDOW).length < RATE_LIMIT_MAX;
  } catch {
    return true;
  }
}

function recordSubmission(): void {
  try {
    const raw = localStorage.getItem(RATE_LIMIT_KEY);
    const timestamps: number[] = raw ? JSON.parse(raw) : [];
    timestamps.push(Date.now());
    const recent = timestamps.filter((t) => Date.now() - t < RATE_LIMIT_WINDOW);
    localStorage.setItem(RATE_LIMIT_KEY, JSON.stringify(recent));
  } catch {
    /* noop */
  }
}

export default function FeedbackForm() {
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [category, setCategory] = useState<ShipCategory>("feature");
  const [honeypot, setHoneypot] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [titleError, setTitleError] = useState("");
  const [messageError, setMessageError] = useState("");
  const [success, setSuccess] = useState(false);
  const fingerprintRef = useRef("");
  const titleRef = useRef<HTMLInputElement>(null);
  const messageRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fingerprintRef.current = generateFingerprint();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;

    // WCAG 3.3.1/3.3.3: the submit button stays enabled so keyboard/AT users
    // can trigger validation and hear WHY it failed. On invalid input we set
    // per-field error text (wired via aria-describedby + aria-invalid) and move
    // focus to the first offending field rather than silently blocking.
    const tErr =
      title.trim().length < 5
        ? "Please add a subject of at least 5 characters."
        : "";
    const mErr =
      message.trim().length < 10
        ? "Please add a message of at least 10 characters."
        : "";
    setTitleError(tErr);
    setMessageError(mErr);
    if (tErr || mErr) {
      if (tErr) titleRef.current?.focus();
      else messageRef.current?.focus();
      return;
    }

    // Honeypot: silently accept and reset without hitting the network.
    if (honeypot) {
      setSuccess(true);
      return;
    }
    if (!checkRateLimit()) {
      setError("You have sent a few notes already. Please try again in a little while.");
      return;
    }
    setSubmitting(true);
    setError("");
    const deviceInfo =
      typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 180) : null;
    const result = await submitShipRequest({
      title: title.trim(),
      description: message.trim(),
      category,
      area: "other",
      edition_context: null,
      device_info: deviceInfo,
      ip_hash: fingerprintRef.current,
    });
    if (result) {
      recordSubmission();
      setSuccess(true);
      setTitle("");
      setMessage("");
      setCategory("feature");
    } else {
      setError("Something went wrong sending that. Please try again.");
    }
    setSubmitting(false);
  };

  const sendAnother = () => {
    setSuccess(false);
    setError("");
    setTitleError("");
    setMessageError("");
    setHoneypot("");
    titleRef.current?.focus();
  };

  if (success) {
    return (
      <div className="fb-success" role="status" aria-live="polite">
        <div className="fb-success__mark" aria-hidden="true">&#9998;</div>
        <p className="fb-success__text">Thanks. We read every note.</p>
        <button type="button" className="fb-success__again" onClick={sendAnother}>
          Send another
        </button>
      </div>
    );
  }

  return (
    <form className="fb-form" onSubmit={handleSubmit} noValidate>
      {/* Honeypot — hidden from real users, catches naive bots. */}
      <div className="fb-honeypot" aria-hidden="true">
        <label htmlFor="fb-website">Website</label>
        <input
          id="fb-website"
          type="text"
          value={honeypot}
          onChange={(e) => setHoneypot(e.target.value)}
          tabIndex={-1}
          autoComplete="off"
        />
      </div>

      <div className="fb-field">
        <label className="fb-label" htmlFor="fb-category">
          Kind of note
        </label>
        <select
          id="fb-category"
          className="fb-select"
          value={category}
          onChange={(e) => setCategory(e.target.value as ShipCategory)}
        >
          {CATEGORY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="fb-field">
        <label className="fb-label" htmlFor="fb-title">
          Subject
        </label>
        <input
          ref={titleRef}
          id="fb-title"
          className="fb-input"
          type="text"
          maxLength={120}
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            if (titleError && e.target.value.trim().length >= 5) setTitleError("");
          }}
          placeholder="A short summary"
          required
          aria-invalid={titleError ? true : undefined}
          aria-describedby={titleError ? "fb-title-error" : "fb-title-hint"}
        />
        {titleError ? (
          <p className="fb-field-error" id="fb-title-error">
            {titleError}
          </p>
        ) : (
          <p className="fb-hint" id="fb-title-hint">
            At least 5 characters.
          </p>
        )}
      </div>

      <div className="fb-field">
        <label className="fb-label" htmlFor="fb-message">
          Message
        </label>
        <textarea
          ref={messageRef}
          id="fb-message"
          className="fb-textarea"
          maxLength={2000}
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            if (messageError && e.target.value.trim().length >= 10) setMessageError("");
          }}
          placeholder="What broke, what is missing, or what would make this better."
          required
          aria-invalid={messageError ? true : undefined}
          aria-describedby={messageError ? "fb-message-error" : "fb-message-hint"}
        />
        {messageError ? (
          <p className="fb-field-error" id="fb-message-error">
            {messageError}
          </p>
        ) : (
          <p className="fb-hint" id="fb-message-hint">
            At least 10 characters.
          </p>
        )}
      </div>

      {error && (
        <p className="fb-error" role="alert">
          {error}
        </p>
      )}

      <button type="submit" className="fb-submit" disabled={submitting}>
        {submitting ? "Sending..." : "Send feedback"}
      </button>
    </form>
  );
}
