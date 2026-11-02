import json,sys
from PIL import Image,ImageDraw
d=json.load(open('gen/_board.json'));r=json.load(open('gen/_routes.json'))
S=16;OX=85;OY=29
def P(x,y):return ((x-OX)*S,(y-OY)*S)
y0=float(sys.argv[1]) if len(sys.argv)>1 else 29;y1=float(sys.argv[2]) if len(sys.argv)>2 else 147
W=int(30*S);H=int((y1-y0)*S)
im=Image.new('RGB',(W,H),(20,20,20));dr=ImageDraw.Draw(im)
def Q(x,y):return ((x-OX)*S,(y-y0)*S)
for a,b in d['edge']:dr.line([Q(*a),Q(*b)],fill=(200,200,200),width=1)
for p in d['pads']:
    x0,yy0,x1,yy1=p['box'];col=(160,40,40) if p['F'] else (40,40,160)
    dr.rectangle([Q(x0,yy0),Q(x1,yy1)],outline=col,fill=None)
for t in sorted(r['tracks'],key=lambda t:-t['layer']):
    col=(255,60,60) if t['layer']==0 else (80,140,255)
    dr.line([Q(*p) for p in t['pts']],fill=col,width=max(1,int(t['w']*S)))
for v in r['vias']:
    x,y=Q(*v['xy']);dr.ellipse([x-5,y-5,x+5,y+5],outline=(255,255,0),width=2)
im.save(sys.argv[3] if len(sys.argv)>3 else 'gen/_render.png')
