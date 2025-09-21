from pydantic import BaseModel, Field
from typing import List, Literal

class RepoInfo(BaseModel):
    github_id: int
    owner: str
    name: str
    default_branch: str

class FileStatus(BaseModel):
    path: str
    status: Literal["indexed", "not-indexed"]

class RepoFilesResponse(BaseModel):
    repo: RepoInfo
    files: List[FileStatus] = Field(default_factory=list)
