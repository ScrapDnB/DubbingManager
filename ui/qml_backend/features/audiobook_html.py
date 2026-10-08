"""HTML documents used by the QML audiobook WebEngine editors."""

from __future__ import annotations

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


def editor_document(html_text: str, font_family: str, zoom: int, chapter: str = "") -> str:
    from ui.qml_backend.features.audiobook_editor import manuscript_document
    return manuscript_document(_body_fragment(html_text), chapter, font_family, zoom)


def chapter_markup_document(source_html: str, chapters: list[dict[str, Any]]) -> str:
    fragments = []
    for chapter in chapters:
        marker = lxml_html.Element("div", {
            "class": "dm-boundary", "data-title": str(chapter.get("title", "")),
            "draggable": "true",
        })
        marker.text = str(chapter.get("title", ""))
        fragments.append(etree.tostring(marker, encoding="unicode", method="html"))
        fragments.append(_body_fragment(str(chapter.get("html", ""))))
    body = "".join(fragments) if chapters else _body_fragment(source_html)
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
function chapterPayload(){{
 const all=markers();if(!all.length)return [];
 const buckets=all.map(()=>document.createElement('div'));let current=0;
 // Text before the first remaining boundary belongs to that chapter too.
 // This preserves the opening pages when the first boundary is moved/deleted.
 [...source.childNodes].forEach(node=>{{
  const at=all.indexOf(node);
  if(at>=0)current=at;else buckets[current].append(node.cloneNode(true));
 }});
 return all.map((marker,index)=>{{
  const holder=buckets[index];
  if(!holder.firstElementChild||!/^H[1-3]$/.test(holder.firstElementChild.tagName)){{
   const heading=document.createElement('h1');heading.textContent=marker.dataset.title;holder.prepend(heading);
  }}
  return {{title:marker.dataset.title,html:'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'+holder.innerHTML+'</body></html>'}};
 }});
}}
function send(){{if(backend)backend.updateBoundaries(JSON.stringify({{sourceHtml:cleanSource(),chapters:chapterPayload()}}))}}
window.dmChapters={{add,moveSelected,renameSelected,deleteSelected,selectTitle,send}};
</script></body></html>"""
