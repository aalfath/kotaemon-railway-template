"""Kotaemon launcher for Railway (replaces upstream app.py; same app, three additions).

1. Every route sits behind Gradio's own login, checked against Kotaemon's user table.
   Upstream's login is UI-only: its Gradio event API answers without a session, so an
   open URL could read the stored provider keys. Here nothing answers before login.
   After the Gradio login the Kotaemon user is signed in automatically (one login).
2. On every boot the "openai" LLM and embedding entries are synced from the
   OPENAI_* variables, and the admin password from KH_FEATURE_USER_MANAGEMENT_PASSWORD,
   so changing a Railway variable and redeploying takes effect.
3. GET /healthz answers 200 without login for Railway's health check.
4. umap-learn (only used by the optional citation plot) is imported on first use,
   not at start-up, which saves about 150 MB of RAM.
"""
import hashlib
import os

import lazy_umap

lazy_umap.install()

from theflow.settings import settings as flowsettings

KH_APP_DATA_DIR = getattr(flowsettings, "KH_APP_DATA_DIR", ".")
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR") or os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR

import gradio as gr  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, PlainTextResponse  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from ktem.db.models import User, engine  # noqa: E402
from ktem.pages import login as ktem_login  # noqa: E402


def _sha(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def sync_admin_password():
    usn = flowsettings.KH_FEATURE_USER_MANAGEMENT_ADMIN
    pwd = flowsettings.KH_FEATURE_USER_MANAGEMENT_PASSWORD
    with Session(engine) as s:
        u = s.exec(select(User).where(User.username_lower == usn.lower())).first()
        if u is not None and u.password != _sha(pwd):
            u.password = _sha(pwd)
            u.admin = True
            s.add(u)
            s.commit()
            print(f'Admin "{usn}": password synced from KH_FEATURE_USER_MANAGEMENT_PASSWORD')


def sync_openai_models():
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return
    base = os.getenv("OPENAI_API_BASE", "") or "https://api.openai.com/v1"
    from ktem.embeddings.db import EmbeddingTable
    from ktem.embeddings.manager import embedding_models_manager
    from ktem.llms.db import LLMTable
    from ktem.llms.manager import llms

    want = {
        LLMTable: (llms, flowsettings.KH_LLMS.get("openai")),
        EmbeddingTable: (embedding_models_manager, flowsettings.KH_EMBEDDINGS.get("openai")),
    }
    for table, (mgr, seed) in want.items():
        if not seed:
            continue
        with Session(engine) as s:
            row = s.query(table).filter_by(name="openai").first()
            if row is None:
                continue  # removed by the admin in the UI: leave it removed
            spec = dict(row.spec or {})
            spec.update(api_key=key, base_url=base, model=seed["spec"]["model"])
            if spec != row.spec:
                row.spec = spec
                s.commit()
                print(f"Synced {table.__tablename__}.openai from OPENAI_* variables")
        mgr.load()


def railway_auth(username: str, password: str) -> bool:
    with Session(engine) as s:
        u = s.exec(
            select(User).where(
                User.username_lower == (username or "").lower().strip(),
                User.password == _sha(password or ""),
            )
        ).first()
    return u is not None


_orig_login = ktem_login.LoginPage.login


def _login(self, usn, pwd, request: gr.Request):
    name = getattr(request, "username", None) if request is not None else None
    if name:
        with Session(engine) as s:
            u = s.exec(select(User).where(User.username_lower == name.lower())).first()
        if u is not None:
            return u.id, "", ""
    return _orig_login(self, usn, pwd, request)


ktem_login.LoginPage.login = _login

from ktem.main import App  # noqa: E402

kapp = App()
demo = kapp.make()  # creates the admin on first boot
sync_admin_password()
sync_openai_models()

server = FastAPI()


@server.get("/healthz", include_in_schema=False)
def healthz():
    return PlainTextResponse("ok")


@server.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(kapp._favicon, media_type="image/svg+xml")


server = gr.mount_gradio_app(
    server,
    demo.queue(),
    path="",
    auth=railway_auth,
    auth_message="Sign in with your Kotaemon account (admin password: the KH_FEATURE_USER_MANAGEMENT_PASSWORD variable).",
    allowed_paths=["libs/ktem/ktem/assets", GRADIO_TEMP_DIR],
    show_error=True,
)

if __name__ == "__main__":
    uvicorn.run(
        server,
        host=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_level="warning",
    )
