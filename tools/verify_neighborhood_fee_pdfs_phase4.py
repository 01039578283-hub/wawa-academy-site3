"""Independent visual-table-cell verification of every candidate fee row."""
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
from pathlib import Path
import json, re
import pdfplumber
import improve_neighborhood_pages as impl
from audit_neighborhood_fees_phase4 import OUT

def compact(value):return re.sub(r'\s+','',value or '')
def integer(value):return int(compact(value).replace(',',''))
def signature(row):return (row['courseKey'],row['capacity'],compact(row['totalTime']),row['period'],row['tuition'],row['totalFee'])

def verify(item):
    errors=[];verified=[];extra=[];pages=[]
    if not item['rows']:return {**item,'tableVerifiedRows':0,'rows':[],'tableErrors':[],'tablePages':[]}
    with pdfplumber.open(OUT/'source-pdfs'/(item['fileId']+'.pdf')) as pdf:
        for page_no in sorted({row['page'] for row in item['rows']}):
            page=pdf.pages[page_no-1];tables=page.extract_tables();matches={};headers=[]
            for table in tables:
                headers.extend(compact(cell) for cells in table[:2] for cell in cells if cell)
                for cells in table:
                    if len(cells)<7 or compact(cells[0])!='보습':continue
                    try:
                        key=(compact(cells[1]),integer(cells[2]),compact(cells[3]),compact(cells[4]),integer(cells[5]),integer(cells[-1]))
                    except (ValueError,TypeError):continue
                    matches[key]=cells
            assert all(word in ''.join(headers) for word in ['교습과목','교습시간','교습기간','총교습비']), (item['center'],page_no,'Unrecognized table heading')
            for row in [row for row in item['rows'] if row['page']==page_no]:
                cells=matches.get(signature(row))
                if cells is None:errors.append([page_no,row['course'],'PDF grid cells did not exactly match extracted fields']);continue
                if any(compact(cell) for cell in cells[6:-1]):extra.append([page_no,row['course'],'Expense cell is present; retain original-only review']);continue
                verified.append(row)
            pages.append(page_no)
    return {**item,'rows':verified,'tableVerifiedRows':len(verified),'tableErrors':errors,'expenseRowsOmitted':extra,'tablePages':pages}

def main():
    source=impl.load(OUT/'fee-reviewed-rows.json');items=[]
    with ProcessPoolExecutor(max_workers=6) as pool:
        for index,result in enumerate(pool.map(verify,source['centers']),1):
            items.append(result)
            if index%20==0:print('Independently verified fee grids',index,flush=True)
    source['centers']=items
    source['gridValidation']={'candidateRows':sum(item['tableVerifiedRows']+len(item['tableErrors'])+len(item.get('expenseRowsOmitted',[])) for item in items),'verifiedRows':sum(item['tableVerifiedRows'] for item in items),'withRows':sum(bool(item['rows']) for item in items),'errors':[[i['center'],e] for i in items for e in i['tableErrors']],'expenseRowsOmitted':[[i['center'],e] for i in items for e in i.get('expenseRowsOmitted',[])]}
    impl.dump(OUT/'fee-grid-verified.json',source)
    print(json.dumps(source['gridValidation'],ensure_ascii=False),flush=True)

if __name__=='__main__':main()
