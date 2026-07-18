import {create} from 'zustand'
import type {Alert} from '../lib/mockData'
import {fetchAiopsSample,fetchAiopsSummary,runAiopsEngine,type AiopsSummary,type EngineResult} from '../lib/api'

type EngineStatus='idle'|'running'|'done'|'error'
type SimPhase='idle'|'streaming'|'done'
type State={
  aiopsSummary:AiopsSummary|null
  engineStatus:EngineStatus
  engineResult:EngineResult|null
  engineError:string|null
  simAlerts:Alert[]
  simPhase:SimPhase
  dark:boolean
  toggleTheme:()=>void
  loadAiopsSummary:()=>Promise<void>
  runEngine:()=>Promise<void>
  simulate:()=>void
}
let simTimer:ReturnType<typeof setInterval>|null=null
export const useOpsStore=create<State>((set,get)=>({
  aiopsSummary:null,engineStatus:'idle',engineResult:null,engineError:null,simAlerts:[],simPhase:'idle',dark:true,
  toggleTheme:()=>set(s=>({dark:!s.dark})),
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
