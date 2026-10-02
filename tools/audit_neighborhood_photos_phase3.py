"""Inspect existing real branch pictures; no source images are modified."""
from pathlib import Path
import hashlib, json
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase3 import OUT

SOURCE = Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\센터정보\센터별 사진')
def pixels(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB').resize((48,48)), dtype=np.float32)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    entries=[]
    for center in impl.FACTS['centers']:
        doc=html.document_fromstring((impl.ROOT/impl.center_path(center).strip('/')/'index.html').read_bytes())
        images=doc.xpath('//section[@id="learning-space"]//img[@data-role="space-image"]')
        folder=SOURCE/center['sourceName']
        originals=[]
        if folder.is_dir():
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    try: originals.append((path,pixels(path)))
                    except (OSError,ValueError): pass
        photos=[]
        if center['photoMode']=='center':
            for image in images:
                public=impl.ROOT/image.get('src').lstrip('/')
                pix=pixels(public)
                matches=sorted(((float(np.mean(np.abs(pix-original))),path) for path,original in originals),key=lambda x:x[0])
                assert matches and matches[0][0]<8, (center['routeName'],image.get('src'),matches[:1])
                score,path=matches[0]
                photos.append({'src':image.get('src'),'original':str(path.relative_to(SOURCE)),'originalSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'publicSha256':hashlib.sha256(public.read_bytes()).hexdigest(),'pixelDifference':round(score,4)})
        entries.append({'region':center['region'],'center':center['routeName'],'mode':center['photoMode'],'sourceFolderExists':folder.is_dir(),'sourceImageCount':len(originals),'photos':photos})
    real=[entry for entry in entries if entry['mode']=='center']
    font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',18)
    sheets=[]
    for offset in range(0,len(real),12):
        subset=real[offset:offset+12]
        sheet=Image.new('RGB',(1600,12*190),'white');draw=ImageDraw.Draw(sheet)
        for row,entry in enumerate(subset):
            draw.text((8,row*190+3),str(offset+row+1)+' '+entry['center'],fill='black',font=font)
            for col,photo in enumerate(entry['photos'][:4]):
                with Image.open(impl.ROOT/photo['src'].lstrip('/')) as original:
                    tile=ImageOps.contain(original.convert('RGB'),(390,148))
                    sheet.paste(tile,(col*400,row*190+30))
                    draw.text((col*400+8,row*190+166),str(col+1),fill='black',font=font)
        name='photo-review-'+str(offset//12+1)+'.jpg';sheet.save(OUT/name,quality=88);sheets.append(name)
    result={'realCenters':len(real),'commonCenters':len(entries)-len(real),'verifiedRealPictures':sum(len(entry['photos']) for entry in real),'entries':entries,'reviewSheets':sheets,'sourceImagesModified':False,'newRealPhotosAdded':0}
    impl.dump(OUT/'photo-audit.json',result)
    print(json.dumps({key:value for key,value in result.items() if key not in ['entries','reviewSheets']},ensure_ascii=False))
if __name__=='__main__':main()
