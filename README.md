[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new/template/kotaemon-2?utm_medium=integration&utm_source=button&utm_campaign=kotaemon)

# Kotaemon on Railway

One-click Railway template for [Kotaemon](https://github.com/Cinnamon/kotaemon) **v0.12.0**
(Apache-2.0), an open-source RAG web app for chatting with your documents: upload files,
index them, and ask questions that are answered with citations to the source passages.

## What the template deploys

| Service | What it does |
|---|---|
| **Kotaemon** | The web app (Gradio UI on port 7860), built from this repo. Its SQLite database, uploaded files, LanceDB document store and Chroma vector store all live on a Railway volume at `/app/ktem_app_data`. Health check: `/healthz`. |

There is no separate database service: Kotaemon keeps everything in its data volume.

## Variables

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | *(you enter it)* | **Required.** Key for OpenAI or any OpenAI-compatible API. Used for chat and for document embeddings. |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | Change it to use an OpenAI-compatible provider (OpenRouter, Together, a LiteLLM or vLLM gateway…). That endpoint must also serve `/embeddings`. |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Chat model name. |
| `OPENAI_EMBEDDINGS_MODEL` | `text-embedding-3-small` | Embedding model name. If you change it after indexing files, re-index them. |
| `KH_FEATURE_USER_MANAGEMENT_ADMIN` | `admin` | Admin user name. |
| `KH_FEATURE_USER_MANAGEMENT_PASSWORD` | generated (`${{secret(24)}}`) | Admin password. Read it in the service's **Variables** tab. |
| `PORT` | `7860` | Port the app listens on. |

These variables are applied again on every deploy: if you change the key, base URL, models or the admin password in Railway and redeploy, Kotaemon uses the new values.

## After deploying

1. Open the service's public URL and sign in as `admin` with the `KH_FEATURE_USER_MANAGEMENT_PASSWORD` value. Nothing in the app (UI or API) answers before you sign in, apart from `/healthz`.
2. In **Files → Upload Files**, upload a PDF, DOCX, TXT or Markdown file and click **Upload and Index**.
3. In **Chat**, pick **Search All** (or **Search In File(s)**) in the file selector on the left and ask a question. The answer cites the passages it used.
4. Add more users under **Resources → Users**. Other providers (Azure OpenAI, Anthropic, Gemini, Groq, Cohere, Mistral, Voyage…) can be added under **Resources → LLMs / Embeddings**.

## Resources

Kotaemon needs about **1 GB RAM**. On Railway's Free plan (0.5 GB per service) it is stopped while loading its libraries. It idles at about 520 MB and peaked at about 700 MB in our tests while indexing and answering. Larger documents need more.

## What this build leaves out

Upstream's own image (`ghcr.io/cinnamon/kotaemon:main-lite`) is about 4.9 GB, because it ships CUDA PyTorch for local models, and is published only under moving tags. This template builds the pinned `v0.12.0` release with upstream's locked dependency versions, but leaves out the parts that need PyTorch or a GPU:

- local models (Ollama, llama.cpp, sentence-transformers rerankers);
- Docling, EasyOCR and PaddleOCR readers (standard PDF, Office, HTML and text readers are included);
- the GraphRAG, LightRAG and NanoGraphRAG indexes (extra packages and RAM).

Upstream's first-run setup wizard is skipped, because the model is set from the variables above.

## How updates reach you

This template builds from this repository (`main`). When we publish a new Kotaemon version, Railway shows an update notice in your project and you choose when to apply it. Read [CHANGELOG.md](CHANGELOG.md) first: breaking changes are listed first. Your data volume is kept across updates.

## Files

- `Dockerfile`: builds Kotaemon from the pinned upstream tag and commit on `python:3.11.14-slim-trixie` (pinned by digest).
- `start.sh`: entrypoint. It refuses to start with an empty or `admin` password, caps CPU threads, and runs the app with `exec`, so a crash exits non-zero and Railway restarts it.
- `railway_app.py`: upstream's `app.py` plus: Gradio login on every route, `/healthz`, and syncing the `OPENAI_*` variables and admin password into the app's database on each boot.
- `lazy_umap.py`: loads `umap-learn` only when a citation plot is drawn (saves about 150 MB of RAM).
