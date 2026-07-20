import {memo,useEffect,useRef,useState} from 'react'
import {AnimatePresence,motion} from 'framer-motion'
import {Activity,ArrowRight,BarChart3,Bot,CheckCircle2,ChevronDown,ChevronRight,Cpu,Database,GitBranch,GitCompare,HardDrive,Layers,Loader2,MemoryStick,Menu,MessageSquare,Network,PanelRight,Play,RotateCcw,Server,ShieldAlert,ShieldCheck,Sun,Moon,Timer,Wrench,Zap} from 'lucide-react'
import {useShallow} from 'zustand/react/shallow'
import {lastOf,useOpsStore} from './useOpsStore'
import {askIncidentCopilot,DEMO_SIZES,fmtTime,type Alert,type CopilotQuestion,type CopilotResponse,type DemoSize,type EngineIncident,type EngineResult} from './api'
import './App.css'

type OpsState='healthy'|'incident'|'resolved'
const severityLabel={critical:'Critical',warning:'Warning',info:'Info'}
function useNow(intervalMs=1000){const [now,setNow]=useState(()=>Date.now());useEffect(()=>{const t=setInterval(()=>setNow(Date.now()),intervalMs);return()=>clearInterval(t)},[intervalMs]);return now}
// Deterministic per-host "last check-in" -- a stable hash of the hostname
// plus a slow real-time drift, so it looks alive on hover without needing
// a per-host timer. Purely illustrative (no backend concept of per-host
// polling exists), unlike everything else in this app -- see conversation.
function checkInSeconds(host:string,now:number){
  let hash=0
  for(let i=0;i<host.length;i++)hash=(hash*31+host.charCodeAt(i))>>>0
  return (hash%9)+Math.floor(now/4000)%6
}
function Severity({value}:{value:Alert['severity']}){return <span className={`severity ${value}`}><i/>{severityLabel[value]}</span>}
function Sidebar(){
  const {aiopsSummary,lastSyncedAt,engineError,view,setView,sidebarOpen}=useOpsStore(useShallow(s=>({aiopsSummary:s.aiopsSummary,lastSyncedAt:s.lastSyncedAt,engineError:s.engineError,view:s.view,setView:s.setView,sidebarOpen:s.sidebarOpen})))
  const now=useNow(1000)
  const connected=!!aiopsSummary
  const syncedAgo=lastSyncedAt?Math.max(0,Math.round((now-lastSyncedAt)/1000)):null
  return <aside className={`sidebar ${sidebarOpen?'':'closed'}`}><div className="brand"><span><Network size={18}/></span><b>Nucleus</b></div><nav><button className={view==='operations'?'active':''} onClick={()=>setView('operations')}><Database size={17}/><span>Operations</span></button><button className={view==='benchmark'?'active':''} onClick={()=>setView('benchmark')}><GitCompare size={17}/><span>Benchmark</span></button><button className={view==='dataset'?'active':''} onClick={()=>setView('dataset')}><HardDrive size={17}/><span>AIOps Dataset</span></button></nav><div className="side-bottom"><div className="engine"><div><Zap size={14}/> Backend API</div><strong className={connected?'':'down'}><i/>{connected?'Connected':'Unreachable'}</strong><small>{connected?`${aiopsSummary.raw_count.toLocaleString()} alerts indexed`:engineError??'Retrying…'}</small>{syncedAgo!==null&&<small className="sync-line">Last sync: {syncedAgo===0?'just now':`${syncedAgo}s ago`}</small>}</div></div></aside>
}
function LiveClock(){const now=useNow(1000);return <div className="live-clock"><i/>{new Date(now).toLocaleTimeString([],{hour12:false})}</div>}
function Topbar(){
  const {dark,toggleTheme,view,aiopsSummary,simPhase,engineResult,simulate,sidebarOpen,toggleSidebar,rightPanelVisible,toggleRightPanel,resetAll}=useOpsStore(useShallow(s=>({dark:s.dark,toggleTheme:s.toggleTheme,view:s.view,aiopsSummary:s.aiopsSummary,simPhase:s.simPhase,engineResult:s.engineResult,simulate:s.simulate,sidebarOpen:s.sidebarOpen,toggleSidebar:s.toggleSidebar,rightPanelVisible:s.rightPanelVisible,toggleRightPanel:s.toggleRightPanel,resetAll:s.resetAll})))
  const showSimulate=view==='operations'&&simPhase==='idle'&&!engineResult
  const showPanelToggle=view==='operations'&&simPhase!=='idle'
  return <header className="topbar">
    <div className="topbar-left">
      <button className="icon-btn" onClick={toggleSidebar} title={sidebarOpen?'Collapse sidebar':'Expand sidebar'}><Menu size={16}/></button>
      <div className="crumb"><span>Operations</span><ChevronRight size={14}/><b>Live monitoring</b></div>
    </div>
    <div className="top-actions">
      {showPanelToggle&&<button className={`icon-btn ${rightPanelVisible?'active-toggle':''}`} onClick={toggleRightPanel} title={rightPanelVisible?'Hide alert panel':'Show alert panel'}><PanelRight size={16}/></button>}
      {showSimulate&&<button className="simulate-btn icon-btn" disabled={!aiopsSummary} title="Simulate incoming alerts" aria-label="Simulate incoming alerts" onClick={()=>simulate()}><Activity size={15}/></button>}
      <button className="reset-btn icon-btn" onClick={resetAll} title="Reset saved dashboard data" aria-label="Reset saved dashboard data"><RotateCcw size={15}/><span>Reset</span></button>
      <LiveClock/>
      <button className="icon-btn" onClick={toggleTheme}>{dark?<Sun size={16}/>:<Moon size={16}/>}</button>
    </div>
  </header>
}
function PanelHead({title,icon,meta}:{title:string;icon:React.ReactNode;meta:React.ReactNode}){return <div className="panel-head"><h2>{icon}{title}</h2><span>{meta}</span></div>}

function fmtUptime(ms:number){const s=Math.floor(ms/1000),h=Math.floor(s/3600),m=Math.floor((s%3600)/60);return h>0?`${h}h ${m}m`:`${m}m ${s%60}s`}
function OperationsHealth({opsState}:{opsState:OpsState}){
  const {aiopsSummary,monitoringSince,alertsReceived,affectedHosts,engineResult}=useOpsStore(useShallow(s=>({aiopsSummary:s.aiopsSummary,monitoringSince:s.monitoringSince,alertsReceived:s.alertsReceived,affectedHosts:s.affectedHosts,engineResult:s.engineResult})))
  const now=useNow(1000)
  if(opsState==='healthy')return <div className="ops-banner healthy"><span className="icon-badge"><ShieldCheck size={22}/></span><div><b>All systems operational</b><span>{aiopsSummary?.host_count??'—'} hosts monitored · 0 active alerts · monitoring for {fmtUptime(now-monitoringSince)}</span></div><i className="ops-pulse"/></div>
  if(opsState==='incident')return <div className="ops-banner incident"><span className="icon-badge"><ShieldAlert size={22}/></span><div><b>Incident in progress</b><span>{alertsReceived.toLocaleString()} alerts received · {affectedHosts.size} hosts affected</span></div><i className="ops-pulse"/></div>
  const m=engineResult?.metrics
  return <div className="ops-banner resolved"><span className="icon-badge"><ShieldCheck size={22}/></span><div><b>Incident resolved</b><span>{m?.raw_count.toLocaleString()} alerts → {m?.incident_count.toLocaleString()} incidents · {m?.reduction_pct.toFixed(2)}% noise reduction</span></div></div>
}

const clusterTone=(opsState:OpsState,affected:number)=>opsState==='incident'&&affected>0?'critical':opsState==='resolved'&&affected>0?'resolved':'ok'
function ClusterCards({opsState}:{opsState:OpsState}){
  const {aiopsSummary,affectedHosts}=useOpsStore(useShallow(s=>({aiopsSummary:s.aiopsSummary,affectedHosts:s.affectedHosts})))
  if(!aiopsSummary)return null
  const osHosts=aiopsSummary.hosts.filter(h=>h.startsWith('os_'))
  const dbHosts=aiopsSummary.hosts.filter(h=>h.startsWith('db_'))
  const osAffected=osHosts.filter(h=>affectedHosts.has(h)).length
  const dbAffected=dbHosts.filter(h=>affectedHosts.has(h)).length
  return <div className="card-grid">
    <div className={`stat-card ${clusterTone(opsState,osAffected)}`} title={osHosts.join(', ')}>
      <span className="icon-badge"><Server size={19}/></span><div><span>Linux Compute Cluster</span><b>{osHosts.length} Hosts</b></div>
      {osAffected>0&&opsState!=='healthy'&&<em>{osAffected} affected</em>}
    </div>
    <div className={`stat-card ${clusterTone(opsState,dbAffected)}`} title={dbHosts.join(', ')}>
      <span className="icon-badge"><Database size={19}/></span><div><span>Oracle Database Cluster</span><b>{dbHosts.length} Hosts</b></div>
      {dbAffected>0&&opsState!=='healthy'&&<em>{dbAffected} affected</em>}
    </div>
  </div>
}

const paramTone=(opsState:OpsState,count:number)=>opsState==='incident'&&count>0?'critical':opsState==='resolved'&&count>0?'resolved':'ok'
const fmtMetric=(key:string,v:number)=>key==='Sess_Connect'?Math.round(v).toLocaleString():`${v.toFixed(1)}%`
function Sparkline({data}:{data:number[]}){
  if(data.length<2)return null
  const w=64,h=24,min=Math.min(...data),max=Math.max(...data),range=max-min||1
  const pts=data.map((v,i)=>`${(i/(data.length-1))*w},${h-((v-min)/range)*h}`).join(' ')
  return <svg className="sparkline" width={w} height={h} viewBox={`0 0 ${w} ${h}`}><polyline points={pts} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
}
function ParameterCards({opsState}:{opsState:OpsState}){
  const {metricCounts,metricSeries}=useOpsStore(useShallow(s=>({metricCounts:s.metricCounts,metricSeries:s.metricSeries})))
  const params=[
    {key:'CPU_util_pct',label:'CPU Utilization',icon:<Cpu size={20}/>},
    {key:'MEM_real_util',label:'Memory',icon:<MemoryStick size={20}/>},
    {key:'Sess_Connect',label:'Sessions',icon:<BarChart3 size={20}/>},
  ]
  return <div className="card-grid">{params.map(p=>{
    const count=metricCounts[p.key]||0
    const series=metricSeries[p.key]||[]
    return <div key={p.key} className={`stat-card ${paramTone(opsState,count)}`}>
      <span className="icon-badge">{p.icon}</span>
      <div><span>{p.label}</span><b>{fmtMetric(p.key,lastOf(metricSeries,p.key))}</b></div>
      <Sparkline data={series}/>
    </div>
  })}</div>
}

function HostChip({host,opsState,Icon,now}:{host:string;opsState:OpsState;Icon:typeof Server;now:number}){
  const isAffected=useOpsStore(s=>s.affectedHosts.has(host))
  const cls=opsState==='incident'&&isAffected?'critical':opsState==='resolved'&&isAffected?'resolved':'ok'
  return <div className={`host-chip ${cls}`} title={`Last check-in: ${checkInSeconds(host,now)}s ago`}><Icon size={13}/>{host}</div>
}
function HostGroup({label,hosts,Icon,opsState,now}:{label:string;hosts:string[];Icon:typeof Server;opsState:OpsState;now:number}){
  if(hosts.length===0)return null
  return <div className="host-group">
    <div className="host-group-label"><Icon size={13}/>{label}<span>{hosts.length}</span></div>
    <div className="host-grid">{hosts.map(h=><HostChip key={h} host={h} opsState={opsState} Icon={Icon} now={now}/>)}</div>
  </div>
}
function HostGrid({opsState}:{opsState:OpsState}){
  const aiopsSummary=useOpsStore(s=>s.aiopsSummary)
  const now=useNow(4000)
  if(!aiopsSummary)return null
  const osHosts=aiopsSummary.hosts.filter(h=>h.startsWith('os_'))
  const dbHosts=aiopsSummary.hosts.filter(h=>h.startsWith('db_'))
  return <div className="host-groups">
    <HostGroup label="Linux hosts" hosts={osHosts} Icon={Server} opsState={opsState} now={now}/>
    <HostGroup label="Oracle DB hosts" hosts={dbHosts} Icon={Database} opsState={opsState} now={now}/>
  </div>
}

const LiveAlertItem=memo(function LiveAlertItem({a}:{a:Alert}){
  return <div className={`live-alert-item ${a.isRootCause?'root':''}`}>
    <div className="live-alert-top"><Severity value={a.severity}/><time>{fmtTime(a.timestamp)}</time></div>
    <b>{a.message}</b>
    <span>{a.service} <i>·</i> <code>{a.host}</code></span>
  </div>
})
function LiveAlertPanel(){
  const {simAlerts,simPhase}=useOpsStore(useShallow(s=>({simAlerts:s.simAlerts,simPhase:s.simPhase})))
  return <motion.aside className="alert-side-panel" initial={{x:'100%'}} animate={{x:0}} exit={{x:'100%'}} transition={{duration:.32,ease:'easeOut'}}>
    <div className="panel-head"><h2><Activity size={15}/>Incoming alerts</h2><span>{simPhase==='streaming'?<><i className="pulse"/>Streaming</>:`${simAlerts.length} shown`}</span></div>
    <div className="alert-side-panel-list">{simAlerts.map(a=><LiveAlertItem a={a} key={a.id}/>)}</div>
    <div className="panel-foot"><span>Unclustered -- one row per raw alert · scroll for more</span></div>
  </motion.aside>
}

function IncidentPhase(){
  const {engineStatus,engineError,runEngine}=useOpsStore(useShallow(s=>({engineStatus:s.engineStatus,engineError:s.engineError,runEngine:s.runEngine})))
  const running=engineStatus==='running'
  return <motion.div key="incident" exit={{opacity:0}} transition={{duration:.5}}>
    <section className="panel run-nucleus-panel">
      <button className="run-nucleus-btn" disabled={running} onClick={()=>void runEngine()}>
        {running?<><Loader2 size={18} className="spin"/>Correlating alerts…</>:<><Play size={18}/>Run Nucleus</>}
      </button>
      <span>{running?'Grouping these 100 alerts into incidents and identifying root causes…':'Correlate this same 100-alert flood into root-cause incidents.'}</span>
      {engineError&&<span className="run-engine-error">{engineError}</span>}
    </section>
  </motion.div>
}

function IncidentRow({i,expanded,onToggle}:{i:EngineIncident;expanded:boolean;onToggle:()=>void}){
  const d=new Date(i.root_timestamp)
  return <>
    <div className={`table-row incident-row ${expanded?'expanded':''}`} onClick={onToggle}>
      <span className="incident-time-cell">{expanded?<ChevronDown size={13}/>:<ChevronRight size={13}/>}<code>{d.toLocaleDateString([],{month:'2-digit',day:'2-digit'})} {d.toLocaleTimeString([],{hour12:false})}</code></span>
      <b>{i.host}</b>
      <span>{i.root_metric}</span>
      <Severity value={i.severity.toLowerCase() as Alert['severity']}/>
      <span>{i.alert_count}</span>
      <span>{i.suppressed_count}</span>
      <code>{i.root_score.toFixed(2)}</code>
    </div>
    {expanded&&<div className="incident-members">
      {i.members.length===0
        ?<span className="sim-hint">No member-alert detail for this run.</span>
        :i.members.map(m=><div key={m.alert_id} className={`incident-member ${m.is_root?'root':''}`}>
          <Severity value={m.severity.toLowerCase() as Alert['severity']}/>
          <time>{new Date(m.timestamp).toLocaleTimeString([],{hour12:false})}</time>
          <b>{m.metric}</b>
          <span>{fmtMetric(m.metric,m.value)}</span>
          <code>{m.host}</code>
          {m.is_root&&<em>Root cause</em>}
        </div>)}
    </div>}
  </>
}

function RootCauseGraph({incident}:{incident:EngineIncident}){
  const members=incident.members
  const root=members.find(m=>m.is_root)??members[0]
  const symptoms=members.filter(m=>!m.is_root).slice(0,5)
  const [selectedId,setSelectedId]=useState(root?.alert_id??'incident')
  useEffect(()=>setSelectedId(root?.alert_id??'incident'),[incident.incident_id,root?.alert_id])
  const selected=members.find(m=>m.alert_id===selectedId)
  const symptomY=(index:number)=>symptoms.length===1?50:14+(index*(72/Math.max(1,symptoms.length-1)))
  const hidden=Math.max(0,incident.suppressed_count-symptoms.length)
  return <section className="panel root-graph-panel">
    <PanelHead title="Root-cause propagation" icon={<GitBranch size={15}/>} meta={<><i className="graph-live-dot"/>Incident #{incident.incident_id} · click any node</>}/>
    <div className="root-graph-stage">
      <svg className="root-graph-edges" viewBox="0 0 1000 320" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="root-path" x1="0" x2="1"><stop stopColor="#ff5c72"/><stop offset="1" stopColor="#5b9dff"/></linearGradient></defs>
        <path d="M 215 160 C 300 160, 340 160, 435 160" className="graph-edge root-edge"/>
        {symptoms.map((m,index)=><path key={m.alert_id} d={`M 565 160 C 650 160, 650 ${symptomY(index)*3.2}, 775 ${symptomY(index)*3.2}`} className="graph-edge symptom-edge"/>)}
      </svg>
      {root&&<button className={`graph-node graph-root ${selectedId===root.alert_id?'selected':''}`} style={{left:'14%',top:'50%'}} onClick={()=>setSelectedId(root.alert_id)}>
        <span className="graph-node-kicker">ROOT CAUSE</span><b>{root.metric}</b><code>{root.host}</code><em>{root.root_score.toFixed(2)} confidence</em>
      </button>}
      <button className={`graph-node graph-hub ${selectedId==='incident'?'selected':''}`} style={{left:'43.5%',top:'50%'}} onClick={()=>setSelectedId('incident')}>
        <span className="graph-node-kicker">CORRELATED</span><b>Incident #{incident.incident_id}</b><code>{incident.alert_count} alerts</code><em>{incident.suppressed_count} suppressed</em>
      </button>
      {symptoms.map((m,index)=><button key={m.alert_id} className={`graph-node graph-symptom ${selectedId===m.alert_id?'selected':''}`} style={{left:'77.5%',top:`${symptomY(index)}%`}} onClick={()=>setSelectedId(m.alert_id)}>
        <span className="graph-node-kicker">SYMPTOM</span><b>{m.metric}</b><code>{new Date(m.timestamp).toLocaleTimeString([],{hour12:false})}</code>
      </button>)}
      {hidden>0&&<span className="graph-hidden-count">+{hidden} more suppressed alerts</span>}
    </div>
    <div className="graph-evidence">
      <div><span>Selected evidence</span><b>{selected?selected.is_root?'Root-cause alert':'Correlated symptom':`Incident #${incident.incident_id}`}</b></div>
      <div><span>Host</span><code>{selected?.host??incident.host}</code></div>
      <div><span>Metric</span><b>{selected?.metric??incident.root_metric}</b></div>
      <div><span>Observed value</span><b>{selected?fmtMetric(selected.metric,selected.value):incident.alert_count}</b></div>
      <div><span>Confidence</span><b className="good">{selected?selected.root_score.toFixed(2):incident.root_score.toFixed(2)}</b></div>
      <div><span>Detected</span><code>{new Date(selected?.timestamp??incident.root_timestamp).toLocaleTimeString([],{hour12:false})}</code></div>
    </div>
  </section>
}

const metricName=(metric:string)=>metric==='MEM_real_util'?'memory utilization':metric==='CPU_util_pct'?'CPU utilization':metric==='Sess_Connect'?'database sessions':metric.replaceAll('_',' ').toLowerCase()
function remediationFor(metric:string,host:string){
  if(metric==='MEM_real_util')return [`Inspect top memory-consuming processes on ${host}.`,`Check for memory leaks or a recent workload spike.`,`Reclaim memory or scale the host after validating impact.`]
  if(metric==='CPU_util_pct')return [`Inspect top CPU-consuming processes on ${host}.`,`Compare load with recent deployments and scheduled jobs.`,`Throttle the offending workload or scale compute capacity.`]
  if(metric==='Sess_Connect')return [`Inspect active and blocked sessions on ${host}.`,`Identify connection leaks or long-running queries.`,`Terminate unsafe sessions only after validating application impact.`]
  return [`Inspect ${metricName(metric)} telemetry on ${host}.`,`Compare the first alert with recent changes and dependencies.`,`Validate recovery before closing the incident.`]
}
function IncidentCopilot({incident}:{incident:EngineIncident}){
  const [question,setQuestion]=useState<CopilotQuestion>('cause')
  const [copilot,setCopilot]=useState<CopilotResponse|null>(null)
  const [loading,setLoading]=useState(false)
  const [usingFallback,setUsingFallback]=useState(false)
  const root=incident.members.find(m=>m.is_root)??incident.members[0]
  const first=new Date(root?.timestamp??incident.root_timestamp)
  const last=new Date(incident.members.at(-1)?.timestamp??incident.root_timestamp)
  const duration=Math.max(0,Math.round((last.getTime()-first.getTime())/1000))
  const metric=metricName(incident.root_metric)
  const fallbackActions=remediationFor(incident.root_metric,incident.host)
  const answers:Record<CopilotQuestion,string>={
    cause:`${incident.host} is the most likely origin. Its ${metric} alert appeared first at ${first.toLocaleTimeString([],{hour12:false})} and received the highest root-cause score (${incident.root_score.toFixed(2)}).`,
    evidence:`Nucleus correlated ${incident.alert_count} alerts on ${incident.host} over ${duration} seconds. ${incident.suppressed_count} later alerts matched the incident's host, source, timing, severity and metric pattern.`,
    action:`Start by checking ${metric} on ${incident.host}. ${fallbackActions[0]} Then validate whether the remaining ${incident.suppressed_count} symptoms stop before closing the incident.`,
  }
  const ask=(nextQuestion:CopilotQuestion)=>{
    setQuestion(nextQuestion);setLoading(true);setCopilot(null);setUsingFallback(false)
    void askIncidentCopilot(incident,nextQuestion).then(result=>setCopilot(result)).catch(()=>setUsingFallback(true)).finally(()=>setLoading(false))
  }
  useEffect(()=>{
    let active=true
    setQuestion('cause');setLoading(true);setCopilot(null);setUsingFallback(false)
    void askIncidentCopilot(incident,'cause').then(result=>{if(active)setCopilot(result)}).catch(()=>{if(active)setUsingFallback(true)}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false}
  },[incident])
  const actions=copilot?.actions??fallbackActions
  return <section className="panel copilot-panel">
    <PanelHead title="Nucleus Incident Copilot" icon={<Bot size={16}/>} meta={<span className={`copilot-grounded ${usingFallback?'fallback':''}`}>{loading?<><Loader2 size={12} className="spin"/>Groq is analysing…</>:copilot?<><CheckCircle2 size={12}/>Groq · {copilot.model}</>:<><CheckCircle2 size={12}/>Evidence fallback</>}</span>}/>
    <div className="copilot-body">
      <div className="copilot-summary">
        <div className="copilot-avatar"><Bot size={20}/></div>
        <div><span className="copilot-label">INCIDENT BRIEF · #{incident.incident_id}</span><p>{copilot?.summary?? <><b>{incident.severity} {metric}</b> on <code>{incident.host}</code> is the probable root cause. It triggered {incident.alert_count-1} correlated symptoms over {duration} seconds; Nucleus suppressed {incident.suppressed_count} duplicate alerts with <strong>{Math.round(incident.root_score*100)}% confidence</strong>.</>}</p></div>
      </div>
      <div className="copilot-columns">
        <div className="copilot-why"><h3><MessageSquare size={14}/>Ask about this incident</h3><div className="copilot-prompts">
          <button disabled={loading} className={question==='cause'?'active':''} onClick={()=>ask('cause')}>What caused this?</button>
          <button disabled={loading} className={question==='evidence'?'active':''} onClick={()=>ask('evidence')}>Show the evidence</button>
          <button disabled={loading} className={question==='action'?'active':''} onClick={()=>ask('action')}>What should I do?</button>
        </div><motion.div key={`${incident.incident_id}-${question}-${loading}`} className="copilot-answer" initial={{opacity:0,y:4}} animate={{opacity:1,y:0}}>{loading?<Loader2 size={15} className="spin"/>:<Bot size={15}/>}<p>{loading?'Analysing the correlated alert evidence…':copilot?.answer??answers[question]}</p></motion.div></div>
        <div className="copilot-actions"><h3><Wrench size={14}/>Recommended response</h3><ol>{actions.map((action,index)=><li key={action}><span>{index+1}</span><p>{action}</p></li>)}</ol></div>
      </div>
    </div>
    <div className="copilot-foot"><span>Evidence used</span><code>{incident.root_alert_id.slice(0,8)}…</code><i/>First signal {first.toLocaleTimeString([],{hour12:false})}<i/>{incident.alert_count} correlated alerts<i/>{incident.root_score.toFixed(2)} root score</div>
  </section>
}

function IncidentCommandCenter({result}:{result:EngineResult}){
  const [replayKey,setReplayKey]=useState(0)
  const [progress,setProgress]=useState(0)
  useEffect(()=>{
    setProgress(0)
    const started=performance.now()
    const timer=setInterval(()=>{
      const next=Math.min(100,((performance.now()-started)/1200)*100)
      setProgress(next)
      if(next>=100)clearInterval(timer)
    },30)
    return()=>clearInterval(timer)
  },[replayKey])
  const m=result.metrics
  const estimatedMinutes=Math.max(0,Math.round((m.raw_count*45-m.incident_count*90)/60))
  const shownIncidents=result.incidents.slice(0,4)
  return <section className="panel command-center-panel">
    <PanelHead title="Live Incident Command Center" icon={<Activity size={15}/>} meta={<><i className="command-live-dot"/>Reduction complete <button className="command-replay" onClick={()=>setReplayKey(k=>k+1)}><RotateCcw size={11}/>Replay</button></>}/>
    <div className="command-compare">
      <div className="command-side command-before">
        <div className="command-side-head"><div><span>WITHOUT NUCLEUS</span><b>Alert flood</b></div><strong>{m.raw_count}</strong></div>
        <div className="flood-stack">{Array.from({length:12},(_,index)=><motion.div key={`${replayKey}-${index}`} className={`flood-alert ${index%4===0?'warning':''}`} animate={{opacity:progress>index*7?.22:1,x:progress>index*7?-10:0}} transition={{duration:.22}}><i/><span>{index%3===0?'CPU threshold exceeded':index%3===1?'Memory utilization critical':'Session count anomaly'}</span><code>#{String(index+1).padStart(2,'0')}</code></motion.div>)}</div>
        <p>Every alert demands attention. Symptoms and causes look identical.</p>
      </div>
      <div className="command-transform">
        <div className="command-ring" style={{'--progress':`${progress*3.6}deg`} as React.CSSProperties}><Zap size={18}/></div>
        <ArrowRight size={18}/><b>{Math.round(progress)}%</b><span>correlated</span>
      </div>
      <div className="command-side command-after">
        <div className="command-side-head"><div><span>WITH NUCLEUS</span><b>Actionable incidents</b></div><strong>{progress>=96?m.incident_count:'—'}</strong></div>
        <div className="command-incidents">{shownIncidents.map((incident,index)=><motion.div key={`${replayKey}-${incident.incident_id}`} className="command-incident" initial={{opacity:0,x:12}} animate={{opacity:progress>45+index*11?1:0,x:progress>45+index*11?0:12}}><span className={`command-severity ${incident.severity.toLowerCase()}`}/><div><b>{incident.root_metric}</b><code>{incident.host}</code></div><em>{incident.alert_count}→1</em></motion.div>)}</div>
        <p>Root causes are ranked; duplicate symptoms are automatically suppressed.</p>
      </div>
    </div>
    <div className="command-impact">
      <div><span>Noise removed</span><b>{m.reduction_pct.toFixed(1)}%</b></div>
      <div><span>Alerts suppressed</span><b>{m.suppressed_count}</b></div>
      <div><span>Compression</span><b>{(m.raw_count/m.incident_count).toFixed(1)}×</b></div>
      <div title="Illustrative estimate: 45 seconds per raw alert versus 90 seconds per correlated incident"><span><Timer size={11}/>Estimated triage saved</span><b>~{estimatedMinutes} min</b><small>illustrative estimate</small></div>
    </div>
  </section>
}
function ResolvedPhase(){
  const {engineResult,reset}=useOpsStore(useShallow(s=>({engineResult:s.engineResult,reset:s.reset})))
  const initialIncident=engineResult?.incidents.reduce((best,current)=>current.alert_count>best.alert_count?current:best,engineResult.incidents[0])
  const [expandedId,setExpandedId]=useState<number|null>(initialIncident?.incident_id??null)
  const selectedIncident=engineResult?.incidents.find(i=>i.incident_id===expandedId)??initialIncident
  const ref=useRef<HTMLDivElement>(null)
  useEffect(()=>{ref.current?.scrollIntoView({behavior:'smooth',block:'start'})},[])
  if(!engineResult)return null
  return <motion.div key="resolved" ref={ref} initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{duration:.5,delay:.15}}>
    <IncidentCommandCenter result={engineResult}/>
    {selectedIncident&&<RootCauseGraph incident={selectedIncident}/>}
    {selectedIncident&&<IncidentCopilot incident={selectedIncident}/>}
    <section className="panel">
      <PanelHead title="Incidents" icon={<Network size={15}/>} meta={<>{engineResult.incidents.length} incidents <button className="back-to-monitoring" onClick={()=>reset()}><RotateCcw size={12}/>Back to monitoring</button></>}/>
      <div className="table-panel engine-incidents-table">
        <div className="table-head"><span>TIME</span><span>HOST</span><span>METRIC</span><span>SEVERITY</span><span>ALERTS</span><span>SUPPRESSED</span><span>ROOT SCORE</span></div>
        <div className="engine-table-body">{engineResult.incidents.map(i=><IncidentRow key={i.incident_id} i={i} expanded={expandedId===i.incident_id} onToggle={()=>setExpandedId(id=>id===i.incident_id?null:i.incident_id)}/>)}</div>
      </div>
    </section>
  </motion.div>
}

function AiopsFullView(){
  const {simPhase,engineResult}=useOpsStore(useShallow(s=>({simPhase:s.simPhase,engineResult:s.engineResult})))
  const opsState:OpsState=engineResult?'resolved':simPhase!=='idle'?'incident':'healthy'
  return <>
    <div className="page-title compact"><div><span>NUCLEUS</span><h1>Operations Center</h1></div></div>
    <OperationsHealth opsState={opsState}/>
    <AnimatePresence mode="wait">
      {opsState==='incident'&&<IncidentPhase/>}
    </AnimatePresence>
    <ClusterCards opsState={opsState}/>
    <ParameterCards opsState={opsState}/>
    <HostGrid opsState={opsState}/>
    <AnimatePresence mode="wait">
      {opsState==='resolved'&&<ResolvedPhase/>}
    </AnimatePresence>
  </>
}
const SIZE_LABEL:Record<DemoSize,string>={100:'100',1000:'1,000',10000:'10,000',100000:'100,000'}
function BenchmarkCard({size}:{size:DemoSize}){
  const entry=useOpsStore(s=>s.benchmarks[size])
  const runBenchmark=useOpsStore(s=>s.runBenchmark)
  const running=entry.status==='running'
  return <div className={`bench-card ${entry.status}`}>
    <div className="bench-card-head">
      <b>{SIZE_LABEL[size]} alerts</b>
      <button className="run-engine-btn secondary" disabled={running} onClick={()=>void runBenchmark(size)}>
        {running?<><Loader2 size={14} className="spin"/>Running…</>:<><Play size={14}/>Run</>}
      </button>
    </div>
    {entry.status==='done'&&entry.result&&<div className="bench-card-body">
      <div><span>Incidents</span><b>{entry.result.metrics.incident_count.toLocaleString()}</b></div>
      <div><span>Reduction</span><b className="good">{entry.result.metrics.reduction_pct.toFixed(2)}%</b></div>
      <div><span>Suppressed</span><b>{entry.result.metrics.suppressed_count.toLocaleString()}</b></div>
      <div><span>Time</span><b>{((entry.elapsedMs??0)/1000).toFixed(2)}s</b></div>
      <div><span>Avg incident size</span><b>{(entry.result.metrics.raw_count/entry.result.metrics.incident_count).toFixed(1)}</b></div>
      <div><span>Throughput</span><b>{Math.round(entry.result.metrics.raw_count/((entry.elapsedMs??1)/1000)).toLocaleString()}/s</b></div>
    </div>}
    {entry.status==='error'&&<span className="run-engine-error">{entry.error}</span>}
    {entry.status==='idle'&&<span className="sim-hint">Not run yet.</span>}
    {running&&<span className="sim-hint">{size>=100000?'~45s on this machine -- a contiguous slice this size is denser than the full dataset.':size>=10000?'~4-5s…':'a moment…'}</span>}
  </div>
}
function ScaleChart(){
  const benchmarks=useOpsStore(s=>s.benchmarks)
  const points=DEMO_SIZES.map(sz=>({size:sz,entry:benchmarks[sz]})).filter(p=>p.entry.status==='done'&&p.entry.result)
  const running=DEMO_SIZES.find(size=>benchmarks[size].status==='running')
  const [selectedSize,setSelectedSize]=useState<DemoSize>(100)
  const seenSizes=useRef(new Set<DemoSize>())
  useEffect(()=>{
    const newlyCompleted=points.find(point=>!seenSizes.current.has(point.size))
    if(newlyCompleted)setSelectedSize(newlyCompleted.size)
    seenSizes.current=new Set(points.map(point=>point.size))
  },[points])
  if(points.length===0&&!running)return null
  const selected=points.find(point=>point.size===selectedSize)??points.at(-1)
  const w=760,h=290,padL=52,padR=24,padT=28,padB=42
  const plotW=w-padL-padR,plotH=h-padT-padB
  const xMin=Math.log10(100),xMax=Math.log10(100000)
  const xPos=(size:number)=>padL+((Math.log10(size)-xMin)/(xMax-xMin))*plotW
  const yPos=(pct:number)=>padT+((100-Math.max(75,pct))/25)*plotH
  const gridY=[75,80,85,90,95,100]
  const linePath=points.map((p,index)=>`${index===0?'M':'L'} ${xPos(p.size)} ${yPos(p.entry.result!.metrics.reduction_pct)}`).join(' ')
  const areaPath=points.length?`${linePath} L ${xPos(points.at(-1)!.size)} ${h-padB} L ${xPos(points[0].size)} ${h-padB} Z`:''
  const selectedResult=selected?.entry.result
  const throughput=selectedResult?Math.round(selectedResult.metrics.raw_count/((selected.entry.elapsedMs??1)/1000)):0
  const compression=selectedResult?selectedResult.metrics.raw_count/selectedResult.metrics.incident_count:0
  return <section className="panel benchmark-intelligence">
    <PanelHead title="Engine scaling intelligence" icon={<GitCompare size={15}/>} meta={<>{running?<><i className="benchmark-live-dot"/>Processing {SIZE_LABEL[running]} alerts</>:<><CheckCircle2 size={12}/>{points.length} of {DEMO_SIZES.length} scales measured</>}</>}/>
    <div className="benchmark-visual">
      <div className="scale-chart">
        <div className="chart-title"><div><span>NOISE REDUCTION CURVE</span><b>Performance improves as alert density grows</b></div><em>Higher is better</em></div>
        <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet">
          <defs><linearGradient id="chart-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1fd88f" stopOpacity=".28"/><stop offset="1" stopColor="#1fd88f" stopOpacity="0"/></linearGradient><filter id="point-glow"><feGaussianBlur stdDeviation="5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
          {gridY.map(g=><g key={g}><line x1={padL} x2={w-padR} y1={yPos(g)} y2={yPos(g)} className="chart-grid"/><text x={padL-10} y={yPos(g)+4} textAnchor="end" className="chart-axis-label">{g}%</text></g>)}
          {DEMO_SIZES.map(sz=><g key={sz}><line x1={xPos(sz)} x2={xPos(sz)} y1={padT} y2={h-padB} className="chart-grid vertical"/><text x={xPos(sz)} y={h-padB+25} textAnchor="middle" className="chart-axis-label">{SIZE_LABEL[sz]}</text></g>)}
          {areaPath&&<motion.path key={`area-${points.length}`} d={areaPath} fill="url(#chart-area)" initial={{opacity:0}} animate={{opacity:1}} transition={{duration:.7}}/>}
          {linePath&&<motion.path key={`line-${points.length}`} d={linePath} fill="none" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" initial={{pathLength:0}} animate={{pathLength:1}} transition={{duration:.8,ease:'easeOut'}}/>}
          {points.map(p=>{const pct=p.entry.result!.metrics.reduction_pct,isSelected=p.size===selected?.size;return <g key={p.size} className="chart-point" onClick={()=>setSelectedSize(p.size)}>
            <line x1={xPos(p.size)} x2={xPos(p.size)} y1={yPos(pct)} y2={h-padB} className="chart-stem"/>{isSelected&&<circle cx={xPos(p.size)} cy={yPos(pct)} r="14" className="chart-point-halo"/>}<circle cx={xPos(p.size)} cy={yPos(pct)} r={isSelected?7:5} className={isSelected?'selected':''} filter={isSelected?'url(#point-glow)':undefined}/><text x={xPos(p.size)} y={yPos(pct)-16} textAnchor="middle" className="chart-point-label">{pct.toFixed(2)}%</text>
          </g>})}
          {running&&<g className="chart-running" transform={`translate(${xPos(running)} ${h-padB-18})`}><circle r="7"/><circle r="14"/><text y="-17" textAnchor="middle">RUNNING</text></g>}
        </svg>
      </div>
      <aside className="benchmark-spotlight">{selected&&selectedResult?<motion.div key={selected.size} initial={{opacity:0,x:8}} animate={{opacity:1,x:0}}><span className="spotlight-kicker">SELECTED RUN</span><h3>{SIZE_LABEL[selected.size]} <small>alerts</small></h3><div className="reduction-ring" style={{'--reduction':`${selectedResult.metrics.reduction_pct*3.6}deg`} as React.CSSProperties}><div><b>{selectedResult.metrics.reduction_pct.toFixed(1)}%</b><span>reduced</span></div></div><div className="spotlight-stats"><div><span>Incidents</span><b>{selectedResult.metrics.incident_count.toLocaleString()}</b></div><div><span>Compression</span><b>{compression.toFixed(1)}×</b></div><div><span>Throughput</span><b>{throughput.toLocaleString()}<small>/s</small></b></div><div><span>Runtime</span><b>{((selected.entry.elapsedMs??0)/1000).toFixed(2)}<small>s</small></b></div></div><p><Zap size={12}/>Nucleus converted every <b>{compression.toFixed(1)}</b> raw alerts into one actionable incident.</p></motion.div>:<div className="spotlight-wait"><Loader2 size={22} className="spin"/><b>Correlating alerts</b><span>The chart will populate when this run completes.</span></div>}</aside>
    </div>
    <div className="benchmark-scale-strip">{DEMO_SIZES.map(size=>{const entry=benchmarks[size],done=entry.status==='done';return <button key={size} disabled={!done} className={`${entry.status} ${selected?.size===size?'active':''}`} onClick={()=>setSelectedSize(size)}><span>{SIZE_LABEL[size]}</span><b>{done?`${entry.result!.metrics.reduction_pct.toFixed(1)}%`:entry.status==='running'?'Running…':'Not run'}</b><i/></button>})}</div>
  </section>
}
function BenchmarkView(){
  const benchmarks=useOpsStore(s=>s.benchmarks)
  const allDone=DEMO_SIZES.every(sz=>benchmarks[sz].status==='done')
  return <>
    <div className="page-title compact"><div><span>NUCLEUS</span><h1>Benchmark</h1><p>Run the real correlation engine on the same graduated, real dataset at four sizes and compare the results side by side.</p></div></div>
    <div className="card-grid bench-grid">{DEMO_SIZES.map(sz=><BenchmarkCard key={sz} size={sz}/>)}</div>
    <ScaleChart/>
    {allDone&&<section className="panel">
      <PanelHead title="Comparison" icon={<GitCompare size={15}/>} meta="all four sizes"/>
      <div className="table-panel bench-table">
        <div className="table-head"><span>SIZE</span><span>INCIDENTS</span><span>REDUCTION</span><span>SUPPRESSED</span><span>HOSTS</span><span>AVG SIZE</span><span>THROUGHPUT</span><span>TIME</span></div>
        {DEMO_SIZES.map(sz=>{const e=benchmarks[sz];if(!e.result)return null;return <div className="table-row" key={sz}>
          <b>{SIZE_LABEL[sz]}</b>
          <span>{e.result.metrics.incident_count.toLocaleString()}</span>
          <span className="good">{e.result.metrics.reduction_pct.toFixed(2)}%</span>
          <span>{e.result.metrics.suppressed_count.toLocaleString()}</span>
          <span>{e.result.metrics.host_count}</span>
          <span>{(e.result.metrics.raw_count/e.result.metrics.incident_count).toFixed(1)}</span>
          <span>{Math.round(e.result.metrics.raw_count/((e.elapsedMs??1)/1000)).toLocaleString()}/s</span>
          <code>{((e.elapsedMs??0)/1000).toFixed(2)}s</code>
        </div>})}
      </div>
    </section>}
  </>
}
function FullDatasetView(){
  const {aiopsSummary,fullRunStatus,fullRunResult,fullRunElapsedMs,fullRunError,runFullDataset}=useOpsStore(useShallow(s=>({aiopsSummary:s.aiopsSummary,fullRunStatus:s.fullRunStatus,fullRunResult:s.fullRunResult,fullRunElapsedMs:s.fullRunElapsedMs,fullRunError:s.fullRunError,runFullDataset:s.runFullDataset})))
  const [expandedId,setExpandedId]=useState<number|null>(null)
  const running=fullRunStatus==='running'
  const m=fullRunResult?.metrics
  return <>
    <div className="page-title compact"><div><span>NUCLEUS</span><h1>AIOps Dataset</h1><p>Run the real correlation engine over the entire real AIOps2020 dataset -- every alert, not a demo slice -- and see the full reduction.</p></div></div>
    <section className="panel run-engine-panel">
      <PanelHead title="Full dataset run" icon={<HardDrive size={15}/>} meta={aiopsSummary?`${aiopsSummary.raw_count.toLocaleString()} real alerts · ${aiopsSummary.host_count} hosts`:'loading dataset…'}/>
      <div className="run-engine-body">
        <button className="run-engine-btn" disabled={running||!aiopsSummary} onClick={()=>void runFullDataset()}>
          {running?<><Loader2 size={15} className="spin"/>Correlating {aiopsSummary?.raw_count.toLocaleString()} alerts…</>:<><Play size={15}/>Run on full dataset</>}
        </button>
        <span className="sim-hint">{running?'Same engine, every real alert in the dataset -- typically 60-90s depending on machine.':'Correlates the complete real dataset (not a fixed demo slice) into root-cause incidents.'}</span>
      </div>
      {fullRunError&&<span className="run-engine-error">{fullRunError}</span>}
    </section>
    {fullRunResult&&m&&<>
      <div className="card-grid">
        <div className="stat-card ok"><span className="icon-badge"><Layers size={19}/></span><div><span>Raw alerts</span><b>{m.raw_count.toLocaleString()}</b></div></div>
        <div className="stat-card ok"><span className="icon-badge"><Network size={19}/></span><div><span>Incidents</span><b>{m.incident_count.toLocaleString()}</b></div></div>
        <div className="stat-card ok"><span className="icon-badge"><ShieldCheck size={19}/></span><div><span>Suppressed</span><b>{m.suppressed_count.toLocaleString()}</b></div></div>
        <div className="stat-card ok"><span className="icon-badge"><GitCompare size={19}/></span><div><span>Reduction</span><b>{m.reduction_pct.toFixed(2)}%</b></div></div>
      </div>
      <section className="panel">
        <PanelHead title="Incidents" icon={<Network size={15}/>} meta={<>{fullRunResult.incidents.length.toLocaleString()} incidents · {((fullRunElapsedMs??0)/1000).toFixed(1)}s</>}/>
        <div className="table-panel engine-incidents-table">
          <div className="table-head"><span>TIME</span><span>HOST</span><span>METRIC</span><span>SEVERITY</span><span>ALERTS</span><span>SUPPRESSED</span><span>ROOT SCORE</span></div>
          <div className="engine-table-body">{fullRunResult.incidents.map(i=><IncidentRow key={i.incident_id} i={i} expanded={expandedId===i.incident_id} onToggle={()=>setExpandedId(id=>id===i.incident_id?null:i.incident_id)}/>)}</div>
        </div>
      </section>
    </>}
  </>
}
function App(){
  const {dark,view,simPhase,sidebarOpen,rightPanelVisible,loadAiopsSummary,jitterBaseline}=useOpsStore(useShallow(s=>({dark:s.dark,view:s.view,simPhase:s.simPhase,sidebarOpen:s.sidebarOpen,rightPanelVisible:s.rightPanelVisible,loadAiopsSummary:s.loadAiopsSummary,jitterBaseline:s.jitterBaseline})))
  useEffect(()=>{void loadAiopsSummary()},[loadAiopsSummary])
  useEffect(()=>{
    const resync=setInterval(()=>void loadAiopsSummary(),20000)
    const jitter=setInterval(()=>jitterBaseline(),2500)
    return()=>{clearInterval(resync);clearInterval(jitter)}
  },[loadAiopsSummary,jitterBaseline])
  const alertPanelOpen=view==='operations'&&simPhase!=='idle'&&rightPanelVisible
  return <div className={dark?'app dark':'app light'}>
    <Sidebar/>
    <div className={`shell ${sidebarOpen?'':'sidebar-closed'}`}>
      <Topbar/>
      <main className={alertPanelOpen?'panel-open':''}>{view==='benchmark'?<BenchmarkView/>:view==='dataset'?<FullDatasetView/>:<AiopsFullView/>}</main>
    </div>
    <AnimatePresence>{alertPanelOpen&&<LiveAlertPanel/>}</AnimatePresence>
  </div>
}
export default App
