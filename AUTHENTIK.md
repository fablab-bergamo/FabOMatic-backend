# Authentik OAuth2/OIDC Integration Guide

## Overview

This guide describes the integration of Authentik SSO (hosted at buco.bglug.it) with the FabOMatic Backend application using OAuth2/OpenID Connect protocol with email-based user matching.

## Current Authentication System Analysis

**Current State:**
- **Authentication:** Flask-Login with password-based authentication (`src/FabOMatic/web/authentication.py:36-55`)
- **User Model:** SQLAlchemy model with email field (`src/FabOMatic/database/models.py:61-148`)
- **Email Field:** Available in User model (line 75: `email = Column(String, nullable=True)`)
- **Authorization:** Role-based with `backend_admin` and `authorize_all` permissions
- **Password Reset:** Token-based email flow already implemented

## Architecture Overview

```
┌──────────────┐         OAuth2/OIDC         ┌──────────────┐
│   Browser    │◄──────────────────────────►│  Authentik   │
│              │                              │  (buco.      │
└──────┬───────┘                              │  bglug.it)   │
       │                                      └──────────────┘
       │ 1. Redirect to Authentik
       │ 2. User authenticates
       │ 3. Redirect back with code
       │ 4. Exchange code for token
       │ 5. Get user info (email)
       ▼
┌──────────────────────────────────────────┐
│       FabOMatic Backend                  │
│  ┌────────────────────────────────────┐  │
│  │  OAuth Handler                     │  │
│  │  - Match user by email             │  │
│  │  - Create session via Flask-Login  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  User Database                     │  │
│  │  - Existing users with emails      │  │
│  │  - No password required for SSO    │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

## Integration Strategy

### Key Design Decisions

1. **Email-Based Matching:** Users are matched by email address - no auto-provisioning of new users
2. **Permission Check:** Only users with `backend_admin` or `authorize_all` role permissions can log in
3. **Fallback Support:** Traditional password login remains available as a fallback mechanism
4. **Zero Migration:** Uses existing User.email field - no database changes required
5. **Security First:** Disabled users are rejected even if email matches

## Implementation Components

### 1. Dependencies

Add to `requirements.txt`:
```
authlib==1.3.2           # OAuth2/OIDC client library
```

### 2. Configuration

Add to `src/FabOMatic/conf/settings.example.toml`:
```toml
[authentik]
enabled = false                                                    # Enable/disable Authentik SSO
server_url = "https://buco.bglug.it"                              # Authentik server URL
client_id = "your-client-id"                                       # OAuth2 Client ID from Authentik
client_secret = "your-client-secret"                               # OAuth2 Client Secret
redirect_uri = "https://your.external.url.for.fabomatic/auth/callback"  # OAuth callback URL
scopes = "openid email profile"                                    # Required scopes
allow_password_fallback = true                                     # Allow traditional login as fallback
```

**Configuration Parameters:**

- `enabled`: Master switch for SSO functionality
- `server_url`: Base URL of your Authentik instance (buco.bglug.it)
- `client_id`: OAuth2 client ID from Authentik provider configuration
- `client_secret`: OAuth2 client secret (keep secure!)
- `redirect_uri`: Must match exactly what's configured in Authentik
- `scopes`: OAuth scopes to request (openid, email, profile are required)
- `allow_password_fallback`: Whether to keep password login available

### 3. OAuth Handler Module

New file: `src/FabOMatic/web/authentik_oauth.py`

This module provides:
- OAuth client initialization using Authlib
- User matching logic based on email
- Permission validation for SSO users
- Integration with existing Flask-Login system

**Key Functions:**
- `get_or_create_user_by_email(email)`: Match user by email and validate permissions
- `is_authentik_enabled()`: Check if SSO is enabled in configuration

### 4. Authentication Routes

Modified file: `src/FabOMatic/web/authentication.py`

**New Routes:**
- `/auth/login`: Initiates OAuth flow by redirecting to Authentik
- `/auth/callback`: Handles OAuth callback, exchanges code for token, matches user

**Modified Routes:**
- `/login`: Enhanced to display SSO button when enabled

### 5. Login Template

Modified file: `src/FabOMatic/flask_app/templates/login.html`

Adds SSO button with visual separator ("or") between password and SSO login options.

## Authentik Server Configuration

### Step 1: Create OAuth2/OIDC Provider

1. Navigate to Authentik admin panel (buco.bglug.it)
2. Go to **Applications** → **Providers** → **Create**
3. Select **OAuth2/OpenID Provider**
4. Configure:
   - **Name:** FabOMatic Backend
   - **Authorization flow:** Authorization Code
   - **Client type:** Confidential
   - **Client ID:** (will be auto-generated or set manually)
   - **Client Secret:** (will be auto-generated)
   - **Redirect URIs:** `https://your.fabomatic.url/auth/callback`
   - **Signing Key:** Select an appropriate certificate

### Step 2: Create Application

1. Go to **Applications** → **Applications** → **Create**
2. Configure:
   - **Name:** FabOMatic
   - **Slug:** `fabomatic` (important - used in .well-known URL)
   - **Provider:** Select the provider created in Step 1
   - **Launch URL:** `https://your.fabomatic.url/`

### Step 3: Configure Scopes

Ensure the following scopes are available:
- `openid` (required for OIDC)
- `email` (required for user matching)
- `profile` (for user display name)

### Step 4: Configure Scope Mappings

1. Go to **Customization** → **Property Mappings**
2. Ensure these mappings are assigned to your provider:
   - **OpenID Email** (provides email claim)
   - **OpenID Profile** (provides name claims)

### Step 5: Note Credentials

From the provider configuration, note:
- **Client ID**
- **Client Secret**

Add these to your `settings.toml`:
```toml
[authentik]
enabled = true
server_url = "https://buco.bglug.it"
client_id = "your-actual-client-id"
client_secret = "your-actual-client-secret"
redirect_uri = "https://your.fabomatic.url/auth/callback"
scopes = "openid email profile"
```

### Step 6: Test Configuration

The OpenID configuration should be available at:
```
https://buco.bglug.it/application/o/fabomatic/.well-known/openid-configuration
```

This URL should return JSON with endpoints like:
- `authorization_endpoint`
- `token_endpoint`
- `userinfo_endpoint`
- `jwks_uri`

## Database Preparation

### Verify Email Configuration

**No migration needed!** The User model already has an email field. However, ensure all admin users have valid emails.

**Check for missing emails:**
```sql
SELECT user_id, name, surname, email FROM users
WHERE (email IS NULL OR email = '')
AND user_id IN (
    SELECT user_id FROM users u
    JOIN roles r ON u.role_id = r.role_id
    WHERE r.backend_admin = 1 OR r.authorize_all = 1
);
```

**Check for duplicate emails:**
```sql
SELECT email, COUNT(*) as count FROM users
WHERE email IS NOT NULL
GROUP BY email
HAVING count > 1;
```

**Update missing emails via web interface or SQL:**
```sql
UPDATE users
SET email = 'admin@fablab.org'
WHERE user_id = 1;
```

## Security Considerations

### Authentication Security

1. **Email Verification:** Authentik MUST be configured to verify email addresses
2. **HTTPS Required:** OAuth2 requires HTTPS (FabOMatic already supports this)
3. **State Parameter:** Authlib automatically handles CSRF protection via state parameter
4. **Token Security:** Tokens are exchanged server-side, never exposed to client
5. **Client Secret:** Keep client secret secure - never commit to version control

### Authorization Security

1. **Permission Validation:** Users must have `backend_admin` or `authorize_all` role
2. **Disabled User Check:** Disabled users are rejected even if email matches
3. **No Auto-Provisioning:** Only existing users can log in (no automatic account creation)
4. **Fallback Access:** Password login remains available for emergency access

### Session Security

1. **Flask Session:** Existing Flask-Login session management is used
2. **Session Timeout:** Consider configuring session timeout in Flask config
3. **Logout:** Existing logout route works for both password and SSO sessions

### Audit & Monitoring

All SSO authentication attempts are logged:
- Successful logins: `User {email} logged in via Authentik SSO`
- Failed matches: `No user found with email {email}`
- Permission failures: `User {email} exists but lacks backend admin permissions`
- Disabled users: `User {email} is disabled`
- Token exchange errors: `Authentik SSO error: {error details}`

## Deployment Strategy

### Phase 1: Preparation

1. **Audit User Emails:**
   - Ensure all admin users have valid, unique email addresses
   - Update any missing or duplicate emails
   - Document which emails will have SSO access

2. **Setup Authentik:**
   - Create OAuth2 provider in Authentik
   - Create application with proper redirect URIs
   - Test .well-known endpoint is accessible
   - Note client ID and secret

3. **Deploy Code:**
   - Merge `authentik` branch to main
   - Deploy to production with `authentik.enabled = false`
   - Verify existing password login still works

### Phase 2: Testing

1. **Enable SSO for Testing:**
   ```toml
   [authentik]
   enabled = true
   server_url = "https://buco.bglug.it"
   client_id = "test-client-id"
   client_secret = "test-client-secret"
   redirect_uri = "https://your.fabomatic.url/auth/callback"
   ```

2. **Test with Single User:**
   - Create test account in Authentik with known email
   - Ensure matching user exists in FabOMatic with admin role
   - Attempt SSO login
   - Verify session works correctly
   - Test logout

3. **Verify Fallback:**
   - Test password login still works
   - Test password reset flow (if needed)

### Phase 3: Rollout

1. **Enable for All Users:**
   - Keep `allow_password_fallback = true`
   - Monitor logs for authentication attempts
   - Provide user documentation

2. **User Communication:**
   - Notify users about SSO availability
   - Provide instructions for first SSO login
   - Document fallback procedure

3. **Monitor:**
   - Watch authentication logs
   - Track SSO vs password login ratio
   - Address any user issues promptly

### Phase 4: Optimization (Optional)

1. **Disable Password Login:**
   ```toml
   allow_password_fallback = false
   ```

2. **Clean Up:**
   - Remove password reset functionality (optional)
   - Update user documentation
   - Remove password-related UI elements

3. **Advanced Features:**
   - Configure session timeout
   - Add group-based role mapping (if Authentik provides groups)
   - Implement automatic session refresh

## Testing Checklist

Before deploying to production, verify:

- [ ] Authlib dependency installed
- [ ] Authentik OAuth2 provider configured
- [ ] Authentik application created with correct slug
- [ ] Redirect URI matches exactly in both configurations
- [ ] All admin users have valid, unique emails
- [ ] settings.toml configured with correct credentials
- [ ] .well-known endpoint accessible from FabOMatic server
- [ ] SSO login works with valid admin email
- [ ] SSO login rejected for non-existent email
- [ ] SSO login rejected for non-admin user email
- [ ] SSO login rejected for disabled user
- [ ] Password fallback still works
- [ ] Session management works correctly
- [ ] Logout functionality works for SSO sessions
- [ ] Audit logs capture SSO events
- [ ] HTTPS certificate valid on FabOMatic server
- [ ] Client secret kept secure (not in version control)

## Troubleshooting

### Common Issues

**Issue: "SSO is not enabled" message**
- Check `authentik.enabled = true` in settings.toml
- Restart FabOMatic application after config change

**Issue: "Authentication failed" after Authentik login**
- Check application logs for detailed error
- Verify client_id and client_secret match Authentik provider
- Ensure redirect_uri matches exactly (including https/http, trailing slash)

**Issue: "No authorized account found for your email"**
- Verify user exists in FabOMatic database with matching email
- Check user has `backend_admin` or `authorize_all` role permission
- Ensure user is not disabled

**Issue: OAuth callback error**
- Check redirect_uri in settings.toml matches Authentik configuration exactly
- Verify Authentik application slug matches .well-known URL
- Check network connectivity from FabOMatic to buco.bglug.it

**Issue: Email not provided by Authentik**
- Verify email scope is requested in settings.toml
- Check Authentik provider has email scope mapping configured
- Ensure user's email is verified in Authentik

### Debug Steps

1. **Enable Debug Logging:**
   ```bash
   python -m FabOMatic --loglevel 10
   ```

2. **Check Authentik Configuration:**
   ```bash
   curl https://buco.bglug.it/application/o/fabomatic/.well-known/openid-configuration
   ```

3. **Test OAuth Flow Manually:**
   - Visit `/auth/login` and watch browser redirects
   - Check browser developer tools for errors
   - Verify redirect back to `/auth/callback` with code parameter

4. **Check Database:**
   ```sql
   SELECT user_id, email, disabled FROM users
   WHERE email = 'test@example.com';

   SELECT r.backend_admin, r.authorize_all
   FROM roles r
   JOIN users u ON u.role_id = r.role_id
   WHERE u.email = 'test@example.com';
   ```

## Benefits of This Integration

✅ **Zero data migration** - uses existing email field
✅ **Secure** - industry-standard OAuth2/OIDC protocol
✅ **Centralized authentication** - managed by Authentik
✅ **Backward compatible** - password login remains available
✅ **User-friendly** - single sign-on experience
✅ **Auditable** - all SSO events logged
✅ **No user creation** - only matches existing authorized users
✅ **Standards-based** - OpenID Connect specification compliance
✅ **Flexible** - easy to disable or rollback if needed

## Alternative: Auto-Provisioning Users

**Note:** The current implementation does NOT auto-provision users for security reasons. Only existing users can log in via SSO.

If you want to automatically create new users from Authentik (not recommended for security-sensitive applications), you would need to:

1. Add configuration for default role:
   ```toml
   [authentik]
   auto_provision = true
   default_role_id = 2  # Role ID for new SSO users
   ```

2. Modify `get_or_create_user_by_email()` in `authentik_oauth.py`:
   ```python
   def get_or_create_user_by_email(email: str, user_info: dict) -> User | None:
       """Create user if doesn't exist (requires default role configuration)."""
       with DBSession() as session:
           user = session.query(User).filter_by(email=email).first()

           if not user:
               # Get default role for SSO users
               default_role_id = FabConfig.getSetting("authentik", "default_role_id")
               if not default_role_id:
                   return None

               user = User(
                   name=user_info.get('given_name', ''),
                   surname=user_info.get('family_name', ''),
                   email=email,
                   role_id=default_role_id,
                   disabled=False
               )
               session.add(user)
               session.commit()
               logging.info(f"Auto-provisioned user from Authentik: {email}")

           return user
   ```

**Security Warning:** Auto-provisioning means anyone with a verified email in Authentik can create an account. Only use this if:
- Authentik is strictly controlled (internal users only)
- Default role has minimal permissions
- You have additional authorization checks in place

## References

- [Authentik OAuth2/OIDC Provider Documentation](https://docs.goauthentik.io/add-secure-apps/providers/oauth2/)
- [Authlib Flask Client Documentation](https://docs.authlib.org/en/latest/client/flask.html)
- [OpenID Connect Specification](https://openid.net/connect/)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)

## Version History

- **v1.0** (2025-10-28): Initial integration guide

---

*For questions or issues with this integration, please file an issue in the GitHub repository.*
