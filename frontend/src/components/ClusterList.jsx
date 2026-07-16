import ClusterCard from "./ClusterCard";

export default function ClusterList({ clusters, loading }) {
  if (loading && clusters.length === 0) {
    return <p className="text-text-muted font-mono text-sm py-8 text-center">Loading clusters…</p>;
  }
  if (clusters.length === 0) {
    return (
      <p className="text-text-muted font-mono text-sm py-8 text-center">
        No clusters formed at these weights — try lowering gamma or beta.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {clusters.map((cluster) => (
        <ClusterCard key={cluster.cluster_id} cluster={cluster} />
      ))}
    </div>
  );
}
