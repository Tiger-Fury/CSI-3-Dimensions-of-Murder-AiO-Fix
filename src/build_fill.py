from pathlib import Path
import struct,json,hashlib
root=Path(__file__).resolve().parents[1];out=root/'dist'/'Fill';out.mkdir(parents=True,exist_ok=True)
align=lambda n,a:(n+a-1)//a*a
data=bytearray(80);data_rva=0x2000
def alloc(payload,alignment=1):
 data.extend(b'\0'*(align(len(data),alignment)-len(data)));offset=len(data);data.extend(payload);return data_rva+offset
def string(s):return alloc(s.encode('ascii')+b'\0')
imports={};iat_ranges=[]
for index,(dll,funcs) in enumerate([('KERNEL32.dll',['GetModuleFileNameA','SetCurrentDirectoryA','LoadLibraryExA','GetProcAddress','ExitProcess','VirtualProtect','FlushInstructionCache']),('USER32.dll',['MessageBoxA','GetSystemMetrics','SetProcessDPIAware','SetWindowLongA','SetWindowPos','CreateWindowExA','SetClassLongA','InvalidateRect','RegisterClassA','DefWindowProcA']),('GDI32.dll',['GetStockObject'])]):
 dllname=string(dll);hints=[alloc(b'\0\0'+n.encode()+b'\0',2) for n in funcs]
 ilt=alloc(b''.join(struct.pack('<I',n) for n in hints)+b'\0'*4,4)
 iat=alloc(b''.join(struct.pack('<I',n) for n in hints)+b'\0'*4,4)
 struct.pack_into('<IIIII',data,index*20,ilt,0,0,dllname,iat)
 for i,name in enumerate(funcs):imports[name]=iat+i*4
 iat_ranges.append((iat,len(funcs)*4+4))
strings={k:string(v) for k,v in {'static':'CSI3FitBackdrop','displayerror':'The engine build could not be adjusted for this display mode. Use the original NoCD launcher.','engine':'t3.mll','original':'CSI3.exe','setexe':'?GameEngine_SetExeFile@@YAXPBD@Z','main':'?GameEngine_WinMain@@YGHPAUHINSTANCE__@@0PADH@Z','empty':'','title':'CSI: 3 Dimensions of Murder','patherror':'Could not determine the game folder. Place this launcher in the game installation.','direrror':'Could not open the game folder.','loaderror':'Could not load t3.mll. Keep this launcher beside the original game files. A required engine dependency may be missing.','exporterror':'The expected Telltale engine entry points were not found in t3.mll.'}.items()}
buffer=alloc(b'\0'*1024,4);set_slot=alloc(b'\0'*4,4);main_slot=alloc(b'\0'*4,4)
DISPLAY_MODE='Fill'
code=bytearray();labels={};fixups=[]

display_slots={n:alloc(b'\0'*4,4) for n in ['desktopW','desktopH','width','height','left','top','prefSink','oldProtect','protectScratch','busy','background']}
rva_fixups=[]
rect_fixups=[]
camera_sites=[0x56f3f,0xb452a,0xb3a18,0xb3c3a,0xb30f0,0xb1fe5]
backdrop_class=alloc(b'\0'*40,4)
def load(reg,name):emit('8b'+reg);imm(display_slots[name])
def store(name):emit('8983');imm(display_slots[name])
def push_value(name):emit('ffb3');imm(display_slots[name])
def engine_address(rva):emit('8d85');imm(rva)
def check(condition):branch(condition,'displayerror')
def protect(rva,n,restore=False):
 lea('93',display_slots['protectScratch' if restore else 'oldProtect']);emit('52')
 if restore:push_value('oldProtect')
 else:emit('6a40')
 emit('68');imm(n);engine_address(rva);emit('50');call('VirtualProtect');emit('85c0');check('0f84')
def flush(rva,n):
 emit('68');imm(n);engine_address(rva);emit('506aff');call('FlushInstructionCache');emit('85c0');check('0f84')
def display_init():
 # Verify every executable patch site before modifying this process's engine image.
 for rva,handler in [(0x57330,0x36c9b5),(0x30dde0,0x3a81ac)]:
  emit('6681bd');imm(rva);emit('6aff');check('0f85')
  emit('80bd');imm(rva+2);emit('68');check('0f85')
  engine_address(handler);emit('3985');imm(rva+3);check('0f85')
 emit('80bd');imm(0x5a01c);emit('68');check('0f85')
 engine_address(0x5d5700);emit('3985');imm(0x5a01d);check('0f85')
 if DISPLAY_MODE=='Fill':
  for site in camera_sites:
   emit('6681bd');imm(site);emit('ff15');check('0f85')
   engine_address(0x3b7388);emit('3985');imm(site+2);check('0f85')
 call('SetProcessDPIAware')
 for name,index in [('desktopW',0),('desktopH',1)]:
  emit('6a'+format(index,'02x'));call('GetSystemMetrics');emit('3d40010000');check('0f8c');emit('3d00400000');check('0f8f');store(name)
 if DISPLAY_MODE=='Fit':
  load('83','desktopW');emit('6bc003');load('8b','desktopH');emit('c1e10239c8');branch('0f8e','fit_width')
  load('83','desktopH');store('height');emit('c1e00231d2b903000000f7f1');store('width');branch('e9','fit_center')
  label('fit_width');load('83','desktopW');store('width');emit('6bc00331d2b904000000f7f1');store('height')
  label('fit_center')
  for axis,size,pos in [('desktopW','width','left'),('desktopH','height','top')]:
   load('83',axis);emit('2b83');imm(display_slots[size]);emit('d1e8');store(pos)
  # Dedicated class avoids STATIC's theme-dependent paint behaviour entirely.
  emit('8b83');imm(imports['DefWindowProcA']);emit('8983');imm(backdrop_class+4)
  emit('899b');imm(backdrop_class+16)
  emit('6a04');call('GetStockObject');emit('8983');imm(backdrop_class+28)
  lea('83',strings['static']);emit('8983');imm(backdrop_class+36)
  lea('83',backdrop_class);emit('50');call('RegisterClassA');emit('85c0');check('0f84')
  emit('6a00536a006a00');push_value('desktopH');push_value('desktopW');emit('6a006a006800000090');lea('83',strings['empty']);emit('50');lea('83',strings['static']);emit('506880000000');call('CreateWindowExA');emit('85c0');check('0f84');store('background')
 else:
  load('83','desktopW');store('width');load('83','desktopH');store('height')
 # Windowed preference reads go into a private sink instead of undoing the selected mode.
 protect(0x5a01d,4);lea('83',display_slots['prefSink']);emit('8985');imm(0x5a01d);protect(0x5a01d,4,True);flush(0x5a01d,4)
 # Lock the fullscreen toggle to this borderless mode for this process only.
 protect(0x57330,1);emit('c685');imm(0x57330);emit('c3');protect(0x57330,1,True);flush(0x57330,1)
 # Replace the hardcoded 800x600 window-adjust handler with our own layout callback.
 protect(0x30dde0,5);emit('c685');imm(0x30dde0);emit('e9')
 emit('8d83');rva_fixups.append(len(code));imm(0);emit('29e82de5dd30008985');imm(0x30dde1)
 protect(0x30dde0,5,True);flush(0x30dde0,5)
 emit('c685');imm(0x5d5700);emit('01')
 if DISPLAY_MODE=='Fill':
  # Keep the real desktop-sized backbuffer and input conversion. Camera projection
  # and its corresponding picking helpers use 4:3 to retain the complete view.
  for site in camera_sites:
   protect(site,6);emit('c685');imm(site);emit('e8')
   emit('8d83');rect_fixups.append((len(code),{0xb3c3a:'pick_rect',0xb452a:'pick_ray'}.get(site,'render_rect')));imm(0);emit('29e82d');imm(site+5);emit('8985');imm(site+1)
   emit('c685');imm(site+5);emit('90');protect(site,6,True);flush(site,6)
def display_callback():
 label('adjust_callback');emit('9c60e800000000');ret=0x1000+len(code);emit('5b81eb');imm(ret)
 emit('8b74241885f6');branch('0f84','adjust_done');emit('8b7e0485ff');branch('0f84','adjust_done')
 emit('83bb');imm(display_slots['busy']);emit('00');branch('0f85','adjust_done')
 emit('c783');imm(display_slots['busy']);imm(1)
 emit('68000000966af057');call('SetWindowLongA')
 emit('68000004006aec57');call('SetWindowLongA')
 emit('6a60');push_value('height');push_value('width');push_value('top');push_value('left');emit('6a0057');call('SetWindowPos')
 emit('c783');imm(display_slots['busy']);imm(0)
 label('adjust_done');emit('619dc3')
 # Both point-at-depth and normalized-direction ray helpers accept physical X.
 # The verified original frames place X at different offsets at the API call.
 for name,offset in [('pick_rect',0xbc),('pick_ray',0x98)]:
  label(name);emit('53e800000000');ret=0x1000+len(code);emit('5b81eb');imm(ret)
  load('83','height');emit('c1e00231d26a03f7342483c4040faf8424');imm(offset)
  emit('99f7bb');imm(display_slots['desktopW']);emit('898424');imm(offset);emit('5b');branch('e9','render_rect')
 label('render_rect');emit('538b4c240ce800000000');ret=0x1000+len(code);emit('5b81eb');imm(ret)
 emit('31c08901894104');load('83','height');emit('89410cc1e00231d2bb03000000f7f3894108b8010000005bc20800')

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
copy_name('original');emit('56ff93');imm(set_slot);emit('83c404');display_init();emit('6a0a');lea('83',strings['empty']);emit('506a0053ff93');imm(main_slot);branch('e9','exit')
for name in ['patherror','direrror','loaderror','exporterror','displayerror']:
 label(name);lea('93',strings[name]);branch('e9','error')
label('error');emit('6a10');lea('83',strings['title']);emit('50526a00');call('MessageBoxA');emit('b801000000')
label('exit');emit('50');call('ExitProcess');emit('5d5f5e5bc3')
display_callback()
for pos in rva_fixups:struct.pack_into('<I',code,pos,0x1000+labels['adjust_callback'])
for pos,target in rect_fixups:struct.pack_into('<I',code,pos,0x1000+labels[target])
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
struct.pack_into('<II',headers,opt+104,data_rva,80)
iat_start=min(x for x,n in iat_ranges);iat_end=max(x+n for x,n in iat_ranges)
struct.pack_into('<II',headers,opt+192,iat_start,iat_end-iat_start)
section=opt+224
for i,(name,vs,rva,rs,rp,flags) in enumerate([(b'.text',len(code),0x1000,text_raw_size,512,0x60000020),(b'.idata',len(data),data_rva,data_raw_size,512+text_raw_size,0xc0000040)]):
 e=section+i*40;headers[e:e+8]=name.ljust(8,b'\0');struct.pack_into('<IIIIIIHHI',headers,e+8,vs,rva,rs,rp,0,0,0,0,flags)
result=bytes(headers)+bytes(code).ljust(text_raw_size,b'\0')+bytes(data).ljust(data_raw_size,b'\0')
(out/'CSI3-Fill.exe').write_bytes(result)
(out/'launcher-code.bin').write_bytes(code)
(out/'launcher-data.bin').write_bytes(data)
report={'mode':DISPLAY_MODE,'displaySlots':display_slots,'callbackRva':0x1000+labels['adjust_callback'],'enginePatchesInMemoryOnly':True,'status':'Generated; independent startup harness and PE validation required','launcherSha256':hashlib.sha256(result).hexdigest(),'codeBytes':len(code),'imageBytes':len(result),'imports':imports,'strings':strings,'pathBufferRva':buffer,'pathBufferBytes':1024,'setExeSlotRva':set_slot,'mainSlotRva':main_slot,'entryRva':4096,'dataRva':data_rva,'originalExeUnmodified':True,'engineUnmodified':True,'gameExecuted':False,'supportedOriginalExeSha256':'0d2a6431822bb2881dbbe829d9b452f681b1e3b1e155327d7e77c7f9d9389d0a','supportedEngineSha256':'26e61a520afe71506fc549f4d0b58321708dfe8fd279a197232230eeac2e261a'}
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['launcherSha256','codeBytes','imageBytes']},indent=2))
