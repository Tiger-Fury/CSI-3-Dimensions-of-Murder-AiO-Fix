from pathlib import Path
import struct,json,hashlib
root=Path(__file__).resolve().parents[1];out=root/'dist'/'Original';out.mkdir(parents=True,exist_ok=True)
align=lambda n,a:(n+a-1)//a*a
data=bytearray(60);data_rva=0x2000
def alloc(payload,alignment=1):
 data.extend(b'\0'*(align(len(data),alignment)-len(data)));offset=len(data);data.extend(payload);return data_rva+offset
def string(s):return alloc(s.encode('ascii')+b'\0')
imports={};iat_ranges=[]
for index,(dll,funcs) in enumerate([('KERNEL32.dll',['GetModuleFileNameA','SetCurrentDirectoryA','LoadLibraryExA','GetProcAddress','ExitProcess']),('USER32.dll',['MessageBoxA'])]):
 dllname=string(dll);hints=[alloc(b'\0\0'+n.encode()+b'\0',2) for n in funcs]
 ilt=alloc(b''.join(struct.pack('<I',n) for n in hints)+b'\0'*4,4)
 iat=alloc(b''.join(struct.pack('<I',n) for n in hints)+b'\0'*4,4)
 struct.pack_into('<IIIII',data,index*20,ilt,0,0,dllname,iat)
 for i,name in enumerate(funcs):imports[name]=iat+i*4
 iat_ranges.append((iat,len(funcs)*4+4))
strings={k:string(v) for k,v in {'engine':'t3.mll','original':'CSI3.exe','setexe':'?GameEngine_SetExeFile@@YAXPBD@Z','main':'?GameEngine_WinMain@@YGHPAUHINSTANCE__@@0PADH@Z','empty':'','title':'CSI: 3 Dimensions of Murder','patherror':'Could not determine the game folder. Place this launcher in the game installation.','direrror':'Could not open the game folder.','loaderror':'Could not load t3.mll. Keep this launcher beside the original game files. A required engine dependency may be missing.','exporterror':'The expected Telltale engine entry points were not found in t3.mll.'}.items()}
buffer=alloc(b'\0'*1024,4);set_slot=alloc(b'\0'*4,4);main_slot=alloc(b'\0'*4,4)
code=bytearray();labels={};fixups=[]
def emit(h):code.extend(bytes.fromhex(h))
def imm(n):code.extend(struct.pack('<I',n))
def label(n):labels[n]=len(code)
def branch(op,n):emit(op);fixups.append((len(code),n));imm(0)
def lea(reg,rva):emit('8d'+reg);imm(rva)
def call(name):emit('ff93');imm(imports[name])
def copy_name(key):
 emit('89fa');lea('8b',strings[key]);label('copy_'+key);emit('8a018802414284c0');branch('0f85','copy_'+key)
emit('53565755e8000000005b81eb');imm(0x1000+9)
lea('b3',buffer);emit('6800040000566a00');call('GetModuleFileNameA');emit('85c0');branch('0f84','patherror');emit('3de8030000');branch('0f83','patherror')
emit('31ff89f2');label('scan');emit('8a0284c0');branch('0f84','scanned');emit('3c5c');branch('0f85','next');emit('89d7');label('next');emit('42');branch('e9','scan')
label('scanned');emit('85ff');branch('0f84','patherror');emit('c6070056');call('SetCurrentDirectoryA');emit('85c0');branch('0f84','direrror');emit('c6075c47')
copy_name('engine');emit('6a086a0056');call('LoadLibraryExA');emit('85c0');branch('0f84','loaderror');emit('89c5')
for name,slot in [('setexe',set_slot),('main',main_slot)]:
 lea('83',strings[name]);emit('5055');call('GetProcAddress');emit('85c0');branch('0f84','exporterror');emit('8983');imm(slot)
copy_name('original');emit('56ff93');imm(set_slot);emit('83c4046a0a');lea('83',strings['empty']);emit('506a0053ff93');imm(main_slot);branch('e9','exit')
for name in ['patherror','direrror','loaderror','exporterror']:
 label(name);lea('93',strings[name]);branch('e9','error')
label('error');emit('6a10');lea('83',strings['title']);emit('50526a00');call('MessageBoxA');emit('b801000000')
label('exit');emit('50');call('ExitProcess');emit('5d5f5e5bc3')
for pos,name in fixups:struct.pack_into('<i',code,pos,labels[name]-pos-4)
assert len(code)<4096
# Minimal two-section native PE32; generated code has no absolute VA operands.
headers=bytearray(512);headers[:2]=b'MZ';struct.pack_into('<I',headers,60,0x80);headers[0x80:0x84]=b'PE\0\0'
struct.pack_into('<HHIIIHH',headers,0x84,0x14c,2,0,0,0,224,0x103)
opt=0x98;text_raw_size=align(len(code),512);data_raw_size=align(len(data),512)
struct.pack_into('<HBBIIIIII',headers,opt,0x10b,1,0,text_raw_size,data_raw_size,0,0x1000,0x1000,data_rva)
struct.pack_into('<III',headers,opt+28,0x400000,4096,512)
struct.pack_into('<HHHHHH',headers,opt+40,4,0,0,0,4,0)
struct.pack_into('<IIII',headers,opt+52,0,align(data_rva+len(data),4096),512,0)
struct.pack_into('<HH',headers,opt+68,2,0)
struct.pack_into('<IIIIII',headers,opt+72,0x100000,0x1000,0x100000,0x1000,0,16)
struct.pack_into('<II',headers,opt+104,data_rva,60)
iat_start=min(x for x,n in iat_ranges);iat_end=max(x+n for x,n in iat_ranges)
struct.pack_into('<II',headers,opt+192,iat_start,iat_end-iat_start)
section=opt+224
for i,(name,vs,rva,rs,rp,flags) in enumerate([(b'.text',len(code),0x1000,text_raw_size,512,0x60000020),(b'.idata',len(data),data_rva,data_raw_size,512+text_raw_size,0xc0000040)]):
 e=section+i*40;headers[e:e+8]=name.ljust(8,b'\0');struct.pack_into('<IIIIIIHHI',headers,e+8,vs,rva,rs,rp,0,0,0,0,flags)
result=bytes(headers)+bytes(code).ljust(text_raw_size,b'\0')+bytes(data).ljust(data_raw_size,b'\0')
(out/'CSI3-NoCD.exe').write_bytes(result)
(out/'launcher-code.bin').write_bytes(code)
(out/'launcher-data.bin').write_bytes(data)
report={'status':'Generated; independent startup harness and PE validation required','launcherSha256':hashlib.sha256(result).hexdigest(),'codeBytes':len(code),'imageBytes':len(result),'imports':imports,'strings':strings,'pathBufferRva':buffer,'pathBufferBytes':1024,'setExeSlotRva':set_slot,'mainSlotRva':main_slot,'entryRva':4096,'dataRva':data_rva,'originalExeUnmodified':True,'engineUnmodified':True,'gameExecuted':False,'supportedOriginalExeSha256':'0d2a6431822bb2881dbbe829d9b452f681b1e3b1e155327d7e77c7f9d9389d0a','supportedEngineSha256':'26e61a520afe71506fc549f4d0b58321708dfe8fd279a197232230eeac2e261a'}
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['launcherSha256','codeBytes','imageBytes']},indent=2))
