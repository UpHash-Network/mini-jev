#!/usr/bin/env python3
"""Render MANUSCRIPT.md to a review PDF; requires reportlab.

Usage: python paper/build_paper.py [--output paper/Mini_Jev_Working_Paper.pdf]
The Markdown is the editable source. This is a review layout, not a venue style.
"""
import argparse
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, Preformatted, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent


def inline(text):
    text = escape(text)
    text = re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)',
                  r'<link href="\2" color="#16456B">\1</link>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8.5">\1</font>', text)
    return text


def build(source, output):
    content = source.read_text(encoding='utf-8')
    if re.search(r'<!--\s*(ANALYSIS_RESULTS|CALIBRATION_ANALYSIS|EXTERNAL_RESULTS|REFERENCES)', content):
        raise ValueError('Unfilled manuscript section; refusing to produce a finished PDF')
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=22*mm,
                            rightMargin=22*mm, topMargin=20*mm, bottomMargin=20*mm,
                            title='Typed Decisions from Frozen Language Models: Readout, Calibration, and Transfer',
                            author='Yuki Oshio', subject='Working paper v0.1; not peer reviewed or submitted')
    base = getSampleStyleSheet()
    styles = {
        'body': ParagraphStyle('paperbody', fontName='Times-Roman', fontSize=10.2,
                               leading=13.1, spaceAfter=6.2, alignment=TA_JUSTIFY,
                               allowWidows=0, allowOrphans=0, splitLongWords=True),
        'title': ParagraphStyle('papertitle', fontName='Times-Bold', fontSize=21,
                                leading=24, spaceAfter=14, alignment=TA_CENTER),
        'h2': ParagraphStyle('paperh2', fontName='Times-Bold', fontSize=13,
                             leading=16, spaceBefore=13, spaceAfter=6, keepWithNext=True),
        'h3': ParagraphStyle('paperh3', fontName='Times-Bold', fontSize=11,
                             leading=14, spaceBefore=9, spaceAfter=5, keepWithNext=True),
        'meta': ParagraphStyle('papermeta', fontName='Helvetica', fontSize=9,
                               leading=13, alignment=TA_CENTER, spaceAfter=5),
        'cell': ParagraphStyle('papercell', fontName='Helvetica', fontSize=8.3,
                               leading=10.5, alignment=TA_LEFT),
        'caption': ParagraphStyle('papercaption', fontName='Times-Italic', fontSize=9,
                                  leading=11.4, spaceBefore=4, spaceAfter=9),
        'code': ParagraphStyle('papercode', fontName='Courier', fontSize=8.1,
                               leading=10.8, leftIndent=8, spaceBefore=4, spaceAfter=8),
    }
    flow = []
    lines = content.splitlines()
    i = 0
    started = False
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith('<!--'):
            i += 1
            continue
        if line.startswith('# '):
            flow.append(Paragraph(inline(line[2:]), styles['title']))
            i += 1
        elif line.startswith('## '):
            started = True
            flow.append(Paragraph(inline(line[3:]), styles['h2']))
            i += 1
        elif line.startswith('### '):
            flow.append(Paragraph(inline(line[4:]), styles['h3']))
            i += 1
        elif line.startswith('```'):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                block.append(lines[i])
                i += 1
            flow.append(Preformatted('\n'.join(block), styles['code']))
            i += 1
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+', c) for c in cells):
                    rows.append([Paragraph(inline(c), styles['cell']) for c in cells])
                i += 1
            ncol = len(rows[0])
            proportions = {2: [0.63,0.37], 3: [0.52,0.24,0.24],
                           4: [0.43,0.19,0.19,0.19], 5: [0.35,0.13,0.17,0.17,0.18]}
            widths = [doc.width*p for p in proportions.get(ncol,[1/ncol]*ncol)]
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EDF1F4')),
                ('LINEABOVE',(0,0),(-1,0),0.75,colors.HexColor('#283949')),
                ('LINEBELOW',(0,0),(-1,0),0.5,colors.HexColor('#738394')),
                ('LINEBELOW',(0,-1),(-1,-1),0.65,colors.HexColor('#738394')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ]))
            flow.extend([table, Spacer(1,8)])
        elif line.startswith('!['):
            match = re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line)
            if not match:
                raise ValueError('Invalid figure syntax')
            img = Image(str(source.parent/match.group(2)))
            factor = min(doc.width/img.imageWidth, 78*mm/img.imageHeight)
            img.drawWidth = img.imageWidth*factor
            img.drawHeight = img.imageHeight*factor
            flow.append(KeepTogether([img,Paragraph(inline(match.group(1)),styles['caption'])]))
            i += 1
        else:
            block = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','![','<!--')):
                block.append(lines[i].strip())
                i += 1
            style = styles['body'] if started else styles['meta']
            flow.append(Paragraph(inline(' '.join(block)),style))

    def page(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#C5CDD5'))
        canvas.line(22*mm,15*mm,A4[0]-22*mm,15*mm)
        canvas.setFillColor(colors.HexColor('#52616F'))
        canvas.setFont('Helvetica',7.5)
        canvas.drawString(22*mm,11*mm,'Mini Jev | Working paper v0.1 | Not peer reviewed')
        canvas.drawRightString(A4[0]-22*mm,11*mm,str(document.page))
        canvas.restoreState()

    output.parent.mkdir(parents=True,exist_ok=True)
    doc.build(flow,onFirstPage=page,onLaterPages=page)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'MANUSCRIPT.md')
    parser.add_argument('--output',type=Path,default=ROOT/'Mini_Jev_Working_Paper.pdf')
    args = parser.parse_args()
    build(args.source.resolve(),args.output.resolve())
    print(args.output)
