from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.user_model import UserModel
from app.domain.user import User
from app.mappers.user_mapper import to_domain


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _base_query(self):
        return select(UserModel).where(UserModel.ativo.is_(True))

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            self._base_query().where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return to_domain(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            self._base_query().where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return to_domain(model) if model else None

    async def add(self, entity: User) -> User:
        model = UserModel(
            email=entity.email,
            senha_hash=entity.senha_hash,
            role=entity.role.value,
            ativo=True,
        )
        self.session.add(model)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(model)
        return to_domain(model)

    async def update_fields(self, user_id: int, fields: dict) -> User | None:
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id, UserModel.ativo.is_(True))
            .values(**fields)
        )
        await self.session.commit()
        return await self.get_by_id(user_id)

    async def soft_delete(self, user_id: int) -> None:
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(ativo=False)
        )
        await self.session.commit()
