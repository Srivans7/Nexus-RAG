import { useEffect, useRef, useState } from 'react';

import { GOOGLE_CLIENT_ID } from '../../services/config';

export function AuthPage({ authError, isLoading, onAuthSuccess }) {
  const googleBtnRef = useRef(null);
  const [activeDialog, setActiveDialog] = useState('');

  useEffect(() => {
    if (!googleBtnRef.current) {
      return undefined;
    }

    googleBtnRef.current.innerHTML = '';

    if (!GOOGLE_CLIENT_ID) {
      return undefined;
    }

    const initializeButton = () => {
      if (!window.google?.accounts?.id) {
        return;
      }

      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: onAuthSuccess,
        auto_select: false,
      });

      window.google.accounts.id.renderButton(googleBtnRef.current, {
        type: 'standard',
        theme: 'filled_black',
        text: 'continue_with',
        shape: 'pill',
        size: 'large',
        width: googleBtnRef.current.offsetWidth || 420,
      });
    };

    if (window.google?.accounts?.id) {
      initializeButton();
      return undefined;
    }

    const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (existingScript) {
      existingScript.addEventListener('load', initializeButton, { once: true });
      return () => existingScript.removeEventListener('load', initializeButton);
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.addEventListener('load', initializeButton, { once: true });
    document.body.appendChild(script);

    return () => {
      script.removeEventListener('load', initializeButton);
    };
  }, [onAuthSuccess]);

  const policyContent = {
    privacy: {
      title: 'Privacy Policy',
      sections: [
        {
          heading: 'Information We Collect',
          body: 'We collect basic account details such as your name, email address, and profile image when you sign in with Google. We also store your chat activity and uploaded documents so the product can provide conversation history and retrieval features.',
        },
        {
          heading: 'How We Use Your Information',
          body: 'Your information is used to authenticate your account, personalize the interface, process your uploaded content, and improve the reliability of the Nexus AI experience. We do not sell your personal information to third parties.',
        },
        {
          heading: 'Data Storage and Security',
          body: 'We use reasonable technical safeguards to protect stored account and application data. While no system can guarantee absolute security, we work to limit access and protect sensitive information from unauthorized use.',
        },
        {
          heading: 'Your Choices',
          body: 'You can stop using the service at any time. If you want your account-related data removed, you can request deletion through support or the future account management tools once they are available.',
        },
      ],
    },
    terms: {
      title: 'Terms and Conditions',
      sections: [
        {
          heading: 'Use of the Service',
          body: 'Nexus AI is provided for lawful use only. You agree not to upload harmful content, misuse the platform, attempt unauthorized access, or interfere with the availability of the service for other users.',
        },
        {
          heading: 'User Content',
          body: 'You are responsible for the documents and prompts you submit. You should only upload content that you are authorized to use, store, and process through this application.',
        },
        {
          heading: 'Service Availability',
          body: 'We may update, suspend, or change parts of the service at any time to improve performance, security, or functionality. We do not guarantee uninterrupted availability at all times.',
        },
        {
          heading: 'Limitation of Liability',
          body: 'Nexus AI is provided on an as-is basis for development and productivity use. You should review AI-generated responses before relying on them in any important, legal, academic, or business context.',
        },
      ],
    },
  };

  const dialog = activeDialog ? policyContent[activeDialog] : null;

  return (
    <div className="auth-shell relative min-h-screen overflow-hidden bg-black text-on-surface">
      <div className="auth-glow auth-glow-primary" />
      <div className="auth-glow auth-glow-secondary" />

      <div className="pointer-events-none hidden lg:block auth-node auth-node-left">
        <div className="auth-node-card">
          <div className="h-2 w-14 rounded-full bg-primary/40" />
          <div className="h-2 w-full rounded-full bg-white/5" />
          <div className="h-2 w-3/4 rounded-full bg-white/5" />
          <div className="mt-2 flex items-center gap-3">
            <div className="h-7 w-7 rounded-full bg-secondary/20" />
            <div className="h-2 w-20 rounded-full bg-white/10" />
          </div>
        </div>
      </div>

      <div className="pointer-events-none hidden lg:block auth-node auth-node-right">
        <div className="auth-node-card border-secondary/20">
          <div className="flex items-center justify-between text-secondary">
            <span className="material-symbols-outlined text-[20px]">memory</span>
            <span className="font-mono text-xs tracking-[0.18em]">ACTIVE</span>
          </div>
          <div className="relative mt-4 h-2 overflow-hidden rounded-full bg-white/5">
            <div className="auth-progress absolute inset-y-0 left-0 w-2/3 rounded-full" />
          </div>
          <p className="mt-3 font-mono text-xs text-on-surface-variant/45">
            Neural Engine: Optimizing Retrieval...
          </p>
        </div>
      </div>

      <main className="relative z-10 flex flex-col min-h-screen items-center justify-center px-6 py-10">
        <div className="w-full max-w-md">
          <div className="mb-10 text-center">
            <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-white/5 backdrop-blur-xl">
              <span className="material-symbols-outlined text-[34px] text-primary">neurology</span>
            </div>
            <h1 className="font-geist text-5xl font-bold tracking-tight text-on-surface">Nexus AI</h1>
            <p className="mt-3 text-lg text-on-surface-variant">The intelligence engine of the future.</p>
          </div>

          <section className="auth-card rounded-[28px] p-7 sm:p-8">
            <div className="space-y-4">
              <div className="auth-social-button">
                <div ref={googleBtnRef} className="w-full min-h-12" />
              </div>

              <button
                className="auth-social-button justify-center gap-3 opacity-70"
                disabled
                type="button"
              >
                <span className="material-symbols-outlined text-[20px]">code</span>
                <span className="font-geist text-base font-semibold">Continue with GitHub</span>
                <span className="ml-auto rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-on-surface-variant/70">
                  Soon
                </span>
              </button>
            </div>

            <p className="mt-5 text-center text-sm leading-6 text-on-surface-variant/80">
              Sign in with Google to access your workspace and saved conversations. GitHub authentication will be added soon.
            </p>

            {authError ? (
              <p className="mt-4 rounded-2xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                {authError}
              </p>
            ) : null}

            {!GOOGLE_CLIENT_ID ? (
              <p className="mt-4 rounded-2xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                Google sign-in is not configured. Add VITE_GOOGLE_CLIENT_ID in the frontend environment.
              </p>
            ) : null}

            {isLoading ? (
              <p className="mt-4 text-sm text-on-surface-variant">Signing you in...</p>
            ) : null}
          </section>

          <div className="mt-8 text-center text-sm text-on-surface-variant">
            <div className="flex items-center justify-center gap-8 text-sm text-on-surface-variant/70">
              <button className="hover:text-on-surface" onClick={() => setActiveDialog('privacy')} type="button">
                Privacy Policy
              </button>
              <button className="hover:text-on-surface" onClick={() => setActiveDialog('terms')} type="button">
                Terms of Service
              </button>
            </div>
          </div>
        </div>
      </main>

      {dialog ? (
        <div className="auth-dialog-overlay" role="dialog" aria-modal="true" aria-labelledby="auth-dialog-title">
          <div className="auth-dialog-card custom-scrollbar">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="auth-dialog-title" className="font-geist text-2xl font-semibold text-on-surface">
                  {dialog.title}
                </h2>
                <p className="mt-2 text-sm text-on-surface-variant">
                  These are standard application policies for the current Nexus AI experience.
                </p>
              </div>
              <button
                className="rounded-full border border-white/10 bg-white/5 p-2 text-on-surface-variant transition hover:text-on-surface"
                onClick={() => setActiveDialog('')}
                type="button"
              >
                <span className="material-symbols-outlined text-base">close</span>
              </button>
            </div>

            <div className="mt-6 space-y-5">
              {dialog.sections.map((section) => (
                <section key={section.heading} className="space-y-2">
                  <h3 className="font-geist text-lg font-semibold text-on-surface">{section.heading}</h3>
                  <p className="text-sm leading-7 text-on-surface-variant">{section.body}</p>
                </section>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}