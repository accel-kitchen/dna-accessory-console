"""Export 2D silk views and 3D renders of the current PCB with kicad-cli (KiCad 9)."""
from pathlib import Path
import subprocess, fitz
ROOT=Path(__file__).resolve().parents[1]
K=r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe'
PCB=str(ROOT/'dna-accesories.kicad_pcb')
OUT=ROOT/'design'/'preview'
def run(*args):subprocess.run([K,*args],check=True,capture_output=True)
for name,layers,mirror in (('front','F.Cu,F.Mask,F.SilkS,Edge.Cuts',False),('back','B.Cu,B.Mask,B.SilkS,Edge.Cuts',True)):
    svg=OUT/f'{name}-kicad.svg'
    run('pcb','export','svg','--mode-single','--page-size-mode','2','--exclude-drawing-sheet',*(['--mirror'] if mirror else []),'-l',layers,'-o',str(svg),PCB)
    pdf=fitz.open('pdf',fitz.open(str(svg)).convert_to_pdf())
    pdf[0].get_pixmap(matrix=fitz.Matrix(14,14)).save(OUT/f'{name}-kicad.png')
# 3D renders: the interference check itself lives in gen/check_interference.py.
views={'3d-top':dict(side='top',w=700,h=2800),
       '3d-bottom':dict(side='bottom',w=700,h=2800),
       '3d-iso-collar':dict(side='top',w=1500,h=1100,rotate='-50,0,25',zoom=2.6,pivot='0,-12.5,0'),
       '3d-iso-collar-back':dict(side='bottom',w=1500,h=1100,rotate='-50,0,155',zoom=2.6,pivot='0,-12.5,0'),
       '3d-usb-side':dict(side='front',w=1500,h=700,zoom=4.2,pivot='0,-13,0')}
for name,v in views.items():
    args=['pcb','render','--quality','high','--background','opaque','--width',str(v['w']),'--height',str(v['h']),'--side',v['side']]
    for key in ('rotate','zoom','pivot'):
        if key in v:args+=[f'--{key}',str(v[key])]
    run(*args,'-o',str(OUT/f'{name}.png'),PCB)
    print('rendered',name)
