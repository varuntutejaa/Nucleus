import { useEffect, useRef, useState } from "react";
import { fetchCorrelatedAlerts, fetchRawAlerts } from "./api";
import Header from "./components/Header";
import Hero from "./components/Hero";
import Controls from "./components/Controls";
import ClusterList from "./components/ClusterList";
import RawTable from "./components/RawTable";
import NoiseSection from "./components/NoiseSection";

// Mirrors app/config.py DEFAULT_ALPHA/BETA/GAMMA on the backend -- keep in
// sync if those change. Hardcoded rather than round-tripped on first load
// so the sliders render in their correct position immediately.
const DEFAULT_WEIGHTS = { alpha: 0.15, beta: 0.55, gamma: 0.3 };
const REPLAY_STEPS = 40;
const REPLAY_TICK_MS = 400;

export default function App() {
  const [view, setView] = useState("correlated");
  const [source, setSource] = useState("synthetic");
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [asOf, setAsOf] = useState(null);

  const [rawData, setRawData] = useState({ alerts: [], count: 0 });
  const [correlatedData, setCorrelatedData] = useState({ clusters: [], noise: [], metrics: null });
  const [rawLoading, setRawLoading] = useState(true);
  const [correlatedLoading, setCorrelatedLoading] = useState(true);
  const [backendOk, setBackendOk] = useState(true);

  const [timeRange, setTimeRange] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const replayTimer = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setRawLoading(true);
    fetchRawAlerts({ source, asOf })
      .then((data) => {
        if (cancelled) return;
        setRawData(data);
        setBackendOk(true);
        if (asOf == null && data.alerts.length > 0) {
          setTimeRange({
            min: data.alerts[0].timestamp_unix,
            max: data.alerts[data.alerts.length - 1].timestamp_unix,
          });
        }
      })
      .catch(() => !cancelled && setBackendOk(false))
      .finally(() => !cancelled && setRawLoading(false));
    return () => {
      cancelled = true;
    };
  }, [source, asOf]);

  useEffect(() => {
    let cancelled = false;
    setCorrelatedLoading(true);
    fetchCorrelatedAlerts({ source, ...weights, asOf })
      .then((data) => {
        if (cancelled) return;
        setCorrelatedData(data);
        setBackendOk(true);
      })
      .catch(() => !cancelled && setBackendOk(false))
      .finally(() => !cancelled && setCorrelatedLoading(false));
    return () => {
      cancelled = true;
    };
  }, [source, weights, asOf]);

  useEffect(() => {
    if (!isPlaying || !timeRange) return;
    const stepSize = (timeRange.max - timeRange.min) / REPLAY_STEPS;
    replayTimer.current = setInterval(() => {
      setAsOf((prev) => {
        const cursor = prev ?? timeRange.min;
        const next = cursor + stepSize;
        if (next >= timeRange.max) {
          setIsPlaying(false);
          return null; // land on the full, final dataset
        }
        return next;
      });
    }, REPLAY_TICK_MS);
    return () => clearInterval(replayTimer.current);
  }, [isPlaying, timeRange]);

  function toggleReplay() {
    if (isPlaying) {
      setIsPlaying(false);
      setAsOf(null);
    } else if (timeRange) {
      setAsOf(timeRange.min);
      setIsPlaying(true);
    }
  }

  function handleSourceChange(next) {
    setIsPlaying(false);
    setAsOf(null);
    setSource(next);
  }

  const progressPct =
    timeRange && asOf != null
      ? Math.min(100, Math.max(0, ((asOf - timeRange.min) / (timeRange.max - timeRange.min)) * 100))
      : 0;

  return (
    <div className="min-h-screen flex flex-col">
      <Header backendOk={backendOk} />
      <Hero metrics={correlatedData.metrics} loading={correlatedLoading} />
      <Controls
        view={view}
        onViewChange={setView}
        weights={weights}
        onWeightsChange={setWeights}
        source={source}
        onSourceChange={handleSourceChange}
        replay={{ isPlaying, onToggle: toggleReplay, progressPct }}
      />
      <main className="mx-auto max-w-7xl w-full px-4 sm:px-6 pb-16 flex-1">
        {view === "correlated" ? (
          <div className="flex flex-col gap-4">
            <ClusterList clusters={correlatedData.clusters} loading={correlatedLoading} />
            <NoiseSection noise={correlatedData.noise} />
          </div>
        ) : (
          <RawTable alerts={rawData.alerts} loading={rawLoading} />
        )}
      </main>
    </div>
  );
}
