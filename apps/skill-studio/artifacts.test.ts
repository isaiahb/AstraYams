import {test,expect} from 'bun:test';
import {normalizeArtifacts} from './src/ArtifactList';
test('artifact panel accepts mixed agent manifests without crashing',()=>{
 expect(normalizeArtifacts(['report.md',{path:'scene.xml',label:'World'},null,{},15,{path:4}])).toEqual([{path:'report.md'},{path:'scene.xml',label:'World'}]);
 expect(normalizeArtifacts({files:[]})).toEqual([]);
});
