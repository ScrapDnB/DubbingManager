"""HTML documents used by the QML audiobook WebEngine editors."""

from __future__ import annotations

import html
import json
from typing import Any

from lxml import etree
from lxml import html as lxml_html


def _body_fragment(html_text: str) -> str:
    if not str(html_text or "").strip():
        return ""
    try:
        document = lxml_html.document_fromstring(html_text)
        body = document.find("body")
        if body is None:
            return html_text
        return (body.text or "") + "".join(
            etree.tostring(child, encoding="unicode", method="html")
            for child in body
        )
    except (etree.ParserError, ValueError):
        return html_text


def canonical_html(body_html: str) -> str:
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
        f"{body_html}</body></html>"
    )


def editor_document(html_text: str, font_family: str, zoom: int) -> str:
    body = _body_fragment(html_text)
    family = json.dumps(str(font_family or "Georgia"))
    scale = max(0.7, min(1.8, 1.0 + int(zoom) * 0.1))
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
html {{ background:#ecebea; }}
body {{ margin:0; padding:36px 24px 80px; color:#202020; background:#ecebea; }}
#editor {{ box-sizing:border-box; width:min(820px, calc(100% - 16px)); min-height:calc(100vh - 72px);
  margin:0 auto; padding:64px 72px 96px; background:#fff; border:1px solid #d8d6d2;
  box-shadow:0 2px 12px rgba(0,0,0,.08); font-family:{family}; font-size:{17 * scale:.2f}px;
  line-height:1.62; outline:none; caret-color:#111; }}
#editor p {{ margin:0 0 1em; text-align:left; }} #editor h1 {{ margin:0 0 1.35em; font-size:1.65em; line-height:1.2; text-align:left; }}
span[data-dm-character] {{ border-radius:3px; padding:1px 0; box-decoration-break:clone; -webkit-box-decoration-break:clone; }}
@media (prefers-color-scheme:dark) {{ html,body {{background:#252525}} #editor {{background:#f8f7f4;border-color:#3c3c3c}} }}
</style></head><body><main id="editor" contenteditable="true" spellcheck="true">{body}</main>
<script>
let backend=null, savedRange=null, slots=[];
const editor=document.getElementById('editor');
new QWebChannel(qt.webChannelTransport, channel => {{ backend=channel.objects.audiobookPage; sendState(); }});
document.addEventListener('selectionchange', () => {{
  const selection=getSelection();
  if (selection.rangeCount && editor.contains(selection.anchorNode)) savedRange=selection.getRangeAt(0).cloneRange();
}});
function restoreRange() {{ if(!savedRange) return null; const s=getSelection(); s.removeAllRanges(); s.addRange(savedRange); return savedRange; }}
function unwrap(node) {{ const parent=node.parentNode; while(node.firstChild) parent.insertBefore(node.firstChild,node); node.remove(); parent.normalize(); }}
function markSpans(range) {{ return [...editor.querySelectorAll('span[data-dm-character]')].filter(span => range.intersectsNode(span)); }}
function htmlDocument() {{ return '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'+editor.innerHTML+'</body></html>'; }}
function segments() {{
  const result=[]; let current=null, text='';
  function flush() {{ const value=text.replace(/\\s+/g,' ').trim(); if(value) result.push({{character:current||'Автор',text:value}}); text=''; }}
  function walk(node, character) {{
    if(node.nodeType===Node.TEXT_NODE) {{ if(character!==current) {{flush(); current=character;}} text+=node.nodeValue; return; }}
    if(node.nodeType!==Node.ELEMENT_NODE) return;
    const next=node.dataset && node.dataset.dmCharacter ? node.dataset.dmCharacter : character;
    const block=/^(P|DIV|H1|H2|H3|LI|BLOCKQUOTE|BR)$/.test(node.tagName);
    if(block) text+=' ';
    node.childNodes.forEach(child=>walk(child,next));
    if(block) text+=' ';
  }}
  walk(editor,null); flush(); return result;
}}
function sendState() {{ if(backend) backend.updateState(htmlDocument(), JSON.stringify(segments())); }}
function setSlots(value) {{ slots=value||[]; }}
function applySlot(index) {{ const slot=slots[index]; if(!slot || !slot.character) return false; return applyMarkup(slot.character,slot.actorId,slot.color); }}
function applyMarkup(character, actorId, color) {{
  const range=restoreRange(); if(!range || range.collapsed || !editor.contains(range.commonAncestorContainer)) return false;
  markSpans(range).forEach(unwrap);
  const span=document.createElement('span'); span.dataset.dmCharacter=character; if(actorId) span.dataset.dmActor=actorId;
  span.style.backgroundColor=color || '#fff2a8'; span.style.color='#111';
  span.appendChild(range.extractContents()); range.insertNode(span); range.selectNodeContents(span); savedRange=range.cloneRange();
  sendState(); return true;
}}
function clearMarkup() {{ const range=restoreRange(); if(!range || range.collapsed) return false; markSpans(range).forEach(unwrap); sendState(); return true; }}
function recolor(character, actorId, color) {{ editor.querySelectorAll('span[data-dm-character]').forEach(span => {{ if(span.dataset.dmCharacter===character) {{ span.style.backgroundColor=color; if(actorId) span.dataset.dmActor=actorId; else delete span.dataset.dmActor; }} }}); sendState(); }}
editor.addEventListener('input', sendState);
editor.addEventListener('keydown', event => {{
  if(!event.metaKey && !event.ctrlKey && !event.altKey && /^[1-9]$/.test(event.key) && savedRange && !savedRange.collapsed) {{
    event.preventDefault(); applySlot(Number(event.key)-1);
  }}
}});
window.dmEditor={{setSlots,applySlot,applyMarkup,clearMarkup,recolor,sendState}};
</script></body></html>"""


def chapter_markup_document(source_html: str, chapters: list[dict[str, Any]]) -> str:
    body = _body_fragment(source_html)
    try:
        container = lxml_html.fragment_fromstring(body or "<p></p>", create_parent="div")
        headings = list(container.xpath(".//h1|.//h2|.//h3"))
        used: set[int] = set()
        for chapter in chapters:
            title = str(chapter.get("title", "")).strip()
            target = next((node for node in headings if id(node) not in used and " ".join(node.text_content().split()) == title), None)
            marker = lxml_html.Element("div", {"class": "dm-boundary", "data-title": title, "draggable": "true"})
            marker.text = title
            if target is not None:
                used.add(id(target))
                target.addprevious(marker)
            else:
                container.append(marker)
                fragment = lxml_html.fragments_fromstring(_body_fragment(str(chapter.get("html", ""))))
                for node in fragment:
                    if isinstance(node, str):
                        marker.tail = (marker.tail or "") + node
                    else:
                        container.append(node)
        body = (container.text or "") + "".join(etree.tostring(child, encoding="unicode", method="html") for child in container)
    except (etree.ParserError, ValueError):
        pass
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="qrc:///qtwebchannel/qwebchannel.js"></script><style>
html,body{{margin:0;background:#ecebea;color:#202020}} body{{padding:28px 22px 80px}}
#source{{box-sizing:border-box;width:min(900px,calc(100% - 12px));min-height:calc(100vh - 56px);margin:auto;padding:58px 70px 90px;background:#fff;border:1px solid #d8d6d2;box-shadow:0 2px 12px rgba(0,0,0,.08);font:17px/1.62 Georgia,serif;outline:none}}
.dm-boundary{{margin:28px -26px 18px;padding:7px 12px;border-top:1px solid #7d9bc1;border-bottom:1px solid #7d9bc1;background:#edf4fc;color:#274c77;font:600 13px system-ui,sans-serif;cursor:grab;user-select:none}}
.dm-boundary.selected{{background:#d8e9fb;border-color:#3976b8}} .drop-target{{box-shadow:0 -3px 0 #3976b8}}
@media(prefers-color-scheme:dark){{html,body{{background:#252525}}#source{{background:#f8f7f4;border-color:#3c3c3c}}}}
</style></head><body><main id="source" contenteditable="true" spellcheck="false">{body}</main><script>
let backend=null,savedRange=null,selected=null; const source=document.getElementById('source');
new QWebChannel(qt.webChannelTransport,c=>{{backend=c.objects.chapterPage; bindMarkers(); send();}});
document.addEventListener('selectionchange',()=>{{const s=getSelection();if(s.rangeCount&&source.contains(s.anchorNode)&&!s.anchorNode.closest?.('.dm-boundary'))savedRange=s.getRangeAt(0).cloneRange();}});
source.addEventListener('beforeinput',e=>e.preventDefault());
function markers(){{return [...source.querySelectorAll('.dm-boundary')]}}
function selectMarker(marker){{markers().forEach(x=>x.classList.remove('selected'));selected=marker;if(marker){{marker.classList.add('selected');marker.scrollIntoView({{block:'center'}});if(backend)backend.boundarySelected(marker.dataset.title);}}}}
function bindMarkers(){{markers().forEach(marker=>{{marker.draggable=true;marker.onclick=e=>{{e.stopPropagation();selectMarker(marker)}};marker.ondragstart=e=>{{selected=marker;e.dataTransfer.setData('text/plain',marker.dataset.title)}};}})}}
function insertionNode(){{if(!savedRange)return null;let n=savedRange.startContainer;if(n.nodeType===3)n=n.parentElement;return n.closest('p,h1,h2,h3,li,blockquote,div')||n;}}
function add(title){{if(!title||markers().some(m=>m.dataset.title===title))return false;const at=insertionNode();if(!at)return false;const m=document.createElement('div');m.className='dm-boundary';m.dataset.title=title;m.textContent=title;at.before(m);bindMarkers();selectMarker(m);send();return true;}}
function moveSelected(){{const at=insertionNode();if(!selected||!at||at===selected)return false;at.before(selected);send();return true;}}
function renameSelected(title){{if(!selected||!title||markers().some(m=>m!==selected&&m.dataset.title===title))return false;const old=selected.dataset.title;selected.dataset.title=title;selected.textContent=title;let h=selected.nextElementSibling;if(h&&/^H[1-3]$/.test(h.tagName))h.textContent=title;if(backend)backend.boundaryRenamed(old,title);send();return true;}}
function deleteSelected(){{if(!selected)return false;const old=selected.dataset.title;const next=selected.nextElementSibling;selected.remove();selected=null;if(backend)backend.boundaryDeleted(old);if(next)next.scrollIntoView({{block:'center'}});send();return true;}}
function selectTitle(title){{selectMarker(markers().find(m=>m.dataset.title===title)||null)}}
source.addEventListener('dragover',e=>{{e.preventDefault();const at=e.target.closest('p,h1,h2,h3,li,blockquote,.dm-boundary');document.querySelectorAll('.drop-target').forEach(x=>x.classList.remove('drop-target'));if(at&&at!==selected)at.classList.add('drop-target')}});
source.addEventListener('drop',e=>{{e.preventDefault();const at=e.target.closest('p,h1,h2,h3,li,blockquote,.dm-boundary');document.querySelectorAll('.drop-target').forEach(x=>x.classList.remove('drop-target'));if(selected&&at&&at!==selected){{at.before(selected);send();}}}});
function cleanSource(){{const clone=source.cloneNode(true);clone.querySelectorAll('.dm-boundary').forEach(x=>x.remove());return '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'+clone.innerHTML+'</body></html>'}}
function chapterPayload(){{const result=[];const all=markers();all.forEach((marker,index)=>{{let content='';let node=marker.nextSibling;while(node&&!(node.nodeType===1&&node.classList.contains('dm-boundary'))){{content+=node.outerHTML!==undefined?node.outerHTML:(node.textContent||'');node=node.nextSibling;}}const holder=document.createElement('div');holder.innerHTML=content;let h=holder.querySelector(':scope > h1,:scope > h2,:scope > h3');if(h)h.outerHTML='<h1>'+marker.dataset.title.replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]))+'</h1>';else holder.insertAdjacentHTML('afterbegin','<h1>'+marker.dataset.title+'</h1>');result.push({{title:marker.dataset.title,html:'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'+holder.innerHTML+'</body></html>'}})}});return result}}
function send(){{if(backend)backend.updateBoundaries(JSON.stringify({{sourceHtml:cleanSource(),chapters:chapterPayload()}}))}}
window.dmChapters={{add,moveSelected,renameSelected,deleteSelected,selectTitle,send}};
</script></body></html>"""
