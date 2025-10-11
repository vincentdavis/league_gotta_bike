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
- `python manage.py createsuperuser` - Create a Django admin superuser

### Frontend/Tailwind CSS
- `cd theme/static_src && npm run dev` - Watch and compile Tailwind CSS in development mode
- `cd theme/static_src && npm run build` - Build production-ready CSS
- `cd theme/static_src && npm install` - Install Node.js dependencies for Tailwind

### Testing and Code Quality
- `pytest` - Run tests using pytest
- `ruff check --fix` - Run linting with ruff and automatically fix issues
- `ruff format` - Format code with ruff
- `python manage.py test` - Run Django's built-in test suite

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

### Environment Variables
Configuration is managed via `.env` file (see `.env.example` for template):
- `DEBUG`: Enable/disable debug mode (default: False)
- `SECRET_KEY`: Django secret key for cryptographic signing
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `INTERNAL_IPS`: Comma-separated list of IPs for debug toolbar (default: 127.0.0.1)
- `DJANGO_PORT`: Development server port (default: 8002)
- `DATABASE_URL`: Database connection string (default: SQLite)

**Important**: Debug toolbar and browser reload are automatically disabled when `DEBUG=False`

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

### User Roles
- Team Owner/Admin (full management) `OrgOwner` and `OrgAdmin`
- Team Captain (limited management)
- Team Members (participation & tracking)
- League Officials (multi-team oversight)
- Parents/Spectators (view-only for youth teams)

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
TeamProfile(race_category, team_colors, etc.)
LeagueProfile(sanctioning_body, region, etc.)
SquadProfile(parent_team, focus_area, etc.)
```

#### accounts.User (Extended)
- Custom user model with role-based permissions
- Profile fields: emergency contact, skill level, bike info

#### organizations.Organization
- type (league, team, squad, club, etc.)
- parent (self-referential FK for hierarchy)
- name, description, logo
- contact information, settings
- Supports unlimited nesting (league → team → squad)

#### organizations.TeamProfile (extends Organization)
- race_category, team_colors
- season info
- meeting locations, equipment

#### organizations.LeagueProfile (extends Organization)
- sanctioning_body, region
- membership requirements
- competition rules

#### members.Membership
- Links User to Organization with role (admin, captain, member)
- Status (active, inactive, prospect)
- Join date, membership fees
- Works across all organization types

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