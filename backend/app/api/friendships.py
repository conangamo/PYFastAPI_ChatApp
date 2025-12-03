"""
Friendship API Endpoints
Handles friend requests, accepting/rejecting, and friend list management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from typing import List
from uuid import UUID

from ..database import get_db
from ..models.user import User
from ..models.friendship import Friendship
from ..schemas.friendship import (
    FriendRequestCreate,
    FriendRequestResponse,
    FriendshipOut,
    FriendWithUser,
    FriendshipStatus
)
from ..core.deps import get_current_user

router = APIRouter(prefix="/friendships", tags=["friendships"])


@router.post("/send-request", response_model=FriendshipOut, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    request: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a friend request to another user
    """
    # Check if trying to add self as friend
    if request.friend_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send friend request to yourself"
        )
    
    # Check if target user exists
    result = await db.execute(select(User).where(User.id == request.friend_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if friendship already exists (in either direction)
    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == current_user.id, Friendship.friend_id == request.friend_id),
                and_(Friendship.user_id == request.friend_id, Friendship.friend_id == current_user.id)
            )
        )
    )
    existing_friendship = result.scalar_one_or_none()
    
    if existing_friendship:
        if existing_friendship.status == "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Friend request already sent or received"
            )
        elif existing_friendship.status == "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already friends with this user"
            )
        elif existing_friendship.status == "blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot send friend request to this user"
            )
        else:
            # If rejected, allow sending new request
            existing_friendship.status = "pending"
            existing_friendship.user_id = current_user.id
            existing_friendship.friend_id = request.friend_id
            await db.commit()
            await db.refresh(existing_friendship)
            return existing_friendship
    
    # Create new friend request
    friendship = Friendship(
        user_id=current_user.id,
        friend_id=request.friend_id,
        status="pending"
    )
    db.add(friendship)
    await db.commit()
    await db.refresh(friendship)
    
    return friendship


@router.post("/respond", response_model=FriendshipOut)
async def respond_to_friend_request(
    response: FriendRequestResponse,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept, reject, or block a friend request
    Only the recipient of the request can respond
    """
    # Get friendship record
    result = await db.execute(
        select(Friendship).where(Friendship.id == response.friendship_id)
    )
    friendship = result.scalar_one_or_none()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    # Check if current user is the recipient
    if friendship.friend_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only respond to friend requests sent to you"
        )
    
    # Check if request is pending
    if friendship.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Friend request is already {friendship.status}"
        )
    
    # Update status based on action
    friendship.status = response.action + "ed"  # accept -> accepted, reject -> rejected, block -> blocked
    await db.commit()
    await db.refresh(friendship)
    
    return friendship


@router.get("/requests/received", response_model=List[FriendWithUser])
async def get_received_friend_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending friend requests received by current user
    """
    result = await db.execute(
        select(Friendship, User)
        .join(User, Friendship.user_id == User.id)
        .where(
            and_(
                Friendship.friend_id == current_user.id,
                Friendship.status == "pending"
            )
        )
        .order_by(Friendship.created_at.desc())
    )
    
    requests = []
    for friendship, user in result.all():
        requests.append(FriendWithUser(
            friendship_id=friendship.id,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            last_seen_at=user.last_seen_at,
            is_active=user.is_active,
            status=friendship.status,
            created_at=friendship.created_at
        ))
    
    return requests


@router.get("/requests/sent", response_model=List[FriendWithUser])
async def get_sent_friend_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending friend requests sent by current user
    """
    result = await db.execute(
        select(Friendship, User)
        .join(User, Friendship.friend_id == User.id)
        .where(
            and_(
                Friendship.user_id == current_user.id,
                Friendship.status == "pending"
            )
        )
        .order_by(Friendship.created_at.desc())
    )
    
    requests = []
    for friendship, user in result.all():
        requests.append(FriendWithUser(
            friendship_id=friendship.id,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            last_seen_at=user.last_seen_at,
            is_active=user.is_active,
            status=friendship.status,
            created_at=friendship.created_at
        ))
    
    return requests


@router.get("/friends", response_model=List[FriendWithUser])
async def get_friends_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all accepted friends of current user
    """
    # Get friendships where current user is either sender or receiver and status is accepted
    result = await db.execute(
        select(Friendship, User)
        .join(
            User,
            or_(
                and_(Friendship.user_id == current_user.id, Friendship.friend_id == User.id),
                and_(Friendship.friend_id == current_user.id, Friendship.user_id == User.id)
            )
        )
        .where(
            and_(
                or_(
                    Friendship.user_id == current_user.id,
                    Friendship.friend_id == current_user.id
                ),
                Friendship.status == "accepted",
                User.id != current_user.id
            )
        )
        .order_by(User.display_name)
    )
    
    friends = []
    for friendship, user in result.all():
        friends.append(FriendWithUser(
            friendship_id=friendship.id,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            last_seen_at=user.last_seen_at,
            is_active=user.is_active,
            status=friendship.status,
            created_at=friendship.created_at
        ))
    
    return friends


@router.get("/status/{user_id}", response_model=FriendshipStatus)
async def check_friendship_status(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check friendship status between current user and another user
    """
    # Check if friendship exists (in either direction)
    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == current_user.id, Friendship.friend_id == user_id),
                and_(Friendship.user_id == user_id, Friendship.friend_id == current_user.id)
            )
        )
    )
    friendship = result.scalar_one_or_none()
    
    if not friendship:
        return FriendshipStatus(
            are_friends=False,
            status=None,
            friendship_id=None,
            initiated_by=None
        )
    
    return FriendshipStatus(
        are_friends=(friendship.status == "accepted"),
        status=friendship.status,
        friendship_id=friendship.id,
        initiated_by=friendship.user_id
    )


@router.delete("/{friendship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friend_or_cancel_request(
    friendship_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a friend or cancel a friend request
    Can be used by either party in the friendship
    """
    # Get friendship record
    result = await db.execute(
        select(Friendship).where(Friendship.id == friendship_id)
    )
    friendship = result.scalar_one_or_none()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friendship not found"
        )
    
    # Check if current user is involved in this friendship
    if friendship.user_id != current_user.id and friendship.friend_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not part of this friendship"
        )
    
    # Delete the friendship
    await db.delete(friendship)
    await db.commit()
    
    return None


@router.get("/search/{query}", response_model=List[FriendWithUser])
async def search_users_for_friends(
    query: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for users to add as friends
    Returns users with their friendship status
    """
    if len(query) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )
    
    # Search users by username or display name
    search_pattern = f"%{query}%"
    result = await db.execute(
        select(User)
        .where(
            and_(
                User.id != current_user.id,  # Exclude current user
                or_(
                    User.username.ilike(search_pattern),
                    User.display_name.ilike(search_pattern)
                )
            )
        )
        .limit(20)
    )
    users = result.scalars().all()
    
    # Get friendship status for each user
    user_results = []
    for user in users:
        # Check friendship status
        friendship_result = await db.execute(
            select(Friendship).where(
                or_(
                    and_(Friendship.user_id == current_user.id, Friendship.friend_id == user.id),
                    and_(Friendship.user_id == user.id, Friendship.friend_id == current_user.id)
                )
            )
        )
        friendship = friendship_result.scalar_one_or_none()
        
        user_results.append(FriendWithUser(
            friendship_id=friendship.id if friendship else None,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            last_seen_at=user.last_seen_at,
            is_active=user.is_active,
            status=friendship.status if friendship else None,
            created_at=friendship.created_at if friendship else None
        ))
    
    return user_results

