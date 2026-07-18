import {create} from 'zustand'
import type {Alert} from '../lib/mockData'
import {DEMO_SIZES,fetchAiopsSample,fetchAiopsSummary,runAiopsEngine,runAiopsSampleEngine,type AiopsSummary,type DemoSize,type EngineResult} from '../lib/api'

type EngineStatus='idle'|'running'|'done'|'error'
type SimPhase='idle'|'streaming'|'done'
type BenchmarkStatus='idle'|'running'|'done'|'error'
type FullRunStatus='idle'|'running'|'done'|'error'
type BenchmarkEntry={status:BenchmarkStatus;result:EngineResult|null;elapsedMs:number|null;error:string|null}
const emptyBenchmarks=():Record<DemoSize,BenchmarkEntry>=>Object.fromEntries(DEMO_SIZES.map(n=>[n,{status:'idle',result:null,elapsedMs:null,error:null}])) as Record<DemoSize,BenchmarkEntry>
const SIM_SAMPLE_SIZE=100
const SIM_BATCH_SIZE=2
const SIM_TICK_MS=70
const SIM_BURST_SIZE=10
const SIM_BURST_TICK_MS=40
const SIM_VISIBLE_CAP=100
const SERIES_LEN=8

// Idle baseline ranges: this dataset only contains threshold-breaching
// (already-alerting) readings, so there's no genuine "normal" telemetry to
// draw an at-rest sparkline from. These ranges are illustrative resting
// values (kept well under each metric's real alert threshold), not
// observations from the dataset -- the real numbers kick in the moment
// alerts start streaming (see `simulate`, which pushes each alert's
// genuine `value` field into the series).
const BASELINES:Record<string,[number,number]>={CPU_util_pct:[2,8],MEM_real_util:[15,30],Sess_Connect:[150,350]}
const seedSeries=():Record<string,number[]>=>{
  const out:Record<string,number[]>={}
  for(const key in BASELINES){
    const [lo,hi]=BASELINES[key]
    let v=lo+Math.random()*(hi-lo)
    out[key]=Array.from({length:SERIES_LEN},()=>{v=Math.max(lo,Math.min(hi,v+(Math.random()-0.5)*(hi-lo)*0.3));return v})
  }
  return out
}
const lastOf=(series:Record<string,number[]>,key:string)=>{const s=series[key];return s&&s.length?s[s.length-1]:0}
const jitterSeries=(series:Record<string,number[]>):Record<string,number[]>=>{
  const out:Record<string,number[]>={...series}
  for(const key in BASELINES){
    const [lo,hi]=BASELINES[key]
    const prev=out[key]??[]
    const last=prev.length?prev[prev.length-1]:lo+Math.random()*(hi-lo)
    const next=Math.max(lo,Math.min(hi,last+(Math.random()-0.5)*(hi-lo)*0.35))
    out[key]=[...prev,next].slice(-SERIES_LEN)
  }
  return out
}

type View='operations'|'benchmark'|'dataset'
type State={
  view:View
  setView:(v:View)=>void
  aiopsSummary:AiopsSummary|null
  monitoringSince:number
  lastSyncedAt:number|null
  engineStatus:EngineStatus
  engineResult:EngineResult|null
  engineError:string|null
  simAlerts:Alert[]
  simPhase:SimPhase
  alertsReceived:number
  affectedHosts:Set<string>
  metricCounts:Record<string,number>
  metricSeries:Record<string,number[]>
  benchmarks:Record<DemoSize,BenchmarkEntry>
  dark:boolean
  toggleTheme:()=>void
  sidebarOpen:boolean
  toggleSidebar:()=>void
  rightPanelVisible:boolean
  toggleRightPanel:()=>void
  fullRunStatus:FullRunStatus
  fullRunResult:EngineResult|null
  fullRunElapsedMs:number|null
  fullRunError:string|null
  runFullDataset:()=>Promise<void>
  loadAiopsSummary:()=>Promise<void>
  runEngine:()=>Promise<void>
  runBenchmark:(size:DemoSize)=>Promise<void>
  simulate:()=>void
  reset:()=>void
  jitterBaseline:()=>void
}
let simTimer:ReturnType<typeof setTimeout>|null=null
const clearSimTimer=()=>{if(simTimer){clearTimeout(simTimer);simTimer=null}}

export const useOpsStore=create<State>((set,get)=>({
  view:'operations',setView:view=>set({view}),
  aiopsSummary:null,monitoringSince:Date.now(),lastSyncedAt:null,engineStatus:'idle',engineResult:null,engineError:null,
  simAlerts:[],simPhase:'idle',alertsReceived:0,affectedHosts:new Set(),metricCounts:{},metricSeries:seedSeries(),
  benchmarks:emptyBenchmarks(),dark:true,
  toggleTheme:()=>set(s=>({dark:!s.dark})),
  sidebarOpen:true,toggleSidebar:()=>set(s=>({sidebarOpen:!s.sidebarOpen})),
  rightPanelVisible:true,toggleRightPanel:()=>set(s=>({rightPanelVisible:!s.rightPanelVisible})),
  fullRunStatus:'idle',fullRunResult:null,fullRunElapsedMs:null,fullRunError:null,
  runFullDataset:async()=>{
    if(get().fullRunStatus==='running')return
    set({fullRunStatus:'running',fullRunError:null})
    const t0=performance.now()
    try{const result=await runAiopsEngine(true);set({fullRunResult:result,fullRunStatus:'done',fullRunElapsedMs:performance.now()-t0})}
    catch(e){set({fullRunStatus:'error',fullRunError:e instanceof Error?e.message:'Full dataset run failed'})}
  },
  loadAiopsSummary:async()=>{try{const summary=await fetchAiopsSummary();set({aiopsSummary:summary,lastSyncedAt:Date.now()})}catch(e){set({aiopsSummary:null,engineError:e instanceof Error?e.message:'Could not reach Nucleus API'})}},
  jitterBaseline:()=>{if(get().simPhase==='idle'&&!get().engineResult)set(s=>({metricSeries:jitterSeries(s.metricSeries)}))},
  runEngine:async()=>{
    clearSimTimer()
    set({engineStatus:'running',engineError:null,simPhase:'done'})
    try{const result=await runAiopsSampleEngine(100,true);set({engineResult:result,engineStatus:'done'})}
    catch(e){set({engineStatus:'error',engineError:e instanceof Error?e.message:'Engine run failed'})}
  },
  simulate:()=>{
    if(get().simPhase==='streaming')return
    clearSimTimer()
    set({simAlerts:[],simPhase:'streaming',alertsReceived:0,affectedHosts:new Set(),metricCounts:{},engineResult:null,engineStatus:'idle',engineError:null,rightPanelVisible:true})
    void fetchAiopsSample(SIM_SAMPLE_SIZE).then(res=>{
      const items=res.alerts,severityMap:Record<string,Alert['severity']>={Critical:'critical',Warning:'warning',Info:'info'}
      const toAlert=(a:typeof items[number])=>({id:a.alert_id,timestamp:a.timestamp,service:a.metric,host:a.host,severity:severityMap[a.severity]??'info',message:a.message,clusterId:null,isRootCause:false} as Alert)
      let i=0
      // First SIM_BURST_SIZE alerts land fast (SIM_BURST_TICK_MS) so the panel
      // doesn't feel like it's crawling on open; the rest then continue to
      // trickle in automatically at the normal pace, no further input needed.
      const step=()=>{
        if(i>=items.length){simTimer=null;set({simPhase:'done'});return}
        const slice=items.slice(i,i+SIM_BATCH_SIZE)
        i+=SIM_BATCH_SIZE
        set(s=>{
          const affected=new Set(s.affectedHosts)
          const metrics={...s.metricCounts}
          const series:Record<string,number[]>={...s.metricSeries}
          slice.forEach(a=>{
            affected.add(a.host)
            metrics[a.metric]=(metrics[a.metric]||0)+1
            if(BASELINES[a.metric]){
              const prev=series[a.metric]??[]
              series[a.metric]=[...prev,a.value].slice(-SERIES_LEN)
            }
          })
          return{simAlerts:[...slice.map(toAlert).reverse(),...s.simAlerts].slice(0,SIM_VISIBLE_CAP),alertsReceived:Math.min(i,items.length),affectedHosts:affected,metricCounts:metrics,metricSeries:series}
        })
        simTimer=setTimeout(step,i<SIM_BURST_SIZE?SIM_BURST_TICK_MS:SIM_TICK_MS)
      }
      step()
    }).catch(e=>{set({simPhase:'idle',engineError:e instanceof Error?e.message:'Could not load alert sample'})})
  },
  reset:()=>{
    clearSimTimer()
    set({simAlerts:[],simPhase:'idle',alertsReceived:0,affectedHosts:new Set(),metricCounts:{},metricSeries:seedSeries(),engineResult:null,engineStatus:'idle',engineError:null})
  },
  runBenchmark:async(size)=>{
    if(get().benchmarks[size].status==='running')return
    set(s=>({benchmarks:{...s.benchmarks,[size]:{status:'running',result:null,elapsedMs:null,error:null}}}))
    const t0=performance.now()
    try{
      const result=await runAiopsSampleEngine(size)
      set(s=>({benchmarks:{...s.benchmarks,[size]:{status:'done',result,elapsedMs:performance.now()-t0,error:null}}}))
    }catch(e){
      set(s=>({benchmarks:{...s.benchmarks,[size]:{status:'error',result:null,elapsedMs:null,error:e instanceof Error?e.message:'Run failed'}}}))
    }
  }
}))

export {lastOf}
