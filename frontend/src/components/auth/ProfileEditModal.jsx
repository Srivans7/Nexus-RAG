import { useState } from 'react';

export function ProfileEditModal({ user, isLoading, onClose, onSave }) {
  const [name, setName] = useState(user?.name || '');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!name.trim()) {
      setError('Name cannot be empty');
      return;
    }

    const updated = await onSave(name);
    if (updated) {
      setSuccess('Profile updated successfully!');
      setTimeout(() => {
        onClose();
      }, 1500);
    } else {
      setError('Failed to update profile. Please try again.');
    }
  };

  return (
    <div className="auth-dialog-overlay" role="dialog" aria-modal="true" aria-labelledby="profile-edit-title">
      <div className="auth-dialog-card max-w-md">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="profile-edit-title" className="font-geist text-2xl font-semibold text-on-surface">
              Edit Profile
            </h2>
            <p className="mt-2 text-sm text-on-surface-variant">
              Update your profile information
            </p>
          </div>
          <button
            className="rounded-full border border-white/10 bg-white/5 p-2 text-on-surface-variant transition hover:text-on-surface"
            onClick={onClose}
            type="button"
            disabled={isLoading}
          >
            <span className="material-symbols-outlined text-base">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {/* Current Avatar */}
          <div className="flex flex-col items-center gap-2">
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.name}
                className="h-16 w-16 rounded-full border border-primary/30 shadow-glow"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-container text-on-primary-container shadow-glow">
                <span className="material-symbols-outlined text-[32px]">person</span>
              </div>
            )}
            <p className="text-xs text-on-surface-variant">{user?.email}</p>
          </div>

          {/* Name Input */}
          <div className="space-y-2">
            <label htmlFor="name" className="block text-sm font-medium text-on-surface">
              Name
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name"
              disabled={isLoading}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-on-surface placeholder-on-surface-variant/50 transition focus:border-primary/50 focus:bg-white/10 focus:outline-none disabled:opacity-50"
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-2xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
              {error}
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="rounded-2xl border border-secondary/30 bg-secondary/10 px-4 py-3 text-sm text-secondary">
              {success}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-on-surface-variant transition hover:bg-white/10 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 rounded-2xl bg-primary px-4 py-3 text-sm font-medium text-on-primary transition hover:bg-primary-container disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
