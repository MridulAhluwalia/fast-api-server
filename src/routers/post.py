import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Depends

from src.database import comment_table, database, post_table
from src.models.post import (
    Comment,
    CommentIn,
    UserPost,
    UserPostIn,
    UserPostWithComments,
)
from src.models.user import User
from src.security import get_current_user, auth2_scheme

router = APIRouter()

logger = logging.getLogger(__name__)


async def _find_post(post_id: int) -> dict:
    logger.info("Find post with id: %d", post_id)
    query = post_table.select().where(post_table.c.id == post_id)
    logger.debug(query)
    return await database.fetch_one(query)


@router.post("/post", response_model=UserPost, status_code=201)
async def create_post(
    post: UserPostIn,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    logger.info("Create post: %s", post)
    data = {**post.model_dump(), "user_id": current_user.id}
    query = post_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)
    new_post = {**data, "id": last_record_id}
    return new_post


@router.get("/", response_model=list[UserPost])
async def get_all_posts() -> list[dict]:
    logger.info("Get all posts")
    query = post_table.select()
    logger.debug(query)
    return await database.fetch_all(query)


@router.post("/comment", response_model=Comment, status_code=201)
async def create_comment(
    comment: CommentIn,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    logger.info("Create comment")
    post = await _find_post(comment.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    data = {**comment.model_dump(), "user_id": current_user.id}
    query = comment_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)
    new_comment = {**data, "id": last_record_id}
    return new_comment


@router.get("/post/{post_id}/comment", response_model=list[Comment])
async def get_comments_on_post(post_id: int) -> list[dict]:
    logger.info("Get comments on the post: %d", post_id)
    query = comment_table.select().where(comment_table.c.post_id == post_id)
    logger.debug(query)
    return await database.fetch_all(query)


@router.get("/post/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comments(post_id: int) -> dict:
    logger.info("Get post with comments")
    post = await _find_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    return {
        "post": post,
        "comments": await get_comments_on_post(post_id),
    }
