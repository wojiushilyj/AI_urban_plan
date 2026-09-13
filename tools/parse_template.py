# -*- coding: utf-8 -*-
"""解析用户上传的选址报告 Word 模板：结构、样式、表格、页眉页脚。"""
import zipfile, sys
from xml.etree import ElementTree as ET

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
}
W = NS['w']

def q(tag):
    return '{%s}%s' % (W, tag)

def para_text(p):
    return ''.join(t.text or '' for t in p.iter(q('t')))

def run_info(p):
    infos = []
    for r in p.findall(q('r')):
        rpr = r.find(q('rPr'))
        if rpr is None:
            continue
        fonts = rpr.find(q('rFonts'))
        sz = rpr.find(q('sz'))
        b = rpr.find(q('b'))
        color = rpr.find(q('color'))
        info = {}
        if fonts is not None:
            info['font'] = fonts.get(q('eastAsia')) or fonts.get(q('ascii'))
        if sz is not None:
            info['sz'] = int(sz.get(q('val'))) / 2
        if b is not None:
            info['b'] = b.get(q('val'), '1') != '0'
        if color is not None:
            info['color'] = color.get(q('val'))
        if info:
            infos.append(info)
    return infos[:2]

def pPr_info(p):
    ppr = p.find(q('pPr'))
    d = {}
    if ppr is None:
        return d
    st = ppr.find(q('pStyle'))
    if st is not None:
        d['style'] = st.get(q('val'))
    jc = ppr.find(q('jc'))
    if jc is not None:
        d['jc'] = jc.get(q('val'))
    num = ppr.find(q('numPr'))
    if num is not None:
        d['num'] = True
    return d

path = r'C:/Users/Administrator/Desktop/工业智慧选址平台｜选址分析报告模板0912.docx'
z = zipfile.ZipFile(path)
doc = ET.fromstring(z.read('word/document.xml'))
body = doc.find(q('body'))

out = []
for el in body:
    tag = el.tag.split('}')[1]
    if tag == 'p':
        txt = para_text(el)
        meta = pPr_info(el)
        ri = run_info(el)
        if txt.strip() or meta:
            out.append('P | %s | %s | runs=%s | %r' % (meta, ('center' if meta.get('jc')=='center' else ''), ri, txt.strip()[:80]))
    elif tag == 'tbl':
        rows = el.findall(q('tr'))
        out.append('TABLE rows=%d' % len(rows))
        for tr in rows[:4]:
            cells = [para_text(tc).strip()[:20] for tc in tr.findall(q('tc'))]
            out.append('   ROW: %s' % cells)
    elif tag == 'sectPr':
        out.append('SECTPR (page setup)')

# 页眉页脚
for name in ['word/header1.xml', 'word/footer1.xml']:
    try:
        h = ET.fromstring(z.read(name))
        out.append('%s TEXT: %r' % (name, ''.join(t.text or '' for t in h.iter(q('t')))))
    except KeyError:
        pass

# styles.xml 中标题样式定义
st = ET.fromstring(z.read('word/styles.xml'))
for s in st.findall(q('style')):
    sid = s.get(q('styleId'))
    if sid in ('1', '2', '3', '4', 'a', 'Heading1', 'Heading2', 'Heading3'):
        name = s.find(q('name'))
        rpr = s.find(q('rPr'))
        info = {}
        if rpr is not None:
            fonts = rpr.find(q('rFonts'))
            szel = rpr.find(q('sz'))
            if fonts is not None:
                info['font'] = fonts.get(q('eastAsia')) or fonts.get(q('ascii'))
            if szel is not None:
                info['sz'] = int(szel.get(q('val'))) / 2
        out.append('STYLE %s (%s): %s' % (sid, name.get(q('val')) if name is not None else '?', info))

print('\n'.join(out))
