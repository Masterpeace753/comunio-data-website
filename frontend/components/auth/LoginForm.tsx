"use client";

import { FormEvent, useState } from "react";

export function LoginForm({ nextPath }: { nextPath: string }) {
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    const formData = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
        cache: "no-store",
      });

      if (!response.ok) {
        setError(
          response.status === 429
            ? "Zu viele Versuche. Bitte später erneut versuchen."
            : "Anmeldung fehlgeschlagen.",
        );
        return;
      }

      window.location.assign(nextPath);
    } catch {
      setError("Der Anmeldedienst ist aktuell nicht erreichbar.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
      <div>
        <label className="mb-2 block text-sm font-semibold" htmlFor="username">
          Benutzername
        </label>
        <input
          className="input"
          id="username"
          name="username"
          autoComplete="username"
          required
          disabled={submitting}
        />
      </div>
      <div>
        <label className="mb-2 block text-sm font-semibold" htmlFor="password">
          Passwort
        </label>
        <input
          className="input"
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          disabled={submitting}
        />
      </div>
      {error && <p className="text-sm text-danger" role="alert">{error}</p>}
      <button
        className="button w-full border-accent bg-accent text-white hover:text-white"
        type="submit"
        disabled={submitting}
      >
        {submitting ? "Anmeldung läuft …" : "Anmelden"}
      </button>
    </form>
  );
}
