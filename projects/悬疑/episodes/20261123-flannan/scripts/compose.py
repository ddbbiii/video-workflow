"""Controlled diary lettering and exactly counted lamp flashes."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from prepare import EP

FONTS = EP/"image/fonts"
HAND = FONTS/"JasonHandwriting2.ttf"
MONO = Path("/System/Library/Fonts/Menlo.ttc")
SONG = Path("/System/Library/Fonts/Supplemental/Songti.ttc")
SIZE = (1920,1080)
LAYOUT = {"S09":(126,535,750),"S14":(112,550,718),"S21":(105,513,752),
          "S23":(120,463,848),"S25":(100,452,915),"S33":(105,538,789),
          "S36":(100,475,911),"S38":(116,542,770),"S44":(115,530,766),"S58":(112,350,1045)}
PROFILE = {"S09":(0,0),"S14":(4,5),"S21":(-3,2),"S38":(4,5),"S44":(-3,2),"S58":(0,1)}

def open_font(path,size):
    return ImageFont.truetype(path,size)

def strips(draw,text,font,width):
    # Prefer semantic clauses, keeping punctuation attached and avoiding an orphan word.
    import re
    clauses=re.findall(r"[^。；，！？]+[。；，！？]?",text)
    lines=[]
    for clause in clauses:
        if draw.textlength(clause,font=font)<=width:
            if lines and draw.textlength(lines[-1]+clause,font=font)<=width:
                lines[-1]+=clause
            else:
                lines.append(clause)
        else:
            count=max(2,int(draw.textlength(clause,font=font)/width)+1)
            step=(len(clause)+count-1)//count
            for i in range(0,len(clause),step):
                lines.append(clause[i:i+step])
    return lines

def paper(im,row):
    shot=row["id"]
    data=row["overlay"]
    private=data["layer"]=="private_diary"
    x,y,w=LAYOUT[shot]
    fontsize=62 if shot=="S58" else 45
    text_size=open_font(HAND,fontsize) if private else open_font(SONG,fontsize-6)
    date_size=open_font(HAND,36) if private else open_font(SONG,38)
    padx=55
    xshift,yshift=PROFILE.get(shot,(0,0))
    if private:
        copy=data["body"]
    elif data["layer"]=="side_by_side_logs":
        copy=data["body"]
    else:
        copy=data["body"]
    scratch=ImageDraw.Draw(Image.new("RGB",(1,1)))
    lines=strips(scratch,copy,text_size,w-padx*2)
    h=84+len(lines)*(fontsize+16)+(62 if private or data["layer"]=="side_by_side_logs" else 0)
    card=Image.new("RGBA",(w,h))
    d=ImageDraw.Draw(card)
    d.polygon([(13,3),(w-8,11),(w-3,h-12),(8,h-5),(3,h//3)],
              fill=(216,203,170,253),outline=(153,130,95,255),width=2)
    d.line((42,19,41,h-20),fill=(159,117,105,156),width=1)
    top=45
    if private:
        d.text((padx+xshift,top+yshift), data["date"], font=date_size,fill=(86,68,51))
        top+=63
    if data["layer"]=="side_by_side_logs":
        d.text((padx,top),data["left"],font=date_size,fill=(74,61,47))
        d.text((w//2+10,top),data["right"],font=date_size,fill=(74,61,47))
        top+=60
    for index,line in enumerate(lines):
        baseline=top+index*(fontsize+16)
        d.line((56,baseline+fontsize+5,w-42,baseline+fontsize+5),fill=(167,151,125,113),width=1)
        d.text((padx+xshift+(index%2)*6,baseline+yshift),line,font=text_size,fill=(57,49,42))
    umbra=Image.new("RGBA",im.size,(12,19,23,0))
    alpha=Image.new("L",im.size)
    alpha.paste(card.getchannel("A").point(lambda a:a//2),(x+7,y+10))
    umbra.putalpha(alpha.filter(ImageFilter.GaussianBlur(14)))
    im.alpha_composite(umbra)
    im.alpha_composite(card,(x,y))

def clock(im,value):
    draw=ImageDraw.Draw(im)
    font=open_font(MONO,41)
    x,y=57,46
    draw.text((x,y),value,font=font,fill=(232,235,229),stroke_width=2,stroke_fill=(32,41,47))

def flash(im,xy):
    x,y=xy
    layer=Image.new("RGBA",im.size)
    d=ImageDraw.Draw(layer)
    d.ellipse((x-15,y-11,x+15,y+11),fill=(255,191,101,153))
    layer=layer.filter(ImageFilter.GaussianBlur(9))
    im.alpha_composite(layer)
    d=ImageDraw.Draw(im)
    d.ellipse((x-5,y-4,x+5,y+4),fill=(255,246,210))
    d.ellipse((x-2,y-2,x+2,y+2),fill=(255,255,248))

def phases(frames,group):
    # Six frames lit, five apart. Twenty-four frames separate number groups.
    states=[(False,28)]
    for gi,count in enumerate(group):
        for i in range(count):
            states.append((True,6))
            states.append((False,24 if i==count-1 and gi<len(group)-1 else 5))
    remain=frames-sum(length for _,length in states)
    if remain<0:
        raise ValueError(f"Not enough exposure length ({frames}) for readably timed signal")
    states[-1]=(False,states[-1][1]+remain)
    return states

def render_still(row, output, lit=False, xy=None):
    with Image.open(EP/"image/final"/f"{row['id']}.png") as source:
        im=source.convert("RGBA")
    data=row.get("overlay")
    if data:
        layer=data["layer"]
        if layer in ("external_clock","external_clock_and_light"):
            clock(im,data["body"])
        else:
            paper(im,row)
            if data.get("outer_time"):
                clock(im,data["outer_time"])
        if lit:
            if xy is None:
                raise ValueError("Inspect and set the flash point in the correct optical plane")
            flash(im,xy)
    im.convert("RGB").save(output)

if __name__=="__main__":
    import sys
    shots=json.loads((EP/"storyboard/SHOT_PLAN.json").read_text())["shots"]
    row=next(s for s in shots if s["id"]==sys.argv[1])
    render_still(row,Path(sys.argv[2]))
