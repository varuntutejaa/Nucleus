import {create} from 'zustand'
import {alerts as seedAlerts,clusters as seedClusters,type Alert,type Cluster,liveMessages} from '../lib/mockData'
import {fetchAiopsSample,fetchAiopsSummary,fetchNucleus,runAiopsEngine,type AiopsSummary,type ApiSource,type EngineResult,type NucleusMetrics} from '../lib/api'
type View='dashboard'|'explorer'|'incidents'|'insights'|'settings'
type Mode='live'|'aiopsFull'
type EngineStatus='idle'|'running'|'done'|'error'
type SimPhase='idle'|'streaming'|'done'
type State={alerts:Alert[];clusters:Cluster[];metrics:NucleusMetrics|null;connection:'connecting'|'connected'|'fallback';error:string|null;source:ApiSource;mode:Mode;aiopsSummary:AiopsSummary|null;engineStatus:EngineStatus;engineResult:EngineResult|null;engineError:string|null;simAlerts:Alert[];simPhase:SimPhase;view:View;layout:'split'|'stacked'|'raw'|'correlated';selected:string|null;sensitivity:number;query:string;dark:boolean;setView:(v:View)=>void;setLayout:(v:State['layout'])=>void;setSelected:(id:string|null)=>void;setSensitivity:(n:number)=>void;setSource:(s:ApiSource)=>void;setMode:(m:Mode)=>void;setQuery:(s:string)=>void;toggleTheme:()=>void;ack:(id:string)=>void;resolve:(id:string)=>void;pushAlert:()=>void;loadRemote:()=>Promise<void>;loadAiopsSummary:()=>Promise<void>;runEngine:()=>Promise<void>;simulate:()=>void}
let simTimer:ReturnType<typeof setInterval>|null=null
export const useOpsStore=create<State>((set,get)=>({
  alerts:seedAlerts,clusters:seedClusters,metrics:null,connection:'connecting',error:null,source:'synthetic',mode:'aiopsFull',aiopsSummary:null,engineStatus:'idle',engineResult:null,engineError:null,simAlerts:[],simPhase:'idle',view:'dashboard',layout:'split',selected:null,sensitivity:72,query:'',dark:true,
  setView:view=>set({view}),setLayout:layout=>set({layout}),setSelected:selected=>set({selected}),setSensitivity:sensitivity=>set({sensitivity}),setSource:source=>{set({source,mode:'live'});void get().loadRemote()},setQuery:query=>set({query}),toggleTheme:()=>set(s=>({dark:!s.dark})),
  setMode:mode=>{set({mode});if(mode==='aiopsFull')void get().loadAiopsSummary()},
  ack:id=>set(s=>({clusters:s.clusters.map(c=>c.id===id?{...c,status:'acknowledged'}:c)})),resolve:id=>set(s=>({clusters:s.clusters.map(c=>c.id===id?{...c,status:'resolved'}:c)})),
  pushAlert:()=>{if(get().connection==='connected')return;const n=get().alerts.length+6300;const a:Alert={id:`ALT-${n}`,timestamp:new Date().toISOString(),service:['checkout-api','auth-service','edge-gateway'][n%3],host:`k8s-use1-${String(n%60).padStart(3,'0')}`,severity:n%4===0?'warning':'info',message:liveMessages[n%liveMessages.length],clusterId:null,isRootCause:false};set(s=>({alerts:[a,...s.alerts].slice(0,180)}))},
  loadRemote:async()=>{set({connection:'connecting',error:null});try{const data=await fetchNucleus(get().source,get().sensitivity);set({...data,connection:'connected',error:null})}catch(e){set({connection:'fallback',error:e instanceof Error?e.message:'Backend unavailable'})}},
  loadAiopsSummary:async()=>{try{const summary=await fetchAiopsSummary();set({aiopsSummary:summary})}catch(e){set({aiopsSummary:null,engineError:e instanceof Error?e.message:'Could not reach Nucleus API'})}},
  runEngine:async()=>{if(simTimer){clearInterval(simTimer);simTimer=null}set({engineStatus:'running',engineError:null,simPhase:'done'});try{const result=await runAiopsEngine();set({engineResult:result,engineStatus:'done'})}catch(e){set({engineStatus:'error',engineError:e instanceof Error?e.message:'Engine run failed'})}},
  simulate:()=>{
    if(get().simPhase==='streaming')return
    if(simTimer){clearInterval(simTimer);simTimer=null}
    set({simAlerts:[],simPhase:'streaming',engineResult:null,engineStatus:'idle',engineError:null})
    void fetchAiopsSample(220).then(res=>{
      const items=res.alerts,severityMap:Record<string,Alert['severity']>={Critical:'critical',Warning:'warning',Info:'info'}
      let i=0
      simTimer=setInterval(()=>{
        if(i>=items.length){if(simTimer)clearInterval(simTimer);simTimer=null;set({simPhase:'done'});return}
        const batch=items.slice(i,i+2).map(a=>({id:a.alert_id,timestamp:a.timestamp,service:a.metric,host:a.host,severity:severityMap[a.severity]??'info',message:a.message,clusterId:null,isRootCause:false} as Alert))
        i+=2
        set(s=>({simAlerts:[...batch.reverse(),...s.simAlerts].slice(0,200)}))
      },45)
    }).catch(e=>{set({simPhase:'idle',engineError:e instanceof Error?e.message:'Could not load alert sample'})})
  }
}))
