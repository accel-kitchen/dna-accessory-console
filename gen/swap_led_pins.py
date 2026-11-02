"""Swap LED pin numbers VDD 1->2 and DOUT 2->1 (XINGLIGHT XL-1010RGBC-WS2812B datasheet p.10-11).
Symbol pin positions are unchanged, so schematic wiring stays; only the pad numbers move."""
import re,sys
def swap_symbol(t):
    # inside symbol definition: pin blocks with name VDD / DOUT
    def fix(m):
        blk=m.group(0)
        if '(name "VDD"' in blk:return blk.replace('(number "1"','(number "2"')
        if '(name "DOUT"' in blk:return blk.replace('(number "2"','(number "1"')
        return blk
    return re.sub(r'\(pin (?:power_in|output) line.*?\(number "[12]"',fix,t,flags=re.S)
p='dna-accesories.kicad_sch'
t=open(p,encoding='utf8').read()
# 1) embedded lib symbol
a=t.index('(symbol "WS2812B:XL-1010RGBC-WS2812B"');b=t.index('(symbol "XIAO',a) if '(symbol "XIAO' in t[a:] else None
end=t.index('\n\t)\n',a) if b is None else b
seg=t[a:end];t=t[:a]+swap_symbol(seg)+t[end:]
# 2) instances
out=[];pos=0
for m in re.finditer(r'\(lib_id "WS2812B:XL-1010RGBC-WS2812B"\)',t):
    s=m.start();e=t.index('\n\t(symbol',s) if '\n\t(symbol' in t[s:] else t.index('(sheet_instances',s)
    out.append((s,e))
for s,e in reversed(out):
    blk=t[s:e]
    blk=re.sub(r'\(pin "1"','(pin "@"',blk);blk=re.sub(r'\(pin "2"','(pin "1"',blk);blk=blk.replace('(pin "@"','(pin "2"')
    t=t[:s]+blk+t[e:]
open(p,'w',encoding='utf8',newline='').write(t)
q='lib/ul_XL-1010RGBC-WS2812B/KiCADv6/2026-06-01_13-23-56.kicad_sym'
l=open(q,encoding='utf8').read();open(q,'w',encoding='utf8',newline='').write(swap_symbol(l))
print(len(out),'instances')
