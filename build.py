from pathlib import Path
import runpy,hashlib,json
root=Path(__file__).resolve().parent
manifest=json.loads((root/'build-manifest.json').read_text())
for mode,item in manifest.items():
 runpy.run_path(str(root/'src'/('build_'+mode.lower()+'.py')),run_name='__main__')
 output=root/'dist'/mode/item['exe']
 assert hashlib.sha256(output.read_bytes()).hexdigest()==item['sha256'],mode+' reproducibility check failed'
 print(mode+': exact released executable reproduced')
