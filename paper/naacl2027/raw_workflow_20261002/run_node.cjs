// CPU execution for reproducibility; native ChainForge execution is separate.
const fs=require('fs'),path=require('path'),vm=require('vm');
const args=process.argv.slice(2),get=k=>args[args.indexOf(k)+1];
if(!args.includes('--cases')||!args.includes('--out'))throw Error('Need --cases and --out');
const out=get('--out');if(fs.existsSync(out))throw Error('Refusing to overwrite output');
const context=vm.createContext({});vm.runInContext(fs.readFileSync(path.join(__dirname,'process.js'),'utf8'),context);
const cases=JSON.parse(fs.readFileSync(get('--cases'))),results={};
for(const c of cases)results[c.id]=JSON.parse(context.process({text:JSON.stringify(c.input)}));
fs.writeFileSync(out,JSON.stringify(results)+'\n');
console.log(JSON.stringify({node:process.version,cases:cases.length,statuses:Object.fromEntries(Object.entries(results).map(([k,v])=>[k,v.status]))}));
