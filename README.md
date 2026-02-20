# League Gotta Bike

A comprehensive sports team management platform focused on cycling teams, clubs, and leagues. League Gotta Bike streamlines team operations, event coordination, member management, and performance tracking.

## How to Help
We'd love your help making League Gotta Bike better! Here are some ways you can contribute:

Test Features - Feel free to explore, add leagues, teams, events... and otherwise test any feature on this development server.
Give Feedback - Share your thoughts on page layouts, mobile layouts, features, workflow...
Report Problems - Found a bug? Let us know!
Ask Questions - If something is unclear, ask! It helps us improve the documentation and user experience.
Suggest Features - Have an idea for a new feature or improvement? We want to hear it!
Thank you for helping make League Gotta Bike better for everyone!

## Features

### ✅ Implemented
- **Organization Management** - Hierarchical structure for leagues, teams, squads, clubs, and practice groups
- **Membership System** - Permission levels (owner, admin, manager, member) and organizational roles
- **Season-Based Memberships** - Manage registrations and memberships by season
- **Event Management** - Create events with recurrence, track RSVPs, and manage attendance
- **Messaging** - Chat rooms with unread counts, organization-specific channels, and announcements
- **Sponsor Management** - Display sponsor logos and links on organization pages
- **Member Import/Export** - CSV bulk operations for member management
- **Mobile API** - REST API (django-ninja) for mobile/PWA applications
- **Multi-Factor Authentication** - TOTP, WebAuthn/Passkeys, and recovery codes
- **Phone Verification** - SMS verification via Sinch API
- **HTMX Integration** - Dynamic partial page updates
- **Cloud Media Storage** - Cloudflare R2 (S3-compatible) for production file uploads

## Tech Stack

- **Backend**: Django 6.0+ (Python 3.14+)
- **ASGI Server**: Daphne (Django Channels)
- **Frontend**: Tailwind CSS v4 + DaisyUI + HTMX
- **Database**: SQLite (development) / PostgreSQL (production)
- **API**: django-ninja (OpenAPI/Swagger auto-docs at `/api/mobile/docs`)
- **Authentication**: django-allauth with MFA
- **Email**: django-anymail with Resend
- **SMS**: Sinch Verification API
- **Media Storage**: Cloudflare R2 (S3-compatible, optional) / local filesystem
- **Static Files**: WhiteNoise
- **Background Tasks**: Django Tasks (database backend)
- **Push Notifications**: django-push-notifications
- **Observability**: Logfire (Pydantic)
- **Testing**: pytest
- **Code Quality**: ruff

## Prerequisites

- Python 3.14+
- Node.js (for Tailwind CSS)
- PostgreSQL (for production)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd league_gotta_bike
   ```

2. **Install Python dependencies**
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies for Tailwind**
   ```bash
   cd theme/static_src
   npm install
   cd ../..
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   # Or use ensure_superuser with environment variables
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

## Development

### Start all services (recommended)
```bash
honcho -f Procfile.tailwind start
```

This starts:
- Daphne ASGI server (port 8003)
- Tailwind CSS watcher
- Background task worker

### Start services individually

**Django server:**
```bash
python manage.py runserver 8002
```

**Tailwind CSS (in another terminal):**
```bash
cd theme/static_src
npm run dev
```

**Background worker (in another terminal):**
```bash
python manage.py db_worker
```

## Testing

### Run all tests
```bash
pytest
```

### Run specific test module
```bash
python manage.py test tests.accounts
```

### Email verification testing
```bash
python manage.py test tests.accounts.test_email
```

Requires `TEST_TO_EMAIL` environment variable for actual email delivery tests.

## Code Quality

### Format code
```bash
ruff format
```

### Lint and fix issues
```bash
ruff check --fix
```

## Project Structure

```
league_gotta_bike/
├── accounts/              # User authentication, profiles, phone verification
├── apps/
│   ├── organizations/     # Leagues, teams, squads, clubs, practice groups
│   ├── membership/        # Member management, roles, and seasons
│   ├── events/            # Event management, RSVP, and attendance
│   ├── messaging/         # Chat rooms, messages, and announcements
│   ├── sponsors/          # Sponsor management and display
│   └── mobile_api/        # REST API (django-ninja) for mobile/PWA
├── theme/                 # Tailwind CSS theme (static_src/)
├── templates/             # Global templates (account/, mfa/)
├── tests/                 # Test suite (organized by app)
└── league_gotta_bike/     # Main project settings, config, ASGI/WSGI
```

## Key Concepts

### Organization Hierarchy
- **Leagues** - Top-level organizations
- **Teams** - Can be standalone or belong to a league
- **Subgroups** - Squads, clubs, and practice groups (always under teams)

### Permissions vs Roles
- **Permission Levels** (authorization) - What you can DO: owner, admin, manager, member
- **Organizational Roles** (identity) - What you ARE: athlete, coach, parent, guardian, etc.
- Users can have multiple roles but only one permission level per organization

### Season-Based Memberships
Organizations can create seasons with registration windows, capacity limits, and automatic approval settings.

## Environment Variables

Key variables in `.env` (see `.env.example` for full template):

- `DEBUG` - Enable debug mode (default: False)
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - Database connection string (default: SQLite)
- `RESEND_API_KEY` - Resend API key for emails
- `DEFAULT_FROM_EMAIL` - Default sender email
- `SINCH_APPLICATION_KEY` / `SINCH_APPLICATION_SECRET` - Sinch SMS verification
- `LOGFIRE_TOKEN` - Logfire API token for monitoring
- `USE_S3` - Enable Cloudflare R2 storage (default: False)
- `AWS_*` - R2 storage credentials (when USE_S3=True)
- `DJANGO_PORT` - Development server port (default: 8002)

## Contributing

See [how_you_can_help.md](theme/static/how_you_can_help.md) for ways to contribute!

## Documentation

Full documentation is available in [CLAUDE.md](CLAUDE.md).

## License

[Add your license here]

## Support

For questions or issues, please [create an issue](https://github.com/your-repo/issues) on GitHub.