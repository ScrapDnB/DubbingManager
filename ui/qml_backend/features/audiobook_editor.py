"""Self-contained manuscript surface; native controls remain in QML."""

from __future__ import annotations

import json


CSS = r'''
:root { color-scheme: light dark; --canvas:#fff; --ink:#232323; --muted:#74747b;
 --line:#e5e5e7; --panel:#f6f6f8; --accent:#087aff; --ui:system-ui,sans-serif; }
* { box-sizing:border-box; }
html,body { margin:0; background:var(--canvas); color:var(--ink); }
body { font-family:var(--ui); }
#editor { max-width:940px; min-height:100vh; margin:auto; padding:44px 64px 100px 100px;
 font:18px/1.65 Georgia,serif; outline:none; overflow-wrap:break-word; caret-color:var(--ink); }
#editor p,#editor blockquote,#editor li,#editor div { position:relative; margin:0 0 1.05em;
 text-indent:0!important; line-height:inherit!important; }
#editor h1 { font-size:1.65em!important; font-weight:600; line-height:1.25; margin:0 0 1.45em!important; }
#editor h2,#editor h3 { font-size:1.2em; line-height:1.3; }
#editor span { color:inherit!important; background:transparent!important; }
#editor span[data-dm-character]:not([data-dm-character="Автор"]) {
 text-decoration-line:underline; text-decoration-color:var(--role-color,#c79832);
 text-decoration-thickness:2px; text-underline-offset:5px; }
#editor [data-role-label]::before { content:attr(data-role-label); position:absolute; right:calc(100% + 18px);
 top:.35em; width:68px; text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
 font:11px/1.4 var(--ui); color:var(--role-color,var(--muted)); padding-right:7px;
 border-right:2px solid var(--role-color,var(--line)); user-select:none; pointer-events:none; }
#editor [data-dialogue-issue="true"] { text-decoration:underline dotted #c28627; text-underline-offset:5px; }
::selection { background:#bddbff; color:#161616; }
#floating { display:none; position:fixed; z-index:10; align-items:center; gap:4px; max-width:calc(100vw - 24px);
 padding:4px; border:1px solid var(--line); border-radius:7px; background:var(--panel);
 box-shadow:0 3px 12px #0002; font:12px var(--ui); }
#floating button,#roles button { font:inherit; color:var(--ink); background:transparent; border:0;
 border-radius:4px; padding:5px 9px; cursor:pointer; text-align:left; }
#floating button:hover,#roles button:hover { background:color-mix(in srgb,var(--accent) 12%,transparent); }
#roles { display:none; position:fixed; z-index:11; padding:4px; min-width:190px; border-radius:6px;
 border:1px solid var(--line); background:var(--panel); box-shadow:0 4px 16px #0002; font:12px var(--ui); }
#roles button { display:block; width:100%; }
#empty { color:var(--muted); padding:80px 30px; text-align:center; font:14px var(--ui); }
@media(max-width:620px) { #editor { padding:28px 28px 80px 74px; } #editor [data-role-label]::before { width:52px; right:calc(100% + 10px); font-size:10px; } }
'''

SCRIPT = r'''
let backend=null, savedRange=null, slots=[], palette=[], ready=false;
let undoStack=[], redoStack=[], lastTyped=0, selectionTimer=null;
const editor=document.getElementById('editor'), floating=document.getElementById('floating'), roles=document.getElementById('roles');
const chapter=CHAPTER_TOKEN;
const newId=()=>crypto.randomUUID().replaceAll('-','');
function snapshot() { return {html:editor.innerHTML,scroll:window.scrollY}; }
function remember(group=false) {
 const now=Date.now(); if(!group || now-lastTyped>700) { undoStack.push(snapshot()); if(undoStack.length>100)undoStack.shift(); }
 lastTyped=group?now:0; redoStack=[];
}
function cleanHtml() {
 const clone=editor.cloneNode(true);
 clone.querySelectorAll('*').forEach(n=>{
  [...n.attributes].forEach(a=>{ if(!['data-dm-character','data-dm-actor','data-dm-run-id'].includes(a.name))n.removeAttribute(a.name); });
 });
 return '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'+clone.innerHTML+'</body></html>';
}
function normalizeIds() {
 const seen=new Set();
 editor.querySelectorAll('span[data-dm-run-id]').forEach(n=>{if(!n.dataset.dmRunId||seen.has(n.dataset.dmRunId))n.dataset.dmRunId=newId();seen.add(n.dataset.dmRunId);});
 const walker=document.createTreeWalker(editor,NodeFilter.SHOW_TEXT), nodes=[]; let n;
 while((n=walker.nextNode())) if(n.nodeValue && !n.parentElement.closest('span[data-dm-run-id]'))nodes.push(n);
 nodes.forEach(n=>{const s=document.createElement('span');s.dataset.dmRunId=newId();n.replaceWith(s);s.append(n);});
}
function decorate() {
 const colors=new Map(palette.filter(s=>s.character).map(s=>[s.character,s.color]));
 editor.querySelectorAll('span[data-dm-character]').forEach(n=>n.style.setProperty('--role-color',colors.get(n.dataset.dmCharacter)||'#b38b32'));
 editor.querySelectorAll('p,blockquote,li').forEach(p=>{
  const first=p.querySelector('span'), role=first?.dataset.dmCharacter||'Автор';
  p.dataset.roleLabel=role; p.style.setProperty('--role-color',colors.get(role)|| (role==='Автор'?'#5285b6':'#b38b32'));
  p.dataset.dialogueIssue=String(role==='Автор' && /^[—–]\s*\S/.test(p.textContent.trim()));
 });
}
function segments() {
 return [...editor.querySelectorAll('p,blockquote,li,h1,h2,h3')].flatMap(p=>{
  const walker=document.createTreeWalker(p,NodeFilter.SHOW_TEXT), out=[];let n;
  while((n=walker.nextNode())) { const c=n.parentElement.closest('[data-dm-character]')?.dataset.dmCharacter||'Автор';
   if(out.length&&out.at(-1).character===c)out.at(-1).text+=n.nodeValue;else out.push({character:c,text:n.nodeValue}); }
  return out.filter(x=>x.text.trim());
 });
}
function sendState() { if(backend&&ready)backend.updateState(cleanHtml(),JSON.stringify(segments()),chapter); }
function restoreRange() {
 if(!savedRange||!editor.contains(savedRange.commonAncestorContainer))return null;
 const s=getSelection();s.removeAllRanges();s.addRange(savedRange);return savedRange;
}
function hideFloating() { floating.style.display='none'; roles.style.display='none'; }
function updateSelection() {
 const s=getSelection();
 if(s.rangeCount&&editor.contains(s.anchorNode)&&editor.contains(s.focusNode))savedRange=s.getRangeAt(0).cloneRange();
 const range=savedRange;
 const valid=range&&editor.contains(range.commonAncestorContainer)&&!range.collapsed;
 const text=valid?range.toString().trim():'';
 const node=valid?(range.startContainer.nodeType===3?range.startContainer.parentElement:range.startContainer):null;
 const role=node?.closest('[data-dm-character]')?.dataset.dmCharacter||'Автор';
 if(backend)backend.updateSelection(JSON.stringify({text,words:text?text.split(/\s+/u).length:0,character:role,canUndo:undoStack.length>0,canRedo:redoStack.length>0}),chapter);
 if(!text || document.activeElement!==editor) { if(!roles.contains(document.activeElement))hideFloating();return; }
 const rect=range.getBoundingClientRect();
 if(rect.bottom<0||rect.top>innerHeight){hideFloating();return;}
 floating.style.display='flex';
 document.getElementById('choose-role').textContent=role+' ▾';
 floating.style.left=Math.max(8,Math.min(innerWidth-floating.offsetWidth-8,rect.left))+'px';
 floating.style.top=Math.max(8,Math.min(innerHeight-floating.offsetHeight-8,rect.top-floating.offsetHeight-8))+'px';
}
function changed() { normalizeIds(); decorate(); sendState(); updateSelection(); }
function applyMarkup(character,actorId,color) {
 const range=restoreRange();if(!range||range.collapsed||!character)return false;
 const walker=document.createTreeWalker(editor,NodeFilter.SHOW_TEXT), nodes=[];let n;
 while((n=walker.nextNode()))if(range.intersectsNode(n)){
  const start=n===range.startContainer?range.startOffset:0, end=n===range.endContainer?range.endOffset:n.length;
  if(end>start)nodes.push({node:n,start,end});
 }
 if(!nodes.length)return false; remember();
 const marked=[];
 nodes.forEach(({node,start,end})=>{
  if(end<node.length)node.splitText(end);
  const selected=start?node.splitText(start):node;
  const span=document.createElement('span');span.dataset.dmCharacter=character;
  span.dataset.dmActor=actorId||'';span.dataset.dmRunId=newId();
  selected.replaceWith(span);span.append(selected);marked.push(span);
 });
 const next=document.createRange();next.setStartBefore(marked[0]);next.setEndAfter(marked.at(-1));savedRange=next;
 editor.focus();restoreRange();changed();return true;
}
function applySlot(index) { const s=slots[index];return s?.character?applyMarkup(s.character,s.actorId,s.color):false; }
function clearMarkup(){return applyMarkup('Автор','','');}
function setSlots(value,allRoles) {
 slots=value||[];palette=allRoles||slots;decorate();roles.replaceChildren();
 palette.forEach(s=>{if(!s.character)return;const b=document.createElement('button');b.textContent=(s.slotIndex>=0?(s.slotIndex+1)+'  ':'')+s.character;b.onclick=()=>{applyMarkup(s.character,s.actorId,s.color);roles.style.display='none';};roles.append(b);});
}
function setPresentation(family,zoom,dark) {
 editor.style.fontFamily=family||'Georgia';editor.style.fontSize=(18*(1+zoom*.1))+'px';
 const vars=dark?{'--canvas':'#222326','--ink':'#e8e8ea','--muted':'#a5a5ac','--line':'#44464c','--panel':'#303136'}:{'--canvas':'#ffffff','--ink':'#232323','--muted':'#74747b','--line':'#e5e5e7','--panel':'#f6f6f8'};
 Object.entries(vars).forEach(([k,v])=>document.documentElement.style.setProperty(k,v));
}
function focusRun(id,text='') {
 const target=[...editor.querySelectorAll('[data-dm-run-id]')].find(n=>n.dataset.dmRunId===id);
 if(!target)return focusText(text);
 editor.focus();const r=document.createRange();r.selectNodeContents(target);savedRange=r;restoreRange();target.scrollIntoView({block:'center'});updateSelection();return true;
}
function focusText(text) {
 const q=(text||'').toLocaleLowerCase();if(!q)return false;
 const walker=document.createTreeWalker(editor,NodeFilter.SHOW_TEXT);let n;
 while((n=walker.nextNode())) {const at=n.nodeValue.toLocaleLowerCase().indexOf(q);if(at>=0){const r=document.createRange();r.setStart(n,at);r.setEnd(n,at+q.length);savedRange=r;editor.focus();restoreRange();n.parentElement.scrollIntoView({block:'center'});updateSelection();return true;}}
 return false;
}
function undo() {
 if(!undoStack.length)return false;redoStack.push(snapshot());const state=undoStack.pop();
 editor.innerHTML=state.html;savedRange=null;window.scrollTo(0,state.scroll);lastTyped=0;changed();return true;
}
function redo() {
 if(!redoStack.length)return false;undoStack.push(snapshot());const state=redoStack.pop();
 editor.innerHTML=state.html;savedRange=null;window.scrollTo(0,state.scroll);lastTyped=0;changed();return true;
}
editor.addEventListener('beforeinput',e=>{if(e.inputType==='historyUndo'){e.preventDefault();undo();}else if(e.inputType==='historyRedo'){e.preventDefault();redo();}else remember(true);});
editor.addEventListener('input',changed);
editor.addEventListener('paste',e=>{e.preventDefault();document.execCommand('insertText',false,e.clipboardData.getData('text/plain'));});
editor.addEventListener('drop',e=>e.preventDefault());
editor.addEventListener('keydown',e=>{
 if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?redo():undo();return;}
 if(e.ctrlKey&&e.key.toLowerCase()==='y'){e.preventDefault();redo();return;}
 if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='s'){e.preventDefault();if(backend)backend.saveProject();return;}
 if(!e.metaKey&&!e.ctrlKey&&!e.altKey&&/^[1-9]$/.test(e.key)&&savedRange&&!savedRange.collapsed){e.preventDefault();applySlot(Number(e.key)-1);}
 if(e.key==='Escape'){hideFloating();getSelection().removeAllRanges();savedRange=null;updateSelection();}
});
document.addEventListener('selectionchange',()=>{clearTimeout(selectionTimer);selectionTimer=setTimeout(updateSelection,40);});
window.addEventListener('scroll',hideFloating,{passive:true});
floating.addEventListener('mousedown',e=>e.preventDefault());roles.addEventListener('mousedown',e=>e.preventDefault());
document.getElementById('choose-role').onclick=()=>{const r=floating.getBoundingClientRect();roles.style.display=roles.style.display==='block'?'none':'block';roles.style.left=r.left+'px';roles.style.top=r.bottom+4+'px';};
document.getElementById('clear-role').onclick=clearMarkup;
document.getElementById('pronounce').onclick=()=>{if(backend)backend.addPronunciation(savedRange?.toString().trim()||'');};
window.dmEditor={setSlots,setPresentation,applySlot,applyMarkup,clearMarkup,focusRun,focusText,undo,redo,sendState};
normalizeIds();decorate();
new QWebChannel(qt.webChannelTransport,c=>{backend=c.objects.audiobookPage;ready=true;backend.editorReady(chapter);});
'''


def manuscript_document(body: str, chapter: str, family: str, zoom: int) -> str:
    script = SCRIPT.replace('CHAPTER_TOKEN', json.dumps(chapter, ensure_ascii=False).replace('<', r'\u003c'))
    return ('<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">'
            '<script src="qrc:///qtwebchannel/qwebchannel.js"></script><style>' + CSS +
            '</style></head><body><main id="editor" contenteditable="true" spellcheck="true" '
            'aria-label="Текст главы">' + body + '</main>'
            '<div id="floating" role="toolbar" aria-label="Разметка выделения">'
            '<button id="choose-role">Роль ▾</button><button id="pronounce">Произношение</button>'
            '<button id="clear-role" title="Вернуть авторский текст">Снять разметку</button></div>'
            '<div id="roles" role="menu"></div><script>' + script +
            '\nsetPresentation(' + json.dumps(family).replace('<', r'\u003c') + ',' + str(zoom) + ',false);</script></body></html>')
