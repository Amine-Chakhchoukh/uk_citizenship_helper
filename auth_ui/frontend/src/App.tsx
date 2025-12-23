import React, { useEffect, useState } from "react";
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

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session ?? null);
      setLoading(false);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => sub.subscription.unsubscribe();
  }, []);

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
    if (error) {
      console.error(error);
      alert(error.message);
    }
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error(error);
      alert(error.message);
    }
  };

  const continueWithEmail = async () => {
    // Not wired yet — this is just UI for now.
    // If you want, next step is: enable Email provider in Supabase + magic link here.
    alert("Email sign-in not wired yet. We can add magic link next.");
  };

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

        {/* Session status */}
        {!loading && session && (
          <div className="finePrint" style={{ marginTop: 4 }}>
            ✅ Signed in as <b>{session.user.email}</b>{" "}
            <button
              type="button"
              onClick={signOut}
              style={{ marginLeft: 12 }}
            >
              Sign out
            </button>
          </div>
        )}

        <div className="stack">
          <ProviderButton
            icon={<GoogleIcon />}
            label={loading ? "Loading…" : session ? "Continue with Google" : "Continue with Google"}
            onClick={signInWithGoogle}
            disabled={loading}
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
          />
        </label>

        <button className="primaryBtn" type="button" onClick={continueWithEmail}>
          Continue
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
      </div>
    </div>
  );
}