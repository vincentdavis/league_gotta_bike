# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Django Application
- `honcho -f Procfile.tailwind start` - Start all services (Django, Tailwind, and task worker)
- `python manage.py runserver 8002` - Start the Django development server only (port configured via DJANGO_PORT in .env)
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

**Structure**:
```
tests/
├── __init__.py
├── accounts/
│   ├── __init__.py
│   ├── test_email.py
│   ├── test_auth.py
│   └── README.md
├── organizations/
│   ├── __init__.py
│   └── test_models.py
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

## Project Architecture

### Django Project Structure
- **league_gotta_bike/**: Main Django project directory containing settings, URLs, and WSGI/ASGI configuration
- **accounts/**: Custom user accounts app for authentication and user management
- **theme/**: Tailwind CSS theme app for frontend styling

### Key Configuration
- Uses **pydantic-settings** for environment variable management (see `.env` file)
- Environment variables loaded from `.env` file using type-safe validation
- Uses **SQLite** database for development (configured in settings.py)
- **Django Debug Toolbar** and **django-browser-reload** enabled only when `DEBUG=True`
- **Django Tasks** configured with DatabaseBackend for background task processing
- **Tailwind CSS v4** with **DaisyUI** component library for styling
- **PostCSS** build pipeline for CSS processing
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
Configuration is managed via `.env` file (see `.env.example` for template):
- `DEBUG`: Enable/disable debug mode (default: False)
- `SECRET_KEY`: Django secret key for cryptographic signing
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `INTERNAL_IPS`: Comma-separated list of IPs for debug toolbar (default: 127.0.0.1)
- `DJANGO_PORT`: Development server port (default: 8002)
- `DATABASE_URL`: Database connection string (default: SQLite)
- `DJANGO_SUPERUSER_USERNAME`: Username for auto-created superuser (optional)
- `DJANGO_SUPERUSER_EMAIL`: Email for auto-created superuser (optional)
- `DJANGO_SUPERUSER_PASSWORD`: Password for auto-created superuser (optional)

**Important**: Debug toolbar and browser reload are automatically disabled when `DEBUG=False`

**Superuser Auto-Creation**: Set the three `DJANGO_SUPERUSER_*` variables and run `python manage.py ensure_superuser` to automatically create an admin account. This is useful for deployment automation on platforms like Railway where you can't run interactive commands.

### App Configuration
The project uses a structured approach to Django apps:
- `DEFAULT_APPS`: Standard Django contrib apps
- `LOCAL_APPS`: Custom project-specific apps (`accounts`)
- `ADDON_APPS`: Third-party apps (`tailwind`, `theme`, `debug_toolbar`)

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

### Static Files
- Template directory: `BASE_DIR / 'templates'`
- Static files are managed through Django's standard static files system
- Tailwind CSS output is served as static files

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
- **Additional Field**: `phone_number` for contact information
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
- `/accounts/signup/` - User registration
- `/accounts/login/` - User login
- `/accounts/logout/` - User logout
- `/accounts/password/reset/` - Password reset
- `/accounts/email/` - Email address management
- `/accounts/password/change/` - Change password
- `/accounts/mfa/` - Two-factor authentication management

#### Custom Templates Location
All allauth templates are customized in `templates/account/` and `templates/mfa/` directories using Tailwind CSS and DaisyUI styling.

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
EMAIL_BACKEND = 'anymail.backends.resend.EmailBackend'
```

#### Testing Emails Locally
In development, emails are sent via the configured Resend API. To test without sending real emails, you can:
1. Use Django's console email backend for development: `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`
2. Configure a development domain in Resend for testing

#### Resend Setup
1. Create an account at https://resend.com
2. Verify your sending domain
3. Generate an API key with "sending access" permission
4. Add the API key to your `.env` file as `RESEND_API_KEY`

## Project Purpose & Roadmap

### Application Overview
League Gotta Bike is a comprehensive sports team management platform focused on cycling teams, clubs, and leagues. The app streamlines team operations, event coordination, member management, and performance tracking.

### Planned Django Apps
```
league_gotta_bike/           # Main project
├── accounts/                # User authentication & profiles (existing)
├── organizations/           # Organization management (leagues, teams, squads, clubs)
├── Calendar/                # Calendar for event, practice, ... scheduling & management.
├── members/                 # Member profiles & roster management
├── communications/          # Messaging & notifications
├── performance/             # Stats & results tracking
├── finances/                # Financial management
└── theme/                   # Frontend styling (existing)
```

### Core Features to Implement
- **Team Management**: Team profiles, roster management, role-based permissions
- **Event System**: Calendar, RSVP, recurring events, location mapping
- **Communication Hub**: Team messaging, announcements, notifications
- **Performance Tracking**: Race results, statistics, progress reports
- **Financial Tools**: Expense tracking, dues management, budget reports

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
- Custom user model with role-based permissions
- Profile fields: emergency contact, skill level, bike info

#### organizations.Organization
- type (league, team, squad, club, etc.)
- parent (self-referential FK for hierarchy)
- name, description, logo
- contact information, settings
- Supports hierarchical nesting with validation

**Organization Hierarchy Rules**:
1. **Leagues**: Top-level organizations (cannot have a parent)
2. **Teams**: Can be top-level (standalone) OR optionally belong to a League
3. **Squads, Clubs, Practice Groups**: ALWAYS sub-organizations of Teams (required parent)

**Sub-Organization Creation Rules**:
- Squads, clubs, and practice groups can ONLY be created by:
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
- `status`: Membership status (active, inactive, prospect)
- Join date, membership fees
- Works across all organization types

**MemberRole Model**:
- Many-to-many relationship: One user can have multiple roles
- `role_type`: Organizational identity (athlete, coach, parent, guardian, medical_staff, etc.)
- Descriptive only - does NOT grant permissions
- Examples: A user can be both "Coach" and "Parent" simultaneously

#### events.Event
- title, description, event_type
- date/time, location, difficulty
- recurring event patterns
- equipment requirements

#### events.EventResponse
- Links User to Event with RSVP status
- Response time, comments

#### performance.Result
- Links User to Event with performance data
- Time, placement, points scored
- Personal notes, conditions

#### communications.Message
- Team announcements, direct messages
- Read status, priority levels

#### finances.Transaction
- Team expenses, member dues
- Categories, payment methods
- Approval workflow

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

- **Backend**: Django 5.2.6 (already configured)
- **Frontend**: Tailwind CSS v4 + DaisyUI (already set up)
- **Database**: SQLite for development, PostgreSQL for production
- **Real-time**: Django Channels for live notifications
- **Testing**: pytest (already configured)
- **Code Quality**: ruff for linting (already set up)

### Desktop and Mobile Applications

- **Progressive Web App (PWA)**: League Gotta Bike
  - Cross-platform compatibility (iOS, Android, Desktop)
  - Native app-like experience with offline capabilities
  - Push notifications support
  - Install-to-home-screen functionality
- **Framework**: Django-based PWA with service worker implementation
- **Integration**: REST APIs for data synchronization