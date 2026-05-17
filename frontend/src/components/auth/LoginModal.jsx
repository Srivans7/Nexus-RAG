import { useEffect, useRef } from 'react';

import { GOOGLE_CLIENT_ID } from '../../services/config';

export function LoginModal({ isOpen, onClose, onAuthSuccess }) {
  const googleBtnRef = useRef(null);

  useEffect(() => {
    if (!isOpen || !googleBtnRef.current || !GOOGLE_CLIENT_ID) return;

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;

    script.onload = () => {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => {
            onAuthSuccess(response);
            onClose();
          },
          auto_select: false,
        });

        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'filled_black',
          size: 'large',
          width: '100%',
          text: 'signin_with',
        });
      }
    };

    document.body.appendChild(script);

    return () => {
      try {
        document.body.removeChild(script);
      } catch (e) {
        // Script already removed
      }
    };
  }, [isOpen, onAuthSuccess, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative rounded-[32px] border border-white/10 bg-surface-container-high px-8 py-12 shadow-2xl w-full max-w-sm">
        <button
          className="absolute right-4 top-4 text-on-surface-variant transition hover:text-on-surface"
          onClick={onClose}
          type="button"
        >
          <span className="material-symbols-outlined">close</span>
        </button>

        <div className="space-y-6">
          <div className="text-center">
            <h2 className="font-geist text-2xl font-semibold text-on-surface">
              Sign in to Nexus AI
            </h2>
            <p className="mt-2 text-sm text-on-surface-variant">
              Access your documents and save your conversations
            </p>
          </div>

          <div className="space-y-4">
            {GOOGLE_CLIENT_ID ? (
              <div ref={googleBtnRef} className="flex justify-center" />
            ) : (
              <p className="rounded-2xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                Google sign-in is not configured yet.
              </p>
            )}

            <div className="flex items-center gap-3">
              <div className="flex-1 border-t border-white/10" />
              <span className="text-xs text-on-surface-variant">or continue as</span>
              <div className="flex-1 border-t border-white/10" />
            </div>

            <button
              className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm font-medium text-on-surface transition hover:bg-white/5"
              onClick={onClose}
              type="button"
            >
              Continue as Guest
            </button>
          </div>

          <p className="text-center text-xs text-on-surface-variant/70">
            By signing in, you agree to our Terms of Service
          </p>
        </div>
      </div>
    </div>
  );
}
