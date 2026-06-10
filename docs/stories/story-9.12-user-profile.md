# story-9.12 — user-profile: server-side settings truth

**Epic:** 9 · **Depends on:** story-9.4 (firebase-auth), story-9.11 (truth-pass-2)
**Decided with Abu 2026-06-10** (instrusctions.md): settings must not live in browser localStorage when the product has real auth + Firestore. The `users/{uid}` profile is the spine the onboarding wizard (story-9.13) and GitLab connect (Wave C) hang off.

## Why

The settings page stores hosting mode + framework preference in `localStorage` — lost on cache clear, invisible across browsers, and dishonest next to a real authenticated backend. `org_id` is a hardcoded `"default"` server-side; no user profile exists at all.

## BDD acceptance criteria

- **Given** an authenticated user with no stored profile, **when** `GET /profile`, **then** a default profile is returned (their uid + token email, `framework_default: "EU AI Act"`, `hosting_pref: "default"`, `onboarded: false`) WITHOUT creating a Firestore document.
- **Given** `PATCH /profile` with a subset of `{org_name, framework_default, hosting_pref, onboarded}`, **then** exactly those fields update (upsert), `updated_at` advances, `created_at` is set once, and the response is the merged profile.
- **Given** a PATCH with an unknown field or invalid value (`hosting_pref` outside `default|byo`, empty `framework_default`), **then** 422 — never a silently-dropped write.
- **Given** two users, **then** each only ever reads/writes their own profile (uid comes from the verified token; there is no profile id parameter).
- **Given** the settings page, **then** hosting + framework prefs load from and save to `/profile` via the proxy; localStorage keeps ONLY the replay clock. The page shows real save state (saving/saved/error) — no fire-and-forget.
- **Given** `/new`, **then** the framework default comes from the profile.
- Route-auth contract: both `/profile` routes carry `require_user` (pinned by the existing auth-scoping registry test automatically).

## File map

- Backend: `storage/models.py` (+`UserProfile`, `HostingPref`), `storage/profiles.py` (new store + seam), `api/profile.py` (new router), `main.py` (include), `tests/unit/api/test_profile_api.py`, `tests/unit/storage/fakes.py` (+InMemoryProfileStore).
- Web: proxy allowlist `+/^profile$/` (`app/api/agent/[...path]/route.ts`), `app/settings/page.tsx` + settings client (server-persisted), `app/new/page.tsx` (profile framework default), `lib/prefs.ts` deleted, `lib/api.ts` (+ProfileDto fetchers), tests (`proxy-allowlist`, profile mapper/save-state).

## Notes

- `gitlab` connection blob and wizard `onboarded` flow build on this in later stories; the model uses `extra="ignore"` reads so those fields can land without migration.
- Email on the profile mirrors the verified token at read/write time — display convenience, not identity.
