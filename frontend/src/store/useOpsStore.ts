import {create} from 'zustand'
import {alerts as seedAlerts,clusters as seedClusters,type Alert,type Cluster,liveMessages} from '../lib/mockData'
import {fetchNucleus,type ApiSource,type NucleusMetrics} from '../lib/api'
type View='dashboard'|'explorer'|'incidents'|'insights'|'settings'
type State={alerts:Alert[];clusters:Cluster[];metrics:NucleusMetrics|null;connection:'connecting'|'connected'|'fallback';error:string|null;source:ApiSource;view:View;layout:'split'|'stacked'|'raw'|'correlated';selected:string|null;sensitivity:number;query:string;dark:boolean;setView:(v:View)=>void;setLayout:(v:State['layout'])=>void;setSelected:(id:string|null)=>void;setSensitivity:(n:number)=>void;setSource:(s:ApiSource)=>void;setQuery:(s:string)=>void;toggleTheme:()=>void;ack:(id:string)=>void;resolve:(id:string)=>void;pushAlert:()=>void;loadRemote:()=>Promise<void>}
export const useOpsStore=create<State>((set,get)=>({
  alerts:seedAlerts,clusters:seedClusters,metrics:null,connection:'connecting',error:null,source:'synthetic',view:'dashboard',layout:'split',selected:null,sensitivity:72,query:'',dark:true,
  setView:view=>set({view}),setLayout:layout=>set({layout}),setSelected:selected=>set({selected}),setSensitivity:sensitivity=>set({sensitivity}),setSource:source=>{set({source});void get().loadRemote()},setQuery:query=>set({query}),toggleTheme:()=>set(s=>({dark:!s.dark})),
  ack:id=>set(s=>({clusters:s.clusters.map(c=>c.id===id?{...c,status:'acknowledged'}:c)})),resolve:id=>set(s=>({clusters:s.clusters.map(c=>c.id===id?{...c,status:'resolved'}:c)})),
  pushAlert:()=>{if(get().connection==='connected')return;const n=get().alerts.length+6300;const a:Alert={id:`ALT-${n}`,timestamp:new Date().toISOString(),service:['checkout-api','auth-service','edge-gateway'][n%3],host:`k8s-use1-${String(n%60).padStart(3,'0')}`,severity:n%4===0?'warning':'info',message:liveMessages[n%liveMessages.length],clusterId:null,isRootCause:false};set(s=>({alerts:[a,...s.alerts].slice(0,180)}))},
  loadRemote:async()=>{set({connection:'connecting',error:null});try{const data=await fetchNucleus(get().source,get().sensitivity);set({...data,connection:'connected',error:null})}catch(e){set({connection:'fallback',error:e instanceof Error?e.message:'Backend unavailable'})}}
}))
