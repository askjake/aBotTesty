#!/usr/bin/env python3
"""install_vlm_control_v2.py - Upgrade VLM Control GUI to comprehensive v2.

Replaces the /vlm_control page with a full-featured model management dashboard.
"""
from __future__ import annotations

import py_compile
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

PATCH_MARKER = "# vlm-control-v2-20260624"


VLM_CONTROL_V2_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VLM Model Control - aBotTesty</title>
<style>
:root{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#e5edf5;--muted:#8b949e;--blue:#2563eb;--green:#22c55e;--amber:#d97706;--red:#dc2626;--radius:14px}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;line-height:1.5}
a{color:#93c5fd;text-decoration:none}a:hover{text-decoration:underline}
header{padding:14px 20px;background:#151b23;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border)}
header h1{font-size:1.1rem;font-weight:700}
.nav{display:flex;gap:14px;font-size:0.85rem}
main{max-width:1480px;margin:0 auto;padding:16px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:1100px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;position:relative}
.card h2{font-size:0.95rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px}
.full-width{grid-column:1/-1}
button{background:var(--blue);color:white;border:0;border-radius:10px;padding:8px 14px;margin:3px;cursor:pointer;font-weight:600;font-size:0.82rem;transition:opacity .15s}
button:hover{opacity:0.85}button:active{opacity:0.7}
button.green{background:var(--green);color:#000}
button.amber{background:var(--amber);color:#000}
button.red{background:var(--red)}
button.ghost{background:transparent;border:1px solid var(--border);color:var(--text)}
input,select,textarea{background:#0b1016;color:var(--text);border:1px solid #3b4450;border-radius:8px;padding:8px 10px;font-size:0.85rem;width:100%}
select{cursor:pointer}
label{display:flex;align-items:center;gap:6px;font-size:0.85rem;margin:4px 0}
label input[type="checkbox"]{width:auto}
pre{white-space:pre-wrap;word-break:break-word;color:#b6c2cf;max-height:400px;overflow:auto;font-size:0.78rem;background:#0b1016;border-radius:8px;padding:10px;margin-top:8px}
.pill{display:inline-block;border-radius:999px;padding:3px 10px;font-size:0.75rem;font-weight:600}
.pill-green{background:#16a34a22;color:var(--green);border:1px solid #16a34a55}
.pill-amber{background:#d9770622;color:var(--amber);border:1px solid #d9770655}
.pill-red{background:#dc262622;color:var(--red);border:1px solid #dc262655}
.pill-blue{background:#2563eb22;color:#60a5fa;border:1px solid #2563eb55}
.pill-gray{background:#37415122;color:var(--muted);border:1px solid #37415155}
.status-banner{padding:12px 16px;border-radius:var(--radius);margin-bottom:12px;display:flex;align-items:center;gap:12px}
.status-banner.ok{background:#16a34a18;border:1px solid #16a34a44}
.status-banner.warn{background:#d9770618;border:1px solid #d9770644}
.status-banner.err{background:#dc262618;border:1px solid #dc262644}
.status-banner .dot{width:12px;height:12px;border-radius:50%;flex-shrink:0}
.status-banner.ok .dot{background:var(--green);box-shadow:0 0 8px var(--green)}
.status-banner.warn .dot{background:var(--amber);box-shadow:0 0 8px var(--amber)}
.status-banner.err .dot{background:var(--red);box-shadow:0 0 8px var(--red)}
.kv{display:grid;grid-template-columns:140px 1fr;gap:4px 12px;font-size:0.82rem;margin:8px 0}
.kv dt{color:var(--muted)}
.kv dd{font-weight:500}
table{border-collapse:collapse;width:100%;font-size:0.78rem}
th,td{border-bottom:1px solid var(--border);padding:6px 8px;text-align:left}
th{color:var(--muted);font-weight:600;text-transform:uppercase;font-size:0.7rem;letter-spacing:0.5px}
tr:hover{background:#1f293755}
tr.active-row{background:#16a34a12;border-left:3px solid var(--green)}
tr.clickable{cursor:pointer}
.slider-wrap{display:flex;align-items:center;gap:8px;margin:4px 0}
.slider-wrap input[type="range"]{flex:1;height:6px;-webkit-appearance:none;appearance:none;background:#374151;border-radius:3px;outline:none;cursor:pointer}
.slider-wrap input[type="range"]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:var(--blue)}
.slider-val{width:40px;text-align:center;font-size:0.82rem;color:var(--muted)}
.mode-btns{display:flex;gap:4px;flex-wrap:wrap}
.mode-btns button{padding:8px 14px;font-size:0.82rem;border-radius:8px}
.mode-btns button.active-mode{outline:2px solid var(--green);outline-offset:2px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:700px){.grid-2{grid-template-columns:1fr}}
.progress-bar{height:6px;background:#374151;border-radius:3px;overflow:hidden;margin:4px 0}
.progress-bar .fill{height:100%;background:var(--green);border-radius:3px;transition:width .3s}
.toast{position:fixed;bottom:20px;right:20px;background:#1f2937;border:1px solid var(--border);border-radius:10px;padding:12px 18px;font-size:0.85rem;z-index:9999;opacity:0;transition:opacity .3s}
.toast.show{opacity:1}
.refresh-indicator{position:absolute;top:10px;right:14px;font-size:0.7rem;color:var(--muted)}
</style>
</head>
<body>
<header>
  <h1>VLM Model Control</h1>
  <div class="nav">
    <a href="/learning">learning</a>
    <a href="/monitor">monitor</a>
    <a href="/intelligence">intelligence</a>
    <a href="/dashboards">dashboards</a>
  </div>
</header>

<main>
<!-- ACTIVE MODEL STATUS -->
<section class="card full-width" id="active-section">
  <h2>Active Model &amp; Server Status</h2>
  <div id="status-banner" class="status-banner err">
    <div class="dot"></div>
    <div id="status-text">Loading...</div>
  </div>
  <div class="grid-2">
    <dl class="kv" id="model-info">
      <dt>Active run</dt><dd id="kv-active-run">-</dd>
      <dt>Base model</dt><dd id="kv-base-model">-</dd>
      <dt>Adapter</dt><dd id="kv-adapter">-</dd>
      <dt>Server</dt><dd id="kv-server-url">-</dd>
      <dt>Uptime</dt><dd id="kv-uptime">-</dd>
    </dl>
    <dl class="kv" id="policy-stats">
      <dt>Mode</dt><dd id="kv-mode">-</dd>
      <dt>Enabled</dt><dd id="kv-enabled">-</dd>
      <dt>Calls</dt><dd id="kv-calls">0</dd>
      <dt>Accepted</dt><dd id="kv-accepted">0</dd>
      <dt>Rejected</dt><dd id="kv-rejected">0</dd>
      <dt>Errors</dt><dd id="kv-errors">0</dd>
    </dl>
  </div>
  <div style="margin-top:8px">
    <button onclick="refreshAll()">&#8635; Refresh all</button>
    <button class="ghost" onclick="healthCheck()">Health check</button>
  </div>
  <span class="refresh-indicator" id="last-refresh">-</span>
</section>

<!-- MODE & POLICY CONTROL -->
<section class="card">
  <h2>Policy Mode &amp; Safety</h2>
  <p style="font-size:0.8rem;color:var(--muted);margin-bottom:10px">
    <b>Shadow:</b> logs suggestions only &middot; <b>Assist:</b> reorders crawler actions &middot; <b>Autonomous:</b> chooses action from allowed list
  </p>
  <div class="mode-btns" id="mode-btns">
    <button data-mode="off" class="ghost" onclick="setMode('off')">Off</button>
    <button data-mode="shadow" onclick="setMode('shadow')">Shadow</button>
    <button data-mode="assist" class="amber" onclick="setMode('assist')">Assist</button>
    <button data-mode="autonomous" class="red" onclick="setMode('autonomous')">Autonomous</button>
  </div>
  <div style="margin-top:12px">
    <label><input id="ctl-enabled" type="checkbox" onchange="saveConfig()"> Enabled (policy active)</label>
    <label><input id="ctl-allow-select" type="checkbox" onchange="saveConfig()"> Allow SELECT key</label>
  </div>
  <div style="margin-top:12px">
    <div class="slider-wrap">
      <span style="font-size:0.78rem;color:var(--muted);min-width:100px">Min Confidence</span>
      <input type="range" id="ctl-confidence" min="0" max="1" step="0.05" value="0.65" oninput="updSlider(this)">
      <span class="slider-val" id="ctl-confidence-val">0.65</span>
    </div>
    <div class="slider-wrap">
      <span style="font-size:0.78rem;color:var(--muted);min-width:100px">Max Risk</span>
      <input type="range" id="ctl-risk" min="0" max="1" step="0.05" value="0.35" oninput="updSlider(this)">
      <span class="slider-val" id="ctl-risk-val">0.35</span>
    </div>
  </div>
  <div style="margin-top:8px">
    <button onclick="saveConfig()">Save config</button>
    <button class="ghost" onclick="testPolicy()">Test policy (current screen)</button>
  </div>
  <pre id="policy-out" style="max-height:200px">ready</pre>
</section>

<!-- AVAILABLE RUNS + PROMOTE -->
<section class="card">
  <h2>Available Training Runs</h2>
  <div style="margin-bottom:8px">
    <button onclick="loadRuns()">&#8635; Reload runs</button>
    <span style="font-size:0.75rem;color:var(--muted);margin-left:8px" id="runs-count">-</span>
  </div>
  <div style="max-height:320px;overflow:auto">
    <table id="runs-table">
      <thead><tr><th>Run</th><th>Status</th><th>Loss</th><th>Steps</th><th>Rows</th><th>Active</th></tr></thead>
      <tbody id="runs-tbody"></tbody>
    </table>
  </div>
  <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
    <div style="font-size:0.82rem;margin-bottom:6px"><b>Selected run:</b> <span id="selected-run-name" style="color:#60a5fa">none</span></div>
    <div id="selected-run-detail" style="font-size:0.78rem;color:var(--muted)"></div>
    <div style="margin-top:8px">
      <button class="green" onclick="promoteSelected()" id="btn-promote" disabled>Promote &amp; Restart Shadow Server</button>
      <button class="ghost" onclick="pullSelected()" id="btn-pull" disabled>Pull adapter local only</button>
    </div>
  </div>
  <pre id="promote-out" style="max-height:160px">ready</pre>
</section>

<!-- LIVE TRAINING PROGRESS -->
<section class="card full-width">
  <h2>Live Training Progress</h2>
  <div id="train-status" style="font-size:0.85rem;margin-bottom:8px">Checking...</div>
  <div class="progress-bar"><div class="fill" id="train-progress" style="width:0%"></div></div>
  <div class="grid-2" style="margin-top:8px">
    <dl class="kv" id="train-kv">
      <dt>Run name</dt><dd id="train-run">-</dd>
      <dt>Step</dt><dd id="train-step">-</dd>
      <dt>Loss</dt><dd id="train-loss">-</dd>
      <dt>ETA</dt><dd id="train-eta">-</dd>
    </dl>
    <pre id="train-log-tail" style="max-height:140px;font-size:0.72rem">-</pre>
  </div>
  <button class="ghost" onclick="refreshTraining()">&#8635; Refresh training</button>
</section>

<!-- PROMOTION HISTORY -->
<section class="card full-width">
  <h2>Promotion History</h2>
  <table id="history-table">
    <thead><tr><th>Date</th><th>Run</th><th>Loss</th><th>Rows</th><th>Status</th></tr></thead>
    <tbody id="history-tbody"></tbody>
  </table>
</section>
</main>

<div class="toast" id="toast"></div>

<script>
const $=id=>document.getElementById(id);
let RUNS=[];
let SELECTED_RUN=null;
let CURRENT_STATE={};
let AUTO_REFRESH=null;

function toast(msg,ms=3000){const t=$('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),ms)}
async function api(url,body=null){const opt=body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{};try{const r=await fetch(url,opt);return await r.json()}catch(e){return{ok:false,error:e.message}}}
function updSlider(el){$(el.id+'-val').textContent=parseFloat(el.value).toFixed(2)}
function fmtUptime(s){if(!s)return'-';const d=Math.floor(s/86400),h=Math.floor((s%86400)/3600),m=Math.floor((s%3600)/60);return d>0?d+'d '+h+'h '+m+'m':h>0?h+'h '+m+'m':m+'m'}

async function refreshStatus(){
  const j=await api('/api/vlm/status');
  if(!j.ok){$('status-text').textContent='Error: '+(j.error||'unknown');return}
  const st=j.state||{};const h=j.health||{};CURRENT_STATE=st;
  const banner=$('status-banner');
  if(h.ok&&st.enabled){banner.className='status-banner ok';$('status-text').innerHTML='<b>Active</b> - Shadow server healthy, policy <b>'+st.mode+'</b> mode'}
  else if(h.ok&&!st.enabled){banner.className='status-banner warn';$('status-text').innerHTML='<b>Server OK</b> but policy is <b>disabled</b>. Enable to start VLM-guided exploration.'}
  else{banner.className='status-banner err';$('status-text').innerHTML='<b>Server unreachable</b> - '+(h.error||'connection failed').substring(0,120)}
  $('kv-active-run').textContent=st.active_run||'(none)';
  $('kv-base-model').textContent=st.base_model||'-';
  $('kv-adapter').textContent=st.active_adapter_path?st.active_adapter_path.split('/').slice(-2).join('/'):('(none)');
  $('kv-server-url').textContent=st.server_url||'-';
  $('kv-uptime').textContent=h.ok?fmtUptime(h.uptime_s):'-';
  $('kv-mode').innerHTML='<span class="pill pill-'+(st.mode==='autonomous'?'red':st.mode==='assist'?'amber':st.mode==='shadow'?'blue':'gray')+'">'+( st.mode||'off')+'</span>';
  $('kv-enabled').innerHTML=st.enabled?'<span class="pill pill-green">yes</span>':'<span class="pill pill-red">no</span>';
  const s=st.stats||{};$('kv-calls').textContent=s.calls||0;$('kv-accepted').textContent=s.accepted||0;$('kv-rejected').textContent=s.rejected||0;$('kv-errors').textContent=s.errors||0;
  $('ctl-enabled').checked=!!st.enabled;$('ctl-allow-select').checked=!!st.allow_select;
  $('ctl-confidence').value=st.min_confidence??0.65;$('ctl-confidence-val').textContent=(st.min_confidence??0.65).toFixed(2);
  $('ctl-risk').value=st.max_risk??0.35;$('ctl-risk-val').textContent=(st.max_risk??0.35).toFixed(2);
  setModeButtons(st.mode||'shadow');
  $('last-refresh').textContent='Updated '+new Date().toLocaleTimeString();
}

function setModeButtons(active){document.querySelectorAll('.mode-btns button').forEach(b=>{b.classList.toggle('active-mode',b.dataset.mode===active)})}
async function setMode(mode){await saveConfigWith({mode})}
async function saveConfig(){await saveConfigWith({})}
async function saveConfigWith(extra){
  const body={enabled:$('ctl-enabled').checked,allow_select:$('ctl-allow-select').checked,min_confidence:parseFloat($('ctl-confidence').value),max_risk:parseFloat($('ctl-risk').value),...extra};
  const j=await api('/api/vlm/config',body);
  if(j.ok){toast('Config saved');await refreshStatus()}else{toast('Error: '+(j.error||'unknown'))}
}
async function healthCheck(){const j=await api('/api/vlm/status');$('policy-out').textContent=JSON.stringify(j.health||j,null,2)}
async function testPolicy(){$('policy-out').textContent='testing...';const j=await api('/api/vlm/policy/test',{});$('policy-out').textContent=JSON.stringify(j,null,2)}

async function loadRuns(){
  const j=await api('/api/vlm/runs?limit=40');RUNS=(j.remote_runs||[]);$('runs-count').textContent=RUNS.length+' runs found';
  const tbody=$('runs-tbody');tbody.innerHTML='';
  for(const r of RUNS){
    const m=r.metrics||{};const active=r.is_health_adapter||r.is_active_run;
    const tr=document.createElement('tr');tr.className=(active?'active-row ':'')+'clickable';tr.onclick=()=>selectRun(r);
    const dateStr=r.run_name.replace('abot_vlm_','').replace('abot_vlm_friday_','').substring(0,8);
    tr.innerHTML='<td style="font-family:monospace;font-size:0.72rem">'+r.run_name+'</td><td><span class="pill pill-'+(r.status==='completed'?'green':r.status==='failed'?'red':'gray')+'">'+( r.status||'?')+'</span>'+(r.has_adapter?' &#10003;':'')+'</td><td>'+(m.train_loss!=null?m.train_loss.toFixed(4):'-')+'</td><td>'+(m.total_steps||'-')+'</td><td>'+(r.total_sft_rows||0)+'</td><td>'+(active?'<span class="pill pill-green">ACTIVE</span>':r.is_pulled_local?'local':'')+'</td>';
    tbody.appendChild(tr);
  }
  loadHistory();
}

function selectRun(r){
  SELECTED_RUN=r;$('selected-run-name').textContent=r.run_name;
  const m=r.metrics||{};const d=r.dataset_counts||{};
  $('selected-run-detail').innerHTML='Status: <b>'+r.status+'</b> | Loss: <b>'+(m.train_loss!=null?m.train_loss.toFixed(4):'-')+'</b> | Steps: '+(m.total_steps||'-')+'<br>Dataset: screen='+(d.screen_perception||0)+', policy='+(d.action_policy||0)+', verify='+(d.outcome_verifier||0)+', images='+(d.images||0)+'<br>Adapter: '+(r.has_adapter?'ready ('+r.adapter_size_mb+'MB)':'no adapter')+' | Local: '+(r.is_pulled_local?'yes':'no');
  $('btn-promote').disabled=!r.has_adapter;$('btn-pull').disabled=!r.has_adapter;
}

async function promoteSelected(){
  if(!SELECTED_RUN||!SELECTED_RUN.has_adapter){toast('Select a completed run first');return}
  if(!confirm('Promote '+SELECTED_RUN.run_name+'?\n\nThis will:\n1. Pull adapter locally\n2. Restart the shadow server with this adapter\n3. Set as active run'))return;
  $('promote-out').textContent='Promoting... (pulling adapter + restarting server, may take 1-2 min)';$('btn-promote').disabled=true;
  const j=await api('/api/vlm/adapter/promote',{run_name:SELECTED_RUN.run_name,pull_local:true,restart_shadow:true});
  $('promote-out').textContent=JSON.stringify(j,null,2);$('btn-promote').disabled=false;
  if(j.ok){toast('Promoted successfully! Server restarting...');setTimeout(refreshAll,8000)}else{toast('Promotion failed: '+(j.error||'see log'))}
}

async function pullSelected(){
  if(!SELECTED_RUN||!SELECTED_RUN.has_adapter)return;
  $('promote-out').textContent='Pulling adapter...';$('btn-pull').disabled=true;
  const j=await api('/api/vlm/adapter/pull',{run_name:SELECTED_RUN.run_name});
  $('promote-out').textContent=JSON.stringify(j,null,2);$('btn-pull').disabled=false;
  toast(j.ok?'Pulled!':'Pull failed');
}

async function refreshTraining(){
  const overview=await api('/api/learning/training/overview');
  if(!overview.ok){$('train-status').textContent='Error loading';return}
  const jobs=overview.remote_jobs||[];
  let active=jobs.find(j=>{const s=(j.metrics||{}).status;return s==='running_or_interrupted'||s==='running_or_started'});
  if(!active)active=jobs.find(j=>j.run_name&&(j.metrics||{}).status==='unknown');
  if(!active&&jobs.length)active=jobs[0];
  if(!active){$('train-status').textContent='No active training jobs';return}
  const m=active.metrics||{};const steps=m.total_steps||0;const totalSteps=7326;
  const pct=steps>0?Math.min(100,(steps/totalSteps*100)):0;
  $('train-run').textContent=active.run_name||'-';$('train-step').textContent=steps?steps+'/'+totalSteps:'-';
  $('train-loss').textContent=m.train_loss!=null?m.train_loss.toFixed(4):'-';
  $('train-progress').style.width=pct.toFixed(1)+'%';
  const status=m.status||'unknown';
  if(status==='completed'){$('train-status').innerHTML='<span class="pill pill-green">completed</span> '+active.run_name+' - loss '+(m.train_loss||0).toFixed(4);$('train-eta').textContent='done'}
  else if(steps>0){const etaS=Math.max(0,totalSteps-steps)*16;$('train-status').innerHTML='<span class="pill pill-blue">training</span> '+active.run_name+' - '+pct.toFixed(1)+'%';$('train-eta').textContent=etaS>3600?'~'+(etaS/3600).toFixed(1)+'h':'~'+Math.ceil(etaS/60)+'m'}
  else{$('train-status').innerHTML='<span class="pill pill-gray">'+status+'</span> '+active.run_name;$('train-eta').textContent='-'}
  if(active.run_name){const remoteDir='/home/montjac/aBotTesty_vlm_jobs/'+active.run_name;const tail=await api('/api/learning/remote/tail',{remote_dir:remoteDir,lines:8});if(tail.ok&&tail.text){const lines=tail.text.trim().split('\n').slice(-6);$('train-log-tail').textContent=lines.join('\n')}}
}

function loadHistory(){
  const tbody=$('history-tbody');
  const pulled=RUNS.filter(r=>r.is_pulled_local||r.is_active_run||r.is_health_adapter);
  tbody.innerHTML='';
  if(!pulled.length){tbody.innerHTML='<tr><td colspan="5" style="color:var(--muted)">No promotions recorded yet.</td></tr>';return}
  for(const r of pulled){
    const m=r.metrics||{};const tr=document.createElement('tr');
    tr.className=r.is_health_adapter?'active-row':'';
    tr.innerHTML='<td>'+r.run_name.replace('abot_vlm_','').substring(0,15)+'</td><td style="font-family:monospace;font-size:0.72rem">'+r.run_name+'</td><td>'+(m.train_loss!=null?m.train_loss.toFixed(4):'-')+'</td><td>'+(r.total_sft_rows||0)+'</td><td>'+(r.is_health_adapter?'<span class="pill pill-green">CURRENT</span>':r.is_pulled_local?'pulled':'-')+'</td>';
    tbody.appendChild(tr);
  }
}

async function refreshAll(){await refreshStatus();await loadRuns();await refreshTraining()}
refreshAll();
AUTO_REFRESH=setInterval(refreshAll,30000);
</script>
</body>
</html>
"""


VLM_CONTROL_V2_ROUTE = """
@app.route("/vlm_control")
def vlm_control_page() -> Response:
    return Response(VLM_CONTROL_V2_HTML, mimetype="text/html")
"""


def find_vlm_control_block(text: str):
    """Find the start and end of the existing vlm_control_page function."""
    route_match = re.search(r'^@app\.route\("/vlm_control"\)\s*\n', text, re.M)
    if not route_match:
        return None, None
    start = route_match.start()
    after = text[route_match.end():]
    # Find next route definition
    next_route = re.search(r'^\n\n@app\.route\(', after, re.M)
    if next_route:
        end = route_match.end() + next_route.start()
    else:
        next_def = re.search(r'^\ndef ', after, re.M)
        if next_def:
            end = route_match.end() + next_def.start()
        else:
            return start, None
    return start, end


def patch_merged_app(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")

    if PATCH_MARKER in text:
        print(f"{path.name}: already patched with v2 GUI")
        return False

    start, end = find_vlm_control_block(text)
    if start is None:
        print(f"ERROR: Could not find @app.route(\'/vlm_control\') in {path.name}")
        return False
    if end is None:
        print(f"ERROR: Could not find end of vlm_control_page function")
        return False

    old_block = text[start:end]
    print(f"Found existing vlm_control block at char {start}-{end}")
    print(f"  Old block size: {len(old_block)} chars")

    # Build new block with the HTML variable and route
    new_block = f"\n{PATCH_MARKER}\n\nVLM_CONTROL_V2_HTML = {repr(VLM_CONTROL_V2_HTML)}\n\n{VLM_CONTROL_V2_ROUTE}\n"
    text = text[:start] + new_block + text[end:]

    path.write_text(text, encoding="utf-8")
    print(f"Replaced vlm_control block with v2 GUI ({len(new_block)} chars)")
    return True


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    app_path = root / "merged_app.py"
    if not app_path.is_file():
        print(f"ERROR: merged_app.py not found under {root}", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = app_path.with_name(f"merged_app.py.bak-vlm-control-v2-{stamp}")
    shutil.copy2(app_path, backup)
    print(f"Backup: {backup}")

    if not patch_merged_app(app_path):
        return 1

    # Verify syntax
    try:
        py_compile.compile(str(app_path), doraise=True)
        print(f"py_compile OK: {app_path.name}")
    except py_compile.PyCompileError as exc:
        print(f"SYNTAX ERROR: {exc}")
        print("Restoring backup...")
        shutil.copy2(backup, app_path)
        return 2

    print(f"\nSuccess! The /vlm_control page has been upgraded to v2.")
    print(f"Restart merged_app.py to see the new GUI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
