"""Only exact base-course rows; raw text and connector extraction must agree."""
import re, json, hashlib
from collections import Counter
import improve_neighborhood_pages as impl
from audit_neighborhood_fees_phase4 import OUT

ROW=re.compile(r'보습\s+([^\n]*?(?:\n[^\n]*?)?)\s+(\d+)\s+([\d,.]+)\s+(\d+\s*개월|\d+\s*주|\d+\s*일)\s+([\d,]+)\s+([\d,]+)(?=\s*(?:[^\d,\s]|$))',re.S)

def course_kind(compact):
    if len(compact)>100 or any(term in compact for term in ['기초','향상','심화','집중','특강','보습','개월','모의고사']):return None
    stages=list(dict.fromkeys(re.findall('초등|중등|고등',compact)))
    if len(stages)!=1:return None
    subjects=[subject for subject in ['영어','수학'] if subject in compact]
    if '국영수' in compact:subjects=['영어','수학']
    if not subjects:return None
    return stages[0],subjects

def records(text):
    rows=[]
    for name,capacity,total_time,period,fee,total in ROW.findall(text):
        name=' '.join(name.split());compact=re.sub(r'\s+','',name)
        kind=course_kind(compact)
        if not kind:continue
        rows.append({'course':name,'courseKey':compact,'stage':kind[0],'subjects':kind[1],'capacity':int(capacity),'totalTime':total_time,'period':re.sub(r'\s+','',period),'tuition':int(fee.replace(',','')),'totalFee':int(total.replace(',',''))})
    return rows

def main():
    audit=impl.load(OUT/'fee-pdf-audit.json');items=[];issues=[]
    for file in audit['files']:
        connector={json.dumps(r,ensure_ascii=False,sort_keys=True) for r in records(file['text'])}
        registered_match=impl.norm(file['registeredName']) in impl.norm(file['title'])
        # The source CSV supplies this exact link. Keep its original title;
        # never rewrite a different registered name into the PDF itself.
        name_ok=registered_match or impl.norm(file['center']) in impl.norm(file['title'])
        rows=[];reasons=[]
        if file.get('error'):reasons.append('PDF download unavailable')
        if not name_ok:reasons.append('Registered academy name not matched in linked file title')
        for page_no,(text,dates) in enumerate(zip(file.get('pageTexts',[]),file.get('pageDates',[])),1):
            page_rows=records(text)
            for row in page_rows:
                key=json.dumps(row,ensure_ascii=False,sort_keys=True)
                if key not in connector:
                    reasons.append('Raw PDF and connector row disagree: '+row['course']);continue
                if len(dates)!=1:
                    reasons.append('Ambiguous page date: '+str(page_no));continue
                if row['tuition']!=row['totalFee'] or row['totalFee']<=0:
                    reasons.append('Tuition/total mismatch: '+row['course']);continue
                rows.append({**row,'page':page_no,'printedDate':dates[0],'timeUnit':'not specified in table heading'})
        if not rows:reasons.append('No unambiguous base English/math rows; retain source confirmation path')
        items.append({'region':file['region'],'center':file['center'],'registeredName':file['registeredName'],'fileId':file['id'],'feeLink':file['feeLink'],'sourceTitle':file['title'],'sourceSha256':file.get('pdfSha256'),'sourcePages':file.get('pdfPages'),'sourceDates':sorted(set(d for page in file.get('pageDates',[]) for d in page)),'nameMatched':name_ok,'registeredNameExactMatch':registered_match,'rows':rows if name_ok else [],'issues':reasons})
        if reasons:issues.append({'center':file['center'],'issues':list(dict.fromkeys(reasons))})
    result={'version':'20261001-v4','retrievedAt':'2026-10-01','rules':['All original URLs preserved.','Workbook controls currently offered grades; fee PDFs do not establish enrollment.','Only exact base English/math or explicitly combined course names; auxiliary programs are not advertised as total fees.','Do not interpret numeric course suffixes as weekly frequency.','Do not infer a missing time unit.','Printed date is page-specific; source modified time is not the effective date.','No current price claim or Offer schema.'],'centers':items,'issues':issues}
    impl.dump(OUT/'fee-reviewed-rows.json',result)
    print(json.dumps({'centers':len(items),'withRows':sum(bool(i['rows']) for i in items),'baseRows':sum(len(i['rows']) for i in items),'rowCounts':dict(Counter(len(i['rows']) for i in items)),'issues':issues},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
