"""Render diverse linked originals including source-only/ambiguous examples."""
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
import pdfplumber, re
from pdf2image import convert_from_path
import improve_neighborhood_pages as impl
from audit_neighborhood_fees_phase4 import OUT,POPPLER

NAMES=['명일점','삼각산점','내발산점','하계점','덕이점','침산점','동춘점','송파위례점','미금점','미사점','돈암점','불당점','수지점','탄벌점','신중동점','구월점']

def render(item):
    row=item['rows'][0] if item['rows'] else None;page_no=row['page'] if row else 1
    path=OUT/'source-pdfs'/(item['fileId']+'.pdf')
    with pdfplumber.open(path) as pdf:
        page=pdf.pages[page_no-1];tables=page.find_tables();table=next(t for t in tables if len(t.rows)>2)
        cell_rows=table.extract();index=next((i for i,cells in enumerate(cell_rows) if len(cells)>1 and re.sub(r'\s+','',cells[1] or '')==(row['courseKey'] if row else '')),2)
        header=table.rows[:2];data_row=table.rows[index]
        boxes=[(table.bbox[0],header[0].bbox[1],table.bbox[2],header[-1].bbox[3]),(table.bbox[0],data_row.bbox[1],table.bbox[2],data_row.bbox[3])]
    image=convert_from_path(path,dpi=145,first_page=page_no,last_page=page_no,poppler_path=POPPLER)[0]
    bands=[]
    for box in boxes:
        band=image.crop(tuple(round(v*145/72) for v in box));band.thumbnail((1100,300));bands.append(band)
    canvas=Image.new('RGB',(1140,90+sum(b.height for b in bands)),'white');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',22)
    draw.text((20,12),item['center']+' · 원문 '+str(page_no)+'쪽 · '+', '.join(item['sourceDates']),fill='black',font=font)
    draw.text((20,44),'일반 과정 행 대조' if row else '금액 전재 제외 · 원문 확인 안내',fill='#6a4636',font=font)
    y=80
    for band in bands:canvas.paste(band,(20,y));y+=band.height
    canvas.save(OUT/('source-review-'+item['center']+'.png'))
    return canvas

def main():
    data=impl.load(OUT/'fee-grid-verified.json')['centers'];by_name={x['center']:x for x in data}
    with ThreadPoolExecutor(max_workers=4) as pool:images=list(pool.map(render,[by_name[n] for n in NAMES]))
    for start in range(0,len(images),4):
        batch=images[start:start+4];canvas=Image.new('RGB',(1140,sum(im.height for im in batch)+len(batch)*18),'#e8e4df');y=0
        for im in batch:canvas.paste(im,(0,y));y+=im.height+18
        canvas.save(OUT/('source-review-sheet-'+str(start//4+1)+'.jpg'),quality=94)
    impl.dump(OUT/'source-visual-review.json',{'renderedOriginals':NAMES,'sourceRowsGridVerified':impl.load(OUT/'fee-grid-verified.json')['gridValidation']['verifiedRows'],'viewedSheets':[]})

if __name__=='__main__':main()
