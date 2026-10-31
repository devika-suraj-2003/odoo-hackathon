from fastapi import APIRouter

router = APIRouter(tags=["Users"])

# TODO: Implement user management endpoints
# GET  /users/me
# PUT  /users/me
# GET  /users          (admin)
# GET  /users/{id}     (admin)
# PUT  /users/{id}     (admin)
# DELETE /users/{id}   (admin)


@router.get("/", summary="Users status / placeholder")
def get_users_status():
    """Placeholder endpoint for the Users router."""
    return {"status": "ok", "message": "Users router is registered"}
