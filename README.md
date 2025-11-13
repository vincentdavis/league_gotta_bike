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
- **Event Management** - Create events, track RSVPs, and manage attendance
- **Real-Time Messaging** - Chat rooms with unread counts and organization-specific channels
- **Sponsor Management** - Display sponsor logos and links on organization pages
- **Member Import/Export** - CSV bulk operations for member management
- **Mobile & Admin APIs** - REST APIs for mobile apps and admin operations
- **Multi-Factor Authentication** - TOTP, WebAuthn/Passkeys, and recovery codes

## Tech Stack

- **Backend**: Django 5.2.7
- **Frontend**: Tailwind CSS v4 + DaisyUI
- **Database**: SQLite (development) / PostgreSQL (production)
- **Authentication**: django-allauth with MFA
- **Email**: django-anymail with Resend
- **Background Tasks**: Django Tasks
- **Testing**: pytest
- **Code Quality**: ruff

## Prerequisites

- Python 3.13+
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
- Django development server (port 8002)
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
├── accounts/              # User authentication and profiles
├── apps/
│   ├── organizations/     # Leagues, teams, squads, clubs
│   ├── membership/        # Member management and seasons
│   ├── events/            # Event management and RSVP
│   ├── messaging/         # Chat rooms and messages
│   ├── sponsors/          # Sponsor management
│   ├── mobile_api/        # REST API for mobile apps
│   └── admin_api/         # Admin API
├── theme/                 # Tailwind CSS theme
├── templates/             # Django templates
├── tests/                 # Test suite
└── league_gotta_bike/     # Main project settings
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

Key variables in `.env`:

- `DEBUG` - Enable debug mode (default: False)
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - Database connection string
- `RESEND_API_KEY` - Resend API key for emails
- `DEFAULT_FROM_EMAIL` - Default sender email
- `LOGFIRE_TOKEN` - Logfire API token for monitoring
- `DJANGO_PORT` - Development server port (default: 8002)

## Contributing

See [how_you_can_help.md](theme/static/how_you_can_help.md) for ways to contribute!

## Documentation

Full documentation is available in [CLAUDE.md](CLAUDE.md).

## License

[Add your license here]

## Support

For questions or issues, please [create an issue](https://github.com/your-repo/issues) on GitHub.