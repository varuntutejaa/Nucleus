import {memo,useEffect,useRef,useState} from 'react'
import {AnimatePresence,motion} from 'framer-motion'
import {Activity,BarChart3,ChevronDown,ChevronRight,Cpu,Database,GitCompare,HardDrive,Layers,Loader2,MemoryStick,Menu,Network,PanelRight,Play,RotateCcw,Server,ShieldAlert,ShieldCheck,Sun,Moon,Zap} from 'lucide-react'
import {useShallow} from 'zustand/react/shallow'
import {lastOf,useOpsStore} from './store/useOpsStore'
import {DEMO_SIZES,type DemoSize,type EngineIncident} from './lib/api'
import {fmtTime,type Alert} from './lib/mockData'
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
  return <aside className={`sidebar ${sidebarOpen?'':'closed'}`}><div className="brand"><span><Network size={18}/></span><b>Nucleus</b></div><nav><button className={view==='operations'?'active':''} onClick={()=>setView('operations')}><Database size={17}/><span>Operations</span></button><button className={view==='benchmark'?'active':''} onClick={()=>setView('benchmark')}><GitCompare size={17}/><span>Compare scale</span></button><button className={view==='dataset'?'active':''} onClick={()=>setView('dataset')}><HardDrive size={17}/><span>AIOps Dataset</span></button></nav><div className="side-bottom"><div className="engine"><div><Zap size={14}/> Backend API</div><strong className={connected?'':'down'}><i/>{connected?'Connected':'Unreachable'}</strong><small>{connected?`${aiopsSummary.raw_count.toLocaleString()} alerts indexed`:engineError??'Retrying…'}</small>{syncedAgo!==null&&<small className="sync-line">Last sync: {syncedAgo===0?'just now':`${syncedAgo}s ago`}</small>}</div></div></aside>
}
function LiveClock(){const now=useNow(1000);return <div className="live-clock"><i/>{new Date(now).toLocaleTimeString([],{hour12:false})}</div>}
function Topbar(){
  const {dark,toggleTheme,view,aiopsSummary,simPhase,engineResult,simulate,sidebarOpen,toggleSidebar,rightPanelVisible,toggleRightPanel}=useOpsStore(useShallow(s=>({dark:s.dark,toggleTheme:s.toggleTheme,view:s.view,aiopsSummary:s.aiopsSummary,simPhase:s.simPhase,engineResult:s.engineResult,simulate:s.simulate,sidebarOpen:s.sidebarOpen,toggleSidebar:s.toggleSidebar,rightPanelVisible:s.rightPanelVisible,toggleRightPanel:s.toggleRightPanel})))
  const showSimulate=view==='operations'&&simPhase==='idle'&&!engineResult
  const showPanelToggle=view==='operations'&&simPhase!=='idle'
  return <header className="topbar">
    <div className="topbar-left">
      <button className="icon-btn" onClick={toggleSidebar} title={sidebarOpen?'Collapse sidebar':'Expand sidebar'}><Menu size={16}/></button>
      <div className="crumb"><span>Operations</span><ChevronRight size={14}/><b>Live monitoring</b></div>
    </div>
    <div className="top-actions">
      {showPanelToggle&&<button className={`icon-btn ${rightPanelVisible?'active-toggle':''}`} onClick={toggleRightPanel} title={rightPanelVisible?'Hide alert panel':'Show alert panel'}><PanelRight size={16}/></button>}
      {showSimulate&&<button className="simulate-btn icon-btn" disabled={!aiopsSummary} title="Simulate incoming alerts" onClick={()=>simulate()}><Activity size={15}/></button>}
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
function ResolvedPhase(){
  const {engineResult,reset}=useOpsStore(useShallow(s=>({engineResult:s.engineResult,reset:s.reset})))
  const [expandedId,setExpandedId]=useState<number|null>(null)
  const ref=useRef<HTMLDivElement>(null)
  useEffect(()=>{ref.current?.scrollIntoView({behavior:'smooth',block:'start'})},[])
  if(!engineResult)return null
  return <motion.div key="resolved" ref={ref} initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{duration:.5,delay:.15}}>
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
    </div>}
    {entry.status==='error'&&<span className="run-engine-error">{entry.error}</span>}
    {entry.status==='idle'&&<span className="sim-hint">Not run yet.</span>}
    {running&&<span className="sim-hint">{size>=100000?'~45s on this machine -- a contiguous slice this size is denser than the full dataset.':size>=10000?'~4-5s…':'a moment…'}</span>}
  </div>
}
function ScaleChart(){
  const benchmarks=useOpsStore(s=>s.benchmarks)
  const points=DEMO_SIZES.map(sz=>({size:sz,entry:benchmarks[sz]})).filter(p=>p.entry.status==='done'&&p.entry.result)
  if(points.length===0)return null
  const w=760,h=260,padL=48,padR=20,padT=20,padB=34
  const plotW=w-padL-padR,plotH=h-padT-padB
  const xMin=Math.log10(100),xMax=Math.log10(100000)
  const xPos=(size:number)=>padL+((Math.log10(size)-xMin)/(xMax-xMin))*plotW
  const yPos=(pct:number)=>padT+(1-pct/100)*plotH
  const gridY=[0,25,50,75,100]
  const line=points.map(p=>`${xPos(p.size)},${yPos(p.entry.result!.metrics.reduction_pct)}`).join(' ')
  return <section className="panel">
    <PanelHead title="Reduction vs. dataset size" icon={<GitCompare size={15}/>} meta={`${points.length} of ${DEMO_SIZES.length} sizes run`}/>
    <div className="scale-chart">
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet">
        {gridY.map(g=><line key={g} x1={padL} x2={w-padR} y1={yPos(g)} y2={yPos(g)} className="chart-grid"/>)}
        {gridY.map(g=><text key={g} x={padL-8} y={yPos(g)+4} textAnchor="end" className="chart-axis-label">{g}%</text>)}
        {DEMO_SIZES.map(sz=><text key={sz} x={xPos(sz)} y={h-padB+22} textAnchor="middle" className="chart-axis-label">{SIZE_LABEL[sz]}</text>)}
        {points.length>1&&<polyline points={line} fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>}
        {points.map(p=>{const pct=p.entry.result!.metrics.reduction_pct;return <g key={p.size}>
          <circle cx={xPos(p.size)} cy={yPos(pct)} r="4.5" fill="var(--green)" stroke="var(--panel)" strokeWidth="2"><title>{`${SIZE_LABEL[p.size]} alerts -> ${pct.toFixed(2)}% reduction`}</title></circle>
          <text x={xPos(p.size)} y={yPos(pct)-12} textAnchor="middle" className="chart-point-label">{pct.toFixed(1)}%</text>
        </g>})}
      </svg>
    </div>
  </section>
}
function BenchmarkView(){
  const benchmarks=useOpsStore(s=>s.benchmarks)
  const runBenchmark=useOpsStore(s=>s.runBenchmark)
  const anyRunning=DEMO_SIZES.some(sz=>benchmarks[sz].status==='running')
  const allDone=DEMO_SIZES.every(sz=>benchmarks[sz].status==='done')
  return <>
    <div className="page-title compact"><div><span>NUCLEUS</span><h1>Compare Scale</h1><p>Run the real correlation engine on the same graduated, real dataset at four sizes and compare the results side by side.</p></div></div>
    <section className="panel run-engine-panel">
      <PanelHead title="Run all sizes" icon={<Layers size={15}/>} meta="100 · 1,000 · 10,000 · 100,000 real contiguous alerts"/>
      <div className="run-engine-body">
        <button className="run-engine-btn" disabled={anyRunning} onClick={()=>DEMO_SIZES.forEach(sz=>void runBenchmark(sz))}>
          {anyRunning?<><Loader2 size={15} className="spin"/>Running…</>:<><Play size={15}/>Run all</>}
        </button>
        <span className="sim-hint">Each size runs independently -- click "Run" on a single card below, or "Run all" to fire all four at once. 100,000 alone takes ~45s locally.</span>
      </div>
    </section>
    <div className="card-grid bench-grid">{DEMO_SIZES.map(sz=><BenchmarkCard key={sz} size={sz}/>)}</div>
    <ScaleChart/>
    {allDone&&<section className="panel">
      <PanelHead title="Comparison" icon={<GitCompare size={15}/>} meta="all four sizes"/>
      <div className="table-panel bench-table">
        <div className="table-head"><span>SIZE</span><span>INCIDENTS</span><span>REDUCTION</span><span>SUPPRESSED</span><span>HOSTS</span><span>TIME</span></div>
        {DEMO_SIZES.map(sz=>{const e=benchmarks[sz];if(!e.result)return null;return <div className="table-row" key={sz}>
          <b>{SIZE_LABEL[sz]}</b>
          <span>{e.result.metrics.incident_count.toLocaleString()}</span>
          <span className="good">{e.result.metrics.reduction_pct.toFixed(2)}%</span>
          <span>{e.result.metrics.suppressed_count.toLocaleString()}</span>
          <span>{e.result.metrics.host_count}</span>
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
