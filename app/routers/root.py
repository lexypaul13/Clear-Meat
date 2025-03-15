from fastapi import APIRouter

router = APIRouter(
    tags=["root"],
)

@router.get("/")
async def root():
    """
    Welcome to the Meat Products API
    """
    return {"message": "Welcome to the Meat Products API"} 