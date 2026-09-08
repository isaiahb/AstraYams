export function normalizeArtifacts(input:unknown):{path:string,label?:string,name?:string,id?:string}[]{
 if(!Array.isArray(input))return [];
 return input.map(a=>typeof a==='string'?{path:a}:a).filter(a=>a&&typeof a.path==='string'&&a.path.length>0);
}
