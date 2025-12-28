import React, { useEffect, useMemo, useState } from "react";
import "./App.css";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabaseClient";

function GoogleIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 48 48"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        fill="#EA4335"
        d="M24 9.5c3.54 0 6.7 1.22 9.2 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6.01c4.51-4.18 7.09-10.33 7.09-17.66z"
      />
      <path
        fill="#FBBC05"
        d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24s.92 7.54 2.56 10.78l7.97-6.19z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.48 0 11.93-2.13 15.9-5.81l-7.73-6.01c-2.15 1.45-4.92 2.31-8.17 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.97 6.19C6.51 42.62 14.62 48 24 48z"
      />
    </svg>
  );
}

function ProviderButton({
  icon,
  label,
  onClick,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      className="providerBtn"
      type="button"
      onClick={onClick}
      disabled={disabled}
    >
      <span className="providerIcon">{icon}</span>
      <span className="providerLabel">{label}</span>
      <span className="providerSpacer" />
    </button>
  );
}

function isValidEmail(e: string) {
  // simple + practical (not RFC-perfect)
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e.trim());
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);

  const [email, setEmail] = useState("");
  const [sendingLink, setSendingLink] = useState(false);
  const [magicSentTo, setMagicSentTo] = useState<string | null>(null);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth
      .getSession()
      .then(({ data }) => {
        setSession(data.session ?? null);
      })
      .finally(() => setLoadingSession(false));

    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => sub.subscription.unsubscribe();
  }, []);

  // Clear transient UI messages when session changes (e.g., user signs in)
  useEffect(() => {
    if (session) {
      setErrorMsg(null);
      setMagicSentTo(null);
    }
  }, [session]);

  const canSendMagic = useMemo(() => {
    if (sendingLink || loadingSession) return false;
    if (!isValidEmail(email)) return false;
    return true;
  }, [email, sendingLink, loadingSession]);

  const signInWithGoogle = async () => {
    setErrorMsg(null);
    setMagicSentTo(null);

    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });

    if (error) setErrorMsg(error.message);
  };

  const signOut = async () => {
    setErrorMsg(null);
    setMagicSentTo(null);

    const { error } = await supabase.auth.signOut();
    if (error) setErrorMsg(error.message);
  };

  const continueWithEmail = async () => {
    setErrorMsg(null);
    setMagicSentTo(null);

    const trimmed = email.trim();
    if (!isValidEmail(trimmed)) {
      setErrorMsg("Please enter a valid email address.");
      return;
    }

    setSendingLink(true);
    try {
      const { error } = await supabase.auth.signInWithOtp({
        email: trimmed,
        options: {
          // where Supabase should send the user back after they click the email link
          emailRedirectTo: window.location.origin,
        },
      });

      if (error) {
        setErrorMsg(error.message);
        return;
      }

      setMagicSentTo(trimmed);
    } finally {
      setSendingLink(false);
    }
  };

  const isAuthed = !!session && !loadingSession;

  return (
    <div className="page">
      <div className="card">
        <div className="header">
          <div className="titleRow">
            <span className="flag" aria-hidden="true">
              🇬🇧
            </span>
            <div className="title">UK Citizenship Absence Checker</div>
          </div>
          <div className="subtitle">
            For EU citizens checking UK residency requirements
          </div>
        </div>

        {/* Status / feedback */}
        {!loadingSession && session && (
          <div className="finePrint" style={{ marginTop: 8, textAlign: "left" }}>
            ✅ Signed in as <b>{session.user.email}</b>
            <button
              type="button"
              onClick={signOut}
              style={{
                marginLeft: 12,
                border: "1px solid #e6e6e6",
                background: "#fff",
                borderRadius: 8,
                padding: "6px 10px",
                cursor: "pointer",
              }}
            >
              Sign out
            </button>
          </div>
        )}

        {magicSentTo && !session && (
          <div
            className="finePrint"
            style={{
              marginTop: 10,
              textAlign: "left",
              background: "#f6ffed",
              border: "1px solid #b7eb8f",
              color: "#135200",
              padding: "10px 12px",
              borderRadius: 10,
            }}
          >
            ✅ Magic link sent to <b>{magicSentTo}</b>. Check your inbox and click
            the link to sign in.
          </div>
        )}

        {errorMsg && (
          <div
            className="finePrint"
            style={{
              marginTop: 10,
              textAlign: "left",
              background: "#fff1f0",
              border: "1px solid #ffa39e",
              color: "#a8071a",
              padding: "10px 12px",
              borderRadius: 10,
            }}
          >
            {errorMsg}
          </div>
        )}

        {/* If you're signed in, you usually don't need to show the login UI */}
        {!isAuthed && (
          <>
            <div className="stack">
              <ProviderButton
                icon={<GoogleIcon />}
                label={loadingSession ? "Loading…" : "Continue with Google"}
                onClick={signInWithGoogle}
                disabled={loadingSession}
              />
            </div>

            <div className="divider" aria-hidden="true">
              <span />
              <span className="or">or</span>
              <span />
            </div>

            <label className="field">
              <div className="fieldLabel">Email</div>
              <input
                className="input"
                placeholder="Enter your email address…"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={sendingLink || loadingSession}
              />
            </label>

            <button
              className="primaryBtn"
              type="button"
              onClick={continueWithEmail}
              disabled={!canSendMagic}
              style={{
                opacity: !canSendMagic ? 0.6 : 1,
                cursor: !canSendMagic ? "not-allowed" : "pointer",
              }}
            >
              {sendingLink ? "Sending link…" : "Continue"}
            </button>

            <div className="finePrint">
              By continuing, you agree to our{" "}
              <a href="#" onClick={(e) => e.preventDefault()}>
                Terms
              </a>{" "}
              and{" "}
              <a href="#" onClick={(e) => e.preventDefault()}>
                Privacy Policy
              </a>
              .
            </div>
          </>
        )}

        {/* Post-login placeholder (Phase 1) */}
        {isAuthed && (
          <div style={{ marginTop: 18 }}>
            <div className="divider" aria-hidden="true" style={{ marginTop: 10 }}>
              <span />
              <span className="or">your trips</span>
              <span />
            </div>
            <div className="finePrint" style={{ textAlign: "left" }}>
              Next: we’ll show the trips UI below this (still on the same page).
            </div>
          </div>
        )}
      </div>
    </div>
  );
}