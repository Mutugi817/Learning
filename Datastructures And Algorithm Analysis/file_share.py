#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.server
import json
import mimetypes
import os
import re
import shutil
import socket
import tempfile
import threading
import urllib.parse
import webbrowser
import zipfile
from pathlib import Path

APP_NAME = "Orbit Share"
VERSION = "3.0"
CHUNK = 1024 * 1024
MAX_DEFAULT = 50 * 1024**3

MIME_OVERRIDES = {
    ".mp4": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska",
    ".mov": "video/quicktime", ".avi": "video/x-msvideo", ".m4v": "video/x-m4v",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".flac": "audio/flac",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif",
    ".webp": "image/webp", ".svg": "image/svg+xml", ".pdf": "application/pdf",
}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".log", ".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".htm", ".sql", ".sh", ".bat", ".ps1", ".c", ".h", ".cpp", ".hpp", ".java", ".rs", ".go", ".ini", ".conf"}
BAD_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def get_mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in MIME_OVERRIDES:
        return MIME_OVERRIDES[ext]
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def clean_name(name: str) -> str:
    name = Path(name).name.strip()
    name = BAD_NAME.sub("_", name).strip(" .")
    if not name:
        name = "uploaded-file"
    if name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}:
        name = "_" + name
    return name[:240]


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(1, 100000):
        p = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not p.exists():
            return p
    raise FileExistsError("Could not create a unique destination name.")


def safe_inside(root: Path, target: Path) -> bool:
    try:
        return os.path.commonpath([str(root), str(target)]) == str(root)
    except ValueError:
        return False


def human(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return f"{v:.1f} {units[i]}" if i else f"{int(v)} B"


def parse_size(s: str) -> int:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)?\s*", s, re.I)
    if not m:
        raise argparse.ArgumentTypeError("Use sizes like 500MB, 2GB or 50GB.")
    mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    return int(float(m.group(1)) * mult[(m.group(2) or "B").upper()])


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Orbit Share</title>
<style>
:root{--bg:#07111f;--panel:#0d1b2c;--panel2:#102238;--line:#1d3149;--text:#f6f8fb;--muted:#91a3b8;--accent:#35b8ff;--accent2:#0b8fe8;--danger:#ff6480;--shadow:0 22px 65px rgba(0,0,0,.35)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,rgba(53,184,255,.12),transparent 30%),var(--bg);color:var(--text);font:14px Inter,system-ui,-apple-system,Segoe UI,sans-serif}.app{display:flex;min-height:100vh}
.side{width:250px;position:fixed;inset:0 auto 0 0;padding:20px;background:rgba(7,18,32,.97);border-right:1px solid var(--line);z-index:20;display:flex;flex-direction:column}.brand{display:flex;gap:11px;align-items:center;margin-bottom:28px}.logo{width:43px;height:43px;border-radius:13px;background:linear-gradient(135deg,#63d0ff,#0b8fe8);display:grid;place-items:center;box-shadow:0 13px 30px rgba(11,143,232,.22)}.logo svg{width:22px}.brand b{display:block}.brand small{display:block;color:var(--muted);font-size:11px;margin-top:2px}.label{font-size:10px;color:#5f758d;font-weight:800;letter-spacing:.1em;text-transform:uppercase;margin:16px 10px 6px}.nav{width:100%;padding:11px 12px;border:0;background:transparent;color:var(--muted);text-align:left;border-radius:10px;cursor:pointer}.nav:hover,.nav.active{color:var(--text);background:rgba(53,184,255,.08)}.usage{margin-top:auto;border:1px solid var(--line);border-radius:14px;padding:13px;background:linear-gradient(145deg,rgba(53,184,255,.06),rgba(13,27,44,.8))}.usage small{color:var(--muted);line-height:1.45}.bar{height:7px;border-radius:20px;background:#15263a;overflow:hidden;margin:9px 0}.bar>i{display:block;width:0;height:100%;background:linear-gradient(90deg,#5dd1ff,#0b8fe8)}
.main{margin-left:250px;width:calc(100% - 250px)}.top{position:sticky;top:0;z-index:15;display:flex;gap:10px;padding:15px 22px;background:rgba(7,17,31,.82);backdrop-filter:blur(18px);border-bottom:1px solid rgba(29,49,73,.7)}.search{flex:1;position:relative}.search span{position:absolute;left:13px;top:11px;color:#647b93}.search input{height:43px;width:100%;padding:0 13px 0 37px;color:var(--text);background:#0a1727;border:1px solid var(--line);border-radius:11px;outline:0}.btn{height:40px;padding:0 13px;color:#dbe7f5;background:#0c1b2d;border:1px solid var(--line);border-radius:10px;cursor:pointer}.btn:hover{background:#12253b}.btn.primary{background:linear-gradient(135deg,#64d2ff,#0b8fe8);color:#02182a;border:0;font-weight:800}.iconbtn{width:39px;height:39px;border:1px solid var(--line);background:#0a1829;color:#9db0c4;border-radius:10px;cursor:pointer}.iconbtn:hover{color:#fff;background:#12253b}.mobile{display:none}
.content{max-width:1600px;margin:auto;padding:25px}.head{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin-bottom:16px}.head h1{font-size:32px;line-height:1;margin:0;letter-spacing:-.05em}.head p{color:var(--muted);margin:8px 0 0;font-size:12px}.actions{display:flex;gap:8px;flex-wrap:wrap}.crumbs{display:flex;gap:7px;overflow:auto;margin-bottom:15px}.crumb{border:0;background:transparent;color:var(--muted);cursor:pointer;padding:3px;white-space:nowrap}.crumb.current{color:#fff;font-weight:700}.drop{display:flex;align-items:center;gap:12px;padding:14px 16px;border:1px dashed #28546e;border-radius:14px;background:rgba(53,184,255,.04);margin-bottom:16px}.drop.drag{border-color:var(--accent);background:rgba(53,184,255,.1)}.drop .dicon{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;background:rgba(53,184,255,.09);color:var(--accent);font-size:18px}.drop b{font-size:12px}.drop small{display:block;color:var(--muted);margin-top:2px;font-size:11px}.panel{overflow:hidden;border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,rgba(15,30,49,.9),rgba(8,18,31,.94));box-shadow:var(--shadow)}.paneltop{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid rgba(29,49,73,.7)}.count{font-size:12px;color:var(--muted)}.thead,.row{display:grid;grid-template-columns:38px minmax(260px,1fr) 110px 160px 160px 135px;gap:9px;align-items:center}.thead{height:40px;padding:0 14px;font-size:10px;color:#627890;text-transform:uppercase;letter-spacing:.08em}.row{min-height:67px;padding:7px 14px;border-top:1px solid rgba(29,49,73,.5)}.row:hover{background:rgba(53,184,255,.025)}.name{display:flex;align-items:center;gap:10px;min-width:0;cursor:pointer}.fileicon{width:38px;height:38px;display:grid;place-items:center;flex:0 0 auto;border-radius:10px;background:#132238;color:#9fb2c7}.folder{color:var(--accent);background:rgba(53,184,255,.09)}.fileicon svg{width:20px}.title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px;font-weight:700}.sub{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#637a93;font-size:11px;margin-top:3px}.cell{color:var(--muted);font-size:12px}.rowactions{display:flex;justify-content:flex-end;gap:5px}.empty{text-align:center;padding:65px 15px;color:var(--muted)}
.transfer{display:none;position:fixed;right:18px;bottom:18px;width:min(420px,calc(100% - 30px));padding:14px;background:rgba(8,19,33,.98);border:1px solid var(--line);border-radius:15px;box-shadow:var(--shadow);z-index:60}.transfer.show{display:block}.trow{padding:9px 0;border-top:1px solid var(--line)}.trow:first-child{border-top:0}.prog{height:6px;border-radius:99px;background:#16283d;overflow:hidden;margin-top:7px}.prog i{display:block;width:0;height:100%;background:linear-gradient(90deg,#62d2ff,#0b8fe8)}.modal{display:none;position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.68);backdrop-filter:blur(10px);place-items:center;padding:18px}.modal.open{display:grid}.card{width:min(1000px,100%);max-height:90vh;background:#091827;border:1px solid var(--line);border-radius:18px;overflow:hidden}.mhead{display:flex;justify-content:space-between;align-items:center;padding:13px 15px;border-bottom:1px solid var(--line)}.mbody{max-height:calc(90vh - 60px);overflow:auto}.preview{display:block;max-width:100%;max-height:78vh;margin:20px auto}.video{display:block;width:100%;max-height:78vh;background:#000}.audio{display:block;width:92%;margin:35px 4%}.frame{display:block;width:100%;height:78vh;border:0;background:#fff}.code{padding:20px;white-space:pre-wrap;word-break:break-word;font:12px/1.6 Consolas,monospace;color:#dbeafe}
.toast{position:fixed;right:18px;top:75px;z-index:120;background:#0e2135;border:1px solid var(--line);padding:11px 13px;border-radius:10px;box-shadow:var(--shadow);font-size:12px}.toast.error{border-color:rgba(255,100,128,.4)}
@media(max-width:1000px){.thead,.row{grid-template-columns:34px minmax(220px,1fr) 95px 130px 125px}.type{display:none}}@media(max-width:760px){.side{transform:translateX(-100%);transition:.2s}.side.open{transform:translateX(0)}.main{margin-left:0;width:100%}.mobile{display:grid}.top{padding:11px}.content{padding:17px 12px}.head{align-items:flex-start;flex-direction:column}.actions{width:100%}.actions .btn{flex:1}.thead{display:none}.row{grid-template-columns:32px minmax(0,1fr) auto;padding:7px 9px}.size,.modified,.type{display:none}.rowactions button:nth-child(n+2){display:none}}
</style>
</head>
<body>
<div class="app">
<aside class="side" id="side">
<div class="brand"><div class="logo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7h6l2 2h10v10H3z"/><path d="M3 7V5a2 2 0 0 1 2-2h4l2 2h4"/></svg></div><div><b>Orbit Share</b><small>Local file workspace</small></div></div>
<div class="label">Workspace</div><button class="nav active" id="home">⌂ &nbsp; Home</button><button class="nav" id="refresh">↻ &nbsp; Refresh</button>
<div class="label">Tools</div><button class="nav" id="newSide">＋ &nbsp; New folder</button><button class="nav" id="upSide">⇧ &nbsp; Upload files</button>
<div class="usage"><b>Disk usage</b><br><small id="useText">Calculating...</small><div class="bar"><i id="useBar"></i></div><small id="root"></small></div>
</aside>
<main class="main"><header class="top"><button class="iconbtn mobile" id="menu">☰</button><div class="search"><span>⌕</span><input id="search" placeholder="Search files and folders..."></div><button class="iconbtn" id="downloadHere" title="Download current folder">⇩</button><button class="iconbtn" id="topRefresh">↻</button></header>
<section class="content"><div class="head"><div><h1 id="title">Home</h1><p id="desc">Manage your local files from a modern browser workspace.</p></div><div class="actions"><button class="btn" id="newFolder">New folder</button><button class="btn" id="upFolder">Upload folder</button><button class="btn primary" id="upFiles">Upload files</button></div></div>
<div class="crumbs" id="crumbs"></div><div class="drop" id="drop"><div class="dicon">⇧</div><div><b>Drag files here to upload</b><small>Any file type is accepted, including MP4, ZIP, ISO and large files.</small></div></div>
<div class="panel"><div class="paneltop"><span class="count" id="count">Loading...</span><button class="btn" id="downloadSelected">Download selected</button></div><div class="thead"><div></div><div>Name</div><div class="size">Size</div><div class="modified">Modified</div><div class="type">Type</div><div></div></div><div id="list"></div></div></section></main></div>
<input id="fileInput" type="file" multiple hidden><input id="folderInput" type="file" webkitdirectory directory multiple hidden>
<div class="transfer" id="transfer"><div style="display:flex;justify-content:space-between"><b>Transfers</b><span id="tstatus" style="color:var(--muted);font-size:11px"></span></div><div id="trows"></div></div>
<div class="modal" id="previewModal"><div class="card"><div class="mhead"><b id="pTitle">Preview</b><button class="iconbtn" id="pClose">×</button></div><div class="mbody" id="pBody"></div></div></div>
<div class="modal" id="formModal"><div class="card" style="width:min(430px,100%);padding:20px"><h3 id="fTitle" style="margin:0 0 6px">New folder</h3><p id="fDesc" style="color:var(--muted);font-size:12px">Enter a name.</p><input id="fInput" style="width:100%;height:43px;background:#0a1625;color:#fff;border:1px solid var(--line);border-radius:10px;padding:0 11px;outline:0"><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px"><button class="btn" id="fCancel">Cancel</button><button class="btn primary" id="fSubmit">Create</button></div></div></div>
<div id="toastBox"></div>
<script>
const S={path:"",entries:[],selected:new Set(),searching:false,action:null};
const $=s=>document.querySelector(s);const esc=x=>String(x).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");const enc=x=>encodeURIComponent(x);const fmt=n=>{if(!n)return"—";let u=["B","KB","MB","GB","TB"],i=0,v=n;while(v>=1024&&i<u.length-1){v/=1024;i++}return`${v.toFixed(i?1:0)} ${u[i]}`};const dt=n=>n?new Intl.DateTimeFormat(undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(n*1000)):"—";
async function api(url,opt={}){const r=await fetch(url,opt);const t=r.headers.get("content-type")||"";if(!r.ok){let m="Request failed";try{m=t.includes("json")?(await r.json()).error:await r.text()}catch{}throw Error(m)}return t.includes("json")?r.json():r}
function toast(msg,error=false){const x=document.createElement("div");x.className="toast"+(error?" error":"");x.textContent=msg;$("#toastBox").append(x);setTimeout(()=>x.remove(),3500)}
function openForm(title,desc,value,button,action){$("#fTitle").textContent=title;$("#fDesc").textContent=desc;$("#fInput").value=value||"";$("#fSubmit").textContent=button;S.action=action;$("#formModal").classList.add("open");setTimeout(()=>$("#fInput").focus(),40)}
function icons(e){return e.is_dir?'<div class="fileicon folder">📁</div>':'<div class="fileicon">📄</div>'}
function canPreview(e){return !e.is_dir&&(e.mime.startsWith("image/")||e.mime.startsWith("video/")||e.mime.startsWith("audio/")||e.mime==="application/pdf"||e.mime.startsWith("text/")||[".json",".md",".py",".js",".ts",".tsx",".jsx",".css",".html",".xml",".sql",".sh"].some(x=>e.name.toLowerCase().endsWith(x)))}
function renderCrumbs(){const c=$("#crumbs");c.innerHTML="";let b=document.createElement("button");b.className="crumb "+(!S.path?"current":"");b.textContent="Home";b.onclick=()=>load("");c.append(b);let a="";for(const part of S.path.split("/").filter(Boolean)){let sep=document.createElement("span");sep.textContent="/";sep.style.color="#526a82";c.append(sep);a=a?a+"/"+part:part;let q=document.createElement("button");q.className="crumb";q.textContent=part;const p=a;q.onclick=()=>load(p);c.append(q)}}
function render(){const l=$("#list");if(!S.entries.length){l.innerHTML='<div class="empty"><h3>Nothing here</h3><p>Upload files, create a folder, or change your search.</p></div>'}else{l.innerHTML=S.entries.map(e=>`<div class="row" data-path="${esc(e.path)}"><div><input type="checkbox" data-check ${S.selected.has(e.path)?"checked":""}></div><div class="name" data-open>${icons(e)}<div style="min-width:0"><div class="title">${esc(e.name)}</div><div class="sub">${S.searching?esc(e.parent||""):(e.is_dir?"Folder":fmt(e.size))}</div></div></div><div class="cell size">${e.is_dir?"—":fmt(e.size)}</div><div class="cell modified">${dt(e.modified)}</div><div class="cell type">${esc(e.mime)}</div><div class="rowactions">${!e.is_dir&&canPreview(e)?'<button class="iconbtn" title="Preview" data-a="preview">◉</button>':''}<button class="iconbtn" title="Download" data-a="download">⇩</button><button class="iconbtn" title="Rename" data-a="rename">✎</button><button class="iconbtn" title="Delete" data-a="delete">🗑</button></div></div>`).join("")}$("#count").textContent=`${S.entries.length} items`}
async function load(path=""){S.path=path;S.searching=false;S.selected.clear();$("#search").value="";try{const d=await api(`/api/list?path=${enc(path)}`);S.entries=d.entries;renderCrumbs();render();$("#title").textContent=path?path.split("/").pop():"Home";$("#desc").textContent=path?"Files and folders in this location.":"Manage your local files from a modern browser workspace."}catch(e){toast(e.message,true)}}
async function search(q){if(!q.trim())return load(S.path);S.searching=true;S.selected.clear();try{const d=await api(`/api/list?search=${enc(q.trim())}`);S.entries=d.entries;renderCrumbs();render();$("#title").textContent="Search";$("#desc").textContent=`Results for “${q.trim()}”`}catch(e){toast(e.message,true)}}
$("#search").oninput=()=>{clearTimeout(window.st);window.st=setTimeout(()=>search($("#search").value),280)};
$("#list").onclick=async e=>{const row=e.target.closest(".row");if(!row)return;const p=row.dataset.path;const a=e.target.closest("[data-a]")?.dataset.a;if(a==="download")return location.href=`/download?path=${enc(p)}`;if(a==="preview")return preview(p);if(a==="delete")return removeItems([p]);if(a==="rename")return renameItem(p);if(e.target.closest("[data-check]"))return;const item=S.entries.find(x=>x.path===p);if(item?.is_dir)return load(p);return canPreview(item)?preview(p):location.href=`/download?path=${enc(p)}`};
$("#list").onchange=e=>{if(!e.target.matches("[data-check]"))return;const p=e.target.closest(".row").dataset.path;if(e.target.checked)S.selected.add(p);else S.selected.delete(p)};
function newFolder(){openForm("Create folder","Create a folder in the current location.","","Create",async name=>{await api("/api/mkdir",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:S.path,name})});$("#formModal").classList.remove("open");toast("Folder created");await load(S.path);stats()})}
function renameItem(path){openForm("Rename","Choose a new name.",path.split("/").pop(),"Rename",async name=>{await api("/api/rename",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path,name})});$("#formModal").classList.remove("open");toast("Renamed");await load(S.searching?"":S.path);stats()})}
async function removeItems(paths){if(!confirm(paths.length===1?"Delete this item?":`Delete ${paths.length} items?`))return;try{await api("/api/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({paths})});toast("Deleted");await load(S.searching?"":S.path);stats()}catch(e){toast(e.message,true)}}
function showTransfer(){$("#transfer").classList.add("show")}
function uploadOne(file,target,label){return new Promise((resolve,reject)=>{const r=document.createElement("div");r.className="trow";r.innerHTML=`<div style="font-size:12px">${esc(label||file.name)}</div><div class="prog"><i></i></div>`;$("#trows").append(r);showTransfer();const xhr=new XMLHttpRequest();xhr.open("POST",`/api/upload?target=${enc(target)}`);xhr.setRequestHeader("X-Filename",encodeURIComponent(file.name));xhr.setRequestHeader("Content-Type","application/octet-stream");xhr.upload.onprogress=e=>{if(e.lengthComputable)r.querySelector("i").style.width=`${e.loaded/e.total*100}%`;$("#tstatus").textContent=`Uploading ${file.name}`};xhr.onload=()=>{if(xhr.status>=200&&xhr.status<300)resolve();else{let m="Upload failed";try{m=JSON.parse(xhr.responseText).error}catch{}reject(Error(m))}};xhr.onerror=()=>reject(Error("Network error"));xhr.send(file)})}
async function uploadFiles(files){const arr=[...files];if(!arr.length)return;$("#trows").innerHTML="";try{for(const f of arr)await uploadOne(f,S.path,f.name);toast(`${arr.length} file(s) uploaded`);await load(S.path);stats()}catch(e){toast(e.message,true)}setTimeout(()=>$("#transfer").classList.remove("show"),1300)}
async function uploadFolder(files){const arr=[...files];if(!arr.length)return;$("#trows").innerHTML="";try{for(const f of arr){const rel=f.webkitRelativePath||f.name;const parts=rel.split("/").filter(Boolean);parts.pop();const nested=parts.join("/");const target=S.path?(nested?S.path+"/"+nested:S.path):nested;if(target)await api("/api/mkdir",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:"",name:target})}).catch(()=>{});await uploadOne(f,target,rel)}toast("Folder uploaded");await load(S.path);stats()}catch(e){toast(e.message,true)}setTimeout(()=>$("#transfer").classList.remove("show"),1300)}
async function preview(path){const e=S.entries.find(x=>x.path===path);const u=`/raw?path=${enc(path)}`;$("#pTitle").textContent=e.name;let b="";if(e.mime.startsWith("image/"))b=`<img class="preview" src="${u}">`;else if(e.mime.startsWith("video/"))b=`<video class="video" controls autoplay playsinline preload="metadata"><source src="${u}" type="${esc(e.mime)}"></video>`;else if(e.mime.startsWith("audio/"))b=`<audio class="audio" controls src="${u}"></audio>`;else if(e.mime==="application/pdf")b=`<iframe class="frame" src="${u}"></iframe>`;else{const r=await fetch(u);const t=await r.text();b=`<pre class="code">${esc(t)}</pre>`}$("#pBody").innerHTML=b;$("#previewModal").classList.add("open")}
async function stats(){try{const d=await api("/api/stats");$("#useText").textContent=`${d.used_human} used · ${d.free_human} free`;$("#useBar").style.width=`${d.percent}%`;$("#root").textContent=d.root}catch{}}
$("#upFiles").onclick=()=>$("#fileInput").click();$("#upSide").onclick=()=>$("#fileInput").click();$("#fileInput").onchange=e=>{uploadFiles(e.target.files);e.target.value=""};$("#upFolder").onclick=()=>$("#folderInput").click();$("#folderInput").onchange=e=>{uploadFolder(e.target.files);e.target.value=""};$("#newFolder").onclick=newFolder;$("#newSide").onclick=newFolder;$("#home").onclick=()=>load("");$("#refresh").onclick=()=>load(S.searching?"":S.path);$("#topRefresh").onclick=()=>load(S.searching?"":S.path);$("#menu").onclick=()=>$("#side").classList.toggle("open");$("#downloadHere").onclick=()=>location.href=`/download?path=${enc(S.path)}`;$("#downloadSelected").onclick=()=>{const paths=[...S.selected];if(!paths.length)return toast("Select items first",true);fetch("/api/download-bundle",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({paths})}).then(async r=>{if(!r.ok)throw Error((await r.json()).error);return r.blob()}).then(b=>{const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="orbit-share-selection.zip";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}).catch(e=>toast(e.message,true))};$("#fCancel").onclick=()=>$("#formModal").classList.remove("open");$("#fSubmit").onclick=()=>{const n=$("#fInput").value.trim();if(n)S.action(n).catch(e=>toast(e.message,true))};$("#fInput").onkeydown=e=>{if(e.key==="Enter")$("#fSubmit").click();if(e.key==="Escape")$("#formModal").classList.remove("open")};$("#pClose").onclick=()=>$("#previewModal").classList.remove("open");$("#previewModal").onclick=e=>{if(e.target.id==="previewModal")e.target.classList.remove("open")};const drop=$("#drop");["dragenter","dragover"].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.add("drag")}));["dragleave","drop"].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.remove("drag")}));drop.ondrop=e=>uploadFiles(e.dataTransfer.files);load("");stats();
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = f"OrbitShare/{VERSION}"

    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def fail(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status)

    def root(self) -> Path:
        return self.server.root

    def resolve(self, rel: str = "", allow_missing: bool = False) -> Path:
        rel = urllib.parse.unquote(rel or "").replace("\\", "/").strip("/")
        if any(part == ".." for part in rel.split("/")):
            raise PermissionError("Path traversal is not allowed.")
        target = self.root().joinpath(*[p for p in rel.split("/") if p and p != "."])
        if allow_missing:
            if not safe_inside(self.root(), target.parent.resolve()):
                raise PermissionError("Path escapes the served directory.")
            return target
        target = target.resolve()
        if not safe_inside(self.root(), target):
            raise PermissionError("Path escapes the served directory.")
        return target

    def rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.root()).as_posix()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self.index()
            elif parsed.path == "/api/list":
                self.listing(q)
            elif parsed.path == "/api/stats":
                self.stats()
            elif parsed.path == "/download":
                self.download(q)
            elif parsed.path == "/raw":
                self.raw(q)
            else:
                self.fail(404, "Not found.")
        except PermissionError as e:
            self.fail(403, str(e))
        except FileNotFoundError:
            self.fail(404, "File or folder not found.")
        except Exception as e:
            self.fail(500, f"Server error: {e}")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/api/upload":
                self.upload(q)
            elif parsed.path == "/api/mkdir":
                self.mkdir()
            elif parsed.path == "/api/rename":
                self.rename()
            elif parsed.path == "/api/delete":
                self.delete()
            elif parsed.path == "/api/download-bundle":
                self.bundle()
            else:
                self.fail(404, "Not found.")
        except PermissionError as e:
            self.fail(403, str(e))
        except ValueError as e:
            self.fail(400, str(e))
        except FileNotFoundError:
            self.fail(404, "File or folder not found.")
        except Exception as e:
            self.fail(500, f"Server error: {e}")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 10 * 1024 * 1024:
            raise ValueError("Request is too large.")
        return json.loads(self.rfile.read(length).decode()) if length else {}

    def index(self) -> None:
        body = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def entry(self, p: Path) -> dict:
        st = p.stat()
        directory = p.is_dir()
        return {"name": p.name, "path": self.rel(p), "parent": self.rel(p.parent), "is_dir": directory, "size": 0 if directory else st.st_size, "modified": st.st_mtime, "mime": "inode/directory" if directory else get_mime(p)}

    def listing(self, q: dict) -> None:
        search = q.get("search", [""])[0].strip().lower()
        if search:
            results = []
            for base, dirs, files in os.walk(self.root(), followlinks=False):
                basep = Path(base)
                dirs[:] = [d for d in dirs if not (basep / d).is_symlink()]
                for name in dirs + files:
                    if search not in name.lower():
                        continue
                    p = basep / name
                    try:
                        results.append(self.entry(p))
                    except OSError:
                        pass
                    if len(results) >= 2000:
                        break
                if len(results) >= 2000:
                    break
            self.send_json({"root": str(self.root()), "entries": results})
            return
        folder = self.resolve(q.get("path", [""])[0])
        if not folder.is_dir():
            raise ValueError("Path is not a directory.")
        items = []
        for p in sorted(folder.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                if p.is_symlink() and not safe_inside(self.root(), p.resolve()):
                    continue
                items.append(self.entry(p))
            except OSError:
                pass
        self.send_json({"root": str(self.root()), "entries": items})

    def stats(self) -> None:
        u = shutil.disk_usage(self.root())
        used = u.total - u.free
        self.send_json({"root": str(self.root()), "used": used, "free": u.free, "total": u.total, "percent": round(used / u.total * 100, 1) if u.total else 0, "used_human": human(used), "free_human": human(u.free)})

    def parse_range(self, header: str, size: int):
        if not header or not header.startswith("bytes="):
            return None
        spec = header[6:].split(",", 1)[0].strip()
        if "-" not in spec:
            return None
        a, b = spec.split("-", 1)
        try:
            if not a:
                length = int(b)
                if length <= 0:
                    return None
                start, end = max(0, size - length), size - 1
            else:
                start = int(a)
                end = int(b) if b else size - 1
                if start >= size:
                    return None
                end = min(end, size - 1)
            return start, end
        except ValueError:
            return None

    def send_file(self, path: Path, attachment: bool) -> None:
        size = path.stat().st_size
        mime = get_mime(path)
        rng = self.parse_range(self.headers.get("Range", ""), size)
        filename = urllib.parse.quote(path.name, safe="")
        cd = f"{'attachment' if attachment else 'inline'}; filename*=UTF-8''{filename}"
        if rng:
            start, end = rng
            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", cd)
            self.end_headers()
            with path.open("rb") as f:
                f.seek(start)
                remaining = length
                while remaining:
                    data = f.read(min(CHUNK, remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", cd)
        self.end_headers()
        with path.open("rb") as f:
            while True:
                data = f.read(CHUNK)
                if not data:
                    break
                self.wfile.write(data)

    def download(self, q: dict) -> None:
        target = self.resolve(q.get("path", [""])[0])
        if target.is_dir():
            self.download_dir(target)
        else:
            self.send_file(target, True)

    def raw(self, q: dict) -> None:
        target = self.resolve(q.get("path", [""])[0])
        if not target.is_file():
            raise ValueError("Only files can be previewed.")
        self.send_file(target, False)

    def zip_tree(self, source: Path, dest: Path, selected_name: str | None = None) -> None:
        root_name = selected_name or source.name
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            if source.is_file():
                zf.write(source, root_name)
                return
            count = 0
            for base, dirs, files in os.walk(source, followlinks=False):
                bp = Path(base)
                dirs[:] = [d for d in dirs if not (bp / d).is_symlink()]
                for name in files:
                    p = bp / name
                    if p.is_symlink():
                        continue
                    zf.write(p, (Path(root_name) / p.relative_to(source)).as_posix())
                    count += 1
            if count == 0:
                zf.writestr(root_name.rstrip("/") + "/", "")

    def download_dir(self, directory: Path) -> None:
        fd, name = tempfile.mkstemp(prefix="orbit-", suffix=".zip")
        os.close(fd)
        z = Path(name)
        try:
            self.zip_tree(directory, z)
            size = z.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", f'attachment; filename="{directory.name}.zip"')
            self.end_headers()
            with z.open("rb") as f:
                while True:
                    data = f.read(CHUNK)
                    if not data:
                        break
                    self.wfile.write(data)
        finally:
            z.unlink(missing_ok=True)

    def upload(self, q: dict) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("Empty upload.")
        if length > self.server.max_upload:
            self.fail(413, f"Maximum upload size is {human(self.server.max_upload)}.")
            return
        folder = self.resolve(q.get("target", [""])[0])
        folder.mkdir(parents=True, exist_ok=True)
        if not folder.is_dir():
            raise ValueError("Upload target is not a folder.")
        filename = self.headers.get("X-Filename")
        if not filename:
            raise ValueError("Missing X-Filename header.")
        filename = clean_name(urllib.parse.unquote(filename))
        dest = unique_path(folder / filename)
        fd, temp_name = tempfile.mkstemp(prefix=".orbit-upload-", dir=str(folder))
        os.close(fd)
        temp = Path(temp_name)
        try:
            remaining = length
            with temp.open("wb") as f:
                while remaining:
                    data = self.rfile.read(min(CHUNK, remaining))
                    if not data:
                        raise ConnectionError("Upload ended before all bytes arrived.")
                    f.write(data)
                    remaining -= len(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, dest)
            temp = None
            self.send_json({"success": True, "path": self.rel(dest), "size": length}, 201)
        finally:
            if temp:
                temp.unlink(missing_ok=True)

    def mkdir(self) -> None:
        d = self.read_json()
        base = str(d.get("path", ""))
        name = str(d.get("name", "")).replace("\\", "/").strip("/")
        if not name:
            raise ValueError("Folder name is required.")
        if "/" in name:
            target = self.resolve(f"{base}/{name}" if base else name, True)
        else:
            target = self.resolve(base) / clean_name(name)
        if target.exists():
            raise ValueError("An item with that name already exists.")
        target.mkdir(parents=True, exist_ok=False)
        self.send_json({"success": True, "path": self.rel(target)}, 201)

    def rename(self) -> None:
        d = self.read_json()
        source = self.resolve(str(d.get("path", "")))
        if source == self.root():
            raise PermissionError("The served root cannot be renamed.")
        target = source.parent / clean_name(str(d.get("name", "")))
        if target.exists():
            raise ValueError("An item with that name already exists.")
        source.rename(target)
        self.send_json({"success": True, "path": self.rel(target)})

    def delete(self) -> None:
        d = self.read_json()
        paths = d.get("paths", [])
        if not isinstance(paths, list) or not paths:
            raise ValueError("No items selected.")
        deleted = []
        for rel in paths:
            target = self.resolve(str(rel))
            if target == self.root():
                raise PermissionError("The served root cannot be deleted.")
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            deleted.append(str(rel))
        self.send_json({"success": True, "deleted": deleted})

    def bundle(self) -> None:
        d = self.read_json()
        paths = d.get("paths", [])
        if not paths:
            raise ValueError("No items selected.")
        fd, name = tempfile.mkstemp(prefix="orbit-selection-", suffix=".zip")
        os.close(fd)
        z = Path(name)
        used = set()
        try:
            with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for rel in paths:
                    src = self.resolve(str(rel))
                    if not src.exists():
                        continue
                    top = src.name
                    if top in used:
                        i = 1
                        while f"{src.stem} ({i}){src.suffix}" in used:
                            i += 1
                        top = f"{src.stem} ({i}){src.suffix}"
                    used.add(top)
                    if src.is_dir():
                        found = False
                        for base, dirs, files in os.walk(src, followlinks=False):
                            bp = Path(base)
                            dirs[:] = [x for x in dirs if not (bp / x).is_symlink()]
                            for fn in files:
                                p = bp / fn
                                if p.is_symlink():
                                    continue
                                archive.write(p, (Path(top) / p.relative_to(src)).as_posix())
                                found = True
                        if not found:
                            archive.writestr(top + "/", "")
                    else:
                        archive.write(src, top)
            size = z.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", 'attachment; filename="orbit-share-selection.zip"')
            self.end_headers()
            with z.open("rb") as f:
                while True:
                    data = f.read(CHUNK)
                    if not data:
                        break
                    self.wfile.write(data)
        finally:
            z.unlink(missing_ok=True)


class Server(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, root: Path, max_upload: int):
        super().__init__(address, Handler)
        self.root = root.resolve()
        self.max_upload = max_upload


def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main() -> None:
    p = argparse.ArgumentParser(description="Orbit Share - local file server")
    p.add_argument("folder", nargs="?", help="Folder to serve")
    p.add_argument("--dir", dest="directory", help="Folder to serve")
    p.add_argument("--host", default="127.0.0.1", help="Bind address; use 0.0.0.0 for LAN")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--max-upload", type=parse_size, default=MAX_DEFAULT)
    p.add_argument("--no-open", action="store_true")
    args = p.parse_args()
    root = Path(args.directory or args.folder or ".").expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Folder does not exist: {root}")
    server = Server((args.host, args.port), root, args.max_upload)
    shown = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    local_url = f"http://{shown}:{args.port}/"
    print("\n" + "=" * 58)
    print(f" {APP_NAME} {VERSION}")
    print("=" * 58)
    print(f" Served folder : {root}")
    print(f" Local URL     : {local_url}")
    print(f" LAN URL       : http://{lan_ip()}:{args.port}/")
    print(f" Bind          : {args.host}")
    print(f" Port          : {args.port}")
    print(f" Upload limit  : {human(args.max_upload)} per file")
    print("=" * 58)
    print(" Press Ctrl+C to stop.\n")
    if not args.no_open:
        threading.Timer(0.5, lambda: webbrowser.open(local_url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Orbit Share...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
