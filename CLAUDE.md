# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Django Application
- `honcho -f Procfile.tailwind start` - Start all services (Daphne ASGI server on port 8003, Tailwind watcher, and task worker)
- `uv run daphne -b 127.0.0.1 -p 8003 league_gotta_bike.asgi:application` - Start the Daphne ASGI server only
- `python manage.py runserver 8002` - Start the Django development server only (WSGI, port configured via DJANGO_PORT in .env)
- `python manage.py db_worker` - Start the background task worker
- `python manage.py migrate` - Apply database migrations
- `python manage.py makemigrations` - Create new database migrations
- `python manage.py collectstatic` - Collect static files for production
- `python manage.py createsuperuser` - Create a Django admin superuser interactively
- `python manage.py ensure_superuser` - Auto-create superuser from environment variables (DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD). Use `--update` flag to update existing superuser credentials. Useful for deployment automation.

### Frontend/Tailwind CSS
- `cd theme/static_src && npm run dev` - Watch and compile Tailwind CSS in development mode
- `cd theme/static_src && npm run build` - Build production-ready CSS
- `cd theme/static_src && npm install` - Install Node.js dependencies for Tailwind

### Testing and Code Quality

#### Test Organization
**IMPORTANT**: All tests must be kept in the `tests/` directory at the project root, organized by app:
- `tests/accounts/` - Tests for accounts app
- `tests/organizations/` - Tests for organizations app
- `tests/membership/` - Tests for membership app
- etc.

**Current structure**:
```
tests/
├── __init__.py
├── accounts/
│   ├── __init__.py
│   ├── test_email.py
│   └── test_sms.py
└── ...
```

**Best Practices**:
- Keep app-level `tests.py` as a stub pointing to `tests/`
- Name test files with `test_` prefix (e.g., `test_email.py`, `test_models.py`)
- Group related tests in the same file
- Add a README.md in test directories for complex test suites

#### Running Tests
- `pytest` - Run all tests using pytest
- `python manage.py test` - Run all tests using Django's test runner
- `python manage.py test tests.accounts` - Run all tests for accounts app
- `ruff check --fix` - Run linting with ruff and automatically fix issues
- `ruff format` - Format code with ruff

#### Email Testing
**Test email delivery for verification and password reset:**
- `python manage.py test tests.accounts.test_email` - Run all email tests
- `python manage.py test tests.accounts.test_email.EmailVerificationTestCase` - Test account verification emails
- `python manage.py test tests.accounts.test_email.PasswordResetTestCase` - Test password reset emails
- Requires `TEST_TO_EMAIL` environment variable set in `.env`
- Sends actual emails via Resend to the configured test address
- See `tests/accounts/README.md` for detailed testing instructions

#### SMS Testing
**Test phone verification via Sinch:**
- `python manage.py test tests.accounts.test_sms` - Run SMS verification tests
- Requires `SINCH_APPLICATION_KEY`, `SINCH_APPLICATION_SECRET`, and `TEST_TO_PHONE_NUMBER` in `.env`
- Phone number must be in E.164 format (e.g., +15555555555)

## Project Architecture

### Django Project Structure
- **league_gotta_bike/**: Main Django project directory containing settings, URLs, ASGI/WSGI configuration, and pydantic-settings config
- **accounts/**: Custom user accounts app for authentication, profiles, and phone verification
- **apps/organizations/**: Organization management (leagues, teams, squads, clubs, practice groups)
- **apps/membership/**: Member management, roles, seasons, and season memberships
- **apps/events/**: Event management, RSVP tracking, and attendance
- **apps/messaging/**: Chat rooms, messages, and announcement channels
- **apps/sponsors/**: Sponsor management and display
- **apps/mobile_api/**: REST API using django-ninja for mobile/PWA applications
- **theme/**: Tailwind CSS theme app for frontend styling

### Key Configuration
- Uses **pydantic-settings** for environment variable management (see `league_gotta_bike/config.py` and `.env` file)
- Environment variables loaded from `.env` file using type-safe validation
- Uses **SQLite** database for development, **PostgreSQL** for production (via `dj-database-url`)
- **Daphne** ASGI server with **Django Channels** for WebSocket support
- **HTMX** via `django-htmx` middleware for dynamic partial page updates
- **Django Debug Toolbar** and **django-browser-reload** enabled only when `DEBUG=True`
- **Django Tasks** configured with DatabaseBackend for background task processing
- **Tailwind CSS v4** with **DaisyUI** component library for styling
- **PostCSS** build pipeline for CSS processing
- **WhiteNoise** for static file serving in production
- **Cloudflare R2** (S3-compatible) for media file storage in production (optional, set `USE_S3=True`)
- **django-push-notifications** for web push notifications
- **Sinch** for SMS phone verification
- **django-ninja** for mobile REST API with auto-generated OpenAPI docs
- **Logfire** for logging, observability, and application monitoring

### Logging and Observability

The project uses **Logfire** (by Pydantic) for comprehensive logging and observability.

#### Features
- **Automatic Django Integration**: Tracks requests, responses, database queries, and middleware
- **ASGI Support**: Monitors WebSocket connections and async operations
- **Database Tracking**: Logs SQLite (dev) and PostgreSQL (production) queries with performance metrics
- **Structured Logging**: JSON-formatted logs with context and tracing
- **Error Tracking**: Automatic exception capture with stack traces

#### When Writing Code
- **Use Logfire for Important Operations**: Log significant events, errors, and business logic
- **Add Context**: Include relevant data like user IDs, organization IDs, event IDs
- **Track Performance**: Use logfire to measure slow operations
- **Async Support**: Logfire automatically tracks async/await operations

#### Example Usage
```python
import logfire

# Basic logging
logfire.info("User created organization", user_id=user.id, org_id=org.id)

# Error logging with context
try:
    process_payment(transaction)
except PaymentError as e:
    logfire.error("Payment failed", error=str(e), transaction_id=transaction.id)

# Performance tracking
with logfire.span("expensive_operation"):
    result = perform_complex_calculation()
```

#### Environment Variables
- `LOGFIRE_TOKEN`: API token for Logfire (optional for local development)
- Configure in Railway for production monitoring

#### Best Practices
- Log user actions that modify data (create, update, delete)
- Log authentication events (login, logout, MFA)
- Log background task execution
- Include relevant IDs for traceability
- Avoid logging sensitive data (passwords, tokens, personal info)

### Environment Variables
Configuration is managed via `.env` file (see `.env.example` for template). All settings defined in `league_gotta_bike/config.py`:

**Core:**
- `DEBUG`: Enable/disable debug mode (default: False)
- `SECRET_KEY`: Django secret key for cryptographic signing
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `CSRF_TRUSTED_ORIGINS`: Comma-separated list of trusted origins for CSRF
- `INTERNAL_IPS`: Comma-separated list of IPs for debug toolbar (default: 127.0.0.1)
- `DJANGO_PORT`: Development server port (default: 8002)
- `DATABASE_URL`: Database connection string (default: `sqlite:///db.sqlite3`)

**Email:**
- `RESEND_API_KEY`: Resend API key for email delivery
- `DEFAULT_FROM_EMAIL`: Default sender email address (default: `noreply@signup.gotta.bike`)

**SMS Verification:**
- `SINCH_APPLICATION_KEY`: Sinch Verification API application key
- `SINCH_APPLICATION_SECRET`: Sinch Verification API application secret

**Media Storage (Cloudflare R2):**
- `USE_S3`: Enable R2 storage for media files (default: False)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: R2 credentials
- `AWS_STORAGE_BUCKET_NAME`: R2 bucket name
- `AWS_S3_ENDPOINT_URL`: R2 endpoint URL
- `AWS_S3_REGION_NAME`: Region (default: `auto`)
- `AWS_S3_CUSTOM_DOMAIN`: Optional CDN domain for media delivery

**Observability:**
- `LOGFIRE_TOKEN`: Logfire API token (optional for local development)

**Testing:**
- `TEST_TO_EMAIL`: Email address for email delivery tests
- `TEST_TO_PHONE_NUMBER`: Phone number for SMS tests (E.164 format)

**Superuser:**
- `DJANGO_SUPERUSER_USERNAME`: Username for auto-created superuser (optional)
- `DJANGO_SUPERUSER_EMAIL`: Email for auto-created superuser (optional)
- `DJANGO_SUPERUSER_PASSWORD`: Password for auto-created superuser (optional)

**Important**: Debug toolbar and browser reload are automatically disabled when `DEBUG=False`

**Superuser Auto-Creation**: Set the three `DJANGO_SUPERUSER_*` variables and run `python manage.py ensure_superuser` to automatically create an admin account. This is useful for deployment automation on platforms like Railway where you can't run interactive commands.

### App Configuration
The project uses a structured approach to Django apps:
- `DEFAULT_APPS`: Standard Django contrib apps
- `LOCAL_APPS`: Custom project-specific apps (`accounts`, `apps.organizations`, `apps.membership`, `apps.events`, `apps.messaging`, `apps.sponsors`, `apps.mobile_api`)
- `ADDON_APPS`: Third-party apps (`tailwind`, `theme`, `push_notifications`, `django_tasks`, `channels`, `allauth`, `anymail`, `phonenumber_field`, `django_htmx`)
- Debug-only: `debug_toolbar`, `django_browser_reload`, `reset_migrations`
- Optional: `storages` (when `USE_S3=True`)
- `daphne` is prepended before all apps for ASGI support

### Frontend Setup
- Tailwind CSS files are in `theme/static_src/`
- Source CSS: `theme/static_src/src/styles.css`
- Compiled CSS output: `theme/static/css/dist/styles.css`
- Uses PostCSS with plugins for nested CSS and simple variables

### Development Dependencies
Key development tools included via pyproject.toml:
- `django-browser-reload` for auto-refresh during development
- `django-debug-toolbar` for debugging
- `django-reset-migrations` for migration management
- `django-stubs` for type checking
- `pytest` for testing
- `ruff` for linting and formatting
- `honcho` for process management (Procfile.tailwind)
- `logfire-mcp` for Logfire MCP integration
- `ty` for type analysis

### Static Files
- Template directory: `BASE_DIR / 'templates'` (global allauth/MFA templates)
- App-level templates in `apps/*/templates/` (organization detail pages, forms, etc.)
- Account templates in `accounts/templates/accounts/` (home, profile)
- Static files served via **WhiteNoise** (`CompressedManifestStaticFilesStorage`)
- Tailwind CSS output is served as static files
- Media files stored locally or on Cloudflare R2 (configurable via `USE_S3`)

## Authentication & Email

### Django-allauth Configuration
The project uses **django-allauth** for comprehensive user authentication with MFA support.

#### Features
- **Email Verification**: Mandatory email verification required to activate new accounts
- **Multi-Factor Authentication (MFA)**: Support for TOTP (authenticator apps), WebAuthn/Passkeys, and recovery codes
- **Customized Templates**: All allauth templates styled with Tailwind CSS and DaisyUI components

#### User Model
Custom User model (`accounts.User`) extends Django's `AbstractUser`:
- **Required Fields**: `username`, `email`, `first_name`, `last_name`
- **Additional Fields**:
  - `phone_number`: PhoneNumberField for contact information (international format)
  - `phone_verified`: Boolean tracking SMS verification status
  - `dob`: Date of birth with age validation (12-110 years)
  - `avatar`: ImageField for profile photos (uploaded to `avatars/%Y/%m/`)
- **Methods**:
  - `racing_age()`: Calculates cycling racing age (age by Dec 31 of current year)
  - `UNDER18()` / `UNDER16()`: Age check helpers for youth athletes
- **Signals**: Phone number changes automatically reset `phone_verified` to False
- **Email Verification**: Email must be verified before account activation
- **Login Method**: Username-based authentication

#### MFA Configuration
Multi-factor authentication is enabled with the following options:
- **TOTP (Time-based One-Time Password)**: 6-digit codes via authenticator apps (Google Authenticator, Authy, 1Password)
- **WebAuthn/Passkeys**: Hardware security keys and biometric authentication
- **Recovery Codes**: 10 backup codes for account recovery
- **Settings**: Configure via Django admin or user account settings at `/accounts/mfa/`

#### Key Settings
```python
ACCOUNT_LOGIN_METHODS = {'username'}
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'first_name*', 'last_name*', 'password1*', 'password2*']
MFA_SUPPORTED_TYPES = ['recovery_codes', 'totp', 'webauthn']
MFA_PASSKEY_LOGIN_ENABLED = True
MFA_PASSKEY_SIGNUP_ENABLED = True
```

#### URLs
- `/accounts/home/` - User dashboard (organizations, chats, events)
- `/accounts/profile/` - User profile display and edit
- `/accounts/signup/` - User registration
- `/accounts/login/` - User login
- `/accounts/logout/` - User logout
- `/accounts/password/reset/` - Password reset
- `/accounts/email/` - Email address management
- `/accounts/password/change/` - Change password
- `/accounts/confirm-email/` - Email verification code entry (custom with resend)
- `/accounts/mfa/` - Two-factor authentication management
- `/accounts/verify-phone/send/` - Send SMS verification code
- `/accounts/verify-phone/confirm/` - Confirm SMS verification code

#### Custom Templates Location
- `templates/account/` - django-allauth account templates (login, signup, password reset, etc.)
- `templates/mfa/` - django-allauth MFA templates (TOTP, WebAuthn, recovery codes)
- `accounts/templates/accounts/` - Custom account views (home.html, profile.html, section partials)

### Django-anymail with Resend
Email delivery is handled by **django-anymail** using the **Resend** API.

#### Configuration
Set the following environment variables in `.env`:
- `RESEND_API_KEY`: Your Resend API key (get from https://resend.com/api-keys)
- `DEFAULT_FROM_EMAIL`: Default sender email address (must be verified in Resend)

#### Features
- **Transactional Email**: Account verification, password resets, notifications
- **Email Tracking**: Monitor email delivery status (configured at Resend domain level)
- **Template Support**: HTML and plain text email templates

#### Backend
```python
# Development (DEBUG=True): emails printed to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Production (DEBUG=False): emails sent via Resend
EMAIL_BACKEND = 'anymail.backends.resend.EmailBackend'
```

#### Testing Emails Locally
In development with `DEBUG=True`, emails are automatically sent to the console (no real emails sent). The Resend backend is only used in production.

#### Resend Setup
1. Create an account at https://resend.com
2. Verify your sending domain
3. Generate an API key with "sending access" permission
4. Add the API key to your `.env` file as `RESEND_API_KEY`

### Phone Verification (Sinch SMS)

Phone verification is handled by the **Sinch Verification API** using the official Python SDK.

#### Implementation
- `accounts/sms_verify.py` - SMS verification logic
- Uses Sinch's managed verification flow (4-digit codes, 10-minute expiry)
- Rate limiting: 60-second cooldown between requests
- Phone verification status tracked on User model (`phone_verified` field)

#### Configuration
Set the following environment variables in `.env`:
- `SINCH_APPLICATION_KEY`: Application key from Sinch dashboard
- `SINCH_APPLICATION_SECRET`: Application secret from Sinch dashboard

#### URLs
- `POST /accounts/verify-phone/send/` - Initiate SMS verification
- `POST /accounts/verify-phone/confirm/` - Confirm verification code

#### Key Behavior
- Phone number changes automatically reset `phone_verified` to False (via signal)
- Verification requires authenticated user with a phone number set
- Uses Django cache for rate limiting

## Project Purpose & Roadmap

### Application Overview
League Gotta Bike is a comprehensive sports team management platform focused on cycling teams, clubs, and leagues. The app streamlines team operations, event coordination, member management, and performance tracking.

### Django Apps Structure

#### Implemented Apps
```
league_gotta_bike/           # Main project
├── accounts/                # ✅ User authentication, profiles, phone verification
├── apps/organizations/      # ✅ Organization management (leagues, teams, squads, clubs, practice groups)
├── apps/membership/         # ✅ Member management, roles, seasons, and season memberships
├── apps/messaging/          # ✅ Chat rooms, messages, announcements
├── apps/events/             # ✅ Event management, RSVP, recurrence, and attendance tracking
├── apps/sponsors/           # ✅ Sponsor management and display
├── apps/mobile_api/         # ✅ REST API (django-ninja) for mobile/PWA applications
└── theme/                   # ✅ Frontend styling (Tailwind CSS + DaisyUI + HTMX)
```

#### Planned Apps (Future Development)
```
├── admin_api/               # 📋 Admin API for management operations
├── performance/             # 📋 Stats & results tracking
├── finances/                # 📋 Financial management with Stripe Connect
└── notifications/           # 📋 Advanced email/push notification system
```

### Core Features

#### ✅ Implemented
- **Organization Management**: Leagues, teams, squads, clubs, practice groups with hierarchical structure
- **Membership System**: Permission levels, organizational roles, season-based memberships
- **Team Management**: Team profiles, roster management, role-based permissions
- **Member Import/Export**: CSV bulk operations for member management
- **Event System**: Event creation with recurrence, RSVP tracking, attendance/check-in management
- **Messaging**: Chat rooms with unread counts, organization-specific channels, announcements
- **Sponsor Management**: Sponsor logos and links on organization pages
- **Account Dashboard**: User home page with organizations, chats, and events
- **Social Media Integration**: Social media accounts for leagues and teams
- **Phone Verification**: SMS verification via Sinch API with rate limiting
- **Mobile API**: REST API (django-ninja) with auth, organizations, chat, and events endpoints
- **HTMX Integration**: Dynamic partial page updates for interactive UI
- **Cloud Media Storage**: Cloudflare R2 (S3-compatible) for production file uploads

#### 📋 Planned
- **Admin API**: Management and administrative operations API
- **Event Calendar View**: Calendar widget integration
- **Performance Tracking**: Race results, statistics, progress reports
- **Financial Tools**: Stripe Connect integration, dues management, expense tracking
- **Advanced Notifications**: Email/push notifications for events and messages
- **Real-time Chat**: WebSocket-based live messaging (Channels infrastructure in place)

### Permissions vs Roles Architecture

**CRITICAL CONCEPT**: The system separates **permission levels** (authorization) from **organizational roles** (identity/function).

#### Permission Levels (What You Can DO)

Permission levels determine **authorization** - what actions a user can perform in an organization:

| Permission Level | Description | Capabilities |
|-----------------|-------------|--------------|
| **Owner** | Full control | All permissions; can delete org; assign any permission level |
| **Administrator** | Most permissions | Edit org, manage members, events, finances; cannot delete org |
| **Manager** | Limited management | Manage members, create events; cannot edit org settings |
| **Member** | Basic access | View content, participate in events; no management |

**Permission Matrix**:
| Action | Owner | Admin | Manager | Member |
|--------|:-----:|:-----:|:-------:|:------:|
| View organization | ✅ | ✅ | ✅ | ✅ |
| Edit organization | ✅ | ✅ | ❌ | ❌ |
| Delete organization | ✅ | ❌ | ❌ | ❌ |
| Manage members | ✅ | ✅ | ✅ | ❌ |
| Assign permissions | ✅ | ✅ | ❌ | ❌ |
| Create/edit events | ✅ | ✅ | ✅ | ❌ |
| View finances | ✅ | ✅ | ✅ | ❌ |
| Manage finances | ✅ | ✅ | ❌ | ❌ |
| Participate in events | ✅ | ✅ | ✅ | ✅ |

**Implementation**:
```python
# Check permission level
membership = Membership.objects.get(user=user, organization=org)
if membership.permission_level in [Membership.OWNER, Membership.ADMIN]:
    # User can edit organization
```

#### Organizational Roles (What You ARE)

Organizational roles are **descriptive identities** - they describe what type of participant you are. Roles do NOT grant permissions.

**Available Roles**:
- **Athlete/Cyclist**: Active participant in cycling activities
- **Coach**: Provides training and guidance
- **Parent**: Parent of a youth athlete
- **Guardian**: Legal guardian of an athlete
- **Team Captain**: Leadership role among athletes
- **Medical Staff**: Provides medical support
- **Mechanic**: Provides bike maintenance
- **Volunteer**: General volunteer
- **Official**: Race/event official
- **Spectator**: Observer/supporter

**Key Features**:
- ✅ **Multiple roles per user**: A person can be "Coach" AND "Parent"
- ✅ **Descriptive only**: Roles don't grant permissions
- ✅ **Display in UI**: Shows user's function(s) in the organization
- ✅ **Filterable**: Search for all coaches, all parents, etc.

**Example**:
```python
# User has Manager permission level + Coach and Parent roles
membership = Membership.objects.create(
    user=user,
    organization=team,
    permission_level=Membership.MANAGER,  # Can manage members
    status=Membership.ACTIVE
)

# Add multiple roles
MemberRole.objects.create(membership=membership, role_type=MemberRole.COACH, is_primary=True)
MemberRole.objects.create(membership=membership, role_type=MemberRole.PARENT)

# Display
print(f"{user.name} - {membership.get_permission_level_display()}")
# Output: "John Doe - Manager"
print(f"Roles: {', '.join([r.get_role_type_display() for r in membership.roles.all()])}")
# Output: "Roles: Coach, Parent"
```

#### Common Scenarios

**Scenario 1: Team Coach with Management**
- Permission Level: `Manager` (can invite members, create events)
- Roles: `Coach` (identity)

**Scenario 2: Parent Volunteer**
- Permission Level: `Member` (basic participation)
- Roles: `Parent`, `Volunteer`

**Scenario 3: Team Owner/Director**
- Permission Level: `Owner` (full control)
- Roles: `Coach`, `Team Captain`

**Scenario 4: Youth Athlete**
- Permission Level: `Member`
- Roles: `Athlete`

**Scenario 5: Support Staff**
- Permission Level: `Member` or `Manager`
- Roles: `Medical Staff`, `Mechanic`, `Volunteer`

#### Best Practices

1. **Assign permission level first** based on what they need to DO
2. **Add roles** to describe what they ARE
3. **Permission level = authorization check** in code
4. **Roles = display and filtering** in UI
5. **Most users** should be `Member` permission level
6. **Limit `Owner`** to 1-2 people per organization
7. **Use `Manager`** for coaches who need to organize events
8. **Multiple roles are encouraged** when appropriate

### Development Phases
1. **Foundation** (Weeks 1-3): Core team/member management
2. **Events** (Weeks 4-6): Calendar and scheduling system
3. **Communication** (Weeks 7-8): Messaging and notifications
4. **Performance** (Weeks 9-10): Stats and results tracking
5. **Finances** (Weeks 11-12): Payment and expense management
6. **Polish** (Weeks 13-16): Advanced features and optimizations

### Project Models

#### Organization Architecture Pattern

**Hybrid Organization Model**: The project uses a hybrid pattern combining a base `Organization` model with type-specific profiles to handle the hierarchical nature of cycling organizations (leagues, teams, squads, clubs).

**Benefits**:
- Flexible hierarchical structure with self-referential parent relationships
- Type-specific fields kept in separate profile models (clean separation)
- Shared logic for permissions, membership, and settings across all org types
- Easily extensible for new organization types without schema bloat

**Structure**:
```python
# Base model with shared fields and hierarchy
Organization(type, parent, name, logo, contact_info, etc.)

# Type-specific profiles (one-to-one with Organization)
TeamProfile(short_description, team_type, banner, etc.)
LeagueProfile(short_description, sanctioning_body, region, banner, etc.)
SquadProfile(parent_team, focus_area, etc.)
```

#### Organization URL Access Control

**Member vs Guest Views**: The system automatically routes users to appropriate views based on their membership status.

**URL Structure**:
- `/{slug}/` - Base URL that auto-redirects based on membership
- `/{slug}/member/` - Member-only view (requires active membership)
- `/{slug}/guest/` - Public/guest view (no login required)

**Examples**:
- `/colorado-cycling-league/` → redirects to `/member/` or `/guest/`
- `/teams/golden-hs/` → redirects to `/member/` or `/guest/`
- `/league/team/` → redirects to `/member/` or `/guest/`

**Access Flow**:
1. User clicks organization link → goes to base URL
2. System checks: Is user authenticated? Is user an active member?
3. Routes to appropriate view:
   - Active member → `/member/` view (full access)
   - Non-member/guest → `/guest/` view (public info only)
4. Direct access protection: Non-members accessing `/member/` URLs are redirected to `/guest/`

**Model URL Methods**:
```python
# Get base redirect URL (use in templates/links)
organization.get_absolute_url()  # Returns /{slug}/

# Get specific view URLs (internal use)
organization.get_member_url()    # Returns /{slug}/member/
organization.get_guest_url()     # Returns /{slug}/guest/
```

**Implementation**:
- `LeagueRedirectView` / `TeamRedirectView` - Check membership and redirect
- `LeagueMemberView` / `TeamMemberView` - Member-only content (requires LoginRequiredMixin)
- `LeagueGuestView` / `TeamGuestView` - Public content

#### Organization Card Template System

**Reusable Card Component**: All organization cards use a single template component for consistency.

**Template**: `organizations/_organization_card.html`

**Usage**:
```django
{% include "organizations/_organization_card.html" with organization=league %}
{% include "organizations/_organization_card.html" with organization=team %}
{% include "organizations/_organization_card.html" with organization=membership.organization permission_level=membership.permission_level permission_level_display=membership.get_permission_level_display %}
```

**Card Display Elements**:
- Logo (24x24, centered, rounded)
- Name (bold, centered)
- Type badge (League/Team with color coding)
- Parent league name (for teams in a league, with icon)
- Team type (for teams with team_profile)
- Short description (with fallback to full description)
- Sponsors section (horizontal layout at bottom)
- Permission level badge (optional, for "My Organizations")

**Locations Used**:
- `league_list.html` - My Organizations, Leagues, Teams sections
- `league_detail.html` - Team cards within league
- Any future pages that need to display organization cards

**Benefits**:
- Single source of truth for card display
- Consistent styling across all pages
- Easy to maintain and update
- Supports both logged-in and logged-out users

#### accounts.User (Extended)
- Custom user model extending `AbstractUser`
- Required: `username`, `email`, `first_name`, `last_name`
- Additional: `phone_number` (PhoneNumberField), `phone_verified`, `dob` (with age validation), `avatar` (ImageField)
- Methods: `racing_age()`, `UNDER18()`, `UNDER16()`, `get_full_name()`
- Signal: `unverify_on_phone_change` resets `phone_verified` when number changes

#### organizations.Organization
- type (league, team, squad, club, etc.)
- parent (self-referential FK for hierarchy)
- name, description, logo
- contact information, settings
- Supports hierarchical nesting with validation

**Organization Hierarchy Rules**:
1. **Leagues**: Top-level organizations (cannot have a parent)
2. **Teams**: Can be top-level (standalone) OR optionally belong to a League
3. **Squads, Clubs, Practice Groups** (collectively called "subgroups"): ALWAYS sub-organizations of Teams (required parent)

**Note on Terminology**: The terms "subgroups" and "sub-organizations" are used interchangeably to refer to Squads, Clubs, and Practice Groups.

**Sub-Organization Creation Rules**:
- Subgroups (squads, clubs, and practice groups) can ONLY be created by:
  - Team owners
  - Team administrators
  - Team managers
- Use `can_create_sub_organization(user, parent_team)` permission helper to check
- Model validation enforces parent-child relationships automatically
- Views creating sub-organizations must verify parent team permissions

**Example**:
```python
from apps.organizations.permissions import can_create_sub_organization

# Check if user can create a squad for this team
if can_create_sub_organization(request.user, team):
    squad = Organization.objects.create(
        type=Organization.SQUAD,
        parent=team,  # Must be a Team
        name="Youth Squad"
    )
```

**This section has been moved above - see Organization Architecture Pattern**

#### organizations.LeagueProfile (extends Organization)
- short_description (max 200 chars for card display)
- sanctioning_body, region
- membership requirements
- competition rules
- banner image

#### organizations.TeamProfile (extends Organization)
- short_description (max 200 chars for card display)
- team_type (high_school, racing, devo)
- banner image

#### membership.Membership & membership.MemberRole

**IMPORTANT**: The system separates **permission levels** (what you can DO) from **organizational roles** (what you ARE).

**Membership Model**:
- Links User to Organization
- `permission_level`: Determines authorization (owner, admin, manager, member)
- `status`: Membership status (active, inactive, prospect, expired, pending_renewal)
- Join date, membership fees
- Works across all organization types

**MemberRole Model**:
- Many-to-many relationship: One user can have multiple roles
- `role_type`: Organizational identity (athlete, coach, parent, guardian, medical_staff, etc.)
- Descriptive only - does NOT grant permissions
- Examples: A user can be both "Coach" and "Parent" simultaneously

#### membership.Season & membership.SeasonMembership

**Season-Based Membership Management**: Organizations can organize memberships by time periods (seasons).

**Season Model** (`apps/membership/models.py`):
- Links to Organization (league or team)
- `name`: Season name (e.g., "Spring 2025", "Fall 2024")
- `start_date` / `end_date`: Season duration
- `registration_open_date` / `registration_close_date`: Registration window
- `is_active`: Whether season is currently active
- `auto_approve_registration`: Automatically approve new registrations
- `registration_fee`: Optional fee for the season
- `max_members`: Optional capacity limit

**SeasonMembership Model**:
- Links User to Organization for a specific Season
- `registration_status`: pending, approved, rejected, waitlisted
- `registration_date`: When user registered
- `approved_date` / `approved_by`: Approval tracking
- `payment_status`: pending, paid, waived, refunded
- Inherits permission level and roles from base Membership

**Key Features**:
- Multiple concurrent seasons per organization
- Automatic approval based on season settings
- Season-specific member lists and reporting
- Registration workflow with approval/rejection
- Payment tracking per season
- Waitlist support when at capacity

**Usage**:
```python
# Create a season
season = Season.objects.create(
    organization=team,
    name="Spring 2025",
    start_date="2025-03-01",
    end_date="2025-05-31",
    auto_approve_registration=True,
    is_active=True
)

# Register user for season
season_membership = SeasonMembership.objects.create(
    membership=membership,  # Base membership
    season=season,
    registration_status=SeasonMembership.APPROVED if season.auto_approve_registration else SeasonMembership.PENDING
)
```

**Templates**:
- `membership/_season_card.html` - Season display card
- `membership/season_detail.html` - Season detail page with member list
- `organizations/season_list.html` - List of all seasons for an organization
- `organizations/season_form.html` - Create/edit season form

#### events.Event & events.EventAttendee

**Event Management with RSVP Tracking**: Organizations can create events and track member attendance.

**Event Model** (`apps/events/models.py`):
- Links to Organization (league, team, squad, club, or practice group)
- `title`, `description`: Event details
- `event_type`: practice, race, meeting, social, fundraiser, training, other
- `start_datetime`, `end_datetime`: Event timing
- `location`: Event location (text field)
- `max_attendees`: Optional capacity limit
- `recurrence`: Recurring event support (none, daily, weekly, monthly)
- `view_permissions`: Controls who can see the event (members-only or public)
- `registration_deadline`: Optional deadline for RSVPs
- `created_by`: User who created the event
- Status tracking: draft, published, cancelled

**EventAttendee Model**:
- Links User to Event with RSVP status
- `status`: attending, not_attending, maybe, no_response
- `checked_in`: Boolean for attendance tracking
- `checked_in_at`: Timestamp for check-in

**Key Features**:
- Event creation with permission checks (owner/admin/manager)
- RSVP system with status tracking
- Attendee list and count
- Capacity management
- Recurring event support (daily, weekly, monthly)
- Registration deadlines
- Check-in/attendance tracking
- Public/private event visibility
- Event detail pages with RSVP buttons
- Event cards for display in lists

**Views** (`apps/events/views.py`):
- `EventDetailView`: Shows event details with RSVP button
- `EventRSVPView`: Handles RSVP submissions (POST only)
- Permission checks ensure only members can RSVP

**Templates**:
- `events/event_detail.html` - Event detail page (pending creation)
- `events/_event_card.html` - Event card component for lists
- Used on account home page to show upcoming events

**Usage**:
```python
# Create an event
event = Event.objects.create(
    organization=team,
    title="Weekly Practice",
    event_type=Event.PRACTICE,
    start_date=timezone.now() + timedelta(days=7),
    created_by=request.user
)

# RSVP to event
EventAttendee.objects.create(
    event=event,
    user=request.user,
    status=EventAttendee.GOING
)
```

#### messaging.ChatRoom, messaging.ChatRoomParticipant, & messaging.Message

**Real-Time Messaging System**: Organizations have chat rooms for member communication with read receipts and unread counts.

**ChatRoom Model** (`apps/messaging/models.py`):
- `room_type`: public, organization, direct, announcement
- `organization`: Optional link to Organization (for org chat rooms)
- `name`: Chat room name/suffix (e.g., "Member Chat", "News & Announcements")
- `description`: Optional room description
- `is_active`: Whether chat room is active
- **Computed `display_name` property**: Dynamically generates full name
  - For organization rooms: `"{organization.name} - {name}"` (e.g., "Golden HS Cycling - Member Chat")
  - For other rooms: Returns `name` as-is
- `created_by`: User who created the room

**Key Features**:
- **Automatic chat room creation** for organizations (apps/organizations/models.py:332-380)
  - "Member Chat" room created when organization enables member chat
  - "News & Announcements" room created when organization enables news channel
  - Rooms automatically activated/deactivated based on organization settings
- **Dynamic naming**: Chat room names automatically reflect organization name changes
- **No database sync needed**: Uses computed property instead of stored name

**ChatRoomParticipant Model**:
- Links User to ChatRoom
- `joined_at`: When user joined the room
- `last_read_at`: Last time user read messages (for unread counts)
- `is_admin`: Whether user is room admin
- Tracks user membership in chat rooms

**Message Model**:
- Links to ChatRoom and sender User
- `content`: Message text
- `sent_at`: Message timestamp
- `is_read`: Read receipt tracking
- `read_at`: When message was read

**Class Methods** (ChatRoom model):
- `get_user_chat_rooms(user)`: Returns all chat rooms user has access to
- `get_unread_count(user)`: Returns number of unread messages for user

**Templates**:
- `messaging/_chat_room_card.html` - Chat room card with unread badge
- Used on account home page

**Usage**:
```python
# Get user's chat rooms with unread counts
rooms = ChatRoom.get_user_chat_rooms(user)
for room in rooms:
    unread = room.get_unread_count(user)
    print(f"{room.display_name}: {unread} unread")

# Send a message
Message.objects.create(
    chat_room=room,
    sender=user,
    content="Hello team!"
)
```

#### sponsors.Sponsor

**Sponsor Management**: Organizations can add sponsor logos and links to their pages.

**Sponsor Model** (`apps/sponsors/models.py`):
- Links to Organization
- `name`: Sponsor name
- `logo`: Sponsor logo image
- `website_url`: Optional sponsor website
- `description`: Optional sponsor description
- `display_order`: Order for display
- `is_active`: Whether sponsor is currently active

**Display Locations**:
- Organization cards (`organizations/_organization_card.html`)
- Shows sponsor logos in horizontal layout at bottom of card

#### performance.Result (Planned)
- Links User to Event with performance data
- Time, placement, points scored
- Personal notes, conditions
- **Status**: Not yet implemented

#### finances.Transaction (Planned)
- Team expenses, member dues
- Categories, payment methods
- Approval workflow
- **Status**: Not yet implemented - planned for Stripe Connect integration

## Implemented Features

### Account Home Page

**User Dashboard**: Centralized home page showing user's organizations, chat rooms, and upcoming events.

**Location**: `/accounts/home/`

**View**: `AccountHomeView` (`accounts/views.py`)
- Requires login
- Shows user's active memberships
- Displays chat rooms with unread counts
- Shows upcoming events (next 30 days)

**Template**: `accounts/home.html`
- Three-column/tab responsive layout
- **Organizations tab**: Shows all user's organizations with permission level badges
- **Chats tab**: Shows chat rooms with unread message counts
- **Events tab**: Shows upcoming events with RSVP buttons
- Mobile-responsive: Tabs on small screens, columns on large screens

**Redirect Behavior**:
- `LOGIN_REDIRECT_URL = '/accounts/home/'` (settings.py)
- LeagueListView redirects authenticated users to home page
- Browse organizations available at `/browse/`

**Component Templates**:
- Uses `organizations/_organization_card.html` for organization display
- Uses `messaging/_chat_room_card.html` for chat room display
- Uses `events/_event_card.html` for event display

### CSV Import/Export for Members

**Member Bulk Operations**: Export and import organization members via CSV files.

**Permission**: Only available to owners, admins, and managers of an organization

**Views** (`apps/organizations/views.py:1081-1274`):
1. **`export_members_csv(request, slug)`**:
   - Downloads all members as CSV with user details
   - Includes: email, first_name, last_name, username, permission_level, status, join_date, roles
   - Filename: `{organization_slug}_members.csv`

2. **`import_members_csv(request, slug)`**:
   - Imports members from uploaded CSV file
   - **Creates new users** if email doesn't exist
   - **Updates existing users** if email matches
   - Creates or updates memberships
   - Transactional (all-or-nothing import)
   - Detailed error reporting (shows first 10 errors)
   - Logs import statistics with Logfire

3. **`download_csv_template(request)`**:
   - Downloads CSV template with example data
   - Shows correct format and field options

**URL Routes** (`apps/organizations/urls.py:29-32`):
- `/<slug>/members/export/` - Export members to CSV
- `/<slug>/members/import/` - Import members from CSV
- `/csv-template/` - Download CSV template

**Template Integration**:
- Import/Export buttons shown on team detail page (`organizations/team_detail.html`)
- Modal dialog for CSV import with format instructions
- Only visible when `can_edit` permission is true

**CSV Format**:
```csv
email,first_name,last_name,username,permission_level,status,join_date,roles
user@example.com,John,Doe,johndoe,member,active,2025-01-01,athlete
```

**Supported Fields**:
- `email` (required): User email
- `first_name`, `last_name`, `username`: User details
- `permission_level`: owner, admin, manager, member
- `status`: active, inactive, prospect
- `join_date`: YYYY-MM-DD format
- `roles`: Comma-separated role types

### Social Media Accounts

**Organization Social Profiles**: Organizations can add social media links to their profiles.

**Model**: `SocialMediaAccount` (linked to Organization)
- `platform`: facebook, twitter, instagram, linkedin, youtube, tiktok, strava, etc.
- `username`: Social media username/handle
- `profile_url`: Full URL to profile
- `display_order`: Order for display
- `is_active`: Whether link is currently active

**Availability**:
- **Only for Leagues and Teams** (not for Clubs, Squads, Practice Groups)
- View logic (`apps/organizations/views.py:813-823`) conditionally adds formset
- Template (`organizations/organization_edit.html:285-374`) conditionally shows section

**Form**:
- Inline formset on organization edit page
- Add/edit/delete multiple social accounts
- Auto-sorts by display_order

**Display**:
- Shows on organization detail pages
- Links to social profiles

### Mobile API

**RESTful API**: JSON API for mobile and PWA applications using **django-ninja**.

**Mobile API** (`apps/mobile_api/`):
- Built with **django-ninja** (auto-generated OpenAPI/Swagger docs at `/api/mobile/docs`)
- Main API instance in `apps/mobile_api/api.py`
- **Routers** (`apps/mobile_api/routers/`):
  - `auth_router.py` - Authentication (login, registration, token management)
  - `organizations_router.py` - Organization and member data access
  - `chat_router.py` - Chat room and messaging endpoints
  - `events_router.py` - Event listing and RSVP
- Health check endpoint: `GET /api/mobile/health`
- All endpoints under `/api/mobile/` namespace

### Implementation Roadmap

#### Phase 1: Foundation (Weeks 1-3)

##### MVP Core Features
- Extend existing accounts app with organization roles
- Create organizations app with hybrid model architecture
- Set up members app for roster management
- Basic organization dashboard with member list
- Simple organization creation and joining workflow

##### Technical Setup
- Configure Django permissions system
- Set up basic templates extending current theme
- Database migrations for core models
- Basic admin interface setup

#### Phase 2: Event Management (Weeks 4-6)

##### Event Features
- Event creation and editing interface
- Calendar view with event listings
- RSVP system with attendance tracking
- Event details pages with location info
- Basic recurring event support

##### UI Components
- Calendar widget integration
- Event cards and list views
- RSVP buttons and status indicators
- Mobile-responsive event pages

#### Phase 3: Communication (Weeks 7-8)

##### Messaging System
- Team announcements board
- Simple messaging interface
- Email notifications for key events
- Event comment threads
- Basic notification system

#### Phase 4: Performance Tracking (Weeks 9-10)

##### Stats & Results
- Result entry forms for events
- Individual performance pages
- Basic statistics and charts
- Team performance summaries
- Export functionality for results

#### Phase 5: Financial Management (Weeks 11-12)

##### Money Management
- Expense tracking system
- Member dues management
- Payment status indicators
- Basic financial reports
- Budget tracking tools

#### Phase 6: Polish & Advanced Features (Weeks 13-16)

##### Enhancement Phase
- Advanced search and filtering
- Data visualization improvements
- Mobile app considerations
- Performance optimizations
- Advanced admin features
- Integration with external services (Strava, MapMyRide)

### Technology Stack

- **Backend**: Django 6.0+ (Python 3.14+)
- **ASGI Server**: Daphne (via Django Channels)
- **Frontend**: Tailwind CSS v4 + DaisyUI + HTMX
- **API**: django-ninja (OpenAPI/Swagger auto-docs)
- **Database**: SQLite for development, PostgreSQL for production
- **Real-time**: Django Channels (infrastructure in place, in-memory channel layer for dev)
- **Email**: django-anymail with Resend
- **SMS**: Sinch Verification API
- **Media Storage**: Cloudflare R2 (S3-compatible, optional) / local filesystem
- **Static Files**: WhiteNoise
- **Background Tasks**: Django Tasks (database backend)
- **Push Notifications**: django-push-notifications
- **Observability**: Logfire (Pydantic)
- **Testing**: pytest
- **Code Quality**: ruff for linting and formatting

### Desktop and Mobile Applications

- **Progressive Web App (PWA)**: League Gotta Bike
  - Cross-platform compatibility (iOS, Android, Desktop)
  - Native app-like experience with offline capabilities
  - Push notifications support
  - Install-to-home-screen functionality
- **Framework**: Django-based PWA with service worker implementation
- **Integration**: REST APIs for data synchronization