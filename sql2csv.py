import re, csv, sys
from pathlib import Path
from datetime import datetime
from io import StringIO

# ---------------- 사용자 입력 ----------------
table_name = input("변환할 테이블명을 입력하세요 : ").strip()
file_path  = input("SQL 파일을 드래그 앤 드롭 하세요 : ").strip().strip('"')
in_path = Path(file_path)
out_path = in_path.with_suffix(".csv")

# ---------------- 유틸 함수 ----------------
def oracle_fmt_to_py(fmt: str) -> str:
    f = fmt.upper()
    mapping = [
        ("HH24", "%H"), ("HH12", "%I"),
        ("YYYY", "%Y"), ("YY", "%y"),
        ("MONTH","%B"), ("MON","%b"),
        ("MM","%m"), ("DD","%d"),
        ("MI","%M"), ("SS","%S"),
    ]
    for k,v in mapping: f = f.replace(k,v)
    return f

def try_parse_oracle_datetime(lit: str, fmt: str):
    try:
        pyfmt = oracle_fmt_to_py(fmt)
        dt = datetime.strptime(lit, pyfmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S") if any(x in pyfmt for x in ("%H","%I","%M","%S")) \
               else dt.strftime("%Y-%m-%d")
    except: return None

def strip_block_and_line_comments_stream(f):
    buf, stmts = [], []
    in_str = False; in_block = False; prev=''
    while True:
        ch = f.read(1)
        if not ch: break
        if in_block:
            if prev=='*' and ch=='/': in_block=False; ch=''
            prev=ch; continue
        if ch=="'":
            if in_str:
                nxt=f.read(1)
                if nxt=="'": buf.append("'"); prev=nxt; continue
                else: in_str=False; buf.append("'"); 
                if not nxt: break
                ch=nxt
            else: in_str=True; buf.append("'"); prev=ch; continue
        if not in_str and ch=='-':
            nxt=f.read(1)
            if nxt=='-':
                while True:
                    c2=f.read(1)
                    if not c2 or c2 in '\r\n':
                        if c2: buf.append(c2)
                        break
                prev=''; continue
            else:
                buf.append('-'); 
                if not nxt: break
                ch=nxt
        if not in_str and prev=='/' and ch=='*':
            if buf and buf[-1]=='/': buf.pop()
            in_block=True; prev=ch; continue
        if not in_str and ch==';':
            stmt=''.join(buf).strip()
            if stmt: stmts.append(stmt)
            buf=[]; prev=ch; continue
        buf.append(ch); prev=ch
    tail=''.join(buf).strip()
    if tail: stmts.append(tail)
    return stmts

def normalize_ident(x:str)->str:
    x=x.strip()
    return x[1:-1] if x.startswith('"') and x.endswith('"') else x.upper()

def extract_top_paren(block,start_idx:int):
    depth=0; out=[]
    for i,ch in enumerate(block[start_idx:],start=start_idx):
        out.append(ch)
        if ch=='(': depth+=1
        elif ch==')':
            depth-=1
            if depth==0: return ''.join(out),i+1
    return None,None

def find_columns_and_values(stmt, table_name):
    s=stmt.strip()
    m=re.search(r"^\s*INSERT\s+INTO\s+",s,flags=re.I)
    if not m: return None,None
    rest=s[m.end():].lstrip()
    ident=r'(?:\"[^\"]+\"|[A-Za-z0-9_$#]+)'
    m2=re.match(rf'{ident}\s*\.?\s*{ident}',rest)
    if not m2: return None,None
    table_part=rest[:m2.end()].strip()
    if '.' in table_part: _,tbl=[p.strip() for p in table_part.split('.',1)]
    else: tbl=table_part
    if normalize_ident(tbl)!=normalize_ident(table_name): return None,None
    after_tbl=rest[m2.end():].lstrip()
    if not after_tbl.startswith('('): return None,None
    cols_blob,idx=extract_top_paren(after_tbl,0)
    if not cols_blob: return None,None
    rest2=after_tbl[idx:].lstrip()
    m3=re.match(r'VALUES\s*\(',rest2,flags=re.I)
    if not m3: return None,None
    vals_blob,idx2=extract_top_paren(rest2,m3.end()-1)
    if not vals_blob: return None,None
    return cols_blob[1:-1],vals_blob[1:-1]

def split_args(argblob:str):
    parts,buf=[],[]; in_str=False; depth=0; i=0; L=len(argblob)
    while i<L:
        ch=argblob[i]
        if ch=="'":
            if in_str:
                if i+1<L and argblob[i+1]=="'": buf.append("'"); i+=2; continue
                else: in_str=False; buf.append("'"); i+=1; continue
            else: in_str=True; buf.append("'"); i+=1; continue
        elif not in_str and ch=='(': depth+=1
        elif not in_str and ch==')' and depth>0: depth-=1
        elif not in_str and depth==0 and ch==',':
            parts.append(''.join(buf).strip()); buf=[]; i+=1; continue
        buf.append(ch); i+=1
    if buf: parts.append(''.join(buf).strip())
    return parts

def clean_value(token:str):
    t=token.strip()
    if t.upper()=="NULL": return ""
    m=re.match(r"(?i)^\s*DATE\s*'([^']+)'",t)
    if m: return m.group(1)
    m=re.match(r"(?i)^\s*TIMESTAMP\s*'([^']+)'",t)
    if m: return m.group(1)
    m=re.match(r"(?is)^\s*TO_(?:DATE|TIMESTAMP)\s*\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)",t)
    if m:
        iso=try_parse_oracle_datetime(m.group(1),m.group(2))
        return iso if iso else m.group(1)
    if t.startswith("'") and t.endswith("'"):
        v = t[1:-1].replace("''","'")
        if re.fullmatch(r"\d{8}", v):
            return v
        return v
    return t


# ---------------- 메인 ----------------
print("1/3) 파일 읽는 중...")
text=in_path.read_text(encoding="utf-8",errors="ignore")
print("   완료 (파일 크기: %.2f MB)"%(len(text)/(1024*1024)))

print("2/3) 문장 분리 및 주석 제거 중...")
stmts=strip_block_and_line_comments_stream(StringIO(text))
print("   완료 (총 %d 문장)"%len(stmts))

print("3/3) INSERT 파싱 및 CSV 변환 중...")

cols=None; rows=[]; matched=0
for idx,stmt in enumerate(stmts,1):
    cblob,vblob=find_columns_and_values(stmt,table_name)
    if cblob and vblob:
        if cols is None: cols=[c.strip() for c in split_args(cblob)]
        vals=[clean_value(x) for x in split_args(vblob)]
        if len(vals)==len(cols):
            rows.append(vals); matched+=1
    if idx%1000==0 or idx==len(stmts):
        progress=idx/len(stmts)*100
        sys.stdout.write(f"\r   진행률: {progress:6.2f}% | 매칭: {matched:,}건")
        sys.stdout.flush()
print()

if not cols:
    print("❌ 지정한 테이블의 INSERT를 찾지 못했습니다.")
else:
    with out_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(cols); w.writerows(rows)
    print(f"✅ 완료: {out_path} (총 {len(rows):,}행)")
