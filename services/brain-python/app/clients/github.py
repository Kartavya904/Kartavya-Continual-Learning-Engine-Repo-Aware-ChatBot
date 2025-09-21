import httpx

GITHUB_API = "https://api.github.com"

async def gh_get(repo_token: str, url: str):
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            url if url.startswith("http") else f"{GITHUB_API}{url}",
            headers={"Authorization": f"Bearer {repo_token}",
                     "Accept": "application/vnd.github+json"}
        )
        r.raise_for_status()
        return r.json()

async def get_repo_info_by_id(token: str, repo_id: int):
    data = await gh_get(token, f"/repositories/{repo_id}")
    full_name = data["full_name"]  # "owner/name"
    owner, name = full_name.split("/", 1)
    default_branch = data["default_branch"]
    return {
        "github_id": data["id"],
        "owner": owner,
        "name": name,
        "default_branch": default_branch,
    }

async def get_tree_paths(token: str, owner: str, name: str, default_branch: str):
    # Need the head commit SHA to fetch the full recursive tree.
    branch = await gh_get(token, f"/repos/{owner}/{name}/branches/{default_branch}")
    head_sha = branch["commit"]["sha"]
    tree = await gh_get(token, f"/repos/{owner}/{name}/git/trees/{head_sha}?recursive=1")
    # Keep only 'blob' (files), ignore 'tree' (dirs) and submodules
    return sorted([e["path"] for e in tree.get("tree", []) if e.get("type") == "blob"])
