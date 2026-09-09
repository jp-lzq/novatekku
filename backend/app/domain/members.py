from dataclasses import dataclass, field


class MemberError(Exception):
    pass


class IdentityConflict(Exception):
    pass


class ConcurrentUpdate(Exception):
    pass


@dataclass(frozen=True)
class MemberView:
    id: str
    username: str
    email: str


@dataclass(frozen=True)
class StoredMember:
    id: str
    username: str
    email: str
    password_hash: str = field(repr=False)
    revision: int = 0
    active: bool = True

    def view(self) -> MemberView:
        return MemberView(self.id, self.username, self.email)


@dataclass(frozen=True)
class StoredSession:
    token_hash: str = field(repr=False)
    csrf_hash: str = field(repr=False)
    member_id: str
    created_at: int
    expires_at: int


@dataclass(frozen=True)
class LoginResult:
    member: MemberView
    token: str = field(repr=False)
    csrf_token: str = field(repr=False)
    expires_at: int
