import json
from datetime import datetime
from github import Github

def _repo():
    import streamlit as st
    g = Github(st.secrets["GITHUB_TOKEN"])
    return g.get_repo(st.secrets["GITHUB_REPO"])

def guardar_envio(tipo: str, datos: dict, archivos: list) -> str:
    repo = _repo()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    conductor = (datos.get("conductor") or "sin_nombre").replace(" ", "_")
    envio_id = f"{ts}_{conductor}"

    urls = []
    for i, file_info in enumerate(archivos):
        if not file_info: continue # Por si hay un archivo nulo
        ext = file_info["name"].split(".")[-1].lower() if "." in file_info["name"] else "bin"
        path = f"archivos/{tipo}/{envio_id}_{i+1}.{ext}"
        
        repo.create_file(
            path=path,
            message=f"archivo {envio_id} #{i+1}",
            content=file_info["data"],
            branch="main",
        )
        urls.append(f"https://raw.githubusercontent.com/{repo.full_name}/main/{path}")

    datos["_tipo"] = tipo
    datos["_enviado_en"] = datetime.now().isoformat(timespec="seconds")
    datos["_archivos"] = urls

    path_json = f"datos/{tipo}/{envio_id}.json"
    repo.create_file(
        path=path_json,
        message=f"registro {envio_id}",
        content=json.dumps(datos, ensure_ascii=False, indent=2),
        branch="main",
    )
    return envio_id