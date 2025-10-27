# Mobile API

This Django app provides REST API endpoints using **django-ninja** for mobile and Progressive Web App (PWA) applications.

## Purpose

The mobile_api app serves as the backend API layer for:
- Mobile applications (iOS/Android)
- Progressive Web App (PWA)
- Third-party integrations

## Current Endpoints

All endpoints use the `/api/mobile/` prefix and are built with **django-ninja**.

### Health Check
- **URL**: `/api/mobile/health`
- **Method**: GET
- **Auth**: None required
- **Response**:
  ```json
  {
    "status": "ok",
    "message": "Mobile API is running",
    "version": "1.0.0"
  }
  ```

### API Documentation
- **OpenAPI/Swagger UI**: `/api/mobile/docs` (automatic interactive documentation)
- **OpenAPI Schema**: `/api/mobile/openapi.json` (machine-readable API spec)

## Planned Features

### Authentication
- Token-based authentication (JWT)
- Session authentication for web clients
- OAuth2 integration for third-party apps

### User Management
- User profile retrieval and updates
- Avatar upload
- Account settings

### Organizations
- List user's organizations (leagues, teams, squads)
- Organization details and member roster
- Join/leave organization requests

### Events
- Upcoming events list
- Event details and RSVP
- Calendar sync

### Messaging
- Inbox and message threads
- Real-time notifications
- Push notification registration

### Performance Data
- User statistics and results
- Leaderboards
- Performance trends

## Development

### Adding New Endpoints with django-ninja

1. Create schemas in `schemas.py`:
   ```python
   from ninja import Schema

   class UserSchema(Schema):
       id: int
       username: str
       email: str
       first_name: str
       last_name: str
   ```

2. Add endpoints to the API in `api.py`:
   ```python
   from ninja import Router
   from django.contrib.auth import get_user_model
   from .schemas import UserSchema

   router = Router()
   User = get_user_model()

   @router.get("/user/profile", response=UserSchema, auth=...)
   def user_profile(request):
       return request.user
   ```

3. The API routes are automatically registered via `urls.py`

### Why django-ninja?

django-ninja offers several advantages:
- **Automatic OpenAPI/Swagger documentation** at `/api/mobile/docs`
- **Type hints and Pydantic schemas** for data validation
- **Better performance** than Django REST Framework
- **Modern Python syntax** with type annotations
- **Automatic request/response serialization**

### Testing

Run tests specific to the mobile_api app:
```bash
pytest tests/mobile_api/
```

## Dependencies

- **django-ninja** - Modern API framework with automatic OpenAPI docs
- **django-cors-headers** - CORS support for cross-origin requests
- **pydantic** - Data validation (included with django-ninja)

## Security Considerations

- All endpoints should require authentication unless specifically public
- Implement rate limiting for API endpoints
- Use HTTPS in production
- Validate and sanitize all input data
- Follow Django security best practices