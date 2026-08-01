# SafeRoute AI — Authentication Setup Guide

Complete step-by-step guide to enable all auth providers in Supabase.

---

## 1. Run the SQL Migration

Open your Supabase project → **SQL Editor** → paste the full contents of
`Backend/supabase_schema.sql` and click **Run**.

This creates:
- `profiles` table (with auto-create trigger on sign-up)
- `route_history`, `saved_routes`, `incident_reports`
- `traffic_reports`, `weather_reports`, `crowd_density_reports`
- `sos_requests`, `emergency_requests`, `notifications`
- `favorite_locations`, `recent_searches`
- All RLS policies, indexes, and updated_at triggers
- Storage buckets: `avatars`, `incident-images`, `route-screenshots`

---

## 2. Enable Email/Password Auth

Supabase Dashboard → **Authentication → Providers → Email**

- ✅ Enable Email provider
- Set "Confirm email" to **Enabled** (users get a verification email)
- Set "Secure email change" to **Enabled**
- Site URL: `http://localhost` (dev) or your production URL

---

## 3. Enable Google OAuth

### Step A — Google Cloud Console

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. APIs & Services → **OAuth consent screen**
   - User type: External
   - App name: SafeRoute AI
   - Add scopes: `email`, `profile`, `openid`
4. APIs & Services → **Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Authorized JavaScript origins:
     ```
     http://localhost
     https://your-production-domain.com
     ```
   - Authorized redirect URIs:
     ```
     https://dwrqfzqalxpyqagyfgmr.supabase.co/auth/v1/callback
     ```
5. Copy **Client ID** and **Client Secret**

### Step B — Supabase Dashboard

1. Authentication → Providers → **Google**
2. Toggle **Enable**
3. Paste Client ID and Client Secret
4. Save

---

## 4. Enable Apple Sign In

### Step A — Apple Developer Account

1. Go to [developer.apple.com](https://developer.apple.com)
2. Certificates, IDs & Profiles → **Identifiers**
3. Register a new App ID with **Sign In with Apple** capability
4. Create a **Services ID** (for web):
   - Identifier: `com.saferoute.ai.web`
   - Enable Sign In with Apple
   - Configure: Return URLs must include:
     ```
     https://dwrqfzqalxpyqagyfgmr.supabase.co/auth/v1/callback
     ```
5. Create a **Key** with Sign In with Apple enabled → download `.p8` file

### Step B — Supabase Dashboard

1. Authentication → Providers → **Apple**
2. Toggle **Enable**
3. Fill in:
   - Services ID (from Step A)
   - Team ID (top-right of Apple Developer account)
   - Key ID
   - Private Key (contents of `.p8` file)
4. Save

---

## 4.5 Enable Microsoft (Azure AD) Login

### Step A — Microsoft Entra ID (Azure)
1. Go to the [Azure Portal](https://portal.azure.com/)
2. Navigate to **Microsoft Entra ID** → **App registrations** → **New registration**
3. Name your app "SafeRoute AI"
4. Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
5. Redirect URI: Select **Web** and enter:
   `https://dwrqfzqalxpyqagyfgmr.supabase.co/auth/v1/callback`
6. Click Register. Copy the **Application (client) ID**.
7. Go to **Certificates & secrets** → **New client secret**. Copy the **Value**.

### Step B — Supabase Dashboard
1. Authentication → Providers → **Microsoft**
2. Toggle **Enable**
3. Paste Client ID and Client Secret
4. Save

---

## 4.6 Enable GitHub Login

### Step A — GitHub Developer Settings
1. Go to your GitHub account settings → **Developer settings** → **OAuth Apps**
2. Click **New OAuth App**
3. Application name: "SafeRoute AI"
4. Homepage URL: `http://localhost` (or your production URL)
5. Authorization callback URL: 
   `https://dwrqfzqalxpyqagyfgmr.supabase.co/auth/v1/callback`
6. Register application. Copy the **Client ID**.
7. Click **Generate a new client secret** and copy the secret.

### Step B — Supabase Dashboard
1. Authentication → Providers → **GitHub**
2. Toggle **Enable**
3. Paste Client ID and Client Secret
4. Save

---

## 5. Enable Phone (OTP) Auth

### Step A — Twilio (recommended)

1. Create a [Twilio](https://www.twilio.com) account
2. Get your **Account SID**, **Auth Token**, and a **phone number**
3. Enable **SMS** in your Twilio account

### Step B — Supabase Dashboard

1. Authentication → Providers → **Phone**
2. Toggle **Enable**
3. SMS provider: **Twilio**
4. Enter Account SID, Auth Token, Message Service SID (or phone number)
5. OTP expiry: 300 seconds (5 minutes)
6. Save

> **Alternative:** For testing without Twilio, Supabase supports a test OTP.
> In the Supabase dashboard under Phone Auth settings, enable "Enable phone confirmations"
> and use the test number `+15005550006` with OTP `123456`.

---

## 6. Configure Redirect URLs

Supabase Dashboard → **Authentication → URL Configuration**

```
Site URL:           http://localhost          (dev)
                    https://yourdomain.com    (prod)

Redirect URLs:
  http://localhost
  http://localhost/*
  http://127.0.0.1
  https://yourdomain.com
  https://yourdomain.com/*
```

These URLs are used after OAuth redirect and password reset flows.

---

## 7. Configure JWT Settings

Supabase Dashboard → **Settings → API**

- Copy your **anon public key** — already set as `SUPA_KEY` in `Frontend/index.html`
- Copy your **service_role key** — set as `SUPABASE_SERVICE_KEY` in `Backend/.env`
- JWT expiry: 3600 seconds (1 hour) — Supabase auto-refreshes
- **Never** expose the service_role key in frontend code

---

## 8. Storage Bucket Policies

The SQL schema creates the storage buckets automatically. Verify them:

Supabase Dashboard → **Storage**

| Bucket           | Public | Purpose                    |
|------------------|--------|----------------------------|
| `avatars`        | ✅ Yes | User profile pictures       |
| `incident-images`| ❌ No  | Incident report photos      |
| `route-screenshots`| ❌ No | Route snapshot images     |

---

## 9. Test Each Auth Method

### Email/Password
1. Open `Frontend/index.html` in browser
2. Click **Get Started** → auth modal opens
3. Click **Register** tab → create account
4. Check email for confirmation link
5. Click confirmation → auto-redirected, profile created

### Google
1. Open auth modal → click **Continue with Google**
2. Google OAuth popup/redirect
3. After auth, profile auto-created with `provider = 'google'`

### Apple
1. Open auth modal → click **Continue with Apple**
2. Apple Sign In flow
3. After auth, profile auto-created with `provider = 'apple'`

### Phone OTP
1. Open auth modal → click **📱 OTP** tab
2. Select country code, enter phone number
3. Click **Send OTP** → OTP arrives via SMS
4. Enter 6-digit OTP → verified → profile created

### Forgot Password
1. Sign In tab → **Forgot password?**
2. Enter email → click **Send Reset Link**
3. Check email → click link → redirected back to app
4. Enter new password in prompt

---

## 10. Verify RLS is Working

In Supabase SQL Editor, test:

```sql
-- Should return 0 rows (no JWT)
select * from profiles;

-- Should work with valid user JWT
select * from profiles where user_id = auth.uid();
```

---

## 11. Backend JWT Verification

The backend in `app.py` has an optional JWT dependency:

```python
# Endpoints using require_user (authenticated only):
GET  /auth/me       — returns user_id from JWT
POST /auth/profile  — upsert profile (requires auth)
GET  /auth/profile  — get own profile (requires auth)

# All original endpoints still work without auth:
POST /find-safe-route    — no auth required
POST /compare-routes     — no auth required
GET  /get-crime-heatmap  — no auth required
```

To pass JWT from frontend to backend:

```javascript
// Get current session token
const { data: { session } } = await _supabase.auth.getSession();
const token = session?.access_token;

// Use in API calls:
fetch('http://localhost:8000/auth/profile', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
```

---

## 12. Environment Variables

`Backend/.env` (already configured):
```
SUPABASE_URL=https://dwrqfzqalxpyqagyfgmr.supabase.co
SUPABASE_KEY=<anon-public-key>
SUPABASE_SERVICE_KEY=<service-role-key>
```

`Frontend/index.html` (already configured):
```javascript
const SUPA_URL = 'https://dwrqfzqalxpyqagyfgmr.supabase.co';
const SUPA_KEY = '<anon-public-key>';
```

---

## Summary of Files Modified

| File | Changes |
|------|---------|
| `Backend/supabase_schema.sql` | Complete rewrite — 12 tables, RLS, triggers, storage |
| `Backend/app.py` | JWT middleware, `/auth/profile`, `/auth/me` endpoints |
| `Frontend/index.html` | Extended auth modal, Google/Apple/Phone OAuth, profile panel |
| `AUTH_SETUP.md` | This file — provider configuration guide |
